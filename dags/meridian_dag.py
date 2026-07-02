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
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import TestBehavior
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
    # TestBehavior.AFTER_ALL: run all model tasks first, then all test tasks.
    # AFTER_EACH (default) runs each model's tests immediately after that model
    # builds, but relationship tests reference other models that may not exist yet.
    # select_models: run only our custom models; Elementary observability models
    # run as part of the edr quality_report task instead of as individual DAG tasks.
    # This avoids ~28 Elementary model tasks queuing ahead of stg_/fct_ models.
    transform_group = DbtTaskGroup(
        group_id="transform_group",
        project_config=_dbt_project_config,
        profile_config=_dbt_profile_config,
        execution_config=_dbt_execution_config,
        render_config=RenderConfig(
            test_behavior=TestBehavior.AFTER_ALL,
            select=["path:models/staging", "path:models/marts"],
        ),
        operator_args={
            "env": {"DUCKDB_PATH": str(_DB_PATH)},
            "pool": "duckdb",
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

    @task(task_id="quality_report", pool="duckdb")
    def quality_report() -> None:
        env = {**os.environ, "DUCKDB_PATH": str(_DB_PATH)}

        def _run(label: str, cmd: list[str]) -> None:
            result = subprocess.run(
                cmd, cwd=_TRANSFORM_DIR, capture_output=True, text=True, env=env
            )
            if result.returncode != 0:
                # edr/dbt write their real errors to stdout, not stderr — surface both.
                raise AirflowFailException(
                    f"{label} failed (exit {result.returncode})\n"
                    f"--- STDOUT ---\n{result.stdout[-3000:]}\n"
                    f"--- STDERR ---\n{result.stderr[-3000:]}"
                )

        # Materialize Elementary's observability models. They are excluded from the
        # Cosmos DbtTaskGroup (which builds only our staging+marts), so their tables
        # do not exist yet — and `edr report` reads exactly those tables.
        _run(
            "dbt run --select elementary",
            [
                "dbt",
                "run",
                "--select",
                "elementary",
                "--profiles-dir",
                str(_TRANSFORM_DIR),
                "--target",
                "duckdb",
            ],
        )

        report_path = _TRANSFORM_DIR / "edr_target" / "elementary_report.html"
        _run(
            "edr report",
            [
                "edr",
                "report",
                "--profiles-dir",
                str(_TRANSFORM_DIR),
                "--profile-target",
                "duckdb",
                "--project-dir",
                str(_TRANSFORM_DIR),
                "--file-path",
                str(report_path),
            ],
        )

    # ── Wire task dependencies ─────────────────────────────────────────────────

    check = check_mart_rows()
    report = quality_report()

    ingest_tasks >> transform_group >> check >> report


meridian_batch_dag()
