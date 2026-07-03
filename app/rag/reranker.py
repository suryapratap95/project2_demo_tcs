from functools import lru_cache

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def _get_model() -> CrossEncoder:
    return CrossEncoder(MODEL_NAME)


def rerank(query: str, documents: list[Document], top_n: int = 4) -> list[tuple[Document, float]]:
    if not documents:
        return []
    model = _get_model()
    pairs = [(query, doc.page_content) for doc in documents]
    scores = model.predict(pairs)
    scored = sorted(zip(documents, scores), key=lambda pair: pair[1], reverse=True)
    return [(doc, float(score)) for doc, score in scored[:top_n]]
