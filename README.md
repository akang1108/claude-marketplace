# claude-marketplace

Andy Kang's personal Claude Code plugin marketplace: Gemini media generation and app naming.

## Quick Start

Add the marketplace from the Claude Code prompt:

```bash
/plugin marketplace add akang1108/claude-marketplace
```

Then install individual plugins:

```bash
/plugin install gemini-image@akang1108-claude-marketplace
```

You may need to restart Claude for skills to be autodetected.

### Requirements

- Claude running locally (terminal or desktop)
- `GEMINI_API_KEY` set in your shell (required by both plugins)

> **Warning:** both plugins rely on `GEMINI_API_KEY` being set in your shell before use.
> - Missing it causes those skills to fail silently or with errors.
> - Exposing API keys via environment variables is a security risk.
>   - Secrets should ideally be managed behind an MCP server (local or remote) instead.

---

## Available Plugins

| Name                                           | Description                                         |
|------------------------------------------------|-----------------------------------------------------|
| [gemini-image](plugins/gemini-image/README.md) | Generate/analyze/caption images via Google Gemini   |
| [gemini-video](plugins/gemini-video/README.md) | Generate short video clips via Google Gemini Omni   |
| [app-naming](plugins/app-naming/README.md)     | Brainstorm and vet app names (whois, App Store, TM) |

---

## Repository Structure

```text
claude-marketplace/
├── plugins/          # Plugin definitions (one plugin per skill)
├── .claude-plugin/    # Marketplace configuration
└── README.md          # This file
```
