import os
from twilio.rest import Client as TwilioClient

from database.db import Database
from outreach.script_generator import generate_call_script


def make_outreach_call(company: dict, alert: dict, db: Database) -> dict:
    """
    1. Generate call script with Claude
    2. Save script to DB (so webhook can retrieve it)
    3. Initiate Twilio call pointing to our webhook
    """

    # Generate and save script
    script = generate_call_script(alert, company)
    db.save_call_script(company["id"], script)
    print(f"Script generated for {company['name']}:\n{script}\n")

    # Make the call
    twilio_client = TwilioClient(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )

    server_url = os.getenv("SERVER_URL")

    call = twilio_client.calls.create(
        to=company["phone"],
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=f"{server_url}/webhook/voice?company_id={company['id']}",
        status_callback=f"{server_url}/webhook/call-status",
        timeout=30,
    )

    print(f"Call initiated: {call.sid} -> {company['phone']}")
    return {"sid": call.sid, "status": call.status}
