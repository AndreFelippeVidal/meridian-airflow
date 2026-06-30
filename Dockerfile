# Astro Runtime 3.x = Airflow 3.2.1 (Python 3.12)
# New registry for Airflow 3.x: astrocrpublic.azurecr.io/runtime
# https://www.astronomer.io/docs/runtime/runtime-release-notes
FROM astrocrpublic.azurecr.io/runtime:3.2-3

# packages.txt and requirements.txt are handled by ONBUILD hooks in the
# Astro runtime base image — no need to COPY/pip-install them explicitly here.

# Make ingestion + transform importable from DAGs (not covered by ONBUILD)
COPY ingestion/ ${AIRFLOW_HOME}/ingestion/
COPY transform/ ${AIRFLOW_HOME}/transform/

# Pre-install dbt packages so Cosmos doesn't re-download them before every model task.
# dbt deps only needs the filesystem — no database connection required.
RUN cd ${AIRFLOW_HOME}/transform && dbt deps --no-partial-parse

# Create the data directory so DuckDB can write meridian.duckdb here
RUN mkdir -p ${AIRFLOW_HOME}/data
