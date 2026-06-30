"""DuckDB ingestion pipeline — run via `make ingest` or as a module."""

from __future__ import annotations

import os
from pathlib import Path

import dlt

from ingestion.meridian_source import meridian_source

# Resolve absolute path so dlt never treats it as relative to its own working dir.
# DUCKDB_PATH env var takes priority (useful for Docker/CI overrides).
_DB_PATH = os.environ.get(
    "DUCKDB_PATH",
    str(Path(__file__).parent.parent / "data" / "meridian.duckdb"),
)
_PIPELINE_NAME = "meridian_duckdb"
_DATASET_NAME = "raw"


def build_pipeline() -> dlt.Pipeline:
    return dlt.pipeline(
        pipeline_name=_PIPELINE_NAME,
        destination=dlt.destinations.duckdb(_DB_PATH),
        dataset_name=_DATASET_NAME,
    )


def run_pipeline() -> dlt.Pipeline:
    """Load all Meridian resources into DuckDB raw schema and return the pipeline."""
    pipeline = build_pipeline()
    load_info = pipeline.run(meridian_source())
    print(load_info)
    return pipeline


if __name__ == "__main__":
    run_pipeline()
