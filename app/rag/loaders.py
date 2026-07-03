import os

from langchain_community.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
)
from langchain_core.documents import Document

_LOADER_BY_EXTENSION = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".html": lambda path: BSHTMLLoader(path, open_encoding="utf-8"),
    ".htm": lambda path: BSHTMLLoader(path, open_encoding="utf-8"),
    ".csv": CSVLoader,
}


def load_document(path: str) -> list[Document]:
    ext = os.path.splitext(path)[1].lower()
    loader_factory = _LOADER_BY_EXTENSION.get(ext)
    if loader_factory is None:
        raise ValueError(f"Unsupported document type: {ext} ({path})")

    docs = loader_factory(path).load()
    for doc in docs:
        doc.metadata["source"] = os.path.basename(path)
    return docs


def load_knowledge_base(directory: str) -> list[Document]:
    documents: list[Document] = []
    for filename in sorted(os.listdir(directory)):
        path = os.path.join(directory, filename)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _LOADER_BY_EXTENSION:
            continue
        documents.extend(load_document(path))
    return documents
