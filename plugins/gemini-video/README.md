# gemini-video

Generate short video clips from text prompts or images using Google Gemini's Omni video model.

## Setup

Add this marketplace and install the plugin:

```bash
/plugin marketplace add akang1108/claude-marketplace
/plugin install gemini-video@akang1108-claude-marketplace
```

## Requirements

- [`uv`](https://docs.astral.sh/uv/) installed
- `GEMINI_API_KEY` set

## Skills

| Skill        | Invocation                                                                      |
|--------------|---------------------------------------------------------------------------------|
| gemini-video | `/gemini-video` or automatic, based on triggers in `.claude-plugin/plugin.json` |

See [`skills/gemini-video/SKILL.md`](skills/gemini-video/SKILL.md) for full operational detail.
