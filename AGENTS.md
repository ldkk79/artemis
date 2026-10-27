# AGENTS.md

Instructions for AI coding agents working in this repository.

## Repository Role

This checkout is a **personal fork** of `google/artemis`.

- `origin` — `ldkk79/artemis`, the personal fork and the only push target.
- `upstream` — `google/artemis`, a read-only reference for syncing.

## Contribution Rules

- **Never push to `upstream`.** Do not open pull requests against
  `google/artemis` either, unless the user explicitly asks for it in that turn.
- Commit and push only to `origin`.
- Do the work on a branch (for example `codex/<topic>`); leave `main` alone.
- Do not amend, rebase, or force-push commits that already exist on `origin`
  unless the user asks for it.

## Local-Only Files

These are gitignored and must stay out of commits:

- `.env` — API keys and machine settings.
- `config/artemis.local.jsonc` — machine-local provider/model overrides,
  selected at runtime through `ARTEMIS_ARTEMIS_JSONC`.

## Working Notes

- The Android target is a physical device; its serial lives in `.env` as
  `ADB_DEVICE_SERIAL`.
- The LLM provider is configured in `config/artemis.local.jsonc`; the matching
  base URL and credential live in `.env`.
- `uv run pytest` runs the hermetic unit suite. Device, integration, and
  end-to-end suites are opt-in through their pytest markers.
