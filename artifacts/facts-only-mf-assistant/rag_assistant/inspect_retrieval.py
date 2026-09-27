"""Inspect retrieved Chroma evidence without calling Groq."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .answering import scheme_context
from .guardrails import refusal_for
from .retrieval import open_collection, retrieve


def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: python -m rag_assistant.inspect_retrieval "What is the ELSS lock-in period?"')
        return 2
    if refusal_for(question):
        print("Question rejected by facts-only or privacy guardrails.")
        return 2
    data_dir = Path(__file__).resolve().parents[1] / "data"
    if open_collection(data_dir).count() == 0:
        print("No indexed chunks. Run python -m rag_assistant.ingest first.")
        return 1
    is_statement = bool(re.search(r"\b(?:statement|capital[\s-]*gains?|folio)\b", question, re.I))
    results = retrieve(question, data_dir, None if is_statement else scheme_context(question))
    for index, item in enumerate(results, 1):
        print(f"{index}. {item['source_id']}  distance={item['distance']:.3f}  {item['url']}")
        print(f"   {item['text'][:350].replace(chr(10), ' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())