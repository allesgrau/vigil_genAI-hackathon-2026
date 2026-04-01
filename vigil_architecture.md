# Vigil — System Architecture

> End-to-end technical specification for the Find → Warn → Protect pipeline.
> Written for implementation at GenAI Zurich Hackathon 2026.

---

## What Already Exists vs. What Needs to Be Built

```
 ALREADY BUILT (Apify hackathon)          TO BUILD (Zurich hackathon)
 ─────────────────────────────────         ──────────────────────────────
 ✅ EUR-Lex scraper                        🔨 Business registry scraper
 ✅ GDPR/EDPB scraper                      🔨 Company-risk matching engine
 ✅ National regulators scraper (17)        🔨 Twilio Voice outreach agent
 ✅ Document chunker                        🔨 Follow-up email (SendGrid)
 ✅ Fact extraction (Claude 3 Haiku)        🔨 Report viewer page
 ✅ Embeddings (text-embedding-3-small)     🔨 Subscription/cooldown logic
 ✅ Relevance filter (keyword + boost)      🔨 /vigil Claude Code Skill
 ✅ Vector store + retriever                🔨 Outreach orchestrator
 ✅ Digest generator                        🔨 Company database (SQLite)
 ✅ Alert engine                            🔨 Landing page (v0.dev → HTML/CSS)
 ✅ Markdown/PDF formatter
 ✅ Streamlit app (subscriber platform)
 ✅ Apify Actor deployment
```

---

## High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VIGIL SYSTEM                                     │
│                                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────────┐    │
│  │             │    │              │    │                             │    │
│  │    FIND     │───►│    WARN      │───►│         PROTECT            │    │
│  │             │    │              │    │                             │    │
│  │  Apify      │    │  Twilio      │    │  /vigil Claude Skill       │    │
│  │  scrapers   │    │  Voice+Email │    │  + Streamlit platform      │    │
│  │  + matching │    │  + SendGrid  │    │  + Landing page (v0.dev)   │    │
│  │             │    │              │    │                             │    │
│  └─────────────┘    └──────────────┘    └─────────────────────────────┘    │
│        │                   │                          │                     │
│        └───────────────────┴──────────────────────────┘                     │
│                            │                                                │
│                    ┌───────┴────────┐                                       │
│                    │   SQLite DB    │                                       │
│                    │  companies     │                                       │
│                    │  outreach_log  │                                       │
│                    │  subscriptions │                                       │
│                    └────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1 — FIND

### 1A. Regulatory Monitoring (already built)

Existing pipeline. No changes needed. Runs on Apify.

```
Apify website-content-crawler
    ↓
EUR-Lex + EDPB + 17 national scrapers (asyncio.gather)
    ↓
Chunker (500 chars, 50 overlap)
    ↓
Fact extraction (Claude 3 Haiku via OpenRouter)
    ↓
Embedding (text-embedding-3-small)
    ↓
Structured facts with deadlines, severity, articles
```

**API used:** Apify Client (`apify-client` Python package)
**LLM used:** `anthropic/claude-3-haiku` via OpenRouter Apify Standby Actor
**Embeddings:** `openai/text-embedding-3-small` via OpenRouter

### 1B. Business Registry Scraper (to build)

Scrapes public EU business registries to discover companies.

**Target registries (start with 2-3 for hackathon):**

| Country | Registry | URL | What we get |
|---------|----------|-----|-------------|
| DE | Handelsregister | handelsregister.de | Company name, legal form, address, business purpose (Gegenstand), registration date |
| PL | KRS (via API) | api-krs.ms.gov.pl | Company name, NIP, REGON, PKD codes (industry classification), address |
| UK | Companies House | api.companieshouse.gov.uk | Company name, SIC codes, registered address, incorporation date |

**Implementation:**

```python
# src/scrapers/registry_scraper.py

async def scrape_registries(client: ApifyClient, countries: List[str]) -> List[dict]:
    """
    Returns list of company profiles:
    {
        "company_name": "TechStartup GmbH",
        "country": "DE",
        "industry": "fintech",          # classified from business purpose / SIC/PKD codes
        "legal_form": "GmbH",
        "address": "Berlin, Germany",
        "phone": "+49...",              # if available
        "email": "info@...",            # if available
        "registration_date": "2024-01-15",
        "business_purpose": "Software development for financial services",
        "raw_industry_codes": ["62.01", "64.19"],  # NACE/SIC/PKD
        "source_registry": "handelsregister.de"
    }
    """
```

**Industry classification from registry codes:**

Registries use standardized industry codes (NACE in EU, SIC in UK, PKD in PL). We map these to Vigil's industry categories:

```python
# src/processing/industry_classifier.py

NACE_TO_VIGIL = {
    "64": "fintech",    # Financial service activities
    "65": "fintech",    # Insurance
    "66": "fintech",    # Activities auxiliary to financial services
    "86": "healthcare", # Human health activities
    "87": "healthcare", # Residential care
    "47": "ecommerce",  # Retail trade
    "62": "saas",       # Computer programming
    "63": "saas",       # Information service activities
    "10": "manufacturing",  # Manufacture of food products
    # ...
}

def classify_industry(nace_codes: List[str]) -> str:
    """Map NACE/SIC/PKD codes to Vigil industry category."""
```

For companies where codes are ambiguous, Claude classifies from the `business_purpose` text field:

```python
def classify_with_llm(business_purpose: str, client: OpenAI) -> str:
    """Fallback: ask Claude to classify industry from free-text description."""
```

**For hackathon:** Start with the Polish KRS API (it has a free REST API at `api-krs.ms.gov.pl`) and/or Companies House (free API with key). Handelsregister is harder to scrape — consider using Apify `website-content-crawler` on it.

### 1C. Company-Risk Matching Engine (to build)

Cross-references discovered companies with extracted regulatory facts to find at-risk businesses.

```python
# src/matching/risk_matcher.py

def match_companies_to_risks(
    companies: List[dict],       # from registry scraper
    facts: List[dict],           # from regulatory pipeline
) -> List[dict]:
    """
    Returns companies with matched risks:
    {
        "company": { ... },
        "matched_risks": [
            {
                "regulation": "AI Act",
                "article": "Art. 52",
                "deadline": "2026-08-01",
                "days_remaining": 28,
                "severity": "critical",
                "action_required": "Register AI systems used in credit scoring",
                "alert_text": "..."  # personalized by Claude
            }
        ],
        "risk_score": 85,          # 0-100
        "priority": "high"         # for outreach queue ordering
    }
    """
```

**Matching logic:**
1. Map company's industry + country to applicable regulations
2. Filter facts by those regulations + future deadlines
3. Score by deadline proximity + severity
4. Generate personalized `alert_text` for each match using Claude

**Output:** Ranked outreach queue, sorted by `risk_score` descending.

---

## Stage 2 — WARN

### 2A. Outreach Orchestrator (to build)

Central controller that manages the call + email outreach and cooldown logic.

```python
# src/outreach/orchestrator.py

async def run_outreach(outreach_queue: List[dict], db: Database):
    """
    For each company in the queue:
    1. Check cooldown (skip if contacted < 3 months ago)
    2. Attempt Twilio Voice call
    3. Always send follow-up email (whether answered or not)
    4. Log attempt in database
    """
    for entry in outreach_queue:
        company = entry["company"]

        # Check cooldown
        if db.is_in_cooldown(company["company_name"]):
            continue

        # Attempt call
        call_result = await make_outreach_call(
            phone=company["phone"],
            alert=entry["matched_risks"][0],
            company=company
        )

        # Always send follow-up email with briefing + subscription link
        await send_subscription_email(company, entry["matched_risks"])
        db.log_outreach(company, "call", call_result.status)
```

### 2B. Twilio Voice — AI Outreach Call (to build)

**How Twilio Voice + AI agent works:**

Twilio doesn't run your AI model directly. Instead, Twilio calls the phone number, and your server controls what happens during the call via **webhooks**. The flow:

```
Vigil server                          Twilio                    Phone
    │                                   │                         │
    │── POST /calls (create call) ─────►│                         │
    │                                   │── rings ───────────────►│
    │                                   │◄── picks up ────────────│
    │◄── POST /webhook/voice ───────────│                         │
    │                                   │                         │
    │── TwiML: <Say> or <Play> ────────►│── plays audio ─────────►│
    │                                   │                         │
```

**Two approaches for AI voice:**

**Approach A — Pre-generated audio (simpler, recommended for hackathon):**

```python
# src/outreach/voice_agent.py
from twilio.rest import Client as TwilioClient
import os

twilio_client = TwilioClient(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

def make_outreach_call(phone: str, alert: dict, company: dict) -> dict:
    """
    1. Generate speech script with Claude
    2. Convert to audio with TTS (Twilio <Say> or ElevenLabs)
    3. Initiate call via Twilio
    4. Twilio hits our webhook, we serve TwiML with the script
    """

    # Step 1: Generate the script
    script = generate_call_script(alert, company)

    # Step 2: Create the call — Twilio will POST to our webhook
    call = twilio_client.calls.create(
        to=phone,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=f"{os.getenv('SERVER_URL')}/webhook/voice?company_id={company['id']}",
        status_callback=f"{os.getenv('SERVER_URL')}/webhook/call-status",
        timeout=30
    )
    return call
```

**The webhook server (FastAPI):**

```python
# src/outreach/webhook_server.py
from fastapi import FastAPI, Request, Form
from twilio.twiml.voice_response import VoiceResponse

app = FastAPI()

@app.post("/webhook/voice")
async def handle_voice(request: Request, company_id: str):
    """Twilio hits this when the call connects."""

    # Get the pre-generated script for this company
    script = db.get_call_script(company_id)

    response = VoiceResponse()

    # Option 1: Twilio's built-in TTS (simplest)
    response.say(
        script,
        voice="Google.en-US-Neural2-F",   # Natural-sounding voice
        language="en-US"
    )

    # After the message, offer to send report
    response.say("Press 1 if you'd like us to send you a detailed report by email.")

    gather = response.gather(
        num_digits=1,
        action=f"/webhook/gather-response?company_id={company_id}",
        timeout=5
    )

    # If no input, hang up
    response.say("Thank you for your time. Goodbye.")

    return str(response)


@app.post("/webhook/gather-response")
async def handle_gather(company_id: str, Digits: str = Form(...)):
    """Handle keypress response during call."""
    response = VoiceResponse()

    if Digits == "1":
        response.say("We'll send you a full report by email shortly. Goodbye.")
        # Trigger subscription email
        await send_subscription_email(company_id)
    else:
        response.say("Thank you. Goodbye.")

    return str(response)


@app.post("/webhook/call-status")
async def handle_call_status(request: Request):
    """Twilio sends call status updates here."""
    form = await request.form()
    status = form.get("CallStatus")  # "completed", "no-answer", "busy", "failed"
    call_sid = form.get("CallSid")

    db.update_call_status(call_sid, status)
    # Email is always sent by the orchestrator regardless of call status
```

**Approach B — Real-time conversational AI (advanced, stretch goal):**

Twilio offers `<Stream>` to pipe live audio to a WebSocket server. You could connect this to Claude or a speech-to-text + Claude + TTS pipeline for real conversations. This is complex — save for post-hackathon.

**For hackathon: Use Approach A.** Pre-generate the script with Claude, play it with Twilio `<Say>`, collect keypress input with `<Gather>`. Simple, reliable, impressive in demo.

### 2C. Call Script Generation (to build)

```python
# src/outreach/script_generator.py

def generate_call_script(alert: dict, company: dict) -> str:
    """Generate a natural 30-second phone script with Claude."""

    prompt = f"""Generate a brief, professional phone script (max 4 sentences).

You are calling {company['company_name']}, a {company['industry']} company in {company['country']}.

Key alert: {alert['regulation']} {alert['article']} — deadline in {alert['days_remaining']} days.
Action required: {alert['action_required']}

The script should:
- Greet and identify as Vigil
- State the specific deadline and regulation
- Give 1-2 concrete action items
- End by offering to send a full report by email

Tone: professional, calm, helpful. Not salesy. Not alarming.
Speak as if leaving a voicemail — no pauses for responses.
"""

    response = openai_client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

### 2D. Follow-up Email with Report Link (to build)

**API: SendGrid** (free tier: 100 emails/day — plenty for hackathon)

```python
# src/outreach/email_sender.py
import sendgrid
from sendgrid.helpers.mail import Mail, Content

sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))

def send_subscription_email(company: dict, risks: List[dict]):
    """Send follow-up email with full briefing + subscription link."""

    # Generate detailed briefing with Claude
    briefing = generate_email_briefing(company, risks)

    message = Mail(
        from_email="alerts@vigil.eu",
        to_emails=company["email"],
        subject=f"Vigil Compliance Alert: {risks[0]['regulation']} deadline approaching",
    )

    # HTML email with:
    # 1. Full briefing (what regulation, what changed, what to do)
    # 2. Deadline countdown
    # 3. CTA button: "Subscribe to Vigil — 49 EUR/month"
    #    Links to: https://vigil.eu/subscribe?company_id=xxx
    message.content = Content("text/html", briefing)

    sg.send(message)
```

### 2E. Company Database & Cooldown Logic (to build)

**SQLite** — lightweight, no server needed, perfect for hackathon.

```python
# src/database/db.py
import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, path="vigil.db"):
        self.conn = sqlite3.connect(path)
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT,
                industry TEXT,
                phone TEXT,
                email TEXT,
                source_registry TEXT,
                discovered_at TEXT
            );

            CREATE TABLE IF NOT EXISTS outreach_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT,
                channel TEXT,        -- 'call', 'email'
                status TEXT,         -- 'answered', 'no_answer', 'email_sent', 'failed'
                regulation TEXT,
                attempted_at TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                company_id TEXT PRIMARY KEY,
                subscribed_at TEXT,
                status TEXT,         -- 'active', 'cancelled'
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );
        """)

    def is_in_cooldown(self, company_id: str) -> bool:
        """Check if company was contacted in the last 3 months."""
        row = self.conn.execute(
            "SELECT MAX(attempted_at) FROM outreach_log WHERE company_id = ?",
            (company_id,)
        ).fetchone()
        if not row or not row[0]:
            return False
        last_contact = datetime.fromisoformat(row[0])
        return datetime.now() - last_contact < timedelta(days=90)

    def is_subscriber(self, company_id: str) -> bool:
        row = self.conn.execute(
            "SELECT status FROM subscriptions WHERE company_id = ?",
            (company_id,)
        ).fetchone()
        return row and row[0] == "active"
```

### 2F. Subscriber Monitoring (for paying subscribers)

Subscribers get the existing Vigil pipeline running automatically:

```python
# src/outreach/subscriber_monitor.py

async def run_monthly_monitoring(db: Database):
    """Run monthly digest for all active subscribers."""
    subscribers = db.get_active_subscribers()

    for sub in subscribers:
        company_profile = {
            "company_name": sub["name"],
            "industry": sub["industry"],
            "country": sub["country"],
            "areas_of_concern": sub["areas"],
        }

        # Run existing Vigil pipeline
        # (scrape → chunk → extract → embed → filter → retrieve → digest → alerts)
        output = await run_vigil_pipeline(company_profile)

        # Send digest by email
        send_digest_email(sub, output)
```

---

## Stage 3 — PROTECT

### 3A. `/vigil` Claude Code Skill (to build)

A Claude Code Skill is a markdown file in the user's `~/.claude/skills/` directory. When the user types `/vigil`, Claude Code loads the skill prompt and executes it with full access to the codebase.

**Skill file:**

```markdown
# ~/.claude/skills/vigil-compliance.md
---
name: vigil
description: Scan the current repository for EU regulatory compliance issues (GDPR, AI Act, DORA, NIS2, PSD2, AML)
---

You are Vigil, an EU regulatory compliance scanner. Analyze the current
repository for compliance issues.

## Instructions

1. **Discover the project structure:**
   - Use Glob to find all source code files (*.py, *.js, *.ts, *.java, *.go, etc.)
   - Use Glob to find all document files (*.md, *.txt, *.pdf, *.html)
   - Use Glob to find config files (Dockerfile, docker-compose*, *.yml, *.yaml, *.env.example)

2. **Analyze source code for compliance risks:**
   - Read key source files (focus on: data models, API endpoints, auth,
     storage, logging, ML/AI pipelines)
   - Check for:
     - PII storage without encryption (GDPR Art. 32)
     - Logging/printing personal data like emails, names, IPs (GDPR Art. 5)
     - Cross-border data transfers without safeguards (GDPR Art. 46)
     - Automated decision-making without human-in-the-loop (AI Act Art. 14, GDPR Art. 22)
     - Missing consent mechanisms for data collection (GDPR Art. 7)
     - Data retention without defined deletion policy (GDPR Art. 17)
     - Missing access controls or authentication (NIS2 Art. 21)
     - Hardcoded credentials or secrets (general security)
     - AI model deployment without transparency disclosures (AI Act Art. 52)
     - Payment data handling without PCI-DSS patterns (PSD2)

3. **Analyze documents for compliance gaps:**
   - Read any privacy policy, terms of service, or DPA files in the repo
   - Check for required GDPR Art. 13/14 disclosures:
     - Identity of controller
     - Purpose of processing
     - Legal basis
     - Data retention period
     - Data subject rights
     - Right to lodge complaint with DPA
     - Automated decision-making disclosure (Art. 22)
   - Flag outdated or missing sections

4. **Analyze infrastructure for compliance risks:**
   - Read Docker/cloud configs for data residency issues
   - Check for unencrypted storage, missing TLS, exposed ports
   - Flag any non-EU cloud regions if detected

5. **Generate report:**
   Format your output as:

   ## Vigil Compliance Report

   **Repository:** [repo name]
   **Scanned:** [number] source files, [number] documents, [number] configs
   **Issues found:** [number]

   ### Critical (immediate legal risk)

   **[Issue title]**
   - File: `path/to/file.py:42`
   - Regulation: GDPR Article 32
   - Issue: [plain-language description]
   - Risk: [what could happen — fine, enforcement action]
   - Fix: [concrete, actionable recommendation]

   ### High (upcoming deadline or significant gap)
   [same format]

   ### Medium (best practice gap)
   [same format]

   ### Compliant
   [list anything that's already well-handled]

6. **Important rules:**
   - Be specific: cite exact file paths and line numbers
   - Be practical: every finding must have a concrete fix
   - Do NOT hallucinate regulations — only cite real articles
   - Do NOT flag things that aren't actual compliance issues
   - Prioritize real risk over theoretical risk
   - If you find no issues, say so
```

**How to install the skill:**

The skill is a single `.md` file. User places it in their Claude Code skills directory:
- Linux/Mac: `~/.claude/skills/vigil-compliance.md`
- Windows: `C:\Users\<user>\.claude\skills\vigil-compliance.md`

Then they type `/vigil` in any repo. That's it.

**For hackathon demo:** Pre-install the skill on the demo machine. Open a terminal in a sample project with known compliance issues. Type `/vigil`. The report appears.

### 3B. Frontend Architecture — Two Separate Sites

Vigil has two frontend surfaces with different audiences and purposes:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                      │
│                                                                       │
│  ┌────────────────────────────┐    ┌──────────────────────────────┐  │
│  │     LANDING PAGE           │    │    SUBSCRIBER PLATFORM       │  │
│  │     (vigil.eu)             │    │    (app.vigil.eu)            │  │
│  │                            │    │                              │  │
│  │  Static HTML/CSS/JS        │    │  Streamlit (existing app)   │  │
│  │  Generated via v0.dev      │    │                              │  │
│  │  Hosted: GitHub Pages      │    │  Hosted: Streamlit Cloud    │  │
│  │                            │    │  (already deployed)          │  │
│  │  Audience: everyone        │    │  Audience: subscribers       │  │
│  │                            │    │                              │  │
│  │  Sections:                 │    │  Features:                   │  │
│  │  - Hero: Find.Warn.Protect │    │  - Regulatory digest         │  │
│  │  - How it works (3 steps)  │    │  - Regulation library        │  │
│  │  - Pricing (free vs sub)   │    │  - Deadline alerts           │  │
│  │  - CTA → subscribe        │    │  - Company profile config    │  │
│  │  - Report viewer (/report) │    │  - PDF/Markdown export       │  │
│  │                            │    │                              │  │
│  └────────────────────────────┘    └──────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Landing page generation workflow:**

1. Go to **v0.dev** (Vercel's AI UI generator)
2. Prompt: *"A modern SaaS landing page for a compliance intelligence platform called Vigil. Dark blue/navy theme with white text. Hero section with tagline 'Find. Warn. Protect.' and subtitle about EU regulatory compliance for SMEs. Three-step horizontal pipeline section showing Find → Warn → Protect with icons. Pricing section with two tiers: Free (one alert) and Subscriber (49 EUR/month). Professional, trustworthy, enterprise-grade design. No emojis."*
3. Iterate on the design in v0.dev until satisfied
4. Export as HTML/CSS (or React — then build to static HTML)
5. Place in `landing/` directory, deploy to GitHub Pages

**For hackathon:** Generate with v0.dev, export, tweak if needed. The landing page hosts the report viewer (`vigil.eu/report/{id}`) linked from follow-up emails.

**Streamlit platform (existing, no changes needed for hackathon):**

The current Streamlit app at `vigil-demo.streamlit.app` already has digest generation and regulation library. This becomes the subscriber platform. No UI work needed for the hackathon — the `/vigil` Claude Skill is the main new PROTECT feature.

---

## Webhook Server Architecture

The WARN stage requires a server that Twilio can reach via public URL. This is the only backend service we need to build and host.

```
┌────────────────────────────────────────────────────────┐
│              FastAPI Webhook Server                      │
│              (hosted on Railway / Render / ngrok)        │
│                                                          │
│  POST /webhook/voice          ← Twilio calls this       │
│  POST /webhook/gather-response ← Twilio keypress        │
│  POST /webhook/call-status    ← Twilio call ended       │
│                                                          │
│  POST /api/outreach/run       ← Trigger outreach cycle   │
│  GET  /api/report/{id}        ← View company report      │
│  POST /api/subscribe          ← Handle subscription      │
│                                                          │
│  Internal:                                               │
│  - SQLite database (companies, outreach_log, subs)       │
│  - Script generator (Claude via OpenRouter)              │
│  - Email sender (SendGrid)                               │
│                                                          │
└────────────────────────────────────────────────────────┘
```

**Hosting for hackathon:**

During development: **ngrok** exposes your local FastAPI server to the internet so Twilio can reach it.

```bash
# Terminal 1: Run the FastAPI server
uvicorn src.outreach.webhook_server:app --port 8000

# Terminal 2: Expose via ngrok
ngrok http 8000
# → https://abc123.ngrok.io  ← use this as SERVER_URL in .env
```

For demo: Deploy on **Railway** or **Render** (free tier, instant deploys from git).

---

## External APIs & Accounts Needed

| Service | What for | Plan | Cost | Setup |
|---------|----------|------|------|-------|
| **Twilio** | Voice calls | Free trial | $15.50 credit (free) | 1. Sign up → 2. Get Account SID + Auth Token → 3. Buy a phone number ($1.15/mo) → 4. Verify your personal number for testing |
| **SendGrid** | Emails | Free tier | 100 emails/day (free) | 1. Sign up → 2. Create API key → 3. Verify sender email |
| **Apify** | Web scraping + OpenRouter LLM | Already have | Existing account | Already configured |
| **ngrok** | Tunnel for local webhooks | Free tier | Free | 1. Sign up → 2. `npm install -g ngrok` → 3. `ngrok http 8000` |
| **v0.dev** | Landing page generation | Free tier | Free (10 generations/mo) | 1. Sign in with GitHub → 2. Prompt → 3. Export code |
| **GitHub Pages** | Landing page hosting | Free | Free | 1. Push `landing/` to repo → 2. Enable Pages in repo settings |

**Environment variables (new, in addition to existing):**

```bash
# .env (add to existing)

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890

# SendGrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Server
SERVER_URL=https://abc123.ngrok.io    # or Railway/Render URL
APP_URL=https://vigil-demo.streamlit.app
```

---

## Proposed Repository Structure

```
vigil_genAI-hackathon-2026/
│
├── .actor/                            # Apify Actor config (existing)
│   ├── actor.json
│   └── input_schema.json
│
├── src/
│   ├── scrapers/                      # FIND — data collection
│   │   ├── eurlex_scraper.py          # ✅ existing
│   │   ├── gdpr_scraper.py            # ✅ existing
│   │   ├── national_scraper.py        # ✅ existing
│   │   └── registry_scraper.py        # 🔨 NEW — business registry scraping
│   │
│   ├── processing/                    # FIND — data processing
│   │   ├── chunker.py                 # ✅ existing
│   │   ├── fact_extractor.py          # ✅ existing
│   │   ├── embedder.py                # ✅ existing
│   │   ├── relevance_filter.py        # ✅ existing
│   │   └── industry_classifier.py     # 🔨 NEW — NACE/SIC → Vigil industry
│   │
│   ├── rag/                           # FIND — retrieval
│   │   ├── vector_store.py            # ✅ existing
│   │   ├── retriever.py               # ✅ existing
│   │   └── prompt_templates.py        # ✅ existing
│   │
│   ├── matching/                      # FIND — company-risk matching
│   │   └── risk_matcher.py            # 🔨 NEW — match companies to deadlines
│   │
│   ├── digest/                        # existing pipeline output
│   │   ├── digest_generator.py        # ✅ existing
│   │   ├── alert_engine.py            # ✅ existing
│   │   └── formatter.py              # ✅ existing
│   │
│   ├── outreach/                      # WARN — all outreach logic
│   │   ├── orchestrator.py            # 🔨 NEW — call + email outreach
│   │   ├── voice_agent.py             # 🔨 NEW — Twilio Voice call creation
│   │   ├── script_generator.py        # 🔨 NEW — Claude generates call script
│   │   ├── email_sender.py            # 🔨 NEW — SendGrid emails
│   │   ├── webhook_server.py          # 🔨 NEW — FastAPI webhooks for Twilio
│   │   └── subscriber_monitor.py      # 🔨 NEW — monthly digest for subs
│   │
│   ├── database/                      # Shared state
│   │   └── db.py                      # 🔨 NEW — SQLite wrapper
│   │
│   └── main.py                        # ✅ existing Apify Actor entrypoint
│
├── skill/
│   └── vigil-compliance.md            # 🔨 NEW — /vigil Claude Code Skill
│
├── landing/                           # 🔨 NEW — static landing page
│   ├── index.html                     # Generated via v0.dev
│   ├── style.css                      # (or Tailwind inline)
│   └── report.html                    # Company report viewer (linked from email)
│
├── app.py                             # ✅ existing Streamlit frontend (subscriber platform)
├── server.py                          # 🔨 NEW — FastAPI server entrypoint
│
├── tests/
│   ├── test_vigil.py                  # ✅ existing
│   ├── test_outreach.py               # 🔨 NEW
│   └── test_skill.py                  # 🔨 NEW
│
├── demo/                              # Demo materials & mock data
│   ├── pre_scraped_facts.json         # 🔨 NEW — pre-scraped regulatory facts for demo
│   ├── mock_alert.json                # 🔨 NEW — hardcoded alert for demo outreach
│   ├── seed_db.py                     # 🔨 NEW — script to seed SQLite with test company
│   ├── sample_app/                    # 🔨 NEW — fake app with planted compliance issues
│   │   ├── app.py                     #   PII in logs, no encryption, no HITL
│   │   ├── models.py                  #   Plaintext PII storage
│   │   ├── scoring.py                 #   Automated decisions without human review
│   │   ├── config.py                  #   US region cloud config
│   │   └── PRIVACY_POLICY.md          #   Intentionally incomplete
│   ├── vigil_start.png                # ✅ existing screenshots
│   ├── working_vigil.png
│   └── ...
├── .streamlit/                        # Streamlit config (existing)
│
├── vigil_vision.md                    # Product vision doc
├── vigil_architecture.md              # This document
├── vigil_description.md               # Original hackathon description
├── README.md                          # ✅ existing
│
├── Dockerfile                         # ✅ existing (Apify Actor)
├── requirements.txt                   # ✅ existing + new deps
├── requirements-dev.txt               # ✅ existing + new deps
├── .env.example                       # ✅ existing + new vars
└── .gitignore                         # ✅ existing
```

**New dependencies to add to `requirements.txt`:**

```
# Twilio
twilio>=9.0.0

# SendGrid
sendgrid>=6.11.0

# FastAPI (webhook server)
fastapi>=0.115.0
uvicorn>=0.30.0

# Database
# (sqlite3 is built-in, no extra dependency)
```

---

## Data Flow — End-to-End

```
                         ┌──────────────────────────────────────┐
                         │           SCHEDULED RUN               │
                         │     (monthly or on-demand)            │
                         └──────────────┬───────────────────────┘
                                        │
                    ┌───────────────────┬┴──────────────────────┐
                    ▼                   ▼                        ▼
          ┌─────────────────┐ ┌─────────────────┐    ┌──────────────────┐
          │  Scrape EU       │ │  Scrape business │    │  Load existing   │
          │  regulations     │ │  registries      │    │  subscribers     │
          │  (existing)      │ │  (new)           │    │  from SQLite     │
          └────────┬────────┘ └────────┬─────────┘    └────────┬─────────┘
                   │                   │                        │
                   ▼                   │                        │
          ┌─────────────────┐          │                        │
          │  Chunk → Extract │          │                        │
          │  → Embed → Filter│          │                        │
          │  → Retrieve      │          │                        │
          │  (existing)      │          │                        │
          └────────┬────────┘          │                        │
                   │                   │                        │
                   ▼                   ▼                        │
          ┌─────────────────────────────────────┐              │
          │  RISK MATCHER                        │              │
          │  companies × regulatory facts        │              │
          │  → outreach queue (sorted by risk)   │              │
          └────────────────┬────────────────────┘              │
                           │                                    │
              ┌────────────┴──────────────┐                    │
              ▼                           ▼                    ▼
    ┌──────────────────┐       ┌───────────────────────────────────┐
    │  OUTREACH         │       │  SUBSCRIBER MONITORING             │
    │  (new companies)  │       │  (existing subscribers)            │
    │                   │       │                                     │
    │  For each:        │       │  Run Vigil pipeline per subscriber  │
    │  1. Check cooldown│       │  → email monthly digest             │
    │  2. Call (Twilio)  │       │  → email for critical alerts        │
    │  3. Always→email  │       │                                     │
    │  4. Log to SQLite │       │                                     │
    └──────────────────┘       └───────────────────────────────────┘
```

---

## How the Demo Machine Should Be Set Up

```
Terminal 1:  uvicorn server:app --port 8000          # FastAPI webhooks
Terminal 2:  ngrok http 8000                          # Public URL for Twilio
Terminal 3:  streamlit run app.py                     # Web platform
Terminal 4:  Claude Code (with /vigil skill installed) # Live demo of PROTECT
Phone:       Your personal phone (verified in Twilio)  # Receives the demo call
```

**Demo preparation checklist:**
- [ ] Twilio account with verified phone number
- [ ] At least 1 test company in SQLite with your phone number
- [ ] Pre-scraped regulatory facts (don't live-scrape on stage — too slow)
- [ ] Sample repo with planted compliance issues for `/vigil` demo
- [ ] `/vigil` skill installed in Claude Code on demo machine

---

## Key Technical Decisions & Rationale

| Decision | Why |
|----------|-----|
| **SQLite, not PostgreSQL** | Zero setup, single file, works everywhere. For a hackathon with <1000 companies, SQLite is more than enough. Migrate to PostgreSQL post-hackathon. |
| **Pre-generated call script, not real-time conversation** | Real-time voice AI requires WebSocket streaming, speech-to-text, TTS pipeline. Pre-generated script with `<Say>` + `<Gather>` gives 90% of the wow factor with 10% of the complexity. |
| **Claude Skill, not web upload** | Zero friction for the user. The skill reads the repo directly — no file picker, no upload, no server processing. Also: trivially fast to build (it's a markdown file). |
| **ngrok for hackathon, Railway for demo** | ngrok is instant (no deploy). Railway/Render gives a stable URL for the actual presentation. |
| **SendGrid, not raw SMTP** | Free tier is enough. Clean API. HTML email templates. Deliverability is handled. |
| **FastAPI, not Flask** | Async-native (matches Twilio's webhook pattern). Auto-generated OpenAPI docs. Type hints. Faster. |
| **Separate `server.py` from `main.py`** | `main.py` = Apify Actor (scraping pipeline). `server.py` = FastAPI (webhooks + API). Different runtimes, different concerns. |
| **v0.dev landing page, not custom frontend** | On a hackathon, you don't have time to write CSS from scratch. v0.dev generates senior-designer-level UI in minutes. Landing page is static HTML — no build step, no framework, instant deploy to GitHub Pages. |
| **Two frontends, not one** | Landing page = marketing, public, static. Streamlit = functional platform for subscribers. Different concerns, different hosting, different audiences. Trying to merge them would compromise both. |
