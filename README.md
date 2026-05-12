# Financial Analyst API

FastAPI service wrapping a LangChain v1 / LangGraph ReAct agent for
Meridian Wealth Partners. The agent has five tools backed by a SQLite
database, a FAISS vector store over policy PDFs, and Tavily web search.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then fill in API keys

# Drop your SQLite DB and policy PDFs into ./data/
# data/meridian_wealth.db
# data/policy_documents/*.pdf

uvicorn app:app --reload
```

Open http://localhost:8000/docs for the OpenAPI UI.

## Project layout

```
app.py                  FastAPI entry point
src/
  config.py             env vars, paths, model names
  schemas.py            Pydantic request/response models
  database_queries.py   SQL helpers
  rag_pipeline.py       PDF → split → embed → FAISS
  agent_tools.py        @tool wrappers
  react_agent.py        System prompt + create_agent factory
data/                   SQLite DB + policy PDFs (gitignored)
vectorstore/            persisted FAISS index (gitignored)
tests/                  pytest suite
```
