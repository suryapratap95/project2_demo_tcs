# FinBot – AI Banking Assistant

FinBot is a production-oriented AI banking assistant built with LangChain, FastAPI, and Streamlit. The project demonstrates how to build secure, enterprise-grade conversational AI using Retrieval-Augmented Generation (RAG), tool calling, Human-in-the-Loop approvals, and multi-agent orchestration.

---

## Features

### AI Agent
- LangChain agent with tool calling
- Deterministic intent classification
- Retrieval-Augmented Generation (RAG)
- Context-aware conversations
- Session-based memory

### Retrieval Pipeline
- Hybrid retrieval (Dense + BM25)
- Cross-encoder reranking
- Multi-query expansion
- Role-based document filtering
- Persistent Chroma vector database

### Enterprise Capabilities
- Human-in-the-Loop approval workflow
- Prompt versioning using YAML
- Redis-backed caching
- Redis conversation memory
- Structured logging
- LangSmith tracing support

### Multi-Agent Architecture
Specialized agents handle different banking domains including:

- Loan Services
- Customer Disputes
- Compliance
- General Banking Support

### APIs
- FastAPI backend
- OpenAPI (Swagger) documentation
- MCP (Model Context Protocol) server for tool interoperability

### Evaluation
- Automated RAG evaluation
- Regression testing
- Retrieval quality measurement
- Embedding drift detection
- HTML evaluation reports

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Backend | FastAPI |
| Frontend | Streamlit |
| LLM Framework | LangChain (LCEL) |
| Vector Database | ChromaDB |
| Embeddings | OpenAI Embeddings |
| Memory | Redis (Upstash) |
| Observability | LangSmith |
| Evaluation | Custom evaluation framework |
| MCP | Model Context Protocol |

---

# Getting Started

## 1. Clone the repository

```bash
git clone <repository-url>

cd finbot
```

---

## 2. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```powershell
python -m venv venv

venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create a `.env` file.

```bash
cp .env.example .env
```

Update it with your credentials.

```env
OPENAI_API_KEY=your-openai-key

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=banking-ai-assistant

UPSTASH_REDIS_REST_URL=https://your-upstash-instance.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-upstash-token
```

---

## 5. Build the knowledge base

Before starting the application, ingest the banking documents into the vector database.

```bash
python -m app.rag.ingest
```

This process:

- Loads documents
- Splits them into chunks
- Generates embeddings
- Stores vectors in ChromaDB

---

# Running the Application

## Start the backend

```bash
uvicorn app.main:app --reload
```

Once the server is running:

```
http://localhost:8000
```

Swagger documentation:

```
http://localhost:8000/docs
```

---

## Start the frontend

```bash
streamlit run frontend/streamlit.py
```

The Streamlit interface provides:

- Interactive chat
- User role selection
- HITL approval dashboard
- Session reset

---

## Start the MCP Server

To expose FinBot tools using the Model Context Protocol:

```bash
python -m app.mcp_server.server
```

Configure compatible MCP clients using:

```
mcp_config.json
```

---

# API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Service health check |
| POST | `/chat` | Chat with FinBot |
| POST | `/reset` | Clear session history |
| GET | `/hitl/pending/{session_id}` | Pending approvals |
| POST | `/hitl/decide` | Approve or reject requests |
| GET | `/prompts` | List prompt templates |
| GET | `/prompts/{name}` | Retrieve prompt |
| POST | `/prompts/reload` | Reload prompts without restart |

---

# Available Tools

The agent can invoke several tools depending on user intent.

| Tool | Purpose |
|------|----------|
| classify_intent | Classifies user requests |
| knowledge_retrieval | Retrieves information from the knowledge base |
| calculate_emi | Calculates loan EMI |
| check_loan_eligibility | Performs eligibility checks |

---

# Prompt Management

Prompt templates are stored as YAML files under the `prompts/` directory.

Example:

```yaml
version: "2.0"

name: finbot_system_prompt

author: finbot-team

updated: "2024-12-01"

template: |
  You are FinBot...
```

Advantages of YAML-based prompts:

- Version controlled
- Easy to review in Git
- Hot reload support
- No application restart required

Reload prompts:

```http
POST /prompts/reload
```

---

# Evaluation

The project includes an evaluation suite for measuring retrieval and response quality.

Run the complete evaluation:

```bash
python -m eval.run_eval
```

Run regression tests:

```bash
python -m eval.regression
```

Run drift detection:

```bash
python -m eval.drift_detector
```

Generate an HTML report:

```bash
python -m eval.dashboard
```

Evaluation reports are generated under:

```
eval/results/
```



# User Roles

The system supports role-aware document access.

- Customer
- Junior Analyst
- Senior Analyst
- Compliance Officer
- Administrator

Each role can only retrieve documents that match its access level.

---

# Human-in-the-Loop (HITL)

Certain high-risk actions require manual approval before execution.

Typical scenarios include:

- High-value transactions
- Compliance-sensitive operations
- Restricted customer requests

Approvals can be viewed and managed through the HITL API or the Streamlit interface.

---

# Observability

FinBot includes built-in monitoring and tracing support.

- LangSmith tracing
- Structured JSON logs
- Custom LangChain callbacks
- Prompt version tracking
- Evaluation dashboards

These features make it easier to debug agent behavior and monitor production deployments.

---

