"""Input controls and explicit facts-only refusals."""

from __future__ import annotations

import re

AMFI_EDUCATION_URL = "https://www.amfiindia.com/investor"
FACTSHEET_DIRECTORY_URL = "https://www.hdfcfund.com/mutual-funds/factsheets"

_PII_PATTERNS = (
    re.compile(r"\b\d{12}\b"),  # Aadhaar
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE),  # PAN
    re.compile(r"(?<!\d)(?:\d[\s-]?){9,18}(?!\d)"),  # account-like numeric strings
    re.compile(r"\b(?:account|folio)\s*(?:number|no\.?|#)?\s*(?:(?:is|=|:|#)\s*)?\d{6,18}\b", re.IGNORECASE),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<!\w)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\w)"),
    re.compile(r"\b(?:otp|one[- ]time password)\b", re.IGNORECASE),
)
_ADVICE = re.compile(
    r"\b(should i|should we|recommend|recommendation|(?:can|may|would)\s+i\s+(?:buy|sell|invest)|"
    r"(?:buy|sell|switch)\s+(?:this|these|now|my)|"
    r"best fund|which fund\s+(?:should|is better)|better fund|suitable for me|right for me|"
    r"good investment|worth investing|portfolio|my goals?|my risk|how much should i invest)\b",
    re.IGNORECASE,
)
_PERFORMANCE = re.compile(
    r"\b(returns?|performance|outperform|underperform|profit|expected loss|"
    r"best performing|historical gains?|nav|cagr|xirr|forecast|predict|guarantee)\b",
    re.IGNORECASE,
)
_RELEVANT = re.compile(
    r"\b(expense|ter|exit load|entry load|sip|minimum|min investment|"
    r"lock[- ]?in|elss|riskometer|risk|benchmark|scheme|fund|"
    r"capital[- ]?gain|statement|cas|consolidated account|"
    r"direct plan|growth option|idcw|objective|allocation)\b",
    re.IGNORECASE,
)


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PII_PATTERNS)


def refusal_for(query: str) -> str | None:
    if contains_pii(query):
        return (
            "Please remove personal or account information (including Aadhaar, PAN, "
            "account numbers, phone/email details, and OTPs) and ask again. This assistant "
            "does not retain that input."
        )
    if _PERFORMANCE.search(query):
        return (
            "I can’t provide or compare performance or NAV claims. Please consult the "
            f"[official HDFC factsheet directory]({FACTSHEET_DIRECTORY_URL}) for current documents."
        )
    if _ADVICE.search(query):
        return (
            "I can only provide sourced facts, not investment advice or portfolio recommendations. "
            f"See [AMFI investor education]({AMFI_EDUCATION_URL})."
        )
    if not _RELEVANT.search(query):
        return (
            "I can answer factual questions about the five HDFC Direct Plan schemes or "
            "official statement guides in this corpus. Please ask about a scheme fact or statement."
        )
    return None
