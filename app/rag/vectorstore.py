import os

from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever

from .embeddings import get_embeddings

COLLECTION_NAME = "securebank_knowledge_base"


def _persist_dir() -> str:
    return os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")


def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=_persist_dir(),
    )


def get_dense_retriever(k: int = 5) -> BaseRetriever:
    return get_vectorstore().as_retriever(search_kwargs={"k": k})
