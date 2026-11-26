from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    id: str
    task_type: str
    name: str
    input_size_mb: float
    cpu_cycles_giga: float
    status: str

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "Task":
        return cls(**{name: record[name] for name in cls.__dataclass_fields__})
