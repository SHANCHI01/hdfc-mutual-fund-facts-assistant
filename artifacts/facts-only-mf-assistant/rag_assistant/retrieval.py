"""Persistent Chroma indexing and scheme-aware retrieval."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .sources import EMBEDDING_MODEL


def _chroma():
    import chromadb
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    return chromadb, DefaultEmbeddingFunction()

def _lexical_bonus(query: str, text: str) -> float:
    """Prefer the exact fact label within semantically retrieved candidates."""
    question = re.sub(r"[\s-]+", " ", query.casefold())
    passage = re.sub(r"[\s-]+", " ", text.casefold())
    if re.search(r"\b(?:min|minimum)\s+sip\b", question) and re.search(r"\b(?:min|minimum)\s+sip\b", passage):
        return 0.45
    if re.search(r"\bbenchmark\b", question):
        if re.search(r"\bbenchmark(?:ed)?\b.{0,300}\b(?:nifty|sensex|bse)\b", passage):
            return 0.55
        return 0.10 if re.search(r"\bbenchmark\b", passage) else 0.0
    for intent, label in (
        (r"\b(?:lock in|lockin)\b", r"\b(?:lock in|lockin)\b"),
        (r"\bexit load\b", r"\bexit load\b"),
        (r"\b(?:expense ratio|ter)\b", r"\b(?:expense ratio|ter)\b"),
        (r"\briskometer\b", r"\briskometer\b"),
    ):
        if re.search(intent, question) and re.search(label, passage):
            return 0.25
    return 0.0


def open_collection(data_dir: Path):
    chromadb, embedding_function = _chroma()
    client = chromadb.PersistentClient(path=str(data_dir / "chroma"))
    return client.get_or_create_collection(
        name="hdfc_direct_facts",
        embedding_function=embedding_function,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_function": "Chroma DefaultEmbeddingFunction (ONNX all-MiniLM-L6-v2)",
        },
    )


def rebuild_collection(data_dir: Path, chunks: list[dict[str, Any]]) -> None:
    if not chunks:
        raise ValueError("Refusing to build an empty Chroma collection.")
    collection = open_collection(data_dir)
    existing_ids = collection.get(include=["metadatas"])["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)
    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[
            {
                key: chunk[key]
                for key in (
                    "source_id", "scheme_id", "title", "url", "last_verified",
                    "source_type", "embedding_model",
                )
            }
            for chunk in chunks
        ],
    )


def retrieve(query: str, data_dir: Path, scheme_ids: list[str] | None = None, limit: int = 4):
    collection = open_collection(data_dir)
    where: dict[str, Any] | None = None
    if scheme_ids:
        where = {"scheme_id": scheme_ids[0]} if len(scheme_ids) == 1 else {"scheme_id": {"$in": scheme_ids}}
    result = collection.query(
        query_texts=[query],
        n_results=min(max(12, limit * 4), max(1, collection.count())),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    found: list[dict[str, Any]] = []
    for doc, metadata, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        found.append({"text": doc, **metadata, "distance": float(distance)})
    found.sort(key=lambda item: (item["distance"] - _lexical_bonus(query, item["text"]), item["distance"]))
    return found[:limit]
