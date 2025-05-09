from sentence_transformers import SentenceTransformer

class Vectorizer:
    def __init__(self):
        # 한국어 모델 로드
        self.model = SentenceTransformer("jhgan/ko-sroberta-multitask")

    def vectorize(self, text: str) -> list:
        # 텍스트를 벡터로 변환
        if text is None:
            return None
        return self.model.encode(text).tolist()