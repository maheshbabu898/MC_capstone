from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3

from backend.config import settings
from backend.database import initialize_database
from backend.routes import analytics, monitoring, offloading, tasks


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    initialize_database()
    yield


app = FastAPI(
    title="MEC Intelligent Offloading API",
    description="Mobile, edge, and cloud task execution with a trained DQN offloading policy.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.vercel\.app)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tasks.router)
app.include_router(offloading.router)
app.include_router(monitoring.router)
app.include_router(analytics.router)


@app.exception_handler(sqlite3.Error)
async def database_error_handler(_, exception: sqlite3.Error) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"Database operation failed: {exception}"})


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"name": "MEC Intelligent Offloading API", "docs": "/docs", "status": "ready"}


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "healthy"}
