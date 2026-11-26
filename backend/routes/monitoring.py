import httpx

from fastapi import APIRouter
import psutil

from backend.config import settings


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


async def _server_resources(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{url}/resources")
            response.raise_for_status()
            return {"available": True, **response.json()}
    except httpx.HTTPError as exc:
        return {"available": False, "error": str(exc)}


@router.get("/resources")
async def resources() -> dict:
    edge, cloud = await __import__("asyncio").gather(
        _server_resources(settings.edge_url), _server_resources(settings.cloud_url)
    )
    return {
        "mobile": {
            "cpu_utilization": psutil.cpu_percent(interval=0.05) / 100.0,
            "memory_utilization": psutil.virtual_memory().percent / 100.0,
            "source": "measured on the backend host; approximate for a mobile client",
        },
        "edge": edge,
        "cloud": cloud,
        "network": {
            "latency_ms": settings.network_latency_ms,
            "bandwidth_mbps": settings.bandwidth_mbps,
            "source": "configurable simulation estimate; not a measured network probe",
        },
    }
