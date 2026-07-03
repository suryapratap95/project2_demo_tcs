import time

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from ..logging_utils import get_logger, log_event
from ..model import RAGAnswer, RetrievedChunk
from .query_transform import get_multi_query_retriever
from .reranker import rerank

logger = get_logger("rag.pipeline")

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are FinBot, SecureBank India's AI banking assistant. Answer the "
        "customer's question using ONLY the context below. If the context "
        "does not contain the answer, say you don't have that information "
        "on file rather than guessing. Be concise and professional. After "
        "the answer, on a new line, cite the sources you used in the format "
        "'Sources: <file1>, <file2>'.\n\nContext:\n{context}"
    )),
    ("human", "{question}"),
])


class RAGPipeline:
    def __init__(self, llm: BaseLanguageModel, retrieve_k: int = 5, rerank_top_n: int = 4):
        self._llm = llm
        self._retrieve_k = retrieve_k
        self._rerank_top_n = rerank_top_n
        self._retriever = get_multi_query_retriever(llm, k=retrieve_k)
        self._chain = ANSWER_PROMPT | llm

    def answer(self, query: str) -> RAGAnswer:
        start = time.monotonic()
        docs = self._retriever.invoke(query)
        reranked = rerank(query, docs, top_n=self._rerank_top_n)

        contexts = [
            RetrievedChunk(content=doc.page_content, source=doc.metadata.get("source", "unknown"), score=score)
            for doc, score in reranked
        ]
        context_block = "\n\n".join(
            f"[{c.source}] {c.content}" for c in contexts
        )
        citations = sorted({c.source for c in contexts})

        result = self._chain.invoke({"context": context_block, "question": query})
        answer_text = result.content if hasattr(result, "content") else str(result)

        log_event(
            logger,
            "rag pipeline answered query",
            query=query,
            retrieved_count=len(docs),
            reranked_count=len(reranked),
            sources=citations,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )

        return RAGAnswer(answer=answer_text, citations=citations, contexts=contexts)
