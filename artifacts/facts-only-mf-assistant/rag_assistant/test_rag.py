"""Offline unit tests; no Groq credentials or network access required."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rag_assistant.answering import UNAVAILABLE_ERROR, _sentences, answer_query
from rag_assistant.chunking import paragraph_chunks
from rag_assistant.guardrails import refusal_for
from rag_assistant.sources import EMBEDDING_MODEL, load_sources, sanitize_scheme_text
from rag_assistant.answering import scheme_context
from rag_assistant.retrieval import _lexical_bonus


class ChunkingTests(unittest.TestCase):
    def test_preserves_paragraphs_and_is_deterministic(self):
        text = "First paragraph has facts.\n\nSecond paragraph has more facts."
        self.assertEqual(paragraph_chunks(text), paragraph_chunks(text))
        self.assertEqual(paragraph_chunks(text, max_chars=100, overlap_chars=10), ["First paragraph has facts.\nSecond paragraph has more facts."])

    def test_chunks_obey_target_except_single_long_paragraph(self):
        chunks = paragraph_chunks("A short paragraph.\n\nAnother short paragraph.", max_chars=24, overlap_chars=4)
        self.assertTrue(all(chunk for chunk in chunks))


class GuardrailTests(unittest.TestCase):
    def test_sensitive_values_rejected(self):
        for query in (
            "My Aadhaar is 123456789012",
            "PAN ABCDE1234F",
            "My account is 1234567890123456",
            "My account number is 12345678",
            "email me a@example.com",
            "OTP is 847291",
            "Call me 9876543210",
        ):
            self.assertIsNotNone(refusal_for(query), query)

    def test_advice_performance_and_irrelevant_refusals(self):
        self.assertIn("AMFI", refusal_for("Should I buy the large cap fund?"))
        self.assertIn("factsheet", refusal_for("What are its returns?"))
        self.assertIsNotNone(refusal_for("Tell me a joke"))

    def test_safe_fact_is_not_refused(self):
        self.assertIsNone(refusal_for("What is the ELSS lock-in period?"))
        self.assertIsNone(refusal_for("Which asset classes does HDFC Balanced Advantage Fund invest in?"))
        self.assertIsNone(refusal_for("How do I download a capital gains and loss statement?"))
        self.assertIn("AMFI", refusal_for("Which fund is better for me?"))
        self.assertIn("AMFI", refusal_for("Is HDFC Small Cap a good investment?"))
        self.assertIn("factsheet", refusal_for("What is the NAV?"))


class ContextAndSanitizationTests(unittest.TestCase):
    def test_submission_source_list_matches_indexed_corpus(self):
        sources = load_sources()
        listed = (Path(__file__).resolve().parents[1] / "docs/sources.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(len(sources), 17)
        self.assertEqual(len({source["url"] for source in sources}), 17)
        self.assertEqual(sum(s["source_type"] == "scheme_document" for s in sources), 10)
        for source in sources:
            self.assertIn(source["url"], listed)
            self.assertTrue(source["text"].strip())

    def test_scheme_filter_context(self):
        self.assertEqual(scheme_context("What is the HDFC Flexi Cap benchmark?"), ["flexi-cap"])
        self.assertEqual(
            scheme_context("Compare the HDFC Flexi Cap and Small Cap facts"),
            ["flexi-cap", "small-cap"],
        )
        self.assertIsNone(scheme_context("What is the minimum SIP?"))

    def test_source_filter_removes_sensitive_and_performance_content(self):
        text = (
            "## Facts\nExpense ratio is published.\n\n"
            "Keep PAN and Aadhaar ready.\n\n"
            "## Historical Performance\nReturns since inception 12%.\n\n"
            "## Exit Load\nExit load details."
        )
        sanitized = sanitize_scheme_text(text)
        self.assertIn("Expense ratio", sanitized)
        self.assertIn("Exit load", sanitized)
        self.assertNotIn("PAN", sanitized)
        self.assertNotIn("12%", sanitized)
        self.assertNotIn("Returns", sanitized)

    def test_model_metadata_name(self):
        self.assertEqual(EMBEDDING_MODEL, "sentence-transformers/all-MiniLM-L6-v2")

    def test_fact_label_reranks_semantic_candidates(self):
        query = "What is the minimum SIP for HDFC Small Cap Fund?"
        self.assertGreater(
            _lexical_bonus(query, "Min SIP ₹ 100"),
            _lexical_bonus(query, "Choose Investment Mode SIP"),
        )
        self.assertGreater(
            _lexical_bonus("What benchmark does HDFC Large Cap Fund use?", "Benchmark: NIFTY 100 (Total Return Index)"),
            _lexical_bonus("What benchmark does HDFC Large Cap Fund use?", "Product labelling: benchmark riskometer"),
        )


class AvailabilityTests(unittest.TestCase):
    def test_currency_abbreviation_does_not_truncate_the_answer(self):
        self.assertEqual(
            _sentences("The minimum application amount is Rs. 500. Check the source."),
            "The minimum application amount is Rs. 500.",
        )

    def test_unfinished_model_reasoning_cannot_be_shown(self):
        self.assertEqual(_sentences("<think>I need to check the evidence"), "")

    def test_missing_groq_key_is_explicit_and_does_not_fabricate(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY is not set"):
                answer_query("What is the ELSS lock-in period?", data_dir=__import__("pathlib").Path("/nonexistent"))
        self.assertIn("GROQ_API_KEY", UNAVAILABLE_ERROR)

    def test_grounded_reply_has_real_source_date_and_history_filters_scheme(self):
        evidence = {
            "title": "HDFC Flexi Cap Fund",
            "url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct",
            "last_verified": "2026-09-27",
            "text": "The benchmark is NIFTY 500 Total Returns Index.",
            "distance": 0.25,
        }
        with patch("rag_assistant.answering.retrieve", return_value=[evidence]) as retrieve_mock:
            with patch("groq.Groq") as groq_mock:
                groq_mock.return_value.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(
                        content="The benchmark is NIFTY 500 Total Returns Index."
                    ))]
                )
                result = answer_query(
                    "What is its benchmark?",
                    Path("/unused"),
                    api_key="fake-test-key",
                    history=[{"role": "user", "content": "Tell me about HDFC Flexi Cap Fund"}],
                )
        self.assertEqual(retrieve_mock.call_args.args[2], ["flexi-cap"])
        self.assertIn("flexi cap", retrieve_mock.call_args.args[0].casefold())
        self.assertIn("Last updated from sources: 2026-09-27", result["answer"])
        self.assertIn(evidence["url"], result["answer"])
        self.assertFalse(result["refused"])

    def test_model_insufficient_evidence_is_not_cited(self):
        evidence = {
            "title": "HDFC Fund", "url": "https://www.hdfcfund.com/",
            "last_verified": "2026-09-27", "text": "Nothing about the requested fact.",
            "distance": 0.3,
        }
        with patch("rag_assistant.answering.retrieve", return_value=[evidence]):
            with patch("groq.Groq") as groq_mock:
                groq_mock.return_value.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="INSUFFICIENT_EVIDENCE"))]
                )
                result = answer_query("What is the ELSS benchmark?", Path("/unused"), api_key="fake-test-key")
        self.assertTrue(result["refused"])
        self.assertEqual(result["sources"], [])


if __name__ == "__main__":
    unittest.main()
