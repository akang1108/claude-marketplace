---
name: gemini-image
description: Generate images from text prompts, analyze existing images, or generate captions/descriptions using Google Gemini's Imagen model. Use when the user types /gemini-image, asks to generate an image, wants to analyze or describe a photo, or requests image creation with AI.
---

You are the `/gemini-image` skill. You generate images, analyze images, and produce text descriptions of images using Google Gemini.

## Bootstrap (run before every invocation)

1. Resolve the skill directory:
   ```bash
   SKILL_DIR="${CLAUDE_PLUGIN_ROOT}/skills/gemini-image"
   ```

2. Create the venv if it doesn't exist:
   ```bash
   if [ ! -d "$SKILL_DIR/.venv" ]; then
     echo "Setting up Gemini environment (first run)..."
     python3 -m venv "$SKILL_DIR/.venv" && "$SKILL_DIR/.venv/bin/pip" install -q google-genai "rembg[cpu]"
   fi
   ```

3. Validate the API key:
   ```bash
   if [ -z "$GEMINI_API_KEY" ]; then
     echo "Error: GEMINI_API_KEY is not set. Add it to your shell profile."
     exit 1
   fi
   ```

## Invocation

Parse the user's arguments to select a mode:

- Default mode is `generate` — run it unless `analyze` or `describe` appears as the first word.
- If the first word is `analyze`, use `--mode analyze`.
- If the first word is `describe`, use `--mode describe`.

Run the script:
```bash
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/gemini_image.py" [flags]
```

**IMPORTANT:** Do NOT pass `--output` unless the user explicitly provided a filename. The script automatically derives a human-readable filename from the prompt (e.g. "pipescape logo" → `pipescape-logo.png`). Never construct a timestamped or otherwise generated filename yourself.

**Output location matters — do not redirect it.** The generated image is a deliverable the user asked for, not a temp file. Run the script from the working directory the user was already in *before* this skill was invoked — do not `cd` into a scratchpad/session/tmp directory first, and do not pass `--output` pointed at one, even if your environment nudges you toward a scratchpad for temp files. That guidance doesn't apply here: this output belongs next to the user, in their cwd.

## Usage Examples

```
# Generate an image (default mode)
/gemini-image a red fox sitting in snow at dusk

# Analyze an existing image
/gemini-image analyze --file screenshot.png
/gemini-image analyze --file photo.jpg --question "What brand is visible in this image?"

# Generate a caption or description from an image
/gemini-image describe --file product.jpg write a marketing caption for this
```

## After Running

- Report the saved filename to the user.
- If Claude Code supports inline image display, show the generated image.
- On error, print the stderr output from the script clearly.
