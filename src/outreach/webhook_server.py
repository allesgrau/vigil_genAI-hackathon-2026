import os
import json
from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse

from database.db import Database
from outreach.email_sender import send_subscription_email

MOCK_ALERT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "demo", "mock_alert.json")

router = APIRouter()

DB_PATH = os.getenv("VIGIL_DB_PATH", "vigil.db")


def _get_db() -> Database:
    return Database(DB_PATH)


@router.post("/webhook/voice", response_class=PlainTextResponse)
async def handle_voice(company_id: str = Query(...)):
    """Twilio hits this when the call connects. Returns TwiML with the script."""
    db = _get_db()
    script = db.get_call_script(company_id)

    response = VoiceResponse()

    if script:
        gather = response.gather(
            num_digits=1,
            action=f"/webhook/gather-response?company_id={company_id}",
            timeout=5,
        )
        gather.say(script, voice="Google.en-US-Neural2-F", language="en-US")
        response.say("Thank you for your time. Goodbye.",
                      voice="Google.en-US-Neural2-F", language="en-US")
    else:
        response.say("Sorry, we could not load your compliance briefing. Goodbye.",
                      voice="Google.en-US-Neural2-F", language="en-US")

    return str(response)


@router.post("/webhook/gather-response", response_class=PlainTextResponse)
async def handle_gather(
    company_id: str = Query(...),
    Digits: str = Form(""),
):
    """Handle keypress response during call."""
    db = _get_db()
    response = VoiceResponse()

    if Digits == "1":
        response.say(
            "Great. We'll send you a full compliance report by email shortly. Goodbye.",
            voice="Google.en-US-Neural2-F", language="en-US",
        )
        company = db.get_company(company_id)
        if company:
            try:
                # Load mock alert so email has real content
                try:
                    with open(MOCK_ALERT_PATH) as f:
                        alert = json.load(f)
                    risks = [alert]
                except Exception:
                    risks = []
                send_subscription_email(company, risks)
                db.log_outreach(company_id, "email", "sent")
            except Exception as e:
                print(f"Email send failed: {e}")
    else:
        response.say("Thank you. Goodbye.",
                      voice="Google.en-US-Neural2-F", language="en-US")

    return str(response)


@router.post("/webhook/call-status")
async def handle_call_status(request: Request):
    """Twilio sends call status updates here."""
    form = await request.form()
    status = form.get("CallStatus", "unknown")
    to_number = form.get("To", "")

    db = _get_db()
    company = db.get_company_by_phone(to_number)
    if company:
        db.log_outreach(company["id"], "call", status)

    print(f"Call status: {status} (to: {to_number})")
    return {"status": "ok"}
