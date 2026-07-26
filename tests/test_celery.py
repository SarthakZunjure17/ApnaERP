import pytest
from httpx import AsyncClient

from app.core.celery import celery_app
from app.tasks.system_tasks import system_health_check_task, system_ping_task


@pytest.mark.asyncio
async def test_celery_app_configuration():
    """
    Test Celery application configuration settings, queues, and task discovery.
    """
    assert celery_app.main == "apnaerp"
    assert celery_app.conf.task_default_queue == "default"
    assert len(celery_app.conf.task_queues) == 4
    
    registered_tasks = list(celery_app.tasks.keys())
    assert "app.tasks.system_tasks.system_ping_task" in registered_tasks
    assert "app.tasks.system_tasks.system_health_check_task" in registered_tasks


@pytest.mark.asyncio
async def test_system_ping_task_execution():
    """
    Test executing system_ping_task in eager mode.
    """
    celery_app.conf.task_always_eager = True
    result = system_ping_task.delay("hello_celery")
    
    assert result.status == "SUCCESS"
    res_data = result.get()
    assert res_data["status"] == "pong"
    assert res_data["payload"] == "hello_celery"
    assert "timestamp" in res_data


@pytest.mark.asyncio
async def test_system_health_check_task_execution():
    """
    Test executing system_health_check_task in eager mode.
    """
    celery_app.conf.task_always_eager = True
    result = system_health_check_task.delay()
    
    assert result.status == "SUCCESS"
    res_data = result.get()
    assert res_data["health"] == "healthy"
    assert res_data["worker_engine"] == "celery"


@pytest.mark.asyncio
async def test_health_celery_endpoint(async_client: AsyncClient):
    """
    Test GET /health/celery endpoint returning broker, backend, tasks, and queue telemetry.
    """
    response = await async_client.get("/health/celery")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert json_data["broker_status"] == "connected"
    assert json_data["registered_tasks_count"] > 0
    assert "default" in json_data["configured_queues"]
    assert "high_priority" in json_data["configured_queues"]


@pytest.mark.asyncio
async def test_health_workers_endpoint(async_client: AsyncClient):
    """
    Test GET /health/workers endpoint returning active worker inspection statistics.
    """
    response = await async_client.get("/health/workers")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert "worker_status" in json_data
    assert "active_worker_count" in json_data
