"""Deterministic paragraph-aware overlapping chunk construction."""

from __future__ import annotations

import hashlib
import re
from typing import Any


def paragraph_chunks(text: str, max_chars: int = 900, overlap_chars: int = 160) -> list[str]:
    """Pack intact paragraphs and overlap the tail when starting each next chunk."""
    if max_chars < 1 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Require max_chars > overlap_chars >= 0.")
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    paragraphs = [p for p in paragraphs if p]
    chunks: list[str] = []
    current = ""

    def overlap_tail(value: str) -> str:
        if not overlap_chars:
            return ""
        start = max(0, len(value) - overlap_chars)
        while start and start < len(value) and not value[start - 1].isspace():
            start += 1
        return value[start:].strip()

    def emit(value: str) -> None:
        value = value.strip()
        if value and (not chunks or chunks[-1] != value):
            chunks.append(value)

    for paragraph in paragraphs:
        # Oversized paragraphs are split on sentence boundaries, then hard-wrapped
        # only when a single sentence itself exceeds the target.
        units = [paragraph]
        if len(paragraph) > max_chars:
            units = re.split(r"(?<=[.!?])\s+", paragraph)
        for unit in units:
            if len(unit) > max_chars:
                for start in range(0, len(unit), max_chars - overlap_chars):
                    piece = unit[start : start + max_chars].strip()
                    if current:
                        emit(current)
                        current = overlap_tail(current) + " " + piece if overlap_chars else piece
                    else:
                        current = piece
                    if len(current) >= max_chars:
                        emit(current)
                        current = overlap_tail(current)
                continue
            candidate = f"{current}\n{unit}".strip() if current else unit
            if len(candidate) <= max_chars:
                current = candidate
            else:
                emit(current)
                tail = overlap_tail(current)
                current = f"{tail}\n{unit}".strip() if tail else unit
                if len(current) > max_chars:
                    emit(current)
                    current = ""
    emit(current)
    return chunks


def make_chunks(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for source in sources:
        for index, text in enumerate(paragraph_chunks(source["text"])):
            digest = hashlib.sha256(
                f'{source["id"]}:{index}:{text}'.encode("utf-8")
            ).hexdigest()[:20]
            chunks.append(
                {
                    "id": f'{source["id"]}-{index:04d}-{digest}',
                    "source_id": source["id"],
                    "scheme_id": source["scheme_id"],
                    "title": source["title"],
                    "url": source["url"],
                    "last_verified": source["last_verified"],
                    "source_type": source["source_type"],
                    "embedding_model": source["embedding_model"],
                    "text": text,
                }
            )
    return chunks
