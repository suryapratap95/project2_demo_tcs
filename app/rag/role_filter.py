"""Role-based RAG access control.

Restricts document retrieval based on authenticated user roles.
Documents are tagged with access_level metadata during ingestion.
At retrieval time, chunks are filtered to only return content the
user's role is authorized to see.

Role hierarchy (lowest to highest):
  customer < junior_analyst < senior_analyst < compliance_officer < admin

Each role sees all content at or below its clearance level.
"""
from langchain_core.documents import Document

ROLE_HIERARCHY = {
    "customer": 1,
    "junior_analyst": 2,
    "senior_analyst": 3,
    "compliance_officer": 4,
    "admin": 5,
}

DOCUMENT_ACCESS_RULES: dict[str, int] = {
    "faq_general.html": 1,
    "savings_account_faq.html": 1,
    "upi_neft_charges.csv": 1,
    "home_loan_policy.docx": 2,
    "card_dispute_policy.pdf": 3,
}

DEFAULT_ACCESS_LEVEL = 1


def get_access_level(role: str) -> int:
    return ROLE_HIERARCHY.get(role, 1)


def get_document_clearance(source: str) -> int:
    filename = source.rsplit("/", 1)[-1] if "/" in source else source
    return DOCUMENT_ACCESS_RULES.get(filename, DEFAULT_ACCESS_LEVEL)


def filter_documents_by_role(documents: list[Document], user_role: str) -> list[Document]:
    """Filter retrieved documents based on user role clearance."""
    user_level = get_access_level(user_role)
    filtered = []
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        doc_level = get_document_clearance(source)
        if user_level >= doc_level:
            filtered.append(doc)
    return filtered


def enrich_metadata_with_access(documents: list[Document]) -> list[Document]:
    """Add access_level metadata to documents during ingestion."""
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        doc.metadata["access_level"] = get_document_clearance(source)
    return documents


def get_role_description(role: str) -> str:
    descriptions = {
        "customer": "End customer - access to public FAQs and general information only",
        "junior_analyst": "Junior bank analyst - access to general policies and loan documents",
        "senior_analyst": "Senior analyst - access to dispute policies and internal procedures",
        "compliance_officer": "Compliance officer - full access to all documents including audit trails",
        "admin": "System admin - unrestricted access to all documents and configurations",
    }
    return descriptions.get(role, "Unknown role - restricted to public access")
