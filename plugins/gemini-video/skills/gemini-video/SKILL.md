---
name: gemini-video
description: Generate short video clips from text prompts or images using Google Gemini's Veo model. Use when the user types /gemini-video, asks to generate a video, animate an image, or create a video clip with AI.
---

You are the `/gemini-video` skill. You generate short video clips using Google Gemini's Veo model from a text prompt or an input image.

## Bootstrap (run before every invocation)

1. Resolve the skill directory:
   ```bash
   SKILL_DIR="${CLAUDE_PLUGIN_ROOT}/skills/gemini-video"
   ```

2. Create the venv if it doesn't exist:
   ```bash
   if [ ! -d "$SKILL_DIR/.venv" ]; then
     echo "Setting up Gemini environment (first run)..."
     python3 -m venv "$SKILL_DIR/.venv" && "$SKILL_DIR/.venv/bin/pip" install -q google-genai
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

```bash
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/gemini_video.py" --prompt "<prompt>" [--image <path>] [--reference <path>] [--duration <seconds>] [--output <filename>] [--tier lite|fast|standard]
```

`--tier` selects the Veo 3.1 quality/cost tier. **Default is `lite`** (cheapest, $0.05-0.08/sec). Use `fast` ($0.10-0.30/sec) or `standard` ($0.40-0.60/sec, highest quality) only when the user explicitly asks for higher quality — e.g. "use standard tier", "use full quality", "use fast tier". Otherwise always default to lite.

**`--reference` (subject-reference/ASSET mode) requires `--tier standard`.** The lite and fast models reject `referenceImages` with a 400 `INVALID_ARGUMENT` error. If the user wants `--reference` mode and hasn't specified a tier, use `--tier standard` automatically and let them know why (no need to ask first).

`--image` and `--reference` are mutually exclusive:
- `--image`: image used as **frame 0** (person will be static unless prompt drives motion)
- `--reference`: image used as **subject/ASSET reference** — model generates the person doing things described in the prompt; better for animating a specific person

**IMPORTANT:** Do NOT pass `--output` unless the user explicitly provided a filename. The script automatically derives a human-readable filename from the prompt (e.g. "timelapse of clouds" → `timelapse-of-clouds.mp4`). Never construct a timestamped or otherwise generated filename yourself.

**Output location matters — do not redirect it.** The generated video is a deliverable the user asked for, not a temp file. Run the script from the working directory the user was already in *before* this skill was invoked — do not `cd` into a scratchpad/session/tmp directory first, and do not pass `--output` pointed at one, even if your environment nudges you toward a scratchpad for temp files. That guidance doesn't apply here: this output belongs next to the user, in their cwd.

Video generation is async and can take 30–120 seconds. Inform the user that generation is in progress. The script prints elapsed time while polling. Report the saved filename when complete.

## Prompt Crafting — Image Input (Person in Photo)

When `--image` is provided and contains a person, the image is used as **frame 0** by Veo. The person will appear static unless the prompt explicitly drives continuous motion and action.

**Rules for person-in-photo prompts:**
- Describe action that starts *immediately* — no "animate this image", no "starting from this pose"
- Include speech/dialogue if the user wants talking — Veo 3 generates audio natively. Write it as: `...saying "Hello, welcome to my channel"`
- Reference the person by what they're doing, not by the photo: "A person smiles warmly at the camera, leans forward, and says..."
- Specify sustained motion throughout: "...gesturing expressively throughout, maintaining eye contact with the camera"
- Avoid static language: no "remains", "sits", "stands still", "poses"

**Bad prompt (causes static photo effect):**
> "Animate this image of a person smiling"

**Good prompt (person active throughout):**
> "A person smiles at the camera, leans slightly forward, and says 'Hey everyone, thanks for watching' while gesturing naturally with their hands"

When the user gives a vague prompt like "make a video of this person talking about X", expand it into a full active-motion prompt following the rules above before invoking the script.

## Usage Examples

```
# Generate a video from a text prompt
/gemini-video a timelapse of clouds moving over a mountain

# Animate an image (static scene)
/gemini-video --image sketch.jpg animate this as a river flowing downstream

# Person in photo — frame 0 mode (person must be animated via prompt)
/gemini-video --image photo.jpg make this person introduce themselves and wave hello

# Person as subject reference — ASSET mode (better for animating a specific person)
/gemini-video --reference headshot.jpg a person walks confidently into a bright office and sits down

# Person in photo — explicit dialogue
/gemini-video --image headshot.jpg this person says "Welcome to the demo" and walks toward the camera

# With custom output filename
/gemini-video a sunset over the ocean --output sunset.mp4

# Override quality tier (default is lite)
/gemini-video --tier standard a sunset over the ocean
/gemini-video --tier fast a timelapse of clouds
```

## Voice / Audio Limitations

Veo's only audio control is `generate_audio` (on/off) — there is no voice identity or voice cloning support in the video generation API. Specifically:

- You **cannot** provide a reference video or audio sample to match a person's voice
- You **cannot** select a specific voice for a person in the video
- Dialogue in the prompt (e.g. *"saying 'Hello'"*) works, but Veo picks the voice — it won't match the subject's real voice
- `--reference` mode (ASSET) has the same limitation; voice identity is not carried from the reference image

If you need the subject's real voice, the workaround is post-processing: generate the video muted, synthesize speech separately (e.g. ElevenLabs, or the Gemini TTS API with `ReplicatedVoiceConfig` + a WAV sample), then mux with `ffmpeg`.

## After Running

- Report the saved `.mp4` filename and its full path.
- Also report: model/tier used, duration, resolution, and file size (all printed by the script after "Saved:").
- Let the user know they can open it with any video player.
- On error, print the stderr output from the script clearly.
