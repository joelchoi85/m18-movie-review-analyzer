import os

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


class SentimentAnalyzer:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"지정한 ONNX 모델 파일을 찾을 수 없습니다: {model_path}"
            )

        model_dir = os.path.dirname(model_path)

        # 정적 타입 경고 방지를 위해 가시적으로 로드
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"]
        )

        self.emotion_map = {
            0: "공포",
            1: "당황",
            2: "분노",
            3: "슬픔",
            4: "중립",
            5: "행복",
            6: "혐오",
        }

    def analyze(self, text: str) -> dict:
        if not text or not text.strip():
            return {"label": "중립", "score": 0.0}

        try:
            assert self.tokenizer is not None, "Tokenizer가 로드되지 않았습니다."
            inputs = self.tokenizer(text, return_tensors="np")

            onnx_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            }
            if "token_type_ids" in inputs:
                onnx_inputs["token_type_ids"] = inputs["token_type_ids"].astype(
                    np.int64
                )

            # 3. ONNX 가속 추론 실행
            outputs = self.session.run(None, onnx_inputs)

            # 타입 검사기 오작동을 방지하기 위해 np.asarray로 감싸 정적 타입을 확정합니다.
            logits = np.asarray(outputs[0])

            # 배치 차원([1, 7] -> [7])을 제거하여 단일 리스트로 가공
            logits_flat = np.squeeze(logits)

            # 4. Softmax 연산으로 확률값 변환
            exp_logits = np.exp(logits_flat - np.max(logits_flat))
            probabilities = exp_logits / np.sum(exp_logits)

            # 5. 결과 추출
            predicted_idx = int(np.argmax(probabilities))
            sentiment_label = self.emotion_map.get(predicted_idx, "중립")
            sentiment_score = float(probabilities[predicted_idx])

            return {"label": sentiment_label, "score": round(sentiment_score, 4)}

        except Exception as e:
            print(f"🚨 [SentimentAnalyzer Error] {e}")
            return {"label": "중립", "score": 0.0}
