#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai", "rembg[cpu]"]
# ///
import argparse
import io
import os
import re
import sys
from pathlib import Path

from google import genai
from google.genai import types

# Imagen is shut down; image generation now goes through generate_content on Nano Banana models.
IMAGE_MODEL = "gemini-nano-banana-2.1"
TEXT_MODEL = "gemini-3.8-flash"

# Keywords that signal the user wants a transparent background
_TRANSPARENT_KEYWORDS = [
    "transparent background", "transparent bg", "no background", "no bg",
    "clear background", "clear bg", "cutout", "remove background",
    "background removed", "background-free", "isolated background",
    "png transparent",
]

# Subjects that clash with green chroma key → use magenta instead
_GREEN_CLASH = [
    "plant", "tree", "leaf", "grass", "frog", "lizard", "dinosaur",
    "jungle", "forest", "green", "succulent", "cactus", "hedge",
]


def _wants_transparent(prompt: str) -> bool:
    lower = prompt.lower()
    return any(kw in lower for kw in _TRANSPARENT_KEYWORDS)


def _pick_chroma(prompt: str) -> tuple[str, tuple[int, int, int]]:
    lower = prompt.lower()
    if any(s in lower for s in _GREEN_CLASH):
        return "bright magenta", (255, 0, 255)
    return "bright lime green", (0, 255, 0)


def _strip_transparent_phrases(prompt: str) -> str:
    for kw in sorted(_TRANSPARENT_KEYWORDS, key=len, reverse=True):
        prompt = re.sub(re.escape(kw), "", prompt, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", prompt).strip().strip(",").strip()


def _remove_background(image_bytes: bytes) -> bytes:
    from rembg import remove

    print("[transparent] Removing background...", flush=True)
    result = remove(image_bytes)
    return result


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


def _extract_image_bytes(response) -> bytes:
    for part in response.parts or []:
        if part.inline_data is not None and part.inline_data.data:
            return part.inline_data.data
    text = " ".join(p.text for p in response.parts or [] if p.text)
    raise RuntimeError(f"Model returned no image. {text}".strip())


def generate_image(prompt: str, output: str | None) -> Path:
    print(f"Prompt: {prompt}")
    transparent = _wants_transparent(prompt)

    if transparent:
        color_name, _ = _pick_chroma(prompt)
        clean = _strip_transparent_phrases(prompt)
        gen_prompt = (
            f"{clean}, isolated on a perfectly flat solid {color_name} background, "
            "pure studio lighting, no shadows, no gradients"
        )
        print(f"[transparent] Using chroma-key trick ({color_name} background)...", flush=True)
    else:
        gen_prompt = prompt

    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=gen_prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )
    image_bytes = _extract_image_bytes(response)

    if transparent:
        image_bytes = _remove_background(image_bytes)

    if output:
        out_path = Path(output)
    else:
        stem = slugify(prompt)
        out_path = unique_path(str(Path.cwd() / stem), ".png")
    out_path.write_bytes(image_bytes)
    print(f"Saved: {out_path}")
    return out_path


def _mime_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/jpeg")


def analyze_image(file: str, question: str) -> None:
    print(f"Prompt: {question}")
    client = genai.Client(api_key=get_api_key())
    image_bytes = Path(file).read_bytes()
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=[
            question,
            types.Part.from_bytes(data=image_bytes, mime_type=_mime_type(file)),
        ],
    )
    print(response.text)


def describe_image(file: str, prompt: str) -> None:
    print(f"Prompt: {prompt}")
    client = genai.Client(api_key=get_api_key())
    image_bytes = Path(file).read_bytes()
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=_mime_type(file)),
        ],
    )
    print(response.text)


def main():
    parser = argparse.ArgumentParser(description="Gemini image tool")
    parser.add_argument("--mode", choices=["generate", "analyze", "describe"], default="generate")
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--file", help="Path to input image")
    parser.add_argument("--question", default="Describe this image in detail.", help="Question for analyze mode")
    parser.add_argument("--output", help="Output filename (overrides auto-generated name)")
    args = parser.parse_args()

    if args.mode == "generate":
        if not args.prompt:
            print("Error: --prompt is required for generate mode", file=sys.stderr)
            sys.exit(1)
        generate_image(args.prompt, args.output)
    elif args.mode == "analyze":
        if not args.file:
            print("Error: --file is required for analyze mode", file=sys.stderr)
            sys.exit(1)
        analyze_image(args.file, args.question)
    elif args.mode == "describe":
        if not args.file or not args.prompt:
            print("Error: --file and --prompt are required for describe mode", file=sys.stderr)
            sys.exit(1)
        describe_image(args.file, args.prompt)


if __name__ == "__main__":
    main()
