"""config.py — env vars, paths, model names.

Loads configuration from environment variables (and optionally a .env file)
once at import time. All paths resolve relative to the project root, which
is auto-detected from this file's location, so the service works regardless
of where it's launched from.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Project root = parent of src/
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# --- Paths ---------------------------------------------------------------
DB_PATH: Path = PROJECT_ROOT / os.getenv("DB_PATH", "data/meridian_wealth.db")
POLICY_DIR: Path = PROJECT_ROOT / os.getenv("POLICY_DIR", "data/policy_documents")
VECTORSTORE_DIR: Path = PROJECT_ROOT / os.getenv("VECTORSTORE_DIR", "vectorstore")

# --- Models --------------------------------------------------------------
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gpt-5-mini")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- RAG params ----------------------------------------------------------
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "300"))
RETRIEVER_K: int = int(os.getenv("RETRIEVER_K", "4"))

# --- Tavily --------------------------------------------------------------
TAVILY_MAX_RESULTS: int = int(os.getenv("TAVILY_MAX_RESULTS", "3"))

# --- FastAPI -------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")


def assert_required_keys() -> None:
    """Raise RuntimeError if any required API key is missing.

    Called from the FastAPI lifespan handler so the service fails fast on
    startup rather than at the first /chat request.
    """
    missing = [k for k in ("OPENAI_API_KEY", "TAVILY_API_KEY") if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. "
            "Set them in .env or your shell environment."
        )
