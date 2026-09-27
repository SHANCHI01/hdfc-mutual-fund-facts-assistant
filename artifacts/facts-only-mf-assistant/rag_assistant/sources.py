"""Source discovery and public-text filtering for the HDFC corpus."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SOURCE_CHECKED_ON = "2026-09-27"
SCHEME_IDS = ("large-cap", "flexi-cap", "elss", "small-cap", "balanced-advantage")
SAFE_GUIDE_SOURCES = (
    {
        "id": "hdfc-cas-guide",
        "scheme_id": "general",
        "title": "Consolidated Account Statement service",
        "url": "https://www.hdfcfund.com/services/consolidated-account-statement",
        "last_verified": SOURCE_CHECKED_ON,
        "text": (
            "HDFC Mutual Fund's Download Statement service provides account statements "
            "summarising purchases, redemptions, switches, dividends and units allotted. "
            "Its official page says an account statement can be downloaded after investing "
            "and there is no charge for receiving or downloading it. Open the linked "
            "official service page to obtain a statement; never enter personal details here."
        ),
    },
    {
        "id": "hdfc-capital-gains-guide",
        "scheme_id": "general",
        "title": "How to get a capital-gains statement for mutual-fund schemes in India",
        "url": "https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india",
        "last_verified": SOURCE_CHECKED_ON,
        "text": (
            "HDFC Mutual Fund's guide How to Get a Capital Gain Statement, updated "
            "3 July 2026, describes obtaining a report for a selected financial year "
            "from a registrar, a distributor platform's tax or reports section, or an "
            "AMC website. It also describes selecting a capital-gains format when "
            "generating a consolidated account statement. Use the linked official "
            "guide for the current procedure; never enter personal details here."
        ),
    },
)

_SENSITIVE_INSTRUCTIONS = re.compile(
    r"\b(?:PAN|Aadhaar|Aadhar|OTP|one[- ]time password|account number|bank details|"
    r"email address|phone number|mobile number|contact details|KYC)\b",
    re.IGNORECASE,
)
_PERFORMANCE_HEADING = re.compile(
    r"^\s*#{1,6}\s*(?:.*(?:performance|historical\s+returns|benchmark\s+performance).*)$",
    re.IGNORECASE,
)
_PERFORMANCE_TERMS = re.compile(
    r"\b(?:returns?\s+since\s+inception|scheme\s+returns|benchmark\s+returns|"
    r"past\s+performance|historical\s+performance|value of investment)\b",
    re.IGNORECASE,
)


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the monorepo by its known API source file, not the cwd."""
    here = (start or Path(__file__)).resolve()
    candidates = (here, *here.parents)
    for candidate in candidates:
        if (candidate / "artifacts/api-server/src/data/hdfc-sources.json").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate artifacts/api-server/src/data/hdfc-sources.json "
        "from this module or its parent directories."
    )


def sanitize_scheme_text(text: str) -> str:
    """Remove performance sections and sensitive transaction instructions."""
    kept: list[str] = []
    skip_performance = False
    skip_return_card = False
    skip_nav_definition = False
    for line in text.splitlines():
        heading = _PERFORMANCE_HEADING.match(line)
        if heading:
            skip_performance = True
            continue
        if line.lstrip().startswith("#"):
            skip_performance = False
        if line.strip().casefold() == "returns":
            skip_return_card = True
            continue
        if skip_return_card:
            if line.strip().casefold() == "inception date":
                skip_return_card = False
            else:
                continue
        if skip_performance or _PERFORMANCE_TERMS.search(line):
            continue
        if re.search(r"\bNAV\s*(?:\(|NA\b|\d)", line, re.IGNORECASE):
            skip_nav_definition = True
            continue
        if skip_nav_definition:
            # The following definition is attached to the removed dated/current NAV value.
            if re.search(r"Net Asset Value|^\s*$", line, re.IGNORECASE):
                continue
            skip_nav_definition = False
        if re.search(r"since inception", line, re.IGNORECASE):
            continue
        if _SENSITIVE_INSTRUCTIONS.search(line):
            continue
        kept.append(line.rstrip())
    # Remove whitespace left by filtered-out source text.
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def load_sources(repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = repo_root or find_repo_root()
    source_path = root / "artifacts/api-server/src/data/hdfc-sources.json"
    if not source_path.is_file():
        raise FileNotFoundError(f"Required official scheme source file not found: {source_path}")
    rows = json.loads(source_path.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in rows}
    missing = sorted(set(SCHEME_IDS) - by_id.keys())
    if missing:
        raise ValueError(f"Official HDFC source file is missing required schemes: {missing}")

    sources: list[dict[str, Any]] = []
    for scheme_id in SCHEME_IDS:
        row = by_id[scheme_id]
        safe_text = sanitize_scheme_text(row["text"])
        if not safe_text:
            raise ValueError(f"Sanitization removed all text for {scheme_id}")
        sources.append(
            {
                "id": scheme_id,
                "scheme_id": scheme_id,
                "title": row["title"],
                "category": row.get("category", ""),
                "url": row["url"],
                "last_verified": row.get("lastVerified"),
                "text": safe_text,
                "source_type": "scheme",
                "embedding_model": EMBEDDING_MODEL,
            }
        )

    for guide in SAFE_GUIDE_SOURCES:
        sources.append(
            {
                **guide,
                "source_type": "statement_guide",
                "embedding_model": EMBEDDING_MODEL,
            }
        )

    document_path = Path(__file__).with_name("official_document_excerpts.json")
    documents = json.loads(document_path.read_text(encoding="utf-8"))
    for document in documents:
        if document["scheme_id"] not in SCHEME_IDS:
            raise ValueError(f'Unknown scheme in official document: {document["id"]}')
        if not document["url"].startswith("https://files.hdfcfund.com/"):
            raise ValueError(f'Untrusted official document URL: {document["id"]}')
        if not document["text"].strip():
            raise ValueError(f'Empty official document excerpt: {document["id"]}')
        sources.append(
            {
                **document,
                "source_type": "scheme_document",
                "embedding_model": EMBEDDING_MODEL,
            }
        )
    if len({source["id"] for source in sources}) != len(sources):
        raise ValueError("Duplicate official source IDs")
    if len({source["url"] for source in sources}) != len(sources):
        raise ValueError("Duplicate official source URLs")
    return sources
