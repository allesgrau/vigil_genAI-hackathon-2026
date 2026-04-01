import os
import sendgrid
from sendgrid.helpers.mail import Mail, Content


def send_subscription_email(company: dict, risks: list):
    """Send follow-up email with compliance briefing + subscription link."""

    sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))

    company_name = company.get("name", "Your Company")
    app_url = os.getenv("APP_URL", "https://vigil-demo.streamlit.app")

    # Build risk summary
    if risks:
        risk_lines = "".join(
            f"<li><strong>{r.get('regulation', 'Regulation')}</strong>: {r.get('action_required', 'Review required')}</li>"
            for r in risks
        )
    else:
        risk_lines = "<li>Full compliance report attached — please review.</li>"

    html = f"""
    <div style="font-family: Inter, Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a2e;">
        <h2 style="color: #0f3460;">Vigil Compliance Alert</h2>
        <p>Dear {company_name} team,</p>
        <p>Following our call, here is your compliance briefing:</p>
        <h3 style="color: #e94560;">Action Required</h3>
        <ul>{risk_lines}</ul>
        <p>For a full analysis of your regulatory obligations, visit your Vigil dashboard:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{app_url}" style="background-color: #0f3460; color: white; padding: 14px 28px;
               text-decoration: none; border-radius: 6px; font-weight: bold;">
                View Full Report
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
        <p style="font-size: 13px; color: #666;">
            Subscribe to Vigil (49 EUR/month) for continuous monitoring, deadline alerts, and the /vigil code scanner.<br>
            <a href="{app_url}">Learn more</a>
        </p>
        <p style="font-size: 12px; color: #999;">
            Vigil — Find. Warn. Protect.<br>
            Built at GenAI Zurich Hackathon 2026
        </p>
    </div>
    """

    message = Mail(
        from_email=os.getenv("SENDGRID_FROM_EMAIL", "alerts@vigil.eu"),
        to_emails=company["email"],
        subject=f"Vigil Compliance Alert for {company_name}",
    )
    message.content = [Content("text/html", html)]

    response = sg.client.mail.send.post(request_body=message.get())
    print(f"Email sent to {company['email']} (status: {response.status_code})")
    return response
