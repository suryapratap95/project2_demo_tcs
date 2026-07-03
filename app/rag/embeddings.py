import os

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")


def get_embeddings() -> Embeddings:
    """Factory for the configured embedding provider.

    Only OpenAI is wired up right now (matches the API key available in
    .env). Kept as a factory so HF/Cohere embeddings can be added later
    without touching callers.
    """
    if EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddings(model="text-embedding-3-small")
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")
