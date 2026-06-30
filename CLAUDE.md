# CLAUDE.md — project context for Claude Code

Always-loaded context. Keep it to durable facts, not procedures (procedures belong in skills).

## What this project is
A component of the **Meridian** marketplace data + AI platform portfolio. Audience:
international/remote recruiters. Optimize for production discipline and a clear README.

## Conventions
- Python 3.12, managed with **uv**. Lint/format with **ruff**, types with **mypy**, tests with **pytest**.
- Run everything through the Makefile: `make setup|lint|fmt|typecheck|test|run`.
- The Meridian domain comes from the **`meridian-core`** dependency (pinned by git tag) — never vendor or redefine it here. To add entities, change `meridian-core`, bump its version + tag, then update the pin in this repo's `pyproject.toml`.
- Every non-obvious decision gets an ADR in `docs/adr/` (use the `/adr` command).
- README section order is fixed — see `docs/STANDARDS.md`. Do not reorder.

## Definition of done
CI green (lint+types+tests), README updated incl. Mermaid diagram, ADRs for key choices,
a demo artifact (GIF or live link). Then a vault note + a LinkedIn draft.

## Guardrails
- Never commit secrets (gitleaks runs in pre-commit). Use a local `.env`, never commit it.
- Prefer open standards (Iceberg, dbt-core, OSS) over a single cloud vendor.
