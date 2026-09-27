# Implementation phases and verification

| Phase | Work | Status |
|---|---|---|
| 1. Scope and source selection | Five HDFC Direct Plan pages; two official HDFC service guides for statement questions | Implemented |
| 2. Loading and chunking | Sanitize snapshot text; write inspectable `data/raw/` and deterministic paragraph-aware `data/chunks.jsonl` | Implemented |
| 3. Embedding and storage | Use ONNX all-MiniLM-L6-v2 in Chroma; write `data/embeddings.txt`; persist the collection in `data/chroma/` | Implemented |
| 4. Guardrails | Block PAN, Aadhaar, account/folio numbers, OTP, email, phone, advice and performance questions | Implemented; check with unit tests |
| 5. Retrieval | Embed questions with the same model, search Chroma and restrict to a named scheme when relevant | Implemented; inspect retrieved chunks offline |
| 6. Generation and UI | Groq `qwen/qwen3.8-27b` generates a short grounded answer in Streamlit, with an official citation and source date | Live answers and refusals verified with a configured `GROQ_API_KEY` |

## Run the checks

From `artifacts/facts-only-mf-assistant/`:

```sh
PYTHONPATH=. python -m rag_assistant.ingest
PYTHONPATH=. python -m unittest rag_assistant.test_rag
PYTHONPATH=. python -m rag_assistant.inspect_retrieval "What is the ELSS lock-in period?"
```

Review the generated files in `data/` and verify that Chroma returns an actual evidence chunk. Do not commit or print personal data or secrets. The index now includes 17 official URLs: five scheme pages, ten verified SID/KIM excerpts, and two statement guides. Live checks covered scheme facts, statement guidance, a scheme follow-up, PDF-sourced Small Cap allocation and ELSS application minimum, and advice/performance/PII refusals. This is not a claim that every possible question is supported by the dated source snapshot.