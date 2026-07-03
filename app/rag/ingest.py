"""Ingestion CLI: loads the knowledge base, chunks it, embeds it, and
upserts it into the persistent Chroma collection.

Usage: python -m app.rag.ingest
Idempotent: clears the existing collection before re-ingesting, so it's
safe to re-run after the source documents change.
"""
import os

from dotenv import load_dotenv

load_dotenv()

from ..logging_utils import get_logger, log_event
from .chunking import chunk_documents
from .loaders import load_knowledge_base
from .vectorstore import get_vectorstore

logger = get_logger("rag.ingest")


def _knowledge_base_dir() -> str:
    return os.getenv("KNOWLEDGE_BASE_DIR", "./data/knowledge_base")


def run_ingest() -> int:
    kb_dir = _knowledge_base_dir()
    log_event(logger, "loading knowledge base", directory=kb_dir)
    documents = load_knowledge_base(kb_dir)
    log_event(logger, "loaded documents", count=len(documents))

    chunks = chunk_documents(documents)
    log_event(logger, "chunked documents", chunk_count=len(chunks))

    vectorstore = get_vectorstore()
    existing_ids = vectorstore.get()["ids"]
    if existing_ids:
        vectorstore.delete(ids=existing_ids)
        log_event(logger, "cleared existing collection", removed=len(existing_ids))

    ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    vectorstore.add_documents(documents=chunks, ids=ids)
    log_event(logger, "ingested chunks into vector store", count=len(chunks))
    return len(chunks)


if __name__ == "__main__":
    run_ingest()
