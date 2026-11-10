#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai"]
# ///
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from google import genai

# Veo is shut down; video generation now goes through the Interactions API on Omni models.
# Newest first: a model can be listed but 404 on the Interactions endpoint while it rolls out.
MODELS = ("gemini-omni-1.2-flash", "gemini-omni-1.1-flash", "gemini-omni-flash-preview")
MIN_DURATION, MAX_DURATION = 3, 15
MAX_IMAGES = 6
REQUEST_TIMEOUT_SECONDS = 600


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


def image_part(image_path: str) -> dict:
    ext = Path(image_path).suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    data = base64.b64encode(Path(image_path).read_bytes()).decode()
    return {"type": "image", "data": data, "mime_type": mime}


def validate_duration(seconds: int) -> str:
    if not MIN_DURATION <= seconds <= MAX_DURATION:
        print(f"Error: --duration must be between {MIN_DURATION} and {MAX_DURATION} seconds.", file=sys.stderr)
        sys.exit(1)
    return f"{seconds}s"


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


def generate_video(
    prompt: str,
    image_paths: list[str],
    output: str | None,
    duration: int | None = None,
    resolution: str | None = None,
    aspect_ratio: str | None = None,
) -> Path:
    print(f"Prompt: {prompt}")

    response_format: dict = {"type": "video"}
    if duration:
        response_format["duration"] = validate_duration(duration)
    if resolution:
        response_format["resolution"] = resolution
    if aspect_ratio:
        response_format["aspect_ratio"] = aspect_ratio

    if image_paths:
        print(f"Mode: image-guided ({len(image_paths)} image(s))")
        contents = [image_part(p) for p in image_paths] + [{"type": "text", "text": prompt}]
    else:
        contents = prompt

    client = genai.Client(api_key=get_api_key())
    print("Generating (can take a minute or more)...", flush=True)
    interaction, model = None, None
    for model in MODELS:
        try:
            interaction = client.interactions.create(
                model=model,
                input=contents,
                response_format=response_format,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            break
        except Exception as e:
            if getattr(e, "status_code", None) != 404 or model == MODELS[-1]:
                raise
            print(f"{model} not available, trying next model...", flush=True)

    video = interaction.output_video
    if video is None or not video.data:
        print("Error: no video data in response", file=sys.stderr)
        sys.exit(1)

    if output:
        out_path = Path(output)
    else:
        stem = slugify(prompt)
        out_path = unique_path(str(Path.cwd() / stem), ".mp4")
    out_path.write_bytes(base64.b64decode(video.data))

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
    parser.add_argument("--image", action="append", default=[], help=f"Reference image to guide the video (repeatable, up to {MAX_IMAGES})")
    parser.add_argument("--duration", type=int, help=f"Clip duration in seconds ({MIN_DURATION}-{MAX_DURATION}, default 10)")
    parser.add_argument("--resolution", choices=["360p", "720p", "1080p", "4k"], help="Output resolution (default 720p)")
    parser.add_argument("--aspect-ratio", choices=["16:9", "9:16"], help="Aspect ratio (default 16:9)")
    parser.add_argument("--output", help="Output filename (overrides auto-generated name)")
    args = parser.parse_args()

    if len(args.image) > MAX_IMAGES:
        print(f"Error: at most {MAX_IMAGES} --image values are supported.", file=sys.stderr)
        sys.exit(1)

    generate_video(
        prompt=args.prompt,
        image_paths=args.image,
        output=args.output,
        duration=args.duration,
        resolution=args.resolution,
        aspect_ratio=args.aspect_ratio,
    )


if __name__ == "__main__":
    main()
