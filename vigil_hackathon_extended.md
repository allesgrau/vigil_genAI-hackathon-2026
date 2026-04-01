# Vigil — Hackathon Extended Plan

> Rozszerzenia do zrobienia PO ukończeniu `vigil_hackathon_MVP.md`.
> Każde rozszerzenie zamienia mockup z MVP na prawdziwy komponent.
> Rób je w tej kolejności — każde jest samodzielne i dodaje widoczną wartość do demo.

---

## Prerequisite

Zanim zaczniesz cokolwiek z tego pliku, upewnij się że:
- [x] Telefon dzwoni (Twilio Voice) ← z MVP
- [x] `/vigil` skill działa ← z MVP
- [x] Email z SendGrid dochodzi ← z MVP

Jeśli nie — wróć do `vigil_hackathon_MVP.md`.

---

## Extension 1 — Live scraping regulacji przez Apify (zamienia pre-scraped JSON)

**Co to zmienia:** Zamiast `demo/pre_scraped_facts.json` ładowanego z pliku, demo pokazuje live scraping jednej strony regulacyjnej przez Apify → ekstrakcję faktów → alert. Na demo mówisz: "Vigil just scraped EUR-Lex in real-time and found this deadline."

**Czas: ~45 min**

### E1.1 Wybierz JEDNĄ stronę do scrapowania

Nie scrapuj 30+ źródeł. Wybierz jedną stronę, która na pewno ma aktualny deadline:

| Opcja | URL | Dlaczego |
|---|---|---|
| **AI Act (rekomendowane)** | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689` | Nowe deadline'y, hot topic, wow na demo |
| GDPR enforcement | `https://edpb.europa.eu/news/news_en` | Zawsze świeże decyzje |

### E1.2 Napisz mini-scraper

Nie pisz nowego scrapera — **użyj istniejącego `eurlex_scraper.py`**, ale z minimalnym zakresem:

```python
# demo/live_scrape.py
import asyncio
from apify_client import ApifyClient
from src.scrapers.eurlex_scraper import scrape_eurlex
from src.processing.chunker import chunk_documents
from src.processing.fact_extractor import extract_facts

async def live_scrape_one_page():
    client = ApifyClient(token=os.getenv("APIFY_TOKEN"))

    # Scrape ONLY AI Act page, test_mode=True (2 URLs, 3 pages max)
    company_profile = {
        "areas_of_concern": ["AI Act"],
        "country": "DE",
        "industry": "fintech"
    }

    docs = await scrape_eurlex(client, company_profile, test_mode=True)
    chunks = chunk_documents(docs)
    facts = extract_facts(chunks, company_profile)

    # Save for matching
    with open("demo/live_scraped_facts.json", "w") as f:
        json.dump(facts, f, indent=2)

    print(f"Scraped {len(docs)} docs → {len(chunks)} chunks → {len(facts)} facts")
    return facts
```

**Koszt:** ~$0.10 (test_mode). **Czas:** ~30-60 sekund.

### E1.3 Zintegruj z demo flow

Zamiast ładować `pre_scraped_facts.json`, odpalasz `live_scrape_one_page()` na początku demo. Na ekranie widać: "Scraping EUR-Lex... Found 12 regulatory facts. Matching against companies..."

**Verify:** Skrypt scrapuje, wyciąga fakty, wyświetla je. Zajmuje <60 sekund.

**Ryzyko:** Apify scraping może być wolne albo failować na demo. **Mitygacja:** Odpal scrape PRZED demo (np. 5 min wcześniej), pokaż wyniki. Albo miej `pre_scraped_facts.json` jako fallback.

---

## Extension 2 — Live scraping rejestru firm przez Apify (zamienia hardcoded firmę)

**Co to zmienia:** Zamiast jednej hardcoded firmy w SQLite, demo pokazuje live discovery firmy z rejestru. Na demo: "Vigil scraped the Polish business registry and found this company."

**Czas: ~1h**

### E2.1 Wybierz rejestr (jeden)

| Opcja | Metoda | Trudność |
|---|---|---|
| **Polish KRS API (rekomendowane)** | REST API, no scraping needed | Łatwe |
| Companies House (UK) | REST API z kluczem | Łatwe, ale trzeba API key |
| Handelsregister (DE) | Apify website-content-crawler | Średnie |

**KRS API jest najłatwiejszy** — darmowy, publiczny, zwraca JSON. Ale nie zwraca numeru telefonu/emaila (to dane nie-publiczne w KRS). Więc:
- Scrapujesz KRS → dostajesz nazwę firmy, PKD kody, adres
- Numer telefonu i email → hardcoded (Twój numer) — w demo mówisz "and we enriched the contact data from public sources"

### E2.2 Scraper rejestru

```python
# src/scrapers/registry_scraper.py
import requests

def scrape_krs(krs_number: str) -> dict:
    """Scrape a single company from Polish KRS API."""
    url = f"https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/{krs_number}?rejestr=P&format=json"
    resp = requests.get(url)
    data = resp.json()

    # Extract key fields from KRS response
    dane = data.get("odppisPełny", {}).get("dane", {})
    return {
        "name": dane.get("nazwa"),
        "krs": krs_number,
        "nip": dane.get("nip"),
        "pkd_codes": [p.get("kod") for p in dane.get("pkd", [])],
        "address": dane.get("adres", {}).get("ulica"),
        "city": dane.get("adres", {}).get("miejscowosc"),
        "country": "PL",
    }


def search_krs_by_name(name: str) -> list:
    """Search KRS by company name."""
    url = f"https://api-krs.ms.gov.pl/api/krs/szukaj?nazwa={name}&rejestr=P&format=json"
    resp = requests.get(url)
    results = resp.json().get("wyniki", [])
    return results[:5]  # Top 5 matches
```

**Alternatywa z Apify (jeśli chcesz mieć Apify w tym stage też):**

```python
async def scrape_registry_apify(client: ApifyClient, url: str) -> list:
    """Scrape any business registry page with Apify website-content-crawler."""
    run = client.actor("apify/website-content-crawler").call(
        run_input={
            "startUrls": [{"url": url}],
            "maxCrawlDepth": 0,
            "maxCrawlPages": 3,
            "outputFormats": ["markdown"],
        },
        memory_mbytes=1024
    )
    docs = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        docs.append({"content": item.get("markdown", ""), "url": item.get("url", "")})
    return docs
```

### E2.3 Industry classifier (prosty)

```python
# src/processing/industry_classifier.py

PKD_TO_VIGIL = {
    "64": "fintech", "65": "fintech", "66": "fintech",
    "86": "healthcare", "87": "healthcare",
    "47": "ecommerce", "62": "saas", "63": "saas",
    "10": "manufacturing", "25": "manufacturing",
}

def classify_industry(pkd_codes: list) -> str:
    for code in pkd_codes:
        prefix = code[:2]
        if prefix in PKD_TO_VIGIL:
            return PKD_TO_VIGIL[prefix]
    return "saas"  # default
```

**Verify:** `classify_industry(["64.19", "62.01"])` → `"fintech"`

---

## Extension 3 — LLM-powered risk matching (zamienia hardcoded alert)

**Co to zmienia:** Zamiast `demo/mock_alert.json`, Claude analizuje firmę + fakty regulacyjne i generuje spersonalizowany alert. Na demo: prawdziwy AI matching, nie hardcoded.

**Czas: ~30 min**

### E3.1 Risk matcher z Claude

```python
# src/matching/risk_matcher.py
import json
from openai import OpenAI
import os

def match_company_to_risks(company: dict, facts: list) -> list:
    """Ask Claude to match a company to regulatory risks from scraped facts."""

    client = OpenAI(
        base_url=os.getenv("OPENROUTER_ACTOR_URL"),
        api_key="dummy",
        default_headers={"Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"}
    )

    facts_text = json.dumps(facts[:20], indent=2)  # Limit to 20 facts for token budget

    prompt = f"""You are a regulatory risk analyst. Given a company profile and a list of
regulatory facts, identify which regulations and deadlines apply to this company.

COMPANY:
- Name: {company['name']}
- Industry: {company.get('industry', 'unknown')}
- Country: {company.get('country', 'EU')}

REGULATORY FACTS:
{facts_text}

Return a JSON array of matched risks. Each risk must have:
- "regulation": regulation name
- "article": specific article if known
- "deadline": deadline date if known, else null
- "days_remaining": estimated days until deadline, else null
- "action_required": what the company must do (1 sentence)
- "severity": "critical", "high", or "medium"

Only return risks that are ACTUALLY RELEVANT to this specific company's industry and country.
Return max 3 most urgent risks. Return ONLY the JSON array.
"""

    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return []
```

### E3.2 Zintegruj z demo flow

```python
# demo/full_pipeline.py — cały FIND→WARN w jednym skrypcie

async def run_find_and_warn():
    # 1. Scrape regulations (Extension 1)
    facts = await live_scrape_one_page()

    # 2. Get company (Extension 2 or hardcoded)
    company = db.get_company("test-001")

    # 3. Match risks (Extension 3)
    risks = match_company_to_risks(company, facts)
    print(f"Found {len(risks)} risks for {company['name']}")

    # 4. Outreach (from MVP)
    if risks:
        await make_outreach_call(company, risks[0])
```

**Verify:** Skrypt scrapuje → matchuje → dzwoni. End-to-end pipeline.

---

## Extension 4 — Orchestrator i cascade wiring (jeśli jeszcze masz czas)

**Co to zmienia:** Call → (no answer) → automatyczny email. Pełna kaskada z `vigil_action_plan.md` Phase 1.7.

**Czas: ~30 min**

### E4.1 Wire `/webhook/call-status`

W `webhook_server.py` dodaj:

```python
@app.post("/webhook/call-status")
async def handle_call_status(request: Request):
    form = await request.form()
    status = form.get("CallStatus")
    company_id = form.get("CallSid")  # need to look up by SID

    if status == "completed":
        # Call was answered — email already triggered by gather-response
        db.log_outreach(company_id, "call", "answered")
    elif status in ("no-answer", "busy", "failed"):
        # Auto-send email as fallback
        company = db.get_company_by_call_sid(call_sid)
        await send_subscription_email(company)
        db.log_outreach(company_id, "call", status)
```

### E4.2 Orchestrator

```python
# src/outreach/orchestrator.py

async def run_outreach_for_company(company_id: str, alert: dict):
    company = db.get_company(company_id)

    if db.is_in_cooldown(company_id):
        print(f"Skipping {company['name']} — in 3-month cooldown")
        return

    # Generate and save script
    script = generate_call_script(alert, company)
    db.save_call_script(company_id, script)

    # Make the call — cascade is handled by webhooks
    make_outreach_call(company, alert)
    db.log_outreach(company_id, "call", "initiated", alert["regulation"])
```

---

## Extension 5 — Scheduled scraping for subscribers (Apify Scheduler)

**Co to zmienia:** Subscribers dostają automatyczny monthly scan nowych regulacji. Apify scheduled Actor odpala scraping co miesiąc, wyniki idą mailem do subscriberów.

**Czas: ~45 min**

### E5.1 Scheduled Apify Actor

- [ ] W Apify Console: weź istniejący scraper (z E1 lub z MVP) i ustaw Schedule → Monthly
- [ ] Actor zapisuje nowe fakty do pliku/bazy
- [ ] Alternatywnie: użyj `cron` lub Apify Scheduler API z kodu:

```python
# src/outreach/subscriber_monitor.py
from src.database.db import get_active_subscribers
from src.outreach.email_sender import send_digest_email

async def run_monthly_digest():
    subscribers = get_active_subscribers()
    for sub in subscribers:
        # Re-run fact extraction for subscriber's profile
        facts = load_latest_scraped_facts()
        risks = match_company_to_risks(sub, facts)
        if risks:
            await send_digest_email(sub, risks)
```

### E5.2 Digest email template

- [ ] Nowy template w `send_digest_email()` — różny od outreach emaila (ten jest dla istniejących subscriberów)
- [ ] Zawiera: nowe regulacje od ostatniego digestu, zbliżające się deadline'y, link do platformy

**Verify:** Subscriber dostaje email z digestem po odpaleniu `run_monthly_digest()`.

---

## Extension 6 — Compliance history (tracking w SQLite)

**Co to zmienia:** Każdy scan `/vigil` i każdy digest są zapisywane. Subscriber widzi historię: co było znalezione, co naprawione.

**Czas: ~30 min**

### E6.1 Tabela compliance_history w SQLite

```sql
CREATE TABLE compliance_history (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    scan_date TEXT NOT NULL,
    scan_type TEXT NOT NULL,  -- 'vigil_skill' or 'monthly_digest'
    findings_count INTEGER,
    findings_json TEXT,       -- full findings as JSON
    FOREIGN KEY (company_id) REFERENCES companies(id)
);
```

### E6.2 Zapis z /vigil i digestów

- [ ] Po każdym skanie `/vigil` → zapisz wynik do `compliance_history`
- [ ] Po każdym monthly digest → zapisz wynik do `compliance_history`
- [ ] Endpoint `GET /api/history/{company_id}` → zwraca historię skanów

### E6.3 Widok w Streamlit

- [ ] Nowa strona w Streamlit: "Compliance History"
- [ ] Timeline z datami skanów, liczbą findings, statusem (resolved/open)

**Verify:** Po 2 skanach `/vigil` historia pokazuje oba wpisy w Streamlit.

---

## Kolejność rozszerzeń — decision tree

```
Skończyłam MVP?
    │
    ├── NIE → wróć do vigil_hackathon_MVP.md
    │
    └── TAK → Ile mam czasu?
                │
                ├── 30 min → Extension 3 (LLM matching)
                │             Zamienia mock alert na prawdziwy AI matching.
                │             Nie wymaga nowych scraperów.
                │
                ├── 1h → Extension 1 + 3 (live scraping regulacji + matching)
                │         "Vigil just scraped EUR-Lex live and matched risks."
                │         Apify jest widocznie użyte = bonus points.
                │
                ├── 1.5h → Extension 1 + 2 + 3 (full FIND pipeline)
                │           Live scraping regulacji + rejestru + LLM matching.
                │           Pełny Find→Warn→Protect bez mocków.
                │
                ├── 2h → Extensions 1-4 (full pipeline + cascade wiring)
                │         Produkcyjna jakość demo.
                │
                ├── 2.5h → Extensions 1-4 + 6 (+ compliance history)
                │           Tracking skanów w SQLite + widok w Streamlit.
                │
                └── 3h+ → Extensions 1-6 (full pipeline + subscriber features)
                           Scheduled scraping + compliance history.
```

---

## Kiedy to robić w grafiku hackathonu

Najlepsze okna czasowe z `vigil_hackathon_MVP.md`:

| Okno | Kiedy | Ile czasu | Rekomendacja |
|---|---|---|---|
| Po feedbacku dnia 1 | 1 kwietnia, 15:00–18:00 | ~3h | Extension 1+3 (po landing page jeśli jury ją chce) |
| Stretch goals dnia 2 | 2 kwietnia, 11:00–12:30 | ~1.5h | Extension 2 (jeśli 1+3 już gotowe) albo Extension 4 |

**Nie rób extensions ZAMIAST deliverables dnia 2** (video, slide, one-pager). Deliverables > extensions.
