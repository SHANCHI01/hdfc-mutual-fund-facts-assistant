"""Grounded Groq answer generation; never fabricates a fallback answer."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .guardrails import contains_pii, refusal_for
from .retrieval import retrieve

UNAVAILABLE_ERROR = (
    "Answer generation is unavailable: GROQ_API_KEY is not set. "
    "Set it in the process environment to enable sourced answers."
)
_SCHEME_ALIASES = {
    "large-cap": ("large cap", "large-cap"),
    "flexi-cap": ("flexi cap", "flexi-cap"),
    "elss": ("elss", "tax saver"),
    "small-cap": ("small cap", "small-cap"),
    "balanced-advantage": ("balanced advantage", "balanced-advantage"),
}


def scheme_context(query: str) -> list[str] | None:
    lowered = query.casefold()
    selected = [
        scheme_id
        for scheme_id, aliases in _SCHEME_ALIASES.items()
        if any(alias in lowered for alias in aliases)
    ]
    return selected or None


def _sentences(text: str, maximum: int = 1) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Never expose an unfinished reasoning block if the model hits a token limit.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE).strip()
    if re.search(r"</?think>", text, flags=re.IGNORECASE):
        return ""
    # A currency abbreviation is not a sentence boundary ("Rs. 500").
    parts = re.split(r"(?<!Rs\.)(?<!Mr\.)(?<!Ms\.)(?<!Dr\.)(?<=[.!?])\s+", text)
    return " ".join(parts[:maximum]).strip()


def _citation_line(results: list[dict[str, Any]]) -> str:
    # Use one actual retrieved chunk; cite only its source URL.
    source = results[0]
    return f'Source: [{source["title"]}]({source["url"]})'


def answer_query(
    query: str,
    data_dir: Path,
    api_key: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    refusal = refusal_for(query)
    if refusal:
        return {"answer": refusal, "sources": [], "refused": True}

    key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(UNAVAILABLE_ERROR)

    safe_history = [
        message for message in (history or [])[-10:]
        if message.get("role") in ("user", "assistant")
        and isinstance(message.get("content"), str)
        and not contains_pii(message["content"])
    ]
    named_in_question = scheme_context(query)
    current_scheme = named_in_question
    if not current_scheme:
        for message in reversed(safe_history):
            if message["role"] == "user" and scheme_context(message["content"]):
                current_scheme = scheme_context(message["content"])
                break
    statement_query = bool(re.search(r"\b(?:statement|capital[\s-]*gains?|folio)\b", query, re.IGNORECASE))
    if current_scheme and len(current_scheme) > 1 and not statement_query:
        return {
            "answer": "Please ask about one HDFC scheme at a time so each factual answer can point to its exact source.",
            "sources": [],
            "refused": True,
        }
    retrieval_query = query
    if not named_in_question and current_scheme and len(current_scheme) == 1 and not statement_query:
        retrieval_query = f"HDFC {_SCHEME_ALIASES[current_scheme[0]][0]} Fund {query}"
    results = retrieve(retrieval_query, data_dir, None if statement_query else current_scheme, limit=4)
    # Lower cosine distance is more similar. Avoid forcing irrelevant corpus matches.
    if not results or results[0]["distance"] > 0.72:
        return {
            "answer": "I could not find a relevant fact in the official sources in this corpus. Please consult the linked HDFC sources for current information.",
            "sources": [],
            "refused": True,
        }
    # Ground the model and its citation in the same single, best-matching excerpt.
    results = results[:1]

    from groq import Groq

    context = "\n\n".join(
        f'SOURCE {i + 1}: {row["title"]} | {row["url"]} | Updated: {row["last_verified"]}\n'
        f'EXCERPT: {row["text"]}'
        for i, row in enumerate(results)
    )
    conversation = "\n".join(
        f'{message["role"]}: {message["content"][:400]}' for message in safe_history
    )
    response = Groq(api_key=key).chat.completions.create(
        model="qwen/qwen3.8-27b",
        temperature=0,
        max_tokens=180,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer only with facts explicitly supported by the supplied excerpts. "
                    "Do not provide advice, performance or NAV claims, personal-data guidance, "
                    "or facts from outside the excerpts. Do not claim a source says more than "
                    "its quoted content. If the excerpts do not answer the question, say so. "
                    "If the excerpt does not directly answer the question, respond exactly "
                    "INSUFFICIENT_EVIDENCE. Use at most two short sentences; no citation "
                    "or source URL in your answer. Conversation is only for resolving "
                    "references, never as evidence."
                ),
            },
            {"role": "user", "content": f"Recent conversation:\n{conversation or '(none)'}\n\nQuestion: {query}\n\nRetrieved excerpts:\n{context}"},
        ],
    )
    content = response.choices[0].message.content or ""
    factual_answer = _sentences(content)
    if (
        not factual_answer
        or "INSUFFICIENT_EVIDENCE" in factual_answer
        or re.search(r"\b(?:cannot|can't|could not|not (?:in|provided by) the (?:source|excerpt))\b", factual_answer, re.I)
    ):
        return {
            "answer": "The source excerpts did not provide a grounded answer.",
            "sources": [],
            "refused": True,
        }
    updated = max((row["last_verified"] or "" for row in results), default="") or "not stated"
    answer = f"{factual_answer}\n\n{_citation_line(results)}\n\nLast updated from sources: {updated}"
    return {"answer": answer, "sources": results, "refused": False}
