#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

TIER_MODELS = {
    "lite": "veo-3.1-lite-generate-preview",
    "fast": "veo-3.1-fast-generate-preview",
    "standard": "veo-3.1-generate-preview",
}


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:max_len].rstrip("-")


def unique_path(stem: str, suffix: str) -> Path:
    path = Path(f"{stem}{suffix}")
    if not path.exists():
        return path
    counter = 2
    while True:
        path = Path(f"{stem}-{counter}{suffix}")
        if not path.exists():
            return path
        counter += 1


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return key


def load_image(image_path: str) -> types.Image:
    image_bytes = Path(image_path).read_bytes()
    ext = Path(image_path).suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/jpeg")
    return types.Image(image_bytes=image_bytes, mime_type=mime)


def probe_video(path: Path) -> dict:
    info = {"duration_seconds": None, "resolution": None}
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return info
    try:
        out = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(out.stdout)
        fmt = data.get("format", {})
        if fmt.get("duration"):
            info["duration_seconds"] = round(float(fmt["duration"]), 1)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                w, h = stream.get("width"), stream.get("height")
                if w and h:
                    info["resolution"] = f"{w}x{h}"
                break
    except Exception:
        pass
    return info


def generate_video(prompt: str, image_path: str | None, reference_path: str | None, output: str | None, duration: int | None = None, tier: str = "lite") -> Path:
    print(f"Prompt: {prompt}")
    model = TIER_MODELS[tier]
    print(f"Tier: {tier} ({model})")
    client = genai.Client(api_key=get_api_key())

    kwargs: dict = {"model": model, "prompt": prompt}
    if reference_path:
        print("Mode: subject reference (--reference)")
        kwargs["config"] = types.GenerateVideosConfig(
            reference_images=[
                types.VideoGenerationReferenceImage(
                    image=load_image(reference_path),
                    reference_type=types.VideoGenerationReferenceType.ASSET,
                )
            ],
            person_generation="allow_adult",
            duration_seconds=duration,
        )
    elif image_path:
        print("Mode: image-to-video frame 0 (--image)")
        kwargs["image"] = load_image(image_path)
        if duration:
            kwargs["config"] = types.GenerateVideosConfig(duration_seconds=duration)

    operation = client.models.generate_videos(**kwargs)

    start = time.time()
    while not operation.done:
        elapsed = int(time.time() - start)
        print(f"Generating... {elapsed}s elapsed", flush=True)
        time.sleep(10)
        operation = client.operations.get(operation)

    video = operation.response.generated_videos[0].video

    if output:
        out_path = Path(output)
    else:
        stem = slugify(prompt)
        out_path = unique_path(str(Path.cwd() / stem), ".mp4")

    if video.video_bytes:
        out_path.write_bytes(video.video_bytes)
    elif video.uri:
        import urllib.request
        api_key = get_api_key()
        url = video.uri if "key=" in video.uri else f"{video.uri}&key={api_key}"
        urllib.request.urlretrieve(url, out_path)
    else:
        print("Error: no video data in response", file=sys.stderr)
        sys.exit(1)

    filesize = out_path.stat().st_size
    info = probe_video(out_path)
    print(f"Saved: {out_path}")
    print(f"Model: {model}")
    print(f"Duration: {info['duration_seconds']}s" if info["duration_seconds"] else "Duration: unknown")
    print(f"Resolution: {info['resolution']}" if info["resolution"] else "Resolution: unknown")
    print(f"File size: {filesize / (1024 * 1024):.2f} MB")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Gemini video generation tool")
    parser.add_argument("--prompt", required=True, help="Text prompt describing the video")
    parser.add_argument("--image", help="Image used as frame 0 (image-to-video)")
    parser.add_argument("--reference", help="Image used as subject reference (ASSET mode)")
    parser.add_argument("--duration", type=int, help="Clip duration in seconds (e.g. 5)")
    parser.add_argument("--output", help="Output filename (overrides auto-generated name)")
    parser.add_argument("--tier", choices=list(TIER_MODELS), default="lite", help="Veo quality tier: lite (default), fast, standard")
    args = parser.parse_args()

    if args.image and args.reference:
        print("Error: --image and --reference are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    generate_video(prompt=args.prompt, image_path=args.image, reference_path=args.reference, output=args.output, duration=args.duration, tier=args.tier)


if __name__ == "__main__":
    main()
