# app-naming

Brainstorm app/product names and vet candidates for availability.

## Setup

```bash
/plugin marketplace add akang1108/claude-marketplace
/plugin install app-naming@akang1108-claude-marketplace
```

## Skills

| Skill      | Invocation                                                                    |
|------------|-------------------------------------------------------------------------------|
| app-naming | `/app-naming` or automatic, based on triggers in `.claude-plugin/plugin.json` |

See [`skills/app-naming/SKILL.md`](skills/app-naming/SKILL.md) for full operational detail.

## Notes

- Domain checks use the local `whois` CLI, `dig`, and registry RDAP only.
- Registrar search sites are never used, to avoid front-running.
