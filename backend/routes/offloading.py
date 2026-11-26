import asyncio
from pathlib import Path
import time

import httpx
from fastapi import APIRouter, HTTPException

from ai_engine.dqn_agent import select_policy_action
from ai_engine.environment import ACTION_NAMES, TaskScenario, estimate_outcome
from backend.config import settings
from backend.database import claim_task, get_task, update_task, utc_now
from backend.routes.monitoring import resources
from backend.schemas import DecisionResponse, ExecutionRequest
from execution.workloads import process_task


router = APIRouter(prefix="/api/offloading", tags=["offloading"])


def _scenario(task: dict, snapshot: dict) -> TaskScenario:
    return TaskScenario(
        input_size_mb=task["input_size_mb"],
        cpu_cycles_giga=task["cpu_cycles_giga"],
        network_latency_ms=settings.network_latency_ms,
        mobile_cpu_available=max(0.02, 1.0 - snapshot["mobile"]["cpu_utilization"]),
        edge_cpu_utilization=(
            snapshot["edge"].get("cpu_utilization", 0.98)
            if snapshot["edge"]["available"] else 1.0
        ),
        cloud_cpu_utilization=(
            snapshot["cloud"].get("cpu_utilization", 0.98)
            if snapshot["cloud"]["available"] else 1.0
        ),
        bandwidth_mbps=settings.bandwidth_mbps,
    )


@router.post("/decide", response_model=DecisionResponse)
async def decide(request: ExecutionRequest) -> dict:
    task = get_task(request.task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if task["status"] in {"processing", "completed"}:
        raise HTTPException(409, f"Cannot decide for a {task['status']} task")
    snapshot = await resources()
    scenario = _scenario(task, snapshot)
    available_actions = [0]
    if snapshot["edge"]["available"]:
        available_actions.append(1)
    if snapshot["cloud"]["available"]:
        available_actions.append(2)
    action, policy = select_policy_action(scenario.state(), settings.model_path, available_actions)
    outcome = estimate_outcome(scenario, action)
    location = ACTION_NAMES[action]
    decision = {
        "action": action,
        "location": location,
        "policy": policy,
        "estimated_latency_ms": float(outcome["delay_seconds"]) * 1000.0,
        "estimated_energy_joules": float(outcome["energy_joules"]),
        "reward": float(outcome["reward"]),
    }
    update_task(
        task["id"], execution_location=location, estimated_latency_ms=decision["estimated_latency_ms"],
        estimated_energy_joules=decision["estimated_energy_joules"],
        estimated_reward=decision["reward"], state_json=scenario.state().tolist(),
        decision_json=decision, error_message=None,
    )
    return {"task_id": task["id"], "state": scenario.state().tolist(), **decision}


async def _execute_remotely(
    task: dict, url: str
) -> tuple[dict, float, float, dict]:
    task_path = task.get("file_path")
    content = await asyncio.to_thread(Path(task_path).read_bytes) if task_path else None
    files = {"file": (Path(task_path).name, content)} if task_path and content is not None else None
    data = {"task_type": task["task_type"], "cpu_cycles_giga": task["cpu_cycles_giga"]}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{url}/execute", data=data, files=files)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"The {task['execution_location']} service failed: {exc}") from exc
    round_trip = time.perf_counter() - started
    try:
        payload = response.json()
        execution_seconds = float(payload["execution_seconds"])
        result = payload["result"]
        server_metrics = payload["server_metrics"]
        if not isinstance(result, dict) or not isinstance(server_metrics, dict):
            raise ValueError("Remote result and server metrics must be JSON objects")
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, f"The {task['execution_location']} service returned an invalid response") from exc
    network_seconds = max(0.0, round_trip - execution_seconds)
    return result, execution_seconds, network_seconds, server_metrics


@router.post("/execute")
async def execute(request: ExecutionRequest) -> dict:
    task = get_task(request.task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if task["status"] == "processing":
        raise HTTPException(409, "Task is already processing")
    if task["status"] == "completed":
        raise HTTPException(409, "Task has already completed")
    if not task["decision"]:
        await decide(request)
        task = get_task(request.task_id)
        if task is None:
            raise HTTPException(404, "Task disappeared before execution")
    location = task["execution_location"]
    if (request.client_result is None) != (request.client_execution_seconds is None):
        raise HTTPException(422, "Client result and measured execution time must be provided together")
    if request.client_result is not None:
        if location != "local" or task["task_type"] != "compute":
            raise HTTPException(422, "Client-side result reporting is supported for local compute tasks")
        if not claim_task(task["id"]):
            raise HTTPException(409, "Task status changed; reload the task before executing")
        result = {
            **request.client_result,
            "measured_processing_seconds": request.client_execution_seconds,
            "workload": "client-side mobile computation",
        }
        update_task(
            task["id"],
            status="completed",
            completed_at=utc_now(),
            execution_seconds=request.client_execution_seconds,
            network_seconds=0.0,
            result_json=result,
        )
        return {
            "task_id": task["id"],
            "status": "completed",
            "location": location,
            "execution_seconds": request.client_execution_seconds,
            "network_seconds": 0.0,
            "estimated_latency_ms": task["estimated_latency_ms"],
            "estimated_energy_joules": task["estimated_energy_joules"],
            "result": result,
        }
    if not claim_task(task["id"]):
        raise HTTPException(409, "Task status changed; reload the task before executing")
    server_metrics = None
    try:
        if location == "local":
            result = await asyncio.to_thread(
                process_task,
                task["task_type"],
                task["cpu_cycles_giga"],
                Path(task["file_path"]).name if task["file_path"] else task["name"],
                None,
                task["file_path"],
            )
            execution_seconds = float(result["measured_processing_seconds"])
            network_seconds = 0.0
        else:
            service_url = settings.edge_url if location == "edge" else settings.cloud_url
            result, execution_seconds, network_seconds, server_metrics = await _execute_remotely(
                task, service_url
            )
        update_task(
            task["id"], status="completed", completed_at=utc_now(),
            execution_seconds=execution_seconds, network_seconds=network_seconds,
            result_json=result, server_metrics_json=server_metrics,
        )
    except HTTPException as exc:
        update_task(task["id"], status="failed", completed_at=utc_now(), error_message=exc.detail)
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        update_task(task["id"], status="failed", completed_at=utc_now(), error_message=str(exc))
        raise HTTPException(422, f"Task processing failed: {exc}") from exc
    return {
        "task_id": task["id"], "status": "completed", "location": location,
        "execution_seconds": execution_seconds, "network_seconds": network_seconds,
        "estimated_latency_ms": task["estimated_latency_ms"],
        "estimated_energy_joules": task["estimated_energy_joules"], "result": result,
        "server_metrics": server_metrics,
    }
