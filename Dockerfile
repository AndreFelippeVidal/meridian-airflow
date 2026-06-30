# Astro Runtime 3.x = Airflow 3.2.1 (Python 3.12)
# New registry for Airflow 3.x: astrocrpublic.azurecr.io/runtime
# https://www.astronomer.io/docs/runtime/runtime-release-notes
FROM astrocrpublic.azurecr.io/runtime:3.2-3

# packages.txt and requirements.txt are handled by ONBUILD hooks in the
# Astro runtime base image — no need to COPY/pip-install them explicitly here.

# Make ingestion + transform importable from DAGs (not covered by ONBUILD).
# --chown=astro:0 matches the ONBUILD COPY so dbt can write logs as the astro user.
COPY --chown=astro:0 ingestion/ ${AIRFLOW_HOME}/ingestion/
COPY --chown=astro:0 transform/ ${AIRFLOW_HOME}/transform/

# Run as root so chown is authoritative: dbt deps downloads tarballs with
# 0444 files; non-root chown silently fails on group changes. After chown,
# chmod u+w ensures the astro user can overwrite everything at runtime.
USER root
RUN cd ${AIRFLOW_HOME}/transform \
    && dbt deps --no-partial-parse \
    && dbt parse --profiles-dir . --profile meridian_batch --target duckdb --no-partial-parse \
    && chown -R astro:0 ${AIRFLOW_HOME}/transform \
    && chmod -R u+w ${AIRFLOW_HOME}/transform
USER astro

# Create the data directory so DuckDB can write meridian.duckdb here
RUN mkdir -p ${AIRFLOW_HOME}/data
