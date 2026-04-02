# Vigil — Devpost Project Details

## Inspiration

I've always loved building solutions that are technically ambitious, data-driven, and — most importantly — genuinely useful to people. I believe data science is one of the most extraordinary fields out there: from raw numbers and plain text, we can literally predict the future or create tools that — with the use of LLMs — democratize access to knowledge that was previously reserved for experts.

The spark for Vigil came from conversations with friends who are founders and students with brilliant startup ideas. Every single one of them complained about the same thing: they spend a shocking amount of money on lawyers, just to stay on top of EU regulations. GDPR, AI Act, DORA, NIS2 — the landscape is vast, constantly changing, and written in language that's completely inaccessible to non-lawyers. They told me how the cost of working with legal teams and the fear of regulatory fines actively slowed down their technological development — money and energy that should go into building products instead goes into compliance paperwork.

And the numbers back this up: European companies spend over [**€150 billion per year**](https://luvianglobalinsights.substack.com/p/as-eus-regulatory-burden-grows-what) on regulatory compliance. **55% of EU-based SMEs** say administrative burdens are their single greatest challenge. For many, the first time they hear about a new regulation is when the fine arrives.

I also had a technical foundation to build on: through my university's Data Science Club, I coordinate a project building a RAG-based chatbot assistant for students & staff at my faculty. That experience with scraping and retrieval systems gave me the confidence to tackle something more ambitious.

## What it does

Vigil is an AI-powered regulatory compliance agent that runs a fully automated, end-to-end pipeline: **Find. Warn. Report. Protect.**

**Find** — Apify's `website-content-crawler` scrapes 30+ live EU regulatory sources across 18 countries (EUR-Lex, EDPB, national DPAs like BaFin, CNIL, UODO, and regulation-specific pages for GDPR, AI Act, DORA, NIS2, PSD2, AML). At the same time, it scrapes business registries to discover companies that may be affected. Claude extracts structured regulatory facts from the scraped text — what's new, what's changing, and what companies need to act on.

**Warn** — Claude matches discovered companies against extracted regulatory risks, generates a personalized call script, and Twilio places an **automated voice call** to the company. The recipient hears a 15-second compliance briefing: the regulation, the deadline, the required action.

**Report** — When the recipient presses 1 during the call, a FastAPI webhook triggers Claude to generate a **full compliance report** — exact legal citations, severity levels, deadlines, numbered action steps, and which regulatory authorities may audit this company — delivered via SendGrid within seconds.

**Protect** — Developers install the `/vigil` skill in Claude Code and type `/vigil` in their terminal. Vigil scans the entire codebase for compliance issues across 6 EU regulations — every finding includes the exact file path, the regulation it violates, and a concrete fix.

On top of the pipeline, Vigil provides a **personalized dashboard** where business owners enter their company profile and receive a monthly digest with deadline alerts, strategic insights tailored to their industry and country, and a complete regulation library that explains every regulation in plain language — no legal jargon, written specifically for their business.

Everything is live. Zero mocks. Every run scrapes real sources, extracts real facts, calls a real phone, sends a real email.

### Nerdy details

**Fact-based embeddings.** Instead of embedding raw text chunks (standard RAG), Vigil uses Claude 3 Haiku to first extract discrete structured facts from each document batch — `claim`, `regulation`, `article`, `deadline`, `action_required`, `severity` — and embeds those facts instead. This dramatically improves retrieval precision: we're searching over semantically rich regulatory claims, not arbitrary text windows.

**Two-step hybrid retrieval.** Facts are first pre-filtered using industry/country/regulation-specific keyword dictionaries (with severity-based bonus scoring: critical 5.0, high 3.0, medium 1.5), then re-ranked by cosine similarity using `text-embedding-3-small` embeddings. This combines the speed of keyword search with the precision of semantic search.

**Recency-constrained prompts.** All LLM prompts include today's date and a strict 30-day window. The model is explicitly instructed to ignore historical regulatory background and surface only recent changes — solving the core problem of RAG systems that return evergreen content as "news". Alert detection filters out past deadlines automatically.

**Dual alert detection.** Urgency is detected through two parallel methods: fast keyword matching (regex deadline extraction + urgency keywords) and accurate LLM parsing (Claude JSON extraction). Results are merged and deduplicated, with LLM alerts taking priority.

**Webhook architecture.** FastAPI handles Twilio's TwiML voice callbacks and keypress events. Call scripts are persisted in SQLite and retrieved stateless by the webhook — no in-memory state needed. Keypress 1 triggers the full email generation + SendGrid delivery pipeline.

**Resilient fallbacks.** Every layer has a fallback: embeddings fall back to deterministic MD5-based pseudo-vectors, LLM calls use bracket-extraction JSON parsing, email reports fall back to templated HTML, and the digest gracefully degrades to simple markdown summaries.

## How I built it

1. **Live scraping** — Three specialized Apify scrapers (`eurlex_scraper`, `gdpr_scraper`, `national_scraper`) covering EUR-Lex, EDPB, GDPR.eu, and 17 national regulators. They run in parallel via `asyncio.gather` with configurable crawl depth.
2. **Chunking** — Paragraph-level chunking (500 chars, 50-char overlap) preserving document metadata.
3. **Fact extraction** — Claude 3 Haiku extracts structured JSON facts in batches of 5 chunks, with JSON parse recovery.
4. **Embedding** — `text-embedding-3-small` via OpenRouter/Apify, with deterministic fallback.
5. **Two-step retrieval** — Keyword pre-filtering with industry/country dictionaries, then cosine similarity re-ranking in an in-memory vector store.
6. **Digest generation** — Claude generates personalized monthly digests, strategic insights, plain-language summaries, and deadline alerts.
7. **Outreach pipeline** — Orchestrator chains Apify scraping → Claude fact extraction → Claude risk matching → Claude script generation → Twilio voice call → FastAPI webhook → Claude report generation → SendGrid email delivery.
8. **Pipeline monitor** — SQLite `pipeline_log` table captures every step. Streamlit monitor with 5-second auto-refresh displays live logs.
9. **Dashboard** — Streamlit app with company profile builder, digest viewer, alert visualization, regulation library, and PDF export.
10. **Developer skill** — Claude Code skill definition (Markdown) that scans repos for GDPR, AI Act, DORA, NIS2, PSD2, and AML issues.

I coded Vigil entirely in Python, in Visual Studio Code, with help from Claude.

## Challenges I ran into

The biggest challenge was designing the full data pipeline: fact-based chunking, two-step retrieval, keyword scoring with industry and country-specific dictionaries, severity-boosted relevance scoring, and an in-memory vector store — all working together coherently. Each layer added complexity, and making sure the right facts surfaced for the right company profile required careful tuning at every step.

Equally hard were the system prompts. Getting Claude to produce exactly the right output format — structured JSON facts, date-aware digests, no hallucinated deadlines, plain English instead of legalese — required significant prompt engineering effort. Real-world regulatory data is also messy, scattered across millions of unstructured pages in multiple languages, which made the scraping layer far more complex than expected.

Then there was the Twilio and SendGrid integration — something completely outside my comfort zone as a Data Science student. My daily world is statistics, probability theory, and linear algebra — not webhook servers, TwiML voice responses, and email delivery APIs. Building the entire outreach architecture from scratch — FastAPI webhook endpoints, Twilio voice callbacks, keypress event handling, stateless script retrieval from SQLite, SendGrid HTML email rendering — required learning an entirely new domain in a matter of hours. Getting the webhook flow right (call initiated → voice plays script → user presses 1 → webhook fires → email generated → email sent) with proper error handling and fallbacks was one of the hardest parts of the project.

## Accomplishments that I'm proud of

I'm genuinely proud of several things. First, the accessibility of the final product — Vigil translates genuinely complex regulatory nuances into plain language that a non-lawyer founder can act on immediately. Second, the data pipeline design: fact-based embeddings over chunk-based retrieval is a meaningful architectural choice that improves precision, and the two-step hybrid retrieval system is something I'm proud to have designed and implemented from scratch. Third — working with Apify. Learning to build on top of Apify's infrastructure, from `website-content-crawler` to OpenRouter Standby, has been one of the most practically valuable skills I've gained from this hackathon, and one I'll definitely carry into future projects.

But what I'm most proud of is the **end-to-end 4-step pipeline** — Find, Warn, Report, Protect — working as a single, fully integrated system. It's not just a dashboard or a chatbot. Vigil scrapes real regulatory sources, discovers real companies, generates personalized alerts, calls a real phone, sends a real email with a legally specific compliance report, and lets developers scan their code — all in one pipeline run.

Finally — and this is personal — I learned to **prototype fast**. I'm a perfectionist by nature, and hackathons are fundamentally incompatible with perfectionism. Letting go of the need to make everything perfect before showing it to anyone was one of the hardest and most valuable lessons of this weekend.

## What I learned

**Real-world data is messy and scattered.** Scraping regulatory sources across 18 countries from unstructured HTML and then synthesizing everything into a single coherent document is genuinely hard. But it's also what makes agentic AI solutions powerful: the value is in the data pipeline, not just the model.

**Prompt engineering is everything.** A good prompt is the difference between a hallucinating model and a precise, structured output. Getting the LLM to extract the right JSON schema, respect a 30-day recency window, and produce plain English — not legalese — required careful iteration.

**Building a clean frontend as a backend/AI person is harder than it looks.** CSS overrides, Streamlit's internal component structure, rendering quirks, theme conflicts — the frontend is full of small but critical details that are invisible until something breaks.

**Feedback is invaluable.** The feedback I received on Day 1 after the initial project pitches fundamentally reshaped Vigil. It helped me structure my idea more clearly and made me realize how important it is to present the problem from a business perspective, not just a technical one. That feedback directly inspired me to build the hub and the pipeline monitor — interfaces that present Vigil's complex technical workings in a way that non-technical judges and users can immediately understand. Without that feedback loop, Vigil would have been a much more technically impressive but far less compelling product.

**Telephony and email delivery are a different world.** As a data science student, I had zero experience with Twilio webhooks, TwiML, FastAPI callback handlers, or SendGrid email APIs. Learning an entirely new domain under hackathon time pressure — and making it work reliably — taught me that the gap between "I've never done this" and "it works in production" is often smaller than it feels.

## What's next for Vigil

- **Automated scheduling** — The orchestrator runs on a weekly cron job. No manual trigger needed — companies receive proactive compliance alerts automatically.
- **Conversational AI agent** — Replace the one-way automated call with an interactive voice agent that companies can talk to, ask follow-up questions, and get real-time regulatory guidance.
- **Automatic ticket generation** — Generate Jira/Linear tickets directly from compliance alerts, so engineering teams can track regulatory action items alongside their sprint work.
- **Security incident monitoring** — Expand beyond regulatory changes to monitor data breaches, security advisories, and CVEs relevant to the company's tech stack — turning Vigil into a full compliance + security intelligence platform.
- **Richer company profiles** — More granular parameters: legal entity type, funding stage, specific data processing activities, tech stack.
- **More countries and sources** — Expanding beyond 18 EU countries to cover UK, US, and APAC regulatory frameworks.
- **Model evaluation** — Benchmarking different LLMs on fact extraction quality and digest accuracy to continuously improve output.

## Built With

- apify
- claude
- fastapi
- ngrok
- numpy
- openrouter
- python
- reportlab
- sendgrid
- sqlite
- streamlit
- twilio
