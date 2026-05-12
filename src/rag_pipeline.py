"""rag_pipeline.py — PDF load → split → embed → FAISS build/load → retriever.

The FAISS index is built once from the policy PDFs and persisted to
VECTORSTORE_DIR. Subsequent startups load from disk, which is fast and
avoids re-paying the embedding cost. Call `get_or_build_vectorstore()`
from the FastAPI lifespan handler.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    POLICY_DIR,
    RETRIEVER_K,
    VECTORSTORE_DIR,
)

logger = logging.getLogger(__name__)


def _get_embeddings() -> OpenAIEmbeddings:
    """Construct the OpenAI embeddings client (model name from config)."""
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def load_policy_pdfs(policy_dir: Path = POLICY_DIR) -> list[Document]:
    """Load every PDF in `policy_dir`; return one Document per page."""
    if not policy_dir.exists():
        raise FileNotFoundError(f"Policy directory not found: {policy_dir}")

    pdf_files = sorted(policy_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {policy_dir}")

    pages: list[Document] = []
    for pdf in pdf_files:
        loaded = PyPDFLoader(str(pdf)).load()
        pages.extend(loaded)
        logger.info("Loaded %s: %d pages", pdf.name, len(loaded))
    logger.info("Total pages loaded: %d", len(pages))
    return pages


def split_documents(
    docs: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Split docs into overlapping chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("Split into %d chunks (size=%d, overlap=%d)", len(chunks), chunk_size, chunk_overlap)
    return chunks


def _build_vectorstore(chunks: list[Document]) -> FAISS:
    logger.info("Embedding %d chunks with %s ...", len(chunks), EMBEDDING_MODEL)
    return FAISS.from_documents(chunks, _get_embeddings())


def _save_vectorstore(vs: FAISS, directory: Path = VECTORSTORE_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    vs.save_local(str(directory))
    logger.info("FAISS index saved to %s", directory)


def _load_vectorstore(directory: Path = VECTORSTORE_DIR) -> FAISS:
    # `allow_dangerous_deserialization=True` is OK here — we wrote this pickle ourselves.
    return FAISS.load_local(
        str(directory),
        _get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def _vectorstore_exists(directory: Path = VECTORSTORE_DIR) -> bool:
    return (directory / "index.faiss").is_file() and (directory / "index.pkl").is_file()


def get_or_build_vectorstore(rebuild: bool = False) -> FAISS:
    """Load FAISS from disk if present, otherwise build from PDFs and persist.

    Set `rebuild=True` to force re-embedding (e.g. after policy PDFs change).
    """
    if not rebuild and _vectorstore_exists():
        logger.info("Loading existing FAISS index from %s", VECTORSTORE_DIR)
        return _load_vectorstore()

    logger.info("Building FAISS index from PDFs in %s", POLICY_DIR)
    pages = load_policy_pdfs()
    chunks = split_documents(pages)
    vs = _build_vectorstore(chunks)
    _save_vectorstore(vs)
    return vs


def get_retriever(vectorstore: FAISS, k: int = RETRIEVER_K) -> VectorStoreRetriever:
    """Return a top-k similarity retriever bound to the given vector store."""
    return vectorstore.as_retriever(search_kwargs={"k": k})
