"""MCP (Model Context Protocol) Server.

Exposes the banking assistant's tools and data sources as standardised
MCP server endpoints. External agents can discover and invoke these
tools at runtime via the MCP protocol over SSE/stdio transport.

Tools exposed:
  - classify_intent: Deterministic intent classification
  - knowledge_retrieval: RAG-backed knowledge lookup
  - get_account_info: Account information lookup (mock)
  - calculate_emi: EMI calculator
  - check_eligibility: Loan eligibility checker

Resources exposed:
  - knowledge_base://documents: List available KB documents
  - knowledge_base://stats: Vector store statistics
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()

from mcp.server import Server
from mcp.server.stdio import run_server
from mcp.types import (
    CallToolResult,
    ListResourcesResult,
    ListToolsResult,
    ReadResourceResult,
    Resource,
    TextContent,
    Tool,
)

server = Server("securebank-finbot")


@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=[
        Tool(
            name="classify_intent",
            description=(
                "Deterministically classify a customer banking message into "
                "intent categories (account_inquiry, card_dispute, loan_query, "
                "complaint, general_faq) with confidence scores and routing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_message": {
                        "type": "string",
                        "description": "The customer's message to classify"
                    }
                },
                "required": ["customer_message"]
            }
        ),
        Tool(
            name="knowledge_retrieval",
            description=(
                "Retrieve a grounded, cited answer from SecureBank's internal "
                "knowledge base using RAG (retrieval-augmented generation). "
                "Covers savings accounts, FDs, home loans, card disputes, "
                "UPI/NEFT charges, and general banking FAQs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The factual question to answer from the knowledge base"
                    },
                    "user_role": {
                        "type": "string",
                        "description": "User role for access control (customer, junior_analyst, senior_analyst, compliance_officer, admin)",
                        "default": "customer"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="calculate_emi",
            description="Calculate EMI for a loan given principal, rate, and tenure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "principal": {"type": "number", "description": "Loan amount in Rs"},
                    "annual_rate": {"type": "number", "description": "Annual interest rate (%)"},
                    "tenure_months": {"type": "integer", "description": "Loan tenure in months"}
                },
                "required": ["principal", "annual_rate", "tenure_months"]
            }
        ),
        Tool(
            name="check_loan_eligibility",
            description="Check basic loan eligibility based on income, age, and employment type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "monthly_income": {"type": "number", "description": "Net monthly income in Rs"},
                    "age": {"type": "integer", "description": "Applicant age in years"},
                    "employment_type": {"type": "string", "enum": ["salaried", "self_employed"]},
                    "loan_type": {"type": "string", "enum": ["home", "personal", "car"]}
                },
                "required": ["monthly_income", "age", "employment_type", "loan_type"]
            }
        ),
    ])


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "classify_intent":
        from app.tools import _classify
        result = _classify(arguments["customer_message"])
        return CallToolResult(content=[TextContent(type="text", text=result.model_dump_json())])

    elif name == "knowledge_retrieval":
        from app.rag.pipeline import RAGPipeline
        from app.llm import get_llm
        from app.rag.role_filter import filter_documents_by_role

        pipeline = RAGPipeline(llm=get_llm())
        user_role = arguments.get("user_role", "customer")
        rag_answer = pipeline.answer(arguments["query"], user_role=user_role)
        return CallToolResult(content=[TextContent(
            type="text",
            text=json.dumps({"answer": rag_answer.answer, "citations": rag_answer.citations})
        )])

    elif name == "calculate_emi":
        p = arguments["principal"]
        r = arguments["annual_rate"] / 12 / 100
        n = arguments["tenure_months"]
        if r == 0:
            emi = p / n
        else:
            emi = p * r * (1 + r) ** n / ((1 + r) ** n - 1)
        total = emi * n
        return CallToolResult(content=[TextContent(
            type="text",
            text=json.dumps({
                "emi": round(emi, 2),
                "total_payment": round(total, 2),
                "total_interest": round(total - p, 2),
            })
        )])

    elif name == "check_loan_eligibility":
        income = arguments["monthly_income"]
        age = arguments["age"]
        emp_type = arguments["employment_type"]
        loan_type = arguments["loan_type"]

        min_income = {"home": 25000, "personal": 20000, "car": 20000}
        max_age = {"home": 60, "personal": 58, "car": 60}
        min_age = 21

        eligible = (
            income >= min_income.get(loan_type, 20000)
            and min_age <= age <= max_age.get(loan_type, 60)
        )
        max_loan = income * 60 if eligible else 0

        return CallToolResult(content=[TextContent(
            type="text",
            text=json.dumps({
                "eligible": eligible,
                "max_loan_amount": max_loan,
                "reason": "Meets all criteria" if eligible else "Does not meet minimum requirements",
            })
        )])

    return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")])


@server.list_resources()
async def list_resources() -> ListResourcesResult:
    return ListResourcesResult(resources=[
        Resource(
            uri="knowledge_base://documents",
            name="Knowledge Base Documents",
            description="List of all documents in the SecureBank knowledge base",
        ),
        Resource(
            uri="knowledge_base://stats",
            name="Vector Store Statistics",
            description="Statistics about the vector store (chunk count, collection info)",
        ),
    ])


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    if uri == "knowledge_base://documents":
        kb_dir = os.getenv("KNOWLEDGE_BASE_DIR", "./data/knowledge_base")
        if os.path.exists(kb_dir):
            files = os.listdir(kb_dir)
        else:
            files = []
        return ReadResourceResult(contents=[TextContent(
            type="text", text=json.dumps({"documents": files})
        )])

    elif uri == "knowledge_base://stats":
        from app.rag.vectorstore import get_vectorstore
        vs = get_vectorstore()
        ids = vs.get()["ids"]
        return ReadResourceResult(contents=[TextContent(
            type="text",
            text=json.dumps({"chunk_count": len(ids), "collection": "securebank_knowledge_base"})
        )])

    return ReadResourceResult(contents=[TextContent(type="text", text="Unknown resource")])


async def main():
    await run_server(server)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
