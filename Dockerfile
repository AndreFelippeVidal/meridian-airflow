# Astro Runtime 13 = Airflow 3.x
# https://www.astronomer.io/docs/astro/runtime-release-notes
FROM quay.io/astronomer/astro-runtime:13.8.0

# Install Python packages into the Airflow environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Make ingestion + transform importable from DAGs
COPY ingestion/ ${AIRFLOW_HOME}/ingestion/
COPY transform/ ${AIRFLOW_HOME}/transform/
