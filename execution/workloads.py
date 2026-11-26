from hashlib import sha256
from io import BytesIO
from pathlib import Path
import time
import zipfile

from PIL import Image, UnidentifiedImageError


_image_model = None
_image_weights = None


def _classify_image(content: bytes) -> dict[str, object]:
    global _image_model, _image_weights
    try:
        import cv2
        import numpy as np
        import torch
        from torchvision.models import MobileNet_V2_Weights, mobilenet_v2
    except ImportError as exc:
        raise RuntimeError(
            "Image recognition requires OpenCV, torch, and torchvision packages"
        ) from exc
    if _image_model is None:
        try:
            _image_weights = MobileNet_V2_Weights.DEFAULT
            model = mobilenet_v2(weights=_image_weights)
            model.eval()
            _image_model = model
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load MobileNetV2 pretrained weights. Check network connection or cache: {exc}"
            ) from exc
    try:
        pixels = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if pixels is None:
            raise ValueError("The uploaded image could not be decoded")
        image = Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
        tensor = _image_weights.transforms()(image).unsqueeze(0)
    except (UnidentifiedImageError, OSError, cv2.error) as exc:
        raise ValueError("The uploaded image could not be decoded") from exc
    with torch.inference_mode():
        probabilities = _image_model(tensor).softmax(dim=1)[0]
        scores, indices = probabilities.topk(5)
    categories = _image_weights.meta["categories"]
    return {
        "labels": [
            {"label": categories[int(index)], "confidence": float(score)}
            for score, index in zip(scores, indices, strict=True)
        ],
        "model": "MobileNetV2",
    }


def _extract_document(content: bytes, filename: str) -> dict[str, object]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must use UTF-8 encoding") from exc
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
            from pypdf.errors import PdfReadError

            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, EOFError, OSError, ValueError) as exc:
            raise ValueError("The PDF could not be read") from exc
    elif suffix == ".docx":
        try:
            from docx import Document
            from docx.oxml.exceptions import InvalidXmlError
            from docx.opc.exceptions import PackageNotFoundError

            if not zipfile.is_zipfile(BytesIO(content)):
                raise ValueError("The uploaded DOCX document is invalid")
            document = Document(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        except (
            InvalidXmlError,
            PackageNotFoundError,
            ValueError,
            zipfile.BadZipFile,
            OSError,
            KeyError,
        ) as exc:
            raise ValueError("The DOCX document could not be read") from exc
    else:
        raise ValueError("Supported document formats are PDF, DOCX, and UTF-8 TXT")
    return {"text": text, "characters_extracted": len(text)}


def process_task(
    task_type: str,
    cpu_cycles_giga: float,
    file_name: str | None = None,
    file_content: bytes | None = None,
    file_path: str | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    if task_type == "compute":
        iterations = max(1, min(1_000_000, round(cpu_cycles_giga * 500_000)))
        digest = b"mobile-edge-computing"
        for _ in range(iterations):
            digest = sha256(digest).digest()
        result: dict[str, object] = {
            "iterations": iterations,
            "digest": digest.hex(),
            "workload": "repeated SHA-256",
        }
    elif task_type in ("image", "document"):
        if file_content is None and file_path is not None:
            file_content = Path(file_path).read_bytes()
        if file_content is None:
            raise ValueError("The task file is missing")
        if task_type == "image":
            result = _classify_image(file_content)
        else:
            result = _extract_document(file_content, file_name or "document.txt")
    else:
        raise ValueError(f"Unsupported task type: {task_type}")
    result["measured_processing_seconds"] = time.perf_counter() - started
    return result
