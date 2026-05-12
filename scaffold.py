"""
scaffold.py — Create the financial-analyst-api FastAPI project skeleton.

Usage
-----
    python scaffold.py                          # creates ./financial-analyst-api
    python scaffold.py --root my-project        # custom root name
    python scaffold.py --root . --force         # scaffold into the cwd

Creates all directories and placeholder files described in the plan:
top-level config (app.py, requirements.txt, .env.example, .gitignore,
README.md), the src/ package (config, schemas, database_queries,
rag_pipeline, agent_tools, react_agent), the tests/ package, and the
empty data/ + vectorstore/ runtime directories.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent


# ---------------------------------------------------------------------------
# File-content builders
# ---------------------------------------------------------------------------

def py_stub(module: str, purpose: str) -> str:
    """Return a minimal Python module placeholder with a docstring."""
    return dedent(f'''\
        """{module} — {purpose}

        TODO: implement.
        """
    ''')


def requirements_txt() -> str:
    return dedent("""\
        # Core agent framework (LangChain v1 / LangGraph v1)
        langchain>=1.0,<2.0
        langchain-core>=1.0,<2.0
        langgraph>=1.0,<2.0

        # LLM + embeddings provider
        langchain-openai>=1.0,<2.0
        openai>=1.50.0

        # Community integrations (FAISS vectorstore, PyPDF loader)
        langchain-community>=0.3,<0.4
        langchain-text-splitters>=0.3,<0.4

        # Vector store + PDF parsing
        faiss-cpu>=1.8.0
        pypdf>=4.0.0

        # Live web search tool
        langchain-tavily>=0.1,<0.2
        tavily-python>=0.5.0

        # FastAPI service layer
        fastapi>=0.115.0
        uvicorn[standard]>=0.30.0
        pydantic>=2.7.0
        pydantic-settings>=2.4.0

        # Config / env
        python-dotenv>=1.0.0
    """)


def env_example() -> str:
    return dedent("""\
        # LLM + embeddings
        OPENAI_API_KEY=sk-...

        # Live web search
        TAVILY_API_KEY=tvly-...

        # Paths (relative to project root)
        DB_PATH=data/meridian_wealth.db
        POLICY_DIR=data/policy_documents
        VECTORSTORE_DIR=vectorstore

        # Model config
        AGENT_MODEL=gpt-5-mini
        EMBEDDING_MODEL=text-embedding-3-small

        # FastAPI
        API_HOST=0.0.0.0
        API_PORT=8000
        LOG_LEVEL=info
    """)


def gitignore() -> str:
    return dedent("""\
        # Python
        __pycache__/
        *.py[cod]
        *$py.class
        *.egg-info/
        .pytest_cache/
        .mypy_cache/
        .ruff_cache/

        # Virtualenvs
        .venv/
        venv/
        env/

        # Secrets
        .env
        .env.local
        *.pem

        # Project data / build artefacts
        vectorstore/*
        !vectorstore/.gitkeep
        data/*.db
        data/*.db-journal

        # IDE
        .idea/
        .vscode/
        *.swp
        .DS_Store
    """)


def readme() -> str:
    return dedent("""\
        # Financial Analyst API

        FastAPI service wrapping a LangChain v1 / LangGraph ReAct agent for
        Meridian Wealth Partners. The agent has five tools backed by a SQLite
        database, a FAISS vector store over policy PDFs, and Tavily web search.

        ## Quick start

        ```bash
        python -m venv .venv
        source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
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
    """)


def app_py_stub() -> str:
    return dedent('''\
        """app.py — FastAPI entry point.

        Wires up:
          * Lifespan: build/load FAISS index, instantiate the agent once
          * /chat  POST  → run agent, return ChatResponse
          * /health GET  → readiness probe (db, vectorstore, Tavily)

        TODO: implement.
        """
    ''')


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def write_file(path: Path, content: str) -> None:
    """Create parent dirs and write `content` to `path` (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  file     {path}")


def make_dir(path: Path, keep: bool = True) -> None:
    """Create directory; optionally drop a .gitkeep so git tracks it empty."""
    path.mkdir(parents=True, exist_ok=True)
    print(f"  dir      {path}")
    if keep:
        (path / ".gitkeep").touch()


# ---------------------------------------------------------------------------
# Scaffold builder
# ---------------------------------------------------------------------------

def build_top_level(root: Path) -> None:
    write_file(root / "app.py", app_py_stub())
    write_file(root / "requirements.txt", requirements_txt())
    write_file(root / ".env.example", env_example())
    write_file(root / ".gitignore", gitignore())
    write_file(root / "README.md", readme())


def build_src(root: Path) -> None:
    src = root / "src"
    modules = {
        "__init__.py": "",
        "config.py": py_stub("config", "env vars, paths, model names"),
        "schemas.py": py_stub("schemas", "Pydantic request/response models for /chat"),
        "database_queries.py": py_stub("database_queries", "SQL helpers over meridian_wealth.db"),
        "rag_pipeline.py": py_stub("rag_pipeline", "PDF load → split → embed → FAISS build/load → retriever"),
        "agent_tools.py": py_stub("agent_tools", "LangChain @tool wrappers for portfolio/market/calc/policy/web"),
        "react_agent.py": py_stub("react_agent", "System prompt + build_agent() factory using create_agent"),
    }
    for name, content in modules.items():
        write_file(src / name, content)


def build_tests(root: Path) -> None:
    tests = root / "tests"
    files = {
        "__init__.py": "",
        "test_database_queries.py": py_stub("test_database_queries", "Tests for SQL helpers"),
        "test_rag_pipeline.py": py_stub("test_rag_pipeline", "Tests for the RAG pipeline"),
        "test_agent.py": py_stub("test_agent", "Tests for tool wiring and agent invocation"),
    }
    for name, content in files.items():
        write_file(tests / name, content)


def build_runtime_dirs(root: Path) -> None:
    make_dir(root / "data")
    make_dir(root / "data" / "policy_documents")
    make_dir(root / "vectorstore")


def build_scaffold(root: Path) -> None:
    print(f"Scaffolding into {root.resolve()}\n")
    root.mkdir(parents=True, exist_ok=True)
    build_top_level(root)
    build_src(root)
    build_tests(root)
    build_runtime_dirs(root)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the financial-analyst-api project skeleton."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("financial-analyst-api"),
        help="Root directory to create (default: ./financial-analyst-api)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Proceed without prompting even if the root is non-empty.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.root

    if root.exists() and any(root.iterdir()) and not args.force:
        reply = input(f"{root} exists and is not empty. Continue? [y/N] ").strip().lower()
        if reply != "y":
            print("Aborted.")
            return 1

    build_scaffold(root)
    print(f"\n✅ Done. Next steps:")
    print(f"   cd {root}")
    print(f"   python -m venv .venv && source .venv/bin/activate")
    print(f"   pip install -r requirements.txt")
    print(f"   cp .env.example .env   # then fill in API keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
