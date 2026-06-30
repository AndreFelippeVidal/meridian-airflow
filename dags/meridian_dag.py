"""
Meridian batch pipeline — Airflow 3 edition.

Topology (compare with meridian-batch-platform/Dagster):

  ingest_group (dlt)
    ├── meridian_source.customers
    ├── meridian_source.products
    ├── meridian_source.orders
    ├── meridian_source.order_items
    └── meridian_source.payments
          ↓
  transform_group (dbt via Cosmos)
    ├── stg_meridian__customers  ─┐
    ├── stg_meridian__products    │
    ├── stg_meridian__orders      │→  dim_customer
    ├── stg_meridian__order_items │→  dim_product
    └── stg_meridian__payments    │→  fct_orders
                                  │→  fct_order_items
                                  │→  fct_payments
                                  └→  mart_marketplace_daily
          ↓
  check_mart_rows          (assert non-empty marts)
          ↓
  quality_report           (edr report HTML)
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pendulum
from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowFailException
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig
from dlt.helpers.airflow_helper import PipelineTasksGroup

# ── Paths ─────────────────────────────────────────────────────────────────────
# Anchor to the project root (parent of dags/) so paths resolve correctly
# both locally (uv run) and inside Astro Docker containers (AIRFLOW_HOME=/usr/local/airflow).

_PROJECT_ROOT = Path(__file__).parent.parent
_INGESTION_DIR = _PROJECT_ROOT / "ingestion"
_TRANSFORM_DIR = _PROJECT_ROOT / "transform"
_DB_PATH = _PROJECT_ROOT / "data" / "meridian.duckdb"


# ── dbt profile mapping for DuckDB ────────────────────────────────────────────
# Cosmos has no built-in DuckDB mapping; we point directly at profiles.yml.

_dbt_profile_config = ProfileConfig(
    profile_name="meridian_batch",
    target_name="duckdb",
    profiles_yml_filepath=_TRANSFORM_DIR / "profiles.yml",
)

_dbt_project_config = ProjectConfig(
    dbt_project_path=_TRANSFORM_DIR,
    manifest_path=_TRANSFORM_DIR / "target" / "manifest.json",
    project_name="meridian_batch",
    install_dbt_deps=False,  # pre-installed in the Docker image via `dbt deps` in Dockerfile
)

_dbt_execution_config = ExecutionConfig(
    dbt_executable_path="dbt",
)


# ── DAG ───────────────────────────────────────────────────────────────────────

@dag(
    dag_id="meridian_batch",
    description="dlt ingest → dbt staging+marts → row-count checks → Elementary report",
    schedule="@daily",
    start_date=pendulum.datetime(2025, 6, 30, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["meridian", "dlt", "dbt", "elementary"],
    default_args={"retries": 1},
)
def meridian_batch_dag() -> None:

    # ── 1. Ingestion — dlt PipelineTasksGroup ─────────────────────────────────
    # Each dlt resource becomes a separate Airflow task when decompose="serialize".
    # This mirrors @dlt_assets in Dagster, which also creates one node per resource.

    ingest_tasks = PipelineTasksGroup(
        pipeline_name="meridian_ingest",
        use_data_folder=False,
        wipe_local_data=True,
    )

    # Import inline to avoid top-level import issues in the Airflow scheduler
    from ingestion.meridian_source import meridian_source
    from ingestion.pipeline import build_pipeline

    pipeline = build_pipeline()
    source = meridian_source()

    ingest_tasks.add_run(
        pipeline=pipeline,
        data=source,
        decompose="serialize",
        trigger_rule="all_done",
        retries=1,
        pool="duckdb",
    )

    # ── 2. Transform — Cosmos DbtTaskGroup ────────────────────────────────────
    # Reads manifest.json and creates one task per dbt model, preserving
    # the staging → marts dependency order. Equivalent to @dbt_assets in Dagster.

    # Pass DUCKDB_PATH explicitly so profiles.yml env_var() resolves to the
    # absolute path inside Docker. Without this, Cosmos runs dbt from a /tmp/
    # working directory and the relative fallback '../data/meridian.duckdb'
    # resolves to /tmp/data/meridian.duckdb (which does not exist).
    transform_group = DbtTaskGroup(
        group_id="transform_group",
        project_config=_dbt_project_config,
        profile_config=_dbt_profile_config,
        execution_config=_dbt_execution_config,
        operator_args={
            "env": {"DUCKDB_PATH": str(_DB_PATH)},
            "pool": "duckdb",  # serialize Cosmos tasks — DuckDB is single-writer
        },
    )

    # ── 3. Row-count checks ───────────────────────────────────────────────────
    # Equivalent to @dg.asset_check(blocking=True) in Dagster.

    @task(task_id="check_mart_rows", pool="duckdb")
    def check_mart_rows() -> None:
        import duckdb
        con = duckdb.connect(str(_DB_PATH), read_only=True)
        for table in ["fct_orders", "mart_marketplace_daily"]:
            count = con.execute(f"SELECT count(*) FROM main_marts.{table}").fetchone()[0]
            if count == 0:
                raise AirflowFailException(f"main_marts.{table} is empty after dbt build")
        con.close()

    # ── 4. Elementary quality report ──────────────────────────────────────────
    # Equivalent to the elementary_report_asset in Dagster.

    @task(task_id="quality_report")
    def quality_report() -> None:
        report_path = _TRANSFORM_DIR / "edr_target" / "elementary_report.html"
        result = subprocess.run(
            [
                "edr", "report",
                "--profiles-dir", str(_TRANSFORM_DIR),
                "--profile-target", "duckdb",
                "--project-dir", str(_TRANSFORM_DIR),
                "--file-path", str(report_path),
            ],
            cwd=_TRANSFORM_DIR,
            capture_output=True,
            text=True,
            env={**os.environ, "DUCKDB_PATH": str(_DB_PATH)},
        )
        if result.returncode != 0:
            raise AirflowFailException(f"edr report failed:\n{result.stderr[-2000:]}")

    # ── Wire task dependencies ─────────────────────────────────────────────────

    check = check_mart_rows()
    report = quality_report()

    ingest_tasks >> transform_group >> check >> report


meridian_batch_dag()
