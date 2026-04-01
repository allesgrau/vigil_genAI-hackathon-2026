# Vigil — Hackathon Action Plan

> Step-by-step implementation plan for the Find → Warn → Protect pipeline.
> Each task is atomic — small enough to complete, test, and move on.

---

## Ground Rules

1. **Build in demo order.** The demo has 3 acts. Build Act 1 first (WARN — the most impressive part), then Act 2 (PROTECT — the easiest part), then Act 1's data pipeline (FIND — the backend nobody sees). If you run out of time, you can fake FIND with hardcoded data and still have a killer demo.
2. **Test each piece before moving on.** Every task ends with a verification step.
3. **Pre-scrape regulatory data early.** Don't rely on live scraping during the demo.
4. **Hardcode first, generalize later.** Get one company working end-to-end before building loops.

---

## Phase 0 — Setup (before the hackathon starts)

> Do this at the hotel the night before, or during the first 30 minutes.

### 0.1 Create accounts and get API keys

- [x] **Twilio** — sign up at twilio.com/try-twilio ✅
  - Get Account SID and Auth Token (Console → Account Info)
  - Buy a phone number (Console → Phone Numbers → Buy a Number, ~$1.15)
  - Add your personal phone as a verified number (Console → Verified Caller IDs)
  - Note: Twilio trial accounts can only call verified numbers — that's fine for demo
- [x] **SendGrid** — sign up at sendgrid.com ✅
  - Create API key (Settings → API Keys → Create)
  - Verify a sender email (Settings → Sender Authentication → Single Sender)
- [x] **ngrok** — sign up at ngrok.com ✅
  - Get auth token (Dashboard → Your Authtoken)
  - Install: `pip install pyngrok` or `npm install -g ngrok`
  - Authenticate: `ngrok config add-authtoken YOUR_TOKEN`
- [x] **v0.dev** — sign in with GitHub at v0.dev (later, Phase 4) ✅

**Verify:** All 4 accounts created, all API keys saved. ✅

### 0.2 Set up environment

- [x] Update `.env` with new keys ✅
  ```bash
  # Add to existing .env
  TWILIO_ACCOUNT_SID=ACxxxxxxxx
  TWILIO_AUTH_TOKEN=xxxxxxxx
  TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
  SENDGRID_API_KEY=SG.xxxxxxxx
  SERVER_URL=http://localhost:8000
  APP_URL=https://vigil-demo.streamlit.app
  ```
- [x] Install new dependencies ✅
  ```bash
  pip install twilio sendgrid fastapi uvicorn pyngrok
  ```
- [x] Create new directories ✅
  ```bash
  mkdir -p src/outreach src/matching src/database skill landing
  ```

**Verify:** `python -c "import twilio, sendgrid, fastapi; print('OK')"` prints OK. ✅

### 0.3 Pre-scrape regulatory data

- [x] Run the existing Vigil pipeline once in full mode for 2-3 company profiles (e.g. fintech/DE, saas/PL, healthcare/FR) ✅
- [x] Save the extracted facts to a JSON file ✅
- [x] This file will be used during the demo instead of live scraping (which takes minutes) ✅

**Verify:** `demo/pre_scraped_facts.json` exists and contains structured facts with deadlines.

---

## Phase 1 — WARN: Twilio Voice + Email (the wow factor)

> This is the most impressive part of the demo. Build it first.

### 1.1 SQLite database

- [x] Create `src/database/db.py` with the `Database` class ✅
  - `__init__` creates tables: `companies`, `outreach_log`, `subscriptions`
  - `add_company(company: dict)`
  - `get_company(company_id: str) -> dict`
  - `log_outreach(company_id, channel, status, regulation)`
  - `is_in_cooldown(company_id) -> bool` (3-month check)
  - `get_company_by_phone(phone) -> dict`
  - `save_call_script(company_id, script)`
  - `get_call_script(company_id) -> str`
- [x] Seed the database with one test company — **your own phone number and email**: ✅
  ```python
  db = Database("vigil.db")
  db.add_company({
      "id": "test-001",
      "name": "TechStartup GmbH",
      "country": "DE",
      "industry": "fintech",
      "phone": "+48XXXXXXXXX",   # YOUR phone number
      "email": "your@email.com", # YOUR email
      "source_registry": "manual"
  })
  ```

**Verify:** `python -c "from src.database.db import Database; db = Database('vigil.db'); print(db.get_company('test-001'))"` prints the test company.

### 1.2 Call script generator

- [x] Create `src/outreach/script_generator.py` ✅
  - Function `generate_call_script(alert: dict, company: dict) -> str`
  - Uses the same OpenRouter client pattern as `fact_extractor.py`
  - Prompt: professional 4-sentence phone briefing (see architecture doc for template)
- [ ] Test it standalone:
  ```python
  script = generate_call_script(
      alert={"regulation": "AI Act", "article": "Art. 52", "days_remaining": 28,
             "action_required": "Register AI systems used in credit scoring"},
      company={"company_name": "TechStartup GmbH", "industry": "fintech", "country": "DE"}
  )
  print(script)
  ```

**Verify:** Script prints a natural, professional 4-sentence phone message.

### 1.3 FastAPI webhook server (minimal)

- [x] Create `server.py` at repo root: ✅
  ```python
  from fastapi import FastAPI
  from src.outreach.webhook_server import router
  app = FastAPI(title="Vigil Outreach Server")
  app.include_router(router)
  ```
- [x] Create `src/outreach/webhook_server.py` with: ✅
  - `POST /webhook/voice` — returns TwiML `<Say>` with the pre-generated script
  - `POST /webhook/gather-response` — handles keypress (1 = send email)
  - `POST /webhook/call-status` — logs call result, triggers follow-up email if no-answer
- [x] Start the server: `uvicorn server:app --port 8000` ✅
- [x] In a second terminal: `ngrok http 8000` ✅
- [x] Note the ngrok URL, update `SERVER_URL` in `.env` ✅

**Verify:** `curl -X POST http://localhost:8000/webhook/voice?company_id=test-001` returns valid TwiML XML.

### 1.4 Twilio Voice call

- [x] Create `src/outreach/voice_agent.py` ✅
  - Function `make_outreach_call(company: dict, alert: dict) -> dict`
  - Generates script via `script_generator`
  - Saves script to database (so webhook can retrieve it)
  - Creates Twilio call pointing to `/webhook/voice`
- [x] Test: call yourself ✅
  ```python
  from src.outreach.voice_agent import make_outreach_call
  result = make_outreach_call(
      company=db.get_company("test-001"),
      alert={"regulation": "AI Act", "article": "Art. 52", "days_remaining": 28,
             "action_required": "Register AI systems used in credit scoring"}
  )
  ```

**Verify:** Your phone rings. You hear the AI-generated compliance briefing. You press 1. The call ends gracefully.

### 1.5 SendGrid follow-up email

- [x] Create `src/outreach/email_sender.py` ✅
- [x] Test: send email to yourself ✅

**Verify:** You receive a professional-looking email with compliance briefing and subscribe button. ✅

### 1.6 Wire up the outreach: call + email

- [x] Create `src/outreach/orchestrator.py` ✅ (LIVE version — zero mocks!)
  - Full pipeline: Apify scrape legislation → Apify scrape registry → Claude matching → Twilio call
  - Also created `src/outreach/orchestrator_mvp.py` as fallback with pre-scraped data
- [x] Update `webhook_server.py`: ✅
  - `/webhook/call-status`: log call result
  - `/webhook/gather-response`: if digit `1`, loads alert + sends email
- [x] **Full end-to-end test:** ✅
  1. Run outreach for test company
  2. Phone rings
  3. Email arrives with briefing + report link + subscription option

**Verify:** The full flow works: call + email. All logged in SQLite. ✅

---

## Phase 2 — PROTECT: `/vigil` Claude Skill (the easy win)

> This is the fastest phase — the skill is just a markdown file.

### 2.1 Write the skill file

- [x] Create `skill/vigil-compliance.md` with the full skill prompt (see architecture doc, section 3A) ✅
- [x] The skill should instruct Claude to: ✅
  1. Glob for source code, documents, and config files
  2. Read key files
  3. Check for compliance issues (GDPR, AI Act, NIS2, etc.)
  4. Return a structured report with file paths, line numbers, regulations, and fixes

**Verify:** Read the file, make sure the prompt is clear and complete.

### 2.2 Install the skill on your machine

- [x] Copy skill to Claude Code skills directory: ✅
  ```bash
  cp skill/vigil-compliance.md ~/.claude/skills/vigil-compliance.md
  ```
  (On Windows: `copy skill\vigil-compliance.md C:\Users\basia\.claude\skills\vigil-compliance.md`)

**Verify:** Open Claude Code, type `/vigil` — it should appear as a recognized skill/command.

### 2.3 Create a demo repo with planted compliance issues

- [x] Create a small demo project (e.g. `demo/sample_app/`) with intentional compliance violations: ✅
  ```python
  # demo/sample_app/app.py — a fake fintech backend with compliance issues

  # Issue 1: PII in logs (GDPR Art. 5, Art. 32)
  import logging
  logging.info(f"User signed up: {user.email}, IP: {request.ip}")

  # Issue 2: No encryption at rest (GDPR Art. 32)
  db.execute("INSERT INTO users (email, name, ssn) VALUES (?, ?, ?)",
             (email, name, ssn))

  # Issue 3: Automated credit scoring without human-in-the-loop (AI Act Art. 14)
  def score_credit(user_data):
      return model.predict(user_data)  # No human review

  # Issue 4: Cross-border transfer (GDPR Art. 46)
  s3_client = boto3.client('s3', region_name='us-east-1')
  s3_client.upload_file(user_data_file, 'my-bucket', 'users.csv')
  ```
  ```markdown
  # demo/sample_app/PRIVACY_POLICY.md — intentionally incomplete
  ## Privacy Policy
  We collect your data to provide our services.
  # Missing: legal basis, retention period, data subject rights,
  # DPA contact, automated decision-making disclosure
  ```

**Verify:** `cd demo/sample_app && /vigil` in Claude Code finds at least 4 issues.

---

## Phase 3 — FIND: Registry Scraping + Risk Matching (the data pipeline)

> This powers the FIND stage. If time is tight, skip this and hardcode 3-5 companies in the database manually. The demo still works.

### 3.1 Business registry scraper (pick ONE registry)

- [ ] Create `src/scrapers/registry_scraper.py`
- [ ] **Recommended first target: Polish KRS API** (free, REST, no scraping needed):
  ```
  GET https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/{krs_number}?rejestr=P&format=json
  ```
  - Or: **Companies House API** (free with API key):
  ```
  GET https://api.company-information.service.gov.uk/search/companies?q=fintech&items_per_page=10
  ```
- [ ] Function `scrape_registry(country: str, query: str, limit: int) -> List[dict]`
  - Returns company profiles with: name, industry codes, address, registration number
  - For hackathon: search for companies in a specific industry (e.g. "fintech", "software")

**Verify:** Function returns a list of real companies with industry codes and contact info.

### 3.2 Industry classifier

- [ ] Create `src/processing/industry_classifier.py`
  - `NACE_TO_VIGIL` mapping dict (NACE section codes → fintech/healthcare/saas/ecommerce/manufacturing)
  - `classify_industry(codes: List[str]) -> str`
  - Fallback: `classify_with_llm(business_purpose: str) -> str` for ambiguous cases

**Verify:** `classify_industry(["64.19", "62.01"])` returns `"fintech"`.

### 3.3 Risk matcher

- [ ] Create `src/matching/risk_matcher.py`
  - Load pre-scraped regulatory facts from `demo/pre_scraped_facts.json`
  - Function `match_company_to_risks(company: dict, facts: List[dict]) -> List[dict]`
  - Filter facts by: company's industry + country + future deadlines
  - Score by: deadline proximity + severity
  - Return top 3 most urgent risks per company

**Verify:** Matching a fintech/DE company returns AI Act and DORA-related risks.

### 3.4 Wire FIND into the outreach pipeline

- [ ] Create an end-to-end script `src/find_and_warn.py`:
  ```python
  # 1. Load pre-scraped regulatory facts
  # 2. Scrape registry (or load from DB)
  # 3. Classify industries
  # 4. Match companies to risks
  # 5. For each match: run outreach orchestrator
  ```

**Verify:** Script discovers companies, matches them to risks, and triggers outreach cascade.

---

## Phase 4 — Landing Page (the polish)

> Visual presentation. Do this after the core pipeline works.

### 4.1 Generate landing page with v0.dev

- [ ] Go to v0.dev
- [ ] Prompt (start with this, iterate):
  ```
  A modern SaaS landing page for "Vigil" — an AI compliance agent for European
  SMEs. Navy/dark blue theme, clean and professional.

  Sections:
  1. Hero: Large "Find. Warn. Protect." tagline. Subtitle: "The AI compliance
     agent that finds your business, warns you before a deadline hits, and
     protects your code from regulatory risk." CTA button: "Get Started".
  2. How it works: Three-step horizontal cards with icons.
     Step 1 "Find" — "We scan business registries and EU regulations to identify
     companies at risk of non-compliance."
     Step 2 "Warn" — "An AI agent calls you with a personalized briefing
     and follows up with a detailed email. We tell you exactly what to do."
     Step 3 "Protect" — "Type /vigil in your terminal. Your code and documents
     are scanned for compliance issues in seconds."
  3. Pricing: Two cards. Free (one compliance alert) vs Subscriber (49 EUR/month
     — unlimited digests, /vigil skill, deadline alerts, regulation library).
  4. Footer with "Built at GenAI Zurich Hackathon 2026" and disclaimer.

  Style: Inter font, no emojis, enterprise-grade, trustworthy.
  ```
- [ ] Iterate 2-3 times until design looks professional
- [ ] Export as HTML/CSS

### 4.2 Place in repo and deploy

- [ ] Save exported files to `landing/index.html` (and `style.css` if separate)
- [ ] Test locally: open `landing/index.html` in browser
- [ ] Deploy to GitHub Pages:
  - Repo Settings → Pages → Source: Deploy from branch → Branch: `main`, Folder: `/landing`
  - Or just push to a `gh-pages` branch

**Verify:** Landing page is live at `https://allesgrau.github.io/vigil_genAI-hackathon-2026/` (or custom domain if configured).

---

## Phase 5 — Demo Rehearsal

> Do not skip this. Practice the demo at least twice.

### 5.1 Prepare demo environment

- [ ] Start all services:
  ```bash
  # Terminal 1: Webhook server
  uvicorn server:app --port 8000

  # Terminal 2: ngrok tunnel
  ngrok http 8000

  # Terminal 3: Streamlit
  streamlit run app.py

  # Terminal 4: Claude Code (for /vigil demo)
  claude
  ```
- [ ] Update `SERVER_URL` in `.env` with ngrok URL
- [ ] Ensure test company in database has your phone number
- [ ] Ensure `demo/sample_app/` exists with planted compliance issues
- [ ] Ensure `/vigil` skill is installed

### 5.2 Dry run the full demo

- [ ] **Act 1 (60s):** Trigger outreach for test company → phone rings on desk → listen to briefing → press 1 → email arrives
- [ ] **Act 2 (60s):** Open Claude Code in `demo/sample_app/` → type `/vigil` → compliance report appears
- [ ] **Act 3 (30s):** Show landing page in browser → show Streamlit platform → deliver business model pitch
- [ ] Time yourself. Adjust if over 3 minutes.

### 5.3 Prepare for failure

- [ ] **If Twilio call fails:** Have a pre-recorded video of the call working as backup
- [ ] **If ngrok is flaky:** Pre-record the call+email cascade, show video, then do live `/vigil` demo
- [ ] **If `/vigil` is slow:** Have a screenshot of the output ready
- [ ] **If internet dies:** Have all demo outputs saved locally (call recording, email screenshot, `/vigil` output, landing page as local HTML)

---

## Sequence and Time Estimates

```
PRIORITY    PHASE    WHAT                              DEPENDS ON
────────    ─────    ────                              ──────────
   ★★★      0       Setup (accounts, env, pre-scrape)  nothing
   ★★★      1.1     SQLite database                    Phase 0
   ★★★      1.2     Call script generator               Phase 0
   ★★★      1.3     FastAPI webhook server              Phase 1.1
   ★★★      1.4     Twilio Voice call                   Phase 1.2, 1.3
   ★★★      1.5     SendGrid email                      Phase 0
   ★★★      1.6     Wire up outreach                    Phase 1.4, 1.5
   ★★★      2.1     Write /vigil skill                  nothing
   ★★★      2.2     Install skill                       Phase 2.1
   ★★★      2.3     Create demo repo                    Phase 2.1
    ★★      3.1     Registry scraper                    Phase 0
    ★★      3.2     Industry classifier                 Phase 3.1
    ★★      3.3     Risk matcher                        Phase 0 (pre-scraped data)
    ★★      3.4     Wire FIND pipeline                  Phase 3.1-3.3, Phase 1.7
     ★      4.1     Generate landing page (v0.dev)      nothing
     ★      4.2     Deploy landing page                 Phase 4.1
   ★★★      5       Demo rehearsal                      everything
```

**Critical path (must finish for demo to work):**

```
Phase 0 → 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 5
                                                 ↑
Phase 0 → 2.1 → 2.2 → 2.3 ─────────────────────┘
```

**If time is tight, cut in this order:**
1. Cut Phase 3 entirely (hardcode companies in DB) — demo still works
2. Cut Phase 4 (no landing page) — show Streamlit instead
3. Cut Phase 1.5 (no email) — demo call only
4. NEVER cut Phase 1.4 (the call) or Phase 2 (the skill) — these ARE the demo

---

## Checklist: "Is My Demo Ready?"

- [ ] I can trigger a phone call to my own number and hear a compliance briefing
- [ ] If I press 1, I receive a follow-up email with subscription info
- [ ] I can type `/vigil` in a demo repo and get a compliance report
- [ ] I have a landing page (or Streamlit) open in a browser tab
- [ ] I have rehearsed the full 3-minute demo at least once
- [ ] I have backup materials (screenshots/video) in case of failure
