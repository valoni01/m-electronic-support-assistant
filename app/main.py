# app/main.py

import gradio as gr
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import uuid4
import structlog

from app.ui import build_ui
from app.observability.logging import configure_logging
from app.observability.metrics import metrics_response


configure_logging()

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        logger.info("http_request_started")

        response = await call_next(request)
        response.headers["x-request-id"] = request_id

        logger.info(
            "http_request_completed",
            status_code=response.status_code,
        )

        return response


app = FastAPI(
    title="Meridian Electronics AI Support Chatbot",
    version="0.1.0",
)

app.add_middleware(RequestContextMiddleware)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ready")
def readiness_check():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return metrics_response()


gradio_app = build_ui()

app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/",
)