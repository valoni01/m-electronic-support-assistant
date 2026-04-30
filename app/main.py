from fastapi import FastAPI
import gradio as gr

from app.ui import build_ui

app = FastAPI(
    title="Meridian Electronics AI Support Chatbot",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ready")
def readiness_check():
    return {"status": "ready"}


gradio_app = build_ui()

app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/",
)