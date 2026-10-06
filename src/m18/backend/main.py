import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from m18.backend.database import init_db

from .api import movie, review
from .services.sentiment import SentimentAnalyzer

sentiment_analyzer: SentimentAnalyzer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # global sentiment_analyzer
    print("backend 초기화")

    init_db()

    current_dir: str = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "core", "artifacts", "model_quantized.onnx")

    print("AI Model Loading...")
    app.state.analyzer = SentimentAnalyzer(model_path=model_path)
    print("AI Model Loaded")

    yield


app = FastAPI(
    title="AI Review API",
    description="Streamlit Frontend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movie.router, prefix="/api/v1", tags=["Movies"])
app.include_router(review.router, prefix="/api/v1", tags=["Reviews"])


@app.get("/", tags=["Root"])
def root_check():
    return {"status": "good", "message": "백엔드가 살아 있음"}
