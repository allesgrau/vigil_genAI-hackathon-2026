# Vigil — Post-Hackathon / Production Gaps

> Tasks that are NOT in the hackathon action plan but ARE required for a fully functional Vigil.
> On demo day, these can be faked or skipped. After demo day, they can't.

---

## Subscription & Payment

### Subscribe endpoint
- [ ] `POST /api/subscribe` — accepts company_id, validates, creates subscription in SQLite
- [ ] For production: integrate Stripe Checkout (one-click payment → webhook confirms → activate subscription)
- [ ] For hackathon: the "Subscribe" button in the email can link to Streamlit app or a static "Thanks!" page

### Subscription management
- [ ] Cancel/pause subscription logic
- [ ] Subscription status checks before running subscriber features
- [ ] Expiry handling (what happens when someone stops paying?)

---

## Report Viewer

### Public report page
- [ ] `landing/report.html` — the page that email links point to (`vigil.eu/report/{id}`)
- [ ] `GET /api/report/{id}` — FastAPI endpoint that returns report data as JSON
- [ ] The HTML page fetches report data and renders: alert summary, deadline, action items, subscribe CTA
- [ ] For hackathon: email link can point to the Streamlit app instead

---

## Subscriber Monitoring

### Monthly automated digests
- [ ] `src/outreach/subscriber_monitor.py` — iterate over active subscribers, run Vigil pipeline per subscriber, email results
- [ ] Scheduling: cron job or Apify scheduled Actor run (monthly)
- [ ] Email template for monthly digest (different from the initial outreach email — this is for existing subscribers)

### Deadline alerts for subscribers
- [ ] 30-day, 14-day, 7-day countdown alerts via email
- [ ] Logic to avoid duplicate alerts (don't send 30-day alert if already sent)
- [ ] Subscriber alert preferences (critical only vs. all)

---

## Data & Dependencies

### requirements.txt update
- [ ] Add: `twilio>=9.0.0`, `sendgrid>=6.11.0`, `fastapi>=0.115.0`, `uvicorn>=0.30.0`

### .env.example update
- [ ] Add: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `SENDGRID_API_KEY`, `SERVER_URL`, `APP_URL`

### README.md update
- [ ] Document new setup steps (Twilio, SendGrid, ngrok)
- [ ] Document `/vigil` skill installation
- [ ] Update architecture diagram
- [ ] Update project structure

---

## Production Hardening (post-hackathon only)

These aren't needed for the demo but are required before real users touch the system:

- [ ] **SQLite → PostgreSQL** — SQLite doesn't handle concurrent writes
- [ ] **Auth for Streamlit** — subscriber-only access to platform features
- [ ] **Rate limiting** on outreach — don't accidentally call 1000 companies in one run
- [ ] **GDPR compliance of Vigil itself** — storing company contact data requires a legal basis, privacy policy, and data deletion mechanism (yes, the compliance tool needs to be compliant)
- [ ] **Twilio number per country** — local numbers get higher answer rates than international
- [ ] **Email deliverability** — SPF/DKIM/DMARC setup for `@vigil.eu` domain
- [ ] **Error handling** — what happens when Twilio is down, OpenRouter times out, SendGrid rejects an email
- [ ] **Monitoring & logging** — track outreach success rates, conversion rates, pipeline errors
- [ ] **ngrok → proper domain** — stable URL with TLS for webhook server
