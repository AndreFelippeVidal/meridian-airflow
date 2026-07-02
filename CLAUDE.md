# CLAUDE.md — project context for Claude Code

Always-loaded context. Keep it to durable facts, not procedures (procedures belong in skills).

## What this project is
A component of the **Meridian** marketplace data + AI platform portfolio. Audience:
international/remote recruiters. Optimize for production discipline and a clear README.

## Conventions
- Python 3.12, managed with **uv**. Lint/format with **ruff**, types with **mypy**, tests with **pytest**.
- Run everything through the Makefile: `make setup|lint|fmt|typecheck|test`. Run the pipeline with `make airflow-dev` (standalone) or `make astro-dev` (full Docker stack).
- The Meridian domain comes from the **`meridian-core`** dependency (pinned by git tag) — never vendor or redefine it here. To add entities, change `meridian-core`, bump its version + tag, then update the pin in this repo's `pyproject.toml`.
- Every non-obvious decision gets an ADR in `docs/adr/` (use the `/adr` command).
- README section order is fixed — see `docs/STANDARDS.md`. Do not reorder.

## Orchestration (Airflow 3 — this repo's distinguishing layer)
- Orchestrator is **Airflow 3 via the Astro CLI**; the single DAG lives in `dags/meridian_dag.py`. Imports come from `airflow.sdk` (not `airflow.decorators`).
- The Astro base image is `astrocrpublic.azurecr.io/runtime` (Airflow 3.x) — **not** `quay.io/astronomer/astro-runtime` (which is 2.x).
- **DuckDB is single-writer.** Every task that opens `data/meridian.duckdb` **must** join the 1-slot `duckdb` Airflow pool (declared in `airflow_settings.yaml`). This includes dlt tasks (`add_run(pool=...)`), Cosmos models (`operator_args={"pool": ...}`), and any `@task`. `max_active_runs=1` is **not** enough. See ADR-0003.
- Elementary's observability models are **excluded** from the Cosmos `DbtTaskGroup` and built inside `quality_report` (`dbt run --select elementary`) right before `edr report`. See ADR-0004.
- `edr report` runs `dbt deps` inside Elementary's root-owned bundled dbt project in site-packages; the Dockerfile `chmod a+w`s it so the `astro` user can write there.

## Definition of done
CI green (lint+types+tests), README updated incl. Mermaid diagram, ADRs for key choices,
a demo artifact (GIF or live link). Then a vault note + a LinkedIn draft.

## Guardrails
- Never commit secrets (gitleaks runs in pre-commit). Use a local `.env`, never commit it.
- Prefer open standards (Iceberg, dbt-core, OSS) over a single cloud vendor.
