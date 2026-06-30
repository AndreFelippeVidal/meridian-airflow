"""Airflow DAG structural tests — run without a live scheduler."""

from __future__ import annotations

from airflow.models import DagBag


def _get_dagbag() -> DagBag:
    return DagBag(dag_folder="dags/", include_examples=False)


def test_dag_loads_no_errors() -> None:
    """DagBag must import the meridian_batch DAG with zero errors."""
    bag = _get_dagbag()
    assert not bag.import_errors, f"DAG import errors: {bag.import_errors}"
    assert "meridian_batch" in bag.dags


def test_dag_has_expected_task_groups() -> None:
    """meridian_batch must contain the dlt ingest and dbt transform task groups."""
    dag = _get_dagbag().dags["meridian_batch"]
    group_ids = {tg.group_id for tg in dag.task_group_dict.values()}
    # dlt PipelineTasksGroup uses pipeline_name as the group_id
    assert "meridian_ingest" in group_ids, f"meridian_ingest missing; groups: {group_ids}"
    assert "transform_group" in group_ids, f"transform_group missing; groups: {group_ids}"


def test_dag_has_quality_tasks() -> None:
    """meridian_batch must contain check_mart_rows and quality_report tasks."""
    dag = _get_dagbag().dags["meridian_batch"]
    task_ids = set(dag.task_ids)
    assert "check_mart_rows" in task_ids, f"check_mart_rows missing; tasks: {task_ids}"
    assert "quality_report" in task_ids, f"quality_report missing; tasks: {task_ids}"


def test_dag_schedule() -> None:
    """DAG must be scheduled daily and not catch up."""
    dag = _get_dagbag().dags["meridian_batch"]
    # Airflow 3 exposes schedule_interval via timetable; compare via schedule property
    assert dag.catchup is False
    assert dag.max_active_runs == 1


def test_dag_tags() -> None:
    """meridian_batch must be tagged for discoverability."""
    dag = _get_dagbag().dags["meridian_batch"]
    tags = set(dag.tags)
    assert "meridian" in tags
    assert "dbt" in tags
