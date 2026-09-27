"""Streamlit facts-only HDFC Direct Plan assistant."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from rag_assistant.answering import UNAVAILABLE_ERROR, answer_query
from rag_assistant.guardrails import contains_pii
from rag_assistant.retrieval import open_collection

DATA_DIR = PACKAGE_ROOT / "data"
EXAMPLES = (
    "What is the ELSS lock-in period?",
    "What benchmark does HDFC Flexi Cap Fund use?",
    "Where can I find HDFC's capital-gains statement guide?",
)
SCHEME_URLS = (
    ("HDFC Large Cap Fund", "https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct"),
    ("HDFC Flexi Cap Fund", "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct"),
    ("HDFC ELSS Tax Saver Fund", "https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct"),
    ("HDFC Small Cap Fund", "https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap-fund/direct"),
    ("HDFC Balanced Advantage Fund", "https://www.hdfcfund.com/explore/mutual-funds/hdfc-balanced-advantage-fund/direct"),
)

st.set_page_config(
    page_title="HDFC Mutual Fund Facts Assistant",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("HDFC Mutual Fund Facts Assistant")
st.write(
    "Welcome. Ask a factual question about one of the five HDFC Direct Plan schemes "
    "or the official statement guides."
)
st.caption("Facts-only. No investment advice. Information may change; check official sources.")

with st.sidebar:
    st.header("Scope and sources")
    st.write("Primary scheme corpus: exactly five HDFC Direct Plan schemes.")
    for title, url in SCHEME_URLS:
        st.markdown(f"- [{title}]({url})")
    st.markdown(
        "- [Consolidated Account Statement service](https://www.hdfcfund.com/services/consolidated-account-statement)\n"
        "- [Capital-gains statement guide](https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india)"
    )
    st.write(
        "Scope is scheme facts and statement-source pointers. Performance/NAV questions, "
        "advice, and personal-data handling are excluded."
    )
    st.caption("Five HDFC scheme pages, ten official SID/KIM documents, and two statement guides.")
    st.caption("Scheme pages checked: 2026-09-27 · Documents checked: 2026-09-28")

st.subheader("Example questions")
for example in EXAMPLES:
    if st.button(example, key=f"example-{EXAMPLES.index(example)}"):
        st.session_state["pending_query"] = example

st.info(
    "Disclaimer: Facts-only information from official HDFC public sources; this assistant "
    "does not provide investment, tax, or legal advice. Do not enter PAN, Aadhaar, account "
    "numbers, phone/email details, or OTPs. Personal information is not stored."
)
if not os.environ.get("GROQ_API_KEY"):
    st.warning(
        "Groq is not configured. Factual answers are unavailable until a GROQ_API_KEY "
        "is added securely; no answer will be invented."
    )

if "history" not in st.session_state:
    st.session_state["history"] = []
try:
    collection = open_collection(DATA_DIR)
    if collection.count() == 0:
        st.error("The source index is empty. Build it with `python -m rag_assistant.ingest`.")
        st.stop()
except Exception as exc:
    st.error(f"Persistent source index is unavailable. Build it with `python -m rag_assistant.ingest`. Details: {exc}")

query = st.chat_input("Ask a factual HDFC scheme or statement question")
pending = st.session_state.pop("pending_query", None)
active_query = pending or query
if active_query:
    if contains_pii(active_query):
        st.warning(
            "Please remove the personal or account information and ask again. "
            "This input will not be added to conversation history."
        )
    else:
        try:
            recent = [
                message
                for exchange in st.session_state["history"][-5:]
                for message in (
                    {"role": "user", "content": exchange["question"]},
                    {"role": "assistant", "content": exchange["answer"]},
                )
            ]
            result = answer_query(active_query, DATA_DIR, history=recent)
            st.session_state["history"].append(
                {"question": active_query, "answer": result["answer"]}
            )
            st.session_state["history"] = st.session_state["history"][-10:]
        except RuntimeError as exc:
            st.error(str(exc) if str(exc) == UNAVAILABLE_ERROR else f"Answer unavailable: {exc}")
        except Exception as exc:
            st.error(f"Answer unavailable: {exc}")

for exchange in st.session_state["history"]:
    with st.chat_message("user"):
        st.write(exchange["question"])
    with st.chat_message("assistant"):
        st.markdown(exchange["answer"])

st.caption(
    "Conversation history is held in temporary Streamlit session state (up to 10 exchanges), "
    "not in the source index; no PII is retained."
)
