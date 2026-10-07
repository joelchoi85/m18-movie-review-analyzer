import os
import threading
from contextlib import asynccontextmanager

import requests
import streamlit as st
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
        url = f"https://huggingface.co/{repo_id}/resolve/main/model_quantized.onnx"

        print("📥 Hugging Face로부터 양자화 모델(122MB) 다운로드를 시작합니다...")

        headers = {}
        if "HF_TOKEN" in st.secrets:
            headers["Authorization"] = f"Bearer {st.secrets['HF_TOKEN']}"

        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(model_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print("✅ AI 모델 파일 다운로드 성공!")
        else:
            raise RuntimeError(
                f"❌ 모델 다운로드 실패. HTTP 상태 코드: {response.status_code}"
            )


# 💡 백그라운드에서 실행될 모델 로드 전체 파이프라인
def bg_model_loader(app: FastAPI, model_path: str):
    try:
        # 1. 파일이 없으면 허깅페이스에서 다운로드 (수십 초 소요)
        download_from_huggingface(model_path)

        # 2. ONNX 인프런스 세션 로드 (수 초 소요)
        print("💡 [BG] AI Model Loading started in background...")
        app.state.analyzer = SentimentAnalyzer(model_path=model_path)

        # 3. 완료 플래그 활성화
        app.state.model_ready = True
        print("✅ [BG] AI Model Successfully Loaded & Ready!")
    except Exception as e:
        print(f"❌ [BG] Background model loading failed: {e}")
        app.state.model_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # global sentiment_analyzer
    print("backend 초기화")
    init_db()

    # 초기 상태 설정
    app.state.model_ready = False
    app.state.analyzer = None

    current_dir: str = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "core", "artifacts", "model_quantized.onnx")
    # 💡 핵심: 모델 다운로드와 로드를 백그라운드 스레드로 던져버리고 lifespan은 즉시 통과!
    bg_thread = threading.Thread(
        target=bg_model_loader, args=(app, model_path), daemon=True
    )
    bg_thread.start()

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
