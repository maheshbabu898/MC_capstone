from fastapi import APIRouter, Query

from ai_engine.evaluate import evaluate
from backend.database import performance_summary


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/performance")
async def performance() -> dict:
    return performance_summary()


@router.get("/comparison")
async def comparison(tasks: int = Query(100, ge=1, le=5000), seed: int = Query(42)) -> dict:
    return evaluate(tasks, seed)
