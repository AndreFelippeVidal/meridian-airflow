# ADR-0002 — Airflow 3 (Astronomer) over Dagster

**Date:** 2026-06-30  
**Status:** Accepted

## Context

`meridian-batch-platform` uses Dagster to orchestrate the same dlt → dbt → Elementary pipeline.
This repo is a parallel comparison: same data layer, different orchestrator.

Airflow 3 was chosen for this variant because:

1. **Market coverage** — Airflow is deployed in ~80% of data teams. Demonstrating it alongside Dagster on a portfolio shows breadth.
2. **Astronomer** provides a free OSS CLI (`astro`) that scaffolds Airflow 3 in Docker with one command, giving a production-grade local environment without a cloud account.
3. **dlt + Cosmos integration** — dlt ships `PipelineTasksGroup`, and `astronomer-cosmos` ships `DbtTaskGroup`, so the full pipeline maps cleanly to Airflow primitives without custom operators.

## Decision

Use **Airflow 3** via the Astro CLI scaffold (`astro dev init`).

| Concern | Solution |
|---------|----------|
| dlt ingestion | `PipelineTasksGroup` with `decompose="serialize"` — one task per resource |
| dbt transform | `DbtTaskGroup` from Cosmos — reads the same `manifest.json`, one task per model |
| Row-count guard | `@task` calling DuckDB directly; raises `AirflowFailException` on empty mart |
| Elementary report | `@task` shelling out `edr report` (same subprocess as Dagster version) |
| DuckDB write conflict | A 1-slot `duckdb` Airflow pool serializes every DB-touching task — see [ADR-0003](0003-duckdb-single-writer-pool.md) (`max_active_runs=1` alone is insufficient) |
| Local dev | `make airflow-dev` runs `airflow standalone`; `make astro-dev` boots the full Docker stack |

## Consequences

**Gained:**
- Airflow UI for task-level monitoring and retry management
- `astro dev start` gives a local environment identical to Astronomer Cloud
- A direct side-by-side comparison with Dagster for portfolio value

**Accepted trade-offs vs Dagster:**
- No per-asset lineage graph (Airflow's Asset concept in v3 is less mature)
- `AssetCheckResult` blocking semantics → replaced by `trigger_rule="all_success"` (default)
- Richer Dagster metadata panel (row counts, etc.) → task logs + XComs instead
- Airflow requires a metadata database (SQLite for standalone, Postgres in Docker)

## Alternatives considered

| Option | Rejected because |
|--------|-----------------|
| Prefect | Smaller OSS footprint; fewer job listings than Airflow |
| Dagster (existing) | Already covered by `meridian-batch-platform` |
| Airflow 2.x | Airflow 3 released; TaskFlow API and Assets are more Pythonic |
