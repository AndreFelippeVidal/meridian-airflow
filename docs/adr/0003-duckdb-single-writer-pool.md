# ADR-0003 — Serialize DuckDB writes with a 1-slot Airflow pool

**Date:** 2026-07-01
**Status:** Accepted
**Supersedes:** the DuckDB-concurrency row of [ADR-0002](0002-airflow3-over-dagster.md)

## Context

DuckDB is single-writer: only one process may hold a write handle to the
`.duckdb` file at a time. A second writer fails with
`IO Error: Could not set lock on file ... Conflicting lock held`.

ADR-0002 assumed `max_active_runs=1` on the DAG was sufficient. It is not.
`max_active_runs=1` only prevents two *DAG runs* from overlapping — it says
nothing about parallelism *within* a single run. Our DAG opens the DuckDB
file from many tasks that Airflow is free to run concurrently:

- the 5 dlt resource tasks (`decompose="serialize"` chains them, but they
  still each open the file),
- every Cosmos `*_run` model task (Cosmos schedules independent models in
  parallel),
- `check_mart_rows` (read) and `quality_report` (writes elementary models).

With the default executor slots, Cosmos happily ran several model tasks at
once and they collided on the DuckDB lock.

## Decision

Create a dedicated Airflow **pool `duckdb` with exactly 1 slot** and assign
it to **every task that opens the DuckDB file**:

| Task(s) | How the pool is set |
|---------|--------------------|
| dlt resource tasks | `add_run(..., pool="duckdb")` on `PipelineTasksGroup` |
| Cosmos dbt model + test tasks | `operator_args={"pool": "duckdb"}` on `DbtTaskGroup` |
| `check_mart_rows` | `@task(pool="duckdb")` |
| `quality_report` | `@task(pool="duckdb")` (it runs `dbt run --select elementary`) |

The pool is declared in `airflow_settings.yaml` (loaded by the Astro CLI on
`astro dev start`). A 1-slot pool forces Airflow to run at most one
DB-touching task at any instant — the orchestration-level equivalent of a
mutex around the DuckDB file.

`max_active_runs=1` is kept as a second, coarser guard against overlapping
runs, but the pool is what actually prevents the lock conflicts.

## Consequences

**Gained:**
- Zero DuckDB lock errors; the pipeline is deterministic.
- The mutex lives in orchestration config, not application code — no retry
  loops or file-lock polling in the tasks themselves.

**Accepted trade-offs:**
- DB-touching tasks run **serially**, so the transform stage is slower than a
  parallel dbt build would be. Acceptable for an embedded warehouse; a real
  warehouse (Snowflake/Trino) removes the constraint and the pool can be
  dropped or widened.
- Every new task that opens the DB must remember to join the pool. This is a
  documented convention (see `CLAUDE.md`).

## Related

- Elementary's observability models are **not** built inside the Cosmos task
  graph (that added ~28 pool-serialized tasks that queued ahead of our own
  models). They are materialized once inside `quality_report` immediately
  before `edr report`, which is the only consumer of those tables. See
  [ADR-0004](0004-elementary-in-quality-task.md).
