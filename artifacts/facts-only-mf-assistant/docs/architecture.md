# Architecture

```
Five official HDFC scheme snapshots + official statement guides
  → remove personal-data instructions and performance/NAV material
  → paragraph/sentence chunks with small overlaps
  → Chroma DefaultEmbeddingFunction (ONNX all-MiniLM-L6-v2, 384 dimensions)
  → persistent Chroma collection

User question
  → PII/advice/performance checks before retrieval or model calls
  → embed with the same MiniLM model
  → retrieve matching Chroma chunks, filtered to a named scheme where applicable
  → use only retrieved evidence in Groq qwen/qwen3.8-27b
  → concise answer + official citation + source verification date
```

The Python app is in `rag_assistant/`. `sources.py` loads five HDFC scheme snapshots captured on 27 September 2026, ten checked SID/KIM excerpts, and two statement guides; `ingest.py` writes inspectable sanitized records to `data/raw/`, chunks to `data/chunks.jsonl`, vector values to `data/embeddings.txt`, and the searchable SQLite-backed Chroma collection to `data/chroma/`. Rebuilding the index does not require Groq access. Use `python -m rag_assistant.ingest` after any reviewed source change.

`guardrails.py` rejects personal identifiers, requests for advice, and performance questions before calling the vector store or Groq. `retrieval.py` queries Chroma. `answering.py` sends only evidence plus the current question and up to ten non-PII conversation messages to Groq. `app.py` is the Streamlit UI; its session history is ephemeral.

**Source rules:** Scheme facts are restricted to five HDFC Direct Plan pages and their official SID/KIM documents. Two HDFC statement guides are supplementary official pages. The five Groww links in the prompt identify the schemes but are not used as evidence, because Groww is not an AMC/SEBI/AMFI source.

**Failure behavior:** Missing Groq credentials, an empty index, a retrieval miss, or an unavailable model must produce an explicit unavailable/insufficient-evidence state—not a fabricated sourced answer. The source snapshot is dated and is not a live feed.