# gemini-image

Generate images, analyze images, or produce captions using Google Gemini's Nano Banana image models.

## Setup

Add this marketplace and install the plugin:

```bash
/plugin marketplace add akang1108/claude-marketplace
/plugin install gemini-image@akang1108-claude-marketplace
```

## Requirements

- [`uv`](https://docs.astral.sh/uv/) installed
- `GEMINI_API_KEY` set

## Skills

| Skill        | Invocation                                                                      |
|--------------|---------------------------------------------------------------------------------|
| gemini-image | `/gemini-image` or automatic, based on triggers in `.claude-plugin/plugin.json` |

See [`skills/gemini-image/SKILL.md`](skills/gemini-image/SKILL.md) for full operational detail.
