import os
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from m18.backend.database import init_db

from .api import movie, review
from .services.sentiment import SentimentAnalyzer

sentiment_analyzer: SentimentAnalyzer | None = None


# 💡 Hugging Face에서 실시간으로 모델을 받는 함수 추가
def download_from_huggingface(model_path: str):
    # 파일이 존재하지 않을 때만 다운로드 진행
    if not os.path.exists(model_path):
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        # ⚠️ 본인의 Hugging Face 유저네임과 레포지토리 이름으로 꼭 변경하세요!
        repo_id = "joelchoi85/m18-bert-q"
        url = f"https://huggingface.co{repo_id}/resolve/main/model_quantized.onnx"

        print("📥 Hugging Face로부터 양자화 모델(122MB) 다운로드를 시작합니다...")

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(model_path, "wb") as f:
                f.writelines(response.iter_content(chunk_size=8192))
            print("✅ AI 모델 파일 다운로드 성공!")
        else:
            raise RuntimeError(
                f"❌ 모델 다운로드 실패. HTTP 상태 코드: {response.status_code}"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # global sentiment_analyzer
    print("backend 초기화")

    init_db()

    current_dir: str = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "core", "artifacts", "model_quantized.onnx")
    download_from_huggingface(model_path)
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
