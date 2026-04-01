## Inspiration

I've always loved building solutions that are technically ambitious, data-driven, and – most importantly – genuinely useful to people. I believe data science is one of the most extraordinary fields out there: from raw numbers and plain text, we can literally predict the future or create tools that – with the use of LLMs – democratize access to knowledge that was previously reserved for experts.

The spark for Vigil came from conversations with friends who are founders and students with brilliant startup ideas. Every single one of them complained about the same thing: they spend a shocking amount of money on lawyers, just to stay on top of EU regulations. GDPR, AI Act, DORA, NIS2 – the landscape is vast, constantly changing, and written in language that's completely inaccessible to non-lawyers.

I also had a technical foundation to build on: through my university's Data Science Club, I coordinate a project building a RAG-based chatbot assistant for students & staff at my faculty. That experience with scraping and retrieval systems gave me the confidence to tackle something more ambitious.

## What it does

Vigil monitors EU regulations in real time and delivers personalized, actionable compliance intelligence for European SMEs – before the deadline hits.

You fill in your company profile: name, industry, country, and which regulations you care about. Vigil does the rest – scraping live sources, reading the regulatory updates so you don't have to, and telling you exactly what changed this month, why it matters for your specific business, and what you need to do about it. Everything lands in a clean digest with deadline alerts and a downloadable PDF report. 

No legal jargon. No generic updates. Just exactly what matters for your business, this month.

---

### 🤓 Nerdy details

Vigil is a full RAG pipeline built on top of Apify's infrastructure, covering 30+ live regulatory sources across 18 EU countries.

**The core innovation: fact-based embeddings.** Instead of embedding raw text chunks (standard RAG), Vigil uses `Claude 3 Haiku` to first extract discrete structured facts from each document batch – `claim`, `regulation`, `article`, `deadline`, `action_required`, `severity` – and embeds those facts instead. This dramatically improves retrieval precision: we're searching over semantically rich regulatory claims, not arbitrary text windows.

**Two-step hybrid retrieval.** Facts are first pre-filtered using industry/country/regulation-specific keyword dictionaries (with severity boost scoring), then re-ranked by cosine similarity using `text-embedding-3-small` embeddings via OpenRouter. This combines the speed of keyword search with the precision of semantic search.

**Recency-constrained prompts.** All LLM prompts include today's date and a strict 30-day window. The model is explicitly instructed to ignore historical regulatory background and surface only recent changes – solving the core problem of RAG systems that return evergreen content as "news".

**Dual output.** The same pipeline powers both an Apify Actor (structured JSON pushed to Apify dataset) and a Streamlit frontend with PDF/Markdown export.

## How I built it

1. **Live scraping** – `apify/website-content-crawler` scrapes EUR-Lex, EDPB, GDPR.eu, and national regulatory sources. Three scrapers run in parallel via `asyncio.gather`.
2. **Chunking** – paragraph-level chunking with overlap.
3. **Fact extraction** – `Claude 3 Haiku` → structured JSON facts per batch.
4. **Embedding** – `text-embedding-3-small` via OpenRouter/Apify Standby.
5. **Two-step retrieval** – keyword filter + cosine similarity vector store.
6. **Digest generation** – personalized monthly digest + plain-language summary + alerts.
7. **Output** – Apify dataset (JSON) + Streamlit UI (PDF/Markdown).

I coded Vigil entirely in Python, in Visual Studio Code, with help from Claude.

## Challenges I ran into

The biggest challenge was designing the full data pipeline: fact-based chunking, two-step retrieval, keyword scoring with industry and country-specific dictionaries, severity-boosted relevance scoring, and an in-memory vector store – all working together coherently. Each layer added complexity, and making sure the right facts surfaced for the right company profile required careful tuning at every step.

Equally hard were the system prompts. Getting Claude to produce exactly the right output format – structured JSON facts, date-aware digests, no hallucinated deadlines, plain English instead of legalese – required significant prompt engineering effort. Real-world regulatory data is also messy, scattered across millions of unstructured pages in multiple languages, which made the scraping layer far more complex than expected.

## Accomplishments that I'm proud of

I'm genuinely proud of three things. First, the accessibility of the final product – Vigil translates genuinely complex regulatory nuances into plain language that a non-lawyer founder can act on immediately. Second, the data pipeline design: fact-based embeddings over chunk-based retrieval is a meaningful architectural choice that improves precision, and the two-step hybrid retrieval system is something I'm proud to have designed and implemented from scratch. Third – working with Apify. Learning to build on top of Apify's infrastructure, from `website-content-crawler` to OpenRouter Standby, has been one of the most practically valuable skills I've gained from this hackathon, and one I'll definitely carry into future projects.

## What I learned

**Real-world data is messy and scattered.** Scraping regulatory sources across 18 countries from unstructured HTML and then synthesizing everything into a single coherent document is genuinely hard. But it's also what makes agentic AI solutions powerful: the value is in the data pipeline, not just the model.

**Prompt engineering is everything.** A good prompt is the difference between a hallucinating model and a precise, structured output. Getting the LLM to extract the right JSON schema, respect a 30-day recency window, and produce plain English – not legalese – required careful iteration.

**Building a clean frontend as a backend/AI person is harder than it looks.** CSS overrides, Streamlit's internal component structure, rendering quirks, theme conflicts – the frontend is full of small but critical details that are invisible until something breaks. Getting the UI to actually look and behave the way you designed it requires a surprising amount of precision and patience.

## What's next for Vigil

There are a few simple ways you can greatly improve Vigil's performance:
- **Richer company profiles** – more granular parameters in the sidebar (legal entity type, funding stage, specific data processing activities)
- **More countries and sources** – expanding beyond the current 18 EU countries to cover UK, US, and APAC regulatory frameworks
- **Multilingual support** – digests in the user's language, not just English

Above all, however, I would like to focus on expanding its fundamental functionalities:
- **Economics & geopolitics module** – analogous digest for macroeconomic and geopolitical changes that affect business strategy
- **Scheduled runs & email alerts** – automatic monthly Actor runs (no manual trigger needed) with push notifications with critical deadline alerts directly to founders' inboxes
- **Model evaluation** – benchmarking different LLMs on fact extraction quality and digest accuracy to continuously improve output