from pathlib import Path
import zipfile

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError

from backend.config import settings
from backend.database import connect, create_task, get_task, list_tasks, update_task, utc_now
from backend.schemas import TaskCreateRequest


router = APIRouter(prefix="/api/tasks", tags=["tasks"])
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}


def public_task(task: dict) -> dict:
    return {key: value for key, value in task.items() if key != "file_path"}


@router.post("/create", status_code=201)
async def create_task_endpoint(request: TaskCreateRequest) -> dict:
    task = create_task(
        task_type=request.task_type,
        name=request.name,
        input_size_mb=request.input_size_mb,
        cpu_cycles_giga=request.cpu_cycles_giga,
    )
    return public_task(task)


@router.post("/upload", status_code=201)
async def upload_task(
    file: UploadFile = File(...),
    task_type: str = Form(...),
    cpu_cycles_giga: float = Form(0.05, gt=0.0, le=2.0),
    name: str | None = Form(None, max_length=120),
) -> dict:
    if task_type not in {"image", "document"}:
        raise HTTPException(422, "Uploaded task_type must be image or document")
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    allowed_extensions = IMAGE_EXTENSIONS if task_type == "image" else DOCUMENT_EXTENSIONS
    if suffix not in allowed_extensions:
        raise HTTPException(415, "Unsupported file extension for the selected task type")
    content = await file.read(settings.max_upload_bytes + 1)
    if not content:
        raise HTTPException(422, "Uploaded file is empty")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_bytes}-byte upload limit")
    if task_type == "image":
        try:
            with Image.open(__import__("io").BytesIO(content)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(415, "Uploaded file is not a valid image") from exc
    elif suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(415, "Uploaded file is not a valid PDF")
    elif suffix == ".txt":
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(415, "Text files must use UTF-8 encoding") from exc
    elif suffix == ".docx" and not zipfile.is_zipfile(__import__("io").BytesIO(content)):
        raise HTTPException(415, "Uploaded file is not a valid DOCX document")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    task = create_task(
        task_type=task_type,
        name=(name or filename or "Uploaded task")[:120],
        input_size_mb=len(content) / (1024 * 1024),
        cpu_cycles_giga=cpu_cycles_giga,
    )
    destination = settings.upload_dir / f"{task['id']}{suffix}"
    try:
        destination.write_bytes(content)
    except OSError as exc:
        update_task(task["id"], status="failed", completed_at=utc_now(), error_message=str(exc))
        raise HTTPException(500, "The uploaded file could not be stored") from exc
    with connect() as connection:
        connection.execute("UPDATE tasks SET file_path = ? WHERE id = ?", (str(destination), task["id"]))
    task["file_path"] = str(destination)
    return public_task(task)


@router.get("")
async def get_tasks(
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)
) -> dict:
    tasks = list_tasks(limit, offset)
    return {"items": [public_task(task) for task in tasks], "count": len(tasks)}


@router.get("/{task_id}")
async def get_task_endpoint(task_id: str) -> dict:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return public_task(task)
