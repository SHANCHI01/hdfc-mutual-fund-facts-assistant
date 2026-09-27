# Product requirements: facts-only mutual fund FAQ

## Goal and audience

The selected product in the assignment is **Groww**. This independent class-demo research assistant addresses factual mutual-fund FAQs relevant to Groww users; it is not affiliated with Groww or HDFC Mutual Fund and does not connect to any user account.

Give retail users and support/content teams short, verifiable answers to factual questions about **five HDFC Mutual Fund Direct Plan schemes**. This is not an adviser or a transaction service.

## In scope

- Questions about investment objectives, expense ratios, exit loads, minimum SIP, ELSS lock-in, riskometer, benchmarks, and official statement-download guidance.
- Retrieval from five public HDFC scheme pages, their ten official SID/KIM documents, and two official HDFC service guides for statements.
- A clear official source link for every factual answer, concise wording (at most three sentences), and a visible source verification date.
- Polite refusals for personalized advice and return/performance requests, with AMFI investor education or the official HDFC factsheet directory as appropriate.
- A welcome line, three example questions, five-scheme scope, source list, and a visible facts-only/no-advice notice.

## Out of scope

- Recommendations, portfolio suitability, forecasts, performance calculations, transactions, and receiving or storing PAN, Aadhaar, folio/account numbers, OTPs, emails, or phone numbers.
- Claims that a dated source snapshot reflects today's facts.
- Using Groww as an official AMC/SEBI/AMFI source. The five Groww links in the brief identify equivalent schemes, but are not authoritative citations.

## Acceptance checks

1. Ingest 17 official URLs (five scheme pages, ten SID/KIM documents, and two statement guides); show inspectable raw text, chunks, stored embeddings, and persistent Chroma collection.
2. Use `all-MiniLM-L6-v2` for document and query embeddings, retrieve evidence before generating a Groq answer, and limit conversation context to 10 messages.
3. Reject sensitive data before retrieval/model calls; refuse advice and performance questions.
4. Answer supported questions with at least one working official citation and a source date; report insufficient evidence for unsupported questions.
5. Provide a Streamlit UI and the README, source list, sample Q&A, and disclaimer.

The Groq-dependent answer step requires a user-provided `GROQ_API_KEY` supplied securely in the runtime environment; without it, the app must state that generation is unavailable rather than fabricate answers.