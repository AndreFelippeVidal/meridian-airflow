# ADR-0004 — Build Elementary models inside the quality task, not the Cosmos graph

**Date:** 2026-07-01
**Status:** Accepted

## Context

The dbt project depends on the `elementary` package, which contributes ~28
observability models (`dbt_models`, `dbt_run_results`, `dbt_tests`,
`data_monitoring_metrics`, …). `edr report` reads those tables to render the
data-quality HTML.

If Cosmos renders the whole manifest, those 28 elementary models become 28
Airflow tasks. Because they all take the 1-slot `duckdb` pool
([ADR-0003](0003-duckdb-single-writer-pool.md)) and are alphabetically/topo
ordered ahead of our `stg_`/`fct_` models, they queue in front of the models
a reviewer actually cares about — bloating the task graph and making the run
grid unreadable.

Two other properties matter:
1. `edr report` runs `dbt deps` against **elementary's own bundled internal
   dbt project** in site-packages, which is root-owned in the Astro image —
   this is a separate permission concern handled in the Dockerfile.
2. The elementary tables only need to exist by the time `edr report` runs;
   nothing upstream reads them.

## Decision

Restrict the Cosmos `DbtTaskGroup` to our own models:

```python
RenderConfig(select=["path:models/staging", "path:models/marts"])
```

and materialize the elementary models **once, inside `quality_report`**,
immediately before generating the report:

```python
dbt run --select elementary   # then: edr report
```

`quality_report` joins the `duckdb` pool because that `dbt run` writes to the
file.

## Consequences

**Gained:**
- The Airflow task graph shows only meaningful nodes: 5 dlt tasks, our
  staging + mart model tasks, one `transform_test`, `check_mart_rows`,
  `quality_report`.
- Elementary tables are still fully materialized before the report — the
  report is unchanged.

**Accepted trade-offs:**
- Elementary models are not individually visible/retryable in the Airflow UI;
  a failure surfaces as a `quality_report` failure. The task raises with full
  `dbt`/`edr` stdout+stderr so the cause is still legible in the log.
- `quality_report` does two things (build elementary + report) rather than
  one. Kept together because the build exists solely to feed the report.
