from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TaskType = Literal["image", "document", "compute"]


class TaskCreateRequest(BaseModel):
    task_type: TaskType
    name: str = Field(default="Untitled task", min_length=1, max_length=120)
    input_size_mb: float = Field(default=1.0, ge=0.0, le=20.0)
    cpu_cycles_giga: float = Field(default=0.05, gt=0.0, le=2.0)


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    task_type: TaskType
    name: str
    input_size_mb: float
    cpu_cycles_giga: float
    status: str


class TaskIdRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64)


class DecisionResponse(BaseModel):
    task_id: str
    action: int
    location: Literal["local", "edge", "cloud"]
    policy: str
    estimated_latency_ms: float
    estimated_energy_joules: float
    reward: float
    state: list[float]


class ExecutionRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64)
    client_execution_seconds: float | None = Field(default=None, ge=0.0, le=180.0)
    client_result: dict[str, Any] | None = None


class ExecutionResponse(BaseModel):
    task_id: str
    status: str
    location: str
    execution_seconds: float
    network_seconds: float
    estimated_latency_ms: float
    estimated_energy_joules: float
    result: dict[str, Any]
