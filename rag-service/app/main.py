from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_embedding_service
from app.api.routes_health import router as health_router
from app.api.routes_indexing import router as indexing_router
from app.api.routes_rag import router as rag_router
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="tactical-rag-service",
    version="0.1.0",
    description="Indexes tactical model outputs and serves grounded RAG tactical answers.",
)
app.include_router(health_router)
app.include_router(indexing_router)
app.include_router(rag_router)


@app.on_event("startup")
async def warmup_models() -> None:
    try:
        embedding = get_embedding_service()
        embedding.embed_text("warmup tactical query")
        logger.info("startup_warmup_done component=embedding")
    except Exception as exc:
        logger.warning("startup_warmup_failed component=embedding error=%s", str(exc))


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    payload = {"error": exc.message}
    if exc.details is not None:
        payload["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("index_request_failed error=%s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Unhandled internal error.", "details": str(exc)},
    )
