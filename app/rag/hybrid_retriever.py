import os

from langchain_classic.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.retrievers import BaseRetriever

from .chunking import chunk_documents
from .loaders import load_knowledge_base
from .vectorstore import get_dense_retriever

BM25_WEIGHT = 0.4
DENSE_WEIGHT = 0.6


def _knowledge_base_dir() -> str:
    return os.getenv("KNOWLEDGE_BASE_DIR", "./data/knowledge_base")


def get_bm25_retriever(k: int = 5) -> BM25Retriever:
    documents = load_knowledge_base(_knowledge_base_dir())
    chunks = chunk_documents(documents)
    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = k
    return retriever


def get_hybrid_retriever(k: int = 5) -> BaseRetriever:
    return EnsembleRetriever(
        retrievers=[get_bm25_retriever(k=k), get_dense_retriever(k=k)],
        weights=[BM25_WEIGHT, DENSE_WEIGHT],
    )
