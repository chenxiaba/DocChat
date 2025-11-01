"""FastAPI application with hardened configuration and security controls."""

from __future__ import annotations

import base64
import binascii
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import uuid4

import structlog
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import run_agentic_pipeline, run_agentic_pipeline_stream
from .auth import router as auth_router
from .config import Settings, get_settings
from .database import init_db
from .memory import SQLiteMemory
from .retriever import build_vector_store


def _configure_logging(settings: Settings) -> None:
    """Configure structlog for structured logging."""

    timestamper = structlog.processors.TimeStamper(fmt="iso")
    processors = [
        structlog.contextvars.merge_contextvars,
        timestamper,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


settings = get_settings()
_configure_logging(settings)
init_db()

logger = structlog.get_logger(__name__)

app = FastAPI(title="DocChat AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

memory = SQLiteMemory()

app.include_router(auth_router)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


class PDFDocument(BaseModel):
    filename: str = Field(..., min_length=1)
    content: str = Field(..., description="Base64 encoded file content")


def _extract_api_key(authorization: str | None, explicit_key: str | None) -> Optional[str]:
    if explicit_key:
        return explicit_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


async def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.api_keys:
        return

    candidate = _extract_api_key(authorization, x_api_key)
    if candidate and candidate in settings.api_keys:
        return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


def _sanitize_filename(filename: str, data_dir: Path) -> Path:
    base = Path(filename).name
    if not base.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 PDF 文件上传")

    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    candidate = data_dir / sanitized
    if candidate.exists():
        candidate = data_dir / f"{candidate.stem}_{uuid4().hex}{candidate.suffix}"
    return candidate


def _decode_document_content(document: PDFDocument) -> bytes:
    try:
        return base64.b64decode(document.content, validate=True)
    except (binascii.Error, ValueError) as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件 {document.filename} 解码失败",
        ) from exc


def _validate_pdf_bytes(data: bytes, settings: Settings) -> None:
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件过大")

    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件格式不是有效的 PDF")


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - defensive
    logger.exception("unhandled_exception", path=str(request.url), error=str(exc))
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "服务器内部错误"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest, _: None = Depends(require_api_key)) -> dict[str, str]:
    try:
        memory.save("user", request.query)
        response = run_agentic_pipeline(request.query)
        memory.save("assistant", response)
        return {"response": response}
    except Exception as exc:  # pragma: no cover - 调用链防护
        logger.exception("chat_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="生成回复失败") from exc


@app.post("/chat_stream")
async def chat_stream(request: ChatRequest, _: None = Depends(require_api_key)) -> StreamingResponse:
    memory.save("user", request.query)

    async def generate_response() -> Iterable[str]:
        full_response = ""
        try:
            async for chunk in run_agentic_pipeline_stream(request.query):
                if chunk.startswith("data: ") and not chunk.endswith("[DONE]\n\n"):
                    content = chunk[6:-2]
                    full_response += content
                yield chunk
        except Exception as exc:  # pragma: no cover - 调用链防护
            logger.exception("chat_stream_failed", error=str(exc))
            yield "data: [错误] 对话生成失败\n\n"
        else:
            memory.save("assistant", full_response)

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )


@app.post("/upload_pdfs")
async def upload_pdfs(
    files: List[PDFDocument],
    background_tasks: BackgroundTasks,
    _: None = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
) -> dict[str, int]:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未提供任何文件")

    stored_paths: list[str] = []
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    for document in files:
        file_bytes = _decode_document_content(document)
        _validate_pdf_bytes(file_bytes, settings)
        path = _sanitize_filename(document.filename, data_dir)
        path.write_bytes(file_bytes)
        stored_paths.append(str(path))

    if stored_paths:
        background_tasks.add_task(build_vector_store, stored_paths)

    logger.info("pdf_uploaded", files=len(stored_paths))
    return {"status": "知识库已更新", "count": len(stored_paths)}


@app.post("/reset_memory")
async def reset_memory(_: None = Depends(require_api_key)) -> dict[str, str]:
    memory.reset()
    return {"status": "记忆已清空"}


@app.get("/list_documents")
async def list_documents(_: None = Depends(require_api_key)) -> dict[str, list[dict[str, float | str]]]:
    documents: list[dict[str, float | str]] = []
    if settings.data_dir.exists():
        for file_path in settings.data_dir.glob("*.pdf"):
            file_size = file_path.stat().st_size
            documents.append(
                {
                    "filename": file_path.name,
                    "size": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                }
            )

    return {"documents": documents}


def _resolve_document_path(filename: str, data_dir: Path) -> Path:
    target = data_dir / Path(filename).name
    try:
        target_resolved = target.resolve(strict=False)
    except FileNotFoundError:  # pragma: no cover - path doesn't exist yet
        target_resolved = target

    if target_resolved.suffix.lower() != ".pdf" or target_resolved.parent.resolve() != data_dir.resolve():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的文件名")

    return target_resolved


@app.post("/delete_document/{filename}")
async def delete_document(
    filename: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_api_key),
) -> dict[str, str]:
    target = _resolve_document_path(filename, settings.data_dir)

    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    target.unlink()

    remaining_docs = [str(path) for path in settings.data_dir.glob("*.pdf")]
    if remaining_docs:
        background_tasks.add_task(build_vector_store, remaining_docs)
    elif settings.vector_db_path.exists():
        shutil.rmtree(settings.vector_db_path)

    return {"status": "成功", "message": f"文档 {target.name} 已删除"}


@app.post("/clear_knowledge_base")
async def clear_knowledge_base(_: None = Depends(require_api_key)) -> dict[str, str]:
    removed: list[str] = []

    if settings.vector_db_path.exists():
        shutil.rmtree(settings.vector_db_path)
        removed.append("向量数据库")

    if settings.data_dir.exists():
        for pdf in settings.data_dir.glob("*.pdf"):
            pdf.unlink()
            removed.append(pdf.name)

    if removed:
        return {"status": "知识库已清空", "message": f"已删除：{', '.join(removed)}"}
    return {"status": "知识库为空", "message": "没有可删除的内容"}


@app.post("/clear_history")
async def clear_history(_: None = Depends(require_api_key)) -> dict[str, str]:
    return {"status": "对话历史已清空", "message": "前端对话历史存储已清理"}

