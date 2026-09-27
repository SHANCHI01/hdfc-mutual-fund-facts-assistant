# HDFC Mutual Fund Facts Assistant

A facts-only RAG chatbot for five HDFC Mutual Fund Direct Plan schemes. The Streamlit app retrieves source passages from a persistent ChromaDB index using **all-MiniLM-L6-v2** embeddings, then uses **Groq `qwen/qwen3.8-27b`** to draft short answers. Every supported answer includes a link to the retrieved official source and **Last updated from sources:** metadata. It does not provide investment advice, return calculations, or transaction services.

## Scope and sources

The five schemes are HDFC Large Cap, Flexi Cap, ELSS Tax Saver, Small Cap, and Balanced Advantage. The [17-URL official source list](docs/sources.md) contains five HDFC AMC scheme pages, five SIDs, five KIMs, and two HDFC statement guides. The five Groww links in the assignment identify the schemes but **are not used as citations**: Groww is a third-party platform, whereas the assignment requires official AMC/SEBI/AMFI sources.

Scheme pages and guides were checked **27 September 2026**; official PDFs were read **28 September 2026** and dated **21 November 2025**. This is not a live HDFC data feed. Verify current figures and procedures on official pages.

## Setup and run

Use Python 3.11. In the repository root on Replit, the installed Python dependencies are managed by `pyproject.toml`; for a standard Python environment install the pinned packages in `requirements.txt` (do not put credentials in a file):

```sh
cd artifacts/facts-only-mf-assistant
python -m pip install -r requirements.txt
PYTHONPATH=. python -m rag_assistant.ingest
PYTHONPATH=. python -m unittest rag_assistant.test_rag
PYTHONPATH=. python -m rag_assistant.inspect_retrieval "What is the ELSS lock-in period?"
```

Add `GROQ_API_KEY` through your host's **secret/environment-variable settings**. Do not paste it into chat or commit it. Without it, the source list and privacy refusals still work, but factual answer generation explicitly reports that Groq is unavailable.

For local Streamlit development from this directory:

```sh
PYTHONPATH=. python -m streamlit run rag_assistant/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

On Replit, use the existing managed web workflow; it sets the port and routes the Streamlit base path. The existing TypeScript API/React implementation remains in the repository for reference, but the Streamlit service is the required-stack prototype.

## RAG data stages

1. **Load:** five dated HDFC scheme snapshots from the repository's API source file, ten short factual excerpts verified against HDFC SID/KIM PDFs, and two curated HDFC statement guides.
2. **Sanitize and chunk:** omit personal-data instructions and performance/NAV passages; group paragraphs and sentences with overlap.
3. **Embed and store:** Chroma's ONNX `DefaultEmbeddingFunction` runs the `all-MiniLM-L6-v2` model (the same model named `sentence-transformers/all-MiniLM-L6-v2`), producing 384-dimensional vectors. Chroma persists to `data/chroma/`.
4. **Retrieve and answer:** embed the query with the same model, search Chroma with scheme filtering where relevant, pass the best cited passage and at most ten recent non-PII conversation messages to Groq.

After ingestion, inspect `data/raw/`, `data/chunks.jsonl`, `data/embeddings.txt`, and the persistent `data/chroma/` directory. Regenerate these files after deliberately reviewing any source update. The Chroma database is ignored in Git and is rebuilt by the production build command.

## Hosting on Render

Create a **Python web service** from the complete repository (do not set the root directory to only the artifact: the five scheme snapshots are in the sibling API package). Set:

- **Root Directory:** repository root
- **Build Command:** `pip install -r artifacts/facts-only-mf-assistant/requirements.txt && cd artifacts/facts-only-mf-assistant && PYTHONPATH=. python -m rag_assistant.ingest`
- **Start Command:** `cd artifacts/facts-only-mf-assistant && PYTHONPATH=. python -m streamlit run rag_assistant/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- **Environment secret:** `GROQ_API_KEY` (must be supplied by the account owner)

This is configuration guidance, **not a claim that a Render deployment exists**. The local Chroma files persist across local restarts. A host without persistent storage may discard the index between deployments; use a persistent disk or rebuild it during startup if your host requires it.

### Vercel compatibility

The current Streamlit server and local Chroma SQLite index cannot be deployed **as-is** as a Vercel Python Function: Vercel runs ASGI/WSGI request handlers and provides a read-only filesystem (apart from temporary `/tmp` storage). A Vercel frontend with a separately hosted persistent Python service would be a different architecture; a Vercel page that merely links elsewhere would not count as a working prototype on Vercel. Do not deploy the older React/OpenAI API as a substitute for this Groq/Chroma/MiniLM/Streamlit prototype.

## Milestone submission checklist

- [x] Official [source list](docs/sources.md) of 17 indexed URLs (within the required 15–25).
- [x] [Sample Q&A](docs/sample-qa.md), setup and scope in this README, and the disclaimer in the Streamlit UI.
- [ ] Public GitHub repository link: requires connecting or creating a repository; this workspace's internal backup remote is not a shareable GitHub URL.
- [ ] Public working prototype link: requires a compatible host and publishing; the development preview is not a permanent submission URL.
- [ ] Google Drive demo video link: optional **only if** a public working prototype link is available.

## Known limits

- Live Groq answers were checked for scheme facts, statement guidance, a follow-up question, and dated citations with a configured key. A valid key and a supported Groq model remain necessary; there is no invented or silent fallback answer when they are unavailable.
- The source pages are snapshots, not automatically refreshed. Fee, risk, benchmark and operational details may have changed.
- The statement passages intentionally omit identity-verification steps. Follow the linked official service for those steps; never enter identifiers in chat.
- Sensitive input is rejected before retrieval and is not stored in chat history. This is a prototype, not a regulated financial-advice or production identity-handling system.
- Semantic retrieval can miss relevant passages. When evidence is weak or absent, the assistant must say so rather than guess.

See [docs/PRD.md](docs/PRD.md), [docs/architecture.md](docs/architecture.md), [docs/implementation.md](docs/implementation.md), [docs/sources.md](docs/sources.md), and [docs/sample-qa.md](docs/sample-qa.md). The UI disclaimer reads: **“Facts-only information from official HDFC public sources; this assistant does not provide investment, tax, or legal advice. Do not enter PAN, Aadhaar, account numbers, phone/email details, or OTPs. Personal information is not stored.”**