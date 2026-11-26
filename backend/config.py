import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _configured_path(variable: str, default: Path) -> Path:
    value = Path(os.getenv(variable, str(default)))
    return value if value.is_absolute() else ROOT_DIR / value


class Settings:
    def __init__(self) -> None:
        self.database_path = _configured_path(
            "MEC_DATABASE_PATH", ROOT_DIR / "backend" / "mec.sqlite3"
        )
        self.upload_dir = _configured_path(
            "MEC_UPLOAD_DIR", ROOT_DIR / "backend" / "uploads"
        )
        self.max_upload_bytes = int(os.getenv("MEC_MAX_UPLOAD_BYTES", 20 * 1024 * 1024))
        self.allowed_origins = [
            origin.strip()
            for origin in os.getenv(
                "MEC_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]
        self.edge_url = os.getenv("MEC_EDGE_URL", "http://127.0.0.1:8001").rstrip("/")
        self.cloud_url = os.getenv("MEC_CLOUD_URL", "http://127.0.0.1:8002").rstrip("/")
        self.network_latency_ms = float(os.getenv("MEC_NETWORK_LATENCY_MS", "45"))
        self.bandwidth_mbps = float(os.getenv("MEC_BANDWIDTH_MBPS", "25"))
        self.model_path = _configured_path(
            "MEC_MODEL_PATH", ROOT_DIR / "ai_engine" / "models" / "dqn.pt"
        )


settings = Settings()
