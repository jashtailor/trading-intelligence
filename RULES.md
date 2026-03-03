# Project Rules

These rules must be strictly followed at all times throughout this project.

---

## 1. Required Files

The following 5 files **must always exist** in the project root:

| File | Purpose |
|------|---------|
| `LOGGING.md` | Logs **all** user prompts and Claude's responses |
| `DECISION.md` | Logs the reasoning behind **every** decision made |
| `ERROR.md` | Logs **all** errors that occurred, with root-cause reasoning |
| `CLAUDE.md` | Claude's persistent context, memory, and project state |
| `README.md` | Project overview and setup documentation |

> `RULES.md` itself is always maintained as the 6th canonical file.

---

## 2. Logging Rules

- **Timestamps are mandatory** on every entry in every `.md` file. Format: `[YYYY-MM-DD HH:MM UTC]`.
- **LOGGING.md**: Every user prompt and Claude response must be appended as a timestamped entry using the format `### [YYYY-MM-DD HH:MM UTC] [PROMPT] User` / `### [YYYY-MM-DD HH:MM UTC] [RESPONSE] Claude`. Never truncate or delete prior entries.
- **DECISION.md**: Before implementing anything non-trivial, log the decision with a timestamp header, the alternatives considered, and the rationale chosen.
- **ERROR.md**: Every error, failure, or unexpected behavior must be logged with: `[YYYY-MM-DD HH:MM UTC]` timestamp, error message, root-cause analysis, and resolution.

---

## 3. Development Rules

- Never skip error handling in scraper code — all exceptions must be caught, logged, and surfaced.
- All data must be stored with timestamps and be deduplicated before writing.
- GitHub Actions workflows must never hard-fail silently — always log to ERROR.md on failure.
- Code must be readable and commented where logic is non-obvious.
- No credentials or API keys may be hardcoded — use GitHub Secrets.

---

## 4. Project Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Continuously scrape glint.trade/feed and store data | In Progress |
| 2 | Feed collected data to a model to generate a world view and stock recommendations | Pending |

---

*Last updated: 2026-03-02*
