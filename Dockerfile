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

# `edr report` cd's into elementary's bundled internal dbt project and runs
# `dbt deps`, which tries to create dbt_packages/ there. That project is pip
# installed into root-owned site-packages (mode 755), so the astro user (uid
# 50000) cannot write it → [Errno 13] Permission denied: 'dbt_packages'.
# Make the internal project writable so edr can install its deps at task time.
RUN EL_PROJECT="$(python -c 'import elementary, os; print(os.path.join(os.path.dirname(elementary.__file__), "monitor", "dbt_project"))')" \
    && chmod -R a+w "$EL_PROJECT"
USER astro

# Create the data directory so DuckDB can write meridian.duckdb here
RUN mkdir -p ${AIRFLOW_HOME}/data
