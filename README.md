# Langchain-BOT

A LangChain-based banking assistant with a tool-calling agent (deterministic
intent classification + RAG-backed knowledge retrieval), Redis-backed
session memory and response caching, a FastAPI backend, and a Streamlit
frontend.

## 1. Create and activate a virtual environment

```bash
python3 -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment variables

Copy the example file and fill in real values:

```bash
cp .env.example .env
```

Edit `.env` and set:

```
OPENAI_API_KEY="sk-..."
LANGSMITH_TRACING=true
LANGSMITH_API_KEY="lsv2_..."
LANGSMITH_PROJECT="banking-ai-assistant"
UPSTASH_REDIS_REST_URL="https://your-instance.upstash.io"
UPSTASH_REDIS_REST_TOKEN="your-upstash-token"
CHROMA_PERSIST_DIR="./data/chroma_db"
KNOWLEDGE_BASE_DIR="./data/knowledge_base"
```

**Never commit `.env`** (it's gitignored) **and never paste real secret
values into README.md or other tracked files** — only `.env` (local,
gitignored) should hold real keys/tokens.

## 4. Generate the sample knowledge base (optional — already committed)

The repo ships with a small synthetic SecureBank knowledge base under
`data/knowledge_base/` (HTML FAQs, a DOCX loan policy, a PDF card dispute
policy, a CSV fee schedule). Regenerate it if you want to tweak the content:

```bash
python -m data.generate_sample_docs
```

## 5. Ingest documents into the vector store

This loads the knowledge base, chunks it, embeds it with OpenAI, and
upserts it into a persistent Chroma collection. **Run this once before
starting the API** (and again any time the knowledge base changes):

```bash
python -m app.rag.ingest
```

## 6. Run the backend API

```bash
uvicorn app.main:app --reload
```

- `GET /health` — checks vector store + Redis connectivity
- `POST /chat` — `{"message": "...", "session_id": "..."}` → agent response
- `POST /reset` — `{"session_id": "..."}` → clears that session's memory

API docs: http://localhost:8000/docs

## 7. Run the Streamlit frontend

In a second terminal (with the venv activated):

```bash
streamlit run frontend/streamlit.py
```

Open http://localhost:8501 and chat with the bot. It talks to the API at
`FASTAPI_URL` (defaults to `http://localhost:8000`).

## 8. Run the evaluation harness

Measures retrieval quality (context precision/recall), answer quality
(faithfulness/answer relevancy), and end-to-end quality (correctness,
helpfulness, persona adherence, safety) against a fixed QA dataset grounded
in the sample knowledge base. All metrics are computed with LLM-judge
prompts against our own model rather than the `ragas` library — `ragas`
(every version) hard-fails to import in this environment because it
eagerly imports a `langchain_community.chat_models.vertexai` module that
current `langchain-community` no longer ships. Requires the vector store
to already be ingested (step 5).

```bash
python -m eval.run_eval
```

Results are written as structured JSON to `eval/results/eval_<timestamp>.json`.

## Project structure

```
app/
  main.py            FastAPI app: /chat, /reset, /health
  chain.py            Tool-calling agent (create_agent), memory + cache wiring
  tools.py             classify_intent (deterministic) + knowledge_retrieval (RAG)
  model.py             Pydantic request/response/domain models
  prompts.py            System prompt + few-shot examples
  memory.py             Redis-backed session chat history
  cache.py               Redis-backed response cache
  llm.py                  Shared ChatOpenAI instance
  logging_utils.py        Structured JSON logging
  rag/                     RAG pipeline: loaders, chunking, embeddings,
                           vector store, hybrid retrieval, multi-query
                           transform, cross-encoder reranking
data/
  knowledge_base/     Synthetic source documents (PDF/DOCX/HTML/CSV)
  generate_sample_docs.py   One-off generator for the above
eval/
  dataset.py            Hand-written QA pairs grounded in the knowledge base
  metrics.py              LLM-judge scoring (retrieval, answer, end-to-end)
  run_eval.py               CLI entrypoint, writes JSON results
frontend/
  streamlit.py         Chat UI
```
