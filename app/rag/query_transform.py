from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever

from .hybrid_retriever import get_hybrid_retriever


def get_multi_query_retriever(llm: BaseLanguageModel, k: int = 5) -> BaseRetriever:
    """Multi-query transform: the LLM rephrases the user question into
    several variants, retrieves for each against the hybrid (BM25 + dense)
    retriever, and de-duplicates the union of results.
    """
    return MultiQueryRetriever.from_llm(
        retriever=get_hybrid_retriever(k=k),
        llm=llm,
    )
