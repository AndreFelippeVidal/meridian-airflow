.PHONY: setup lint fmt typecheck test run clean \
        ingest verify-ingest dbt-deps transform dbt-test \
        airflow-init airflow-dev dag-parse dag-test \
        astro-dev edr-report evidence-sources evidence-build

# uv handles venv + lockfile + installs. https://docs.astral.sh/uv/

setup:          ## create venv, install deps, install pre-commit hooks
	uv sync
	uv run pre-commit install
	$(MAKE) airflow-init

lint:           ## lint without changing files
	uv run ruff check .

fmt:            ## auto-format + autofix
	uv run ruff format .
	uv run ruff check --fix .

typecheck:      ## static types
	uv run mypy src

test:           ## run all tests
	AIRFLOW_HOME=$(shell pwd)/.airflow uv run pytest

run:            ## (unused placeholder — use airflow-dev or astro-dev)
	@echo "Use 'make airflow-dev' or 'make astro-dev' to run the pipeline"

# ── Data pipeline ─────────────────────────────────────────────────────────────

ingest:         ## load Meridian domain data into DuckDB raw schema
	uv run python -m ingestion.pipeline

verify-ingest:  ## pytest gate for ingestion
	uv run pytest tests/test_ingestion.py -v

dbt-deps:       ## install dbt packages
	cd transform && uv run dbt deps

transform:      ## dbt build — models + tests
	cd transform && uv run dbt build --profiles-dir .

dbt-test:       ## dbt tests only
	cd transform && uv run dbt test --profiles-dir .

edr-report:     ## generate Elementary data quality HTML report
	cd transform && DUCKDB_PATH="$(shell pwd)/data/meridian.duckdb" \
	uv run edr report \
	  --profiles-dir . --profile-target duckdb --project-dir . \
	  --file-path edr_target/elementary_report.html

# ── Airflow (standalone / local) ──────────────────────────────────────────────

airflow-init:   ## initialise Airflow SQLite metadata DB (run once after setup)
	AIRFLOW_HOME=$(shell pwd)/.airflow uv run airflow db migrate

airflow-dev:    ## start Airflow standalone UI (http://localhost:8080)
	AIRFLOW_HOME=$(shell pwd)/.airflow \
	AIRFLOW__CORE__DAGS_FOLDER=$(shell pwd)/dags \
	uv run airflow standalone

dag-parse:      ## validate DAG loads with zero import errors
	AIRFLOW_HOME=$(shell pwd)/.airflow uv run python -c \
	  "from airflow.models import DagBag; b=DagBag('dags/',include_examples=False); \
	   print('errors:',b.import_errors); assert not b.import_errors; print('OK')"

dag-test:       ## dry-run the DAG for today's logical date (no real task execution)
	AIRFLOW_HOME=$(shell pwd)/.airflow uv run airflow dags test meridian_batch

# ── Astro CLI (Docker-based) ──────────────────────────────────────────────────

astro-dev:      ## start full Astro environment in Docker (http://localhost:8080)
	astro dev start

clean:
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache __pycache__ */__pycache__
