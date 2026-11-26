import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import time
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
import psutil

from execution.workloads import process_task


def create_server_app(server_name: str) -> FastAPI:
    active_tasks = 0
    completed_tasks = 0
    failed_tasks = 0
    state_lock = asyncio.Lock()
    server_process = psutil.Process()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(title=f"MEC {server_name.title()} Server", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "server": server_name}

    @app.get("/resources")
    async def resources() -> dict[str, Any]:
        virtual_memory = psutil.virtual_memory()
        process_memory = server_process.memory_info().rss
        return {
            "server": server_name,
            "cpu_utilization": psutil.cpu_percent(interval=0.05) / 100.0,
            "memory_utilization": virtual_memory.percent / 100.0,
            "process_memory_bytes": process_memory,
            "process_memory_utilization": process_memory / virtual_memory.total,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "queue_length": max(0, active_tasks - 1),
        }

    @app.post("/execute")
    async def execute(
        task_type: str = Form(...),
        cpu_cycles_giga: float = Form(..., gt=0.0, le=2.0),
        file: UploadFile | None = File(None),
    ) -> dict[str, Any]:
        nonlocal active_tasks, completed_tasks, failed_tasks
        if task_type not in {"compute", "image", "document"}:
            raise HTTPException(422, "Unsupported task type")
        content = await file.read(20 * 1024 * 1024 + 1) if file else None
        if content is not None and len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "File exceeds the server limit")
        async with state_lock:
            active_tasks += 1
        started = time.perf_counter()
        cpu_before = server_process.cpu_times()
        try:
            result = await asyncio.to_thread(
                process_task,
                task_type,
                cpu_cycles_giga,
                file.filename if file else None,
                content,
            )
            execution_seconds = float(result["measured_processing_seconds"])
            cpu_after = server_process.cpu_times()
            round_trip_processing_seconds = time.perf_counter() - started
            virtual_memory = psutil.virtual_memory()
            memory_bytes = server_process.memory_info().rss
            process_cpu_seconds = (
                cpu_after.user + cpu_after.system - cpu_before.user - cpu_before.system
            )
            server_metrics = {
                "server": server_name,
                "cpu_utilization": psutil.cpu_percent(interval=0.05) / 100.0,
                "process_cpu_percent": (
                    100.0 * process_cpu_seconds / round_trip_processing_seconds
                    if round_trip_processing_seconds > 0
                    else 0.0
                ),
                "memory_utilization": virtual_memory.percent / 100.0,
                "process_memory_bytes": memory_bytes,
                "process_memory_utilization": memory_bytes / virtual_memory.total,
                "process_cpu_seconds": process_cpu_seconds,
                "active_tasks": active_tasks,
                "sampled_at": datetime.now(timezone.utc).isoformat(),
            }
            async with state_lock:
                completed_tasks += 1
            return {
                "server": server_name,
                "execution_seconds": execution_seconds,
                "round_trip_processing_seconds": round_trip_processing_seconds,
                "server_metrics": server_metrics,
                "result": result,
            }
        except (RuntimeError, ValueError, OSError) as exc:
            async with state_lock:
                failed_tasks += 1
            raise HTTPException(422, f"{server_name} task processing failed: {exc}") from exc
        finally:
            async with state_lock:
                active_tasks -= 1

    return app
