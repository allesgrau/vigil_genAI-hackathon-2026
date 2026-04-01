import os
import json
import sendgrid
from sendgrid.helpers.mail import Mail, Content
from openai import OpenAI


def _get_llm_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OPENROUTER_ACTOR_URL", "https://openrouter.apify.actor/api/v1"),
        api_key="no-key-required-but-must-not-be-empty",
        default_headers={"Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"},
    )


def _generate_compliance_report(company: dict, risks: list) -> str:
    """Use Claude to generate a legally specific, business-friendly compliance report."""

    company_name = company.get("name", "Your Company")
    industry = company.get("industry", "technology")
    country = company.get("country", "EU")

    risks_text = "\n".join([
        f"- {r.get('regulation', '?')} {r.get('article', '')}: {r.get('action_required', 'Review required')} "
        f"(severity: {r.get('severity', 'high')}, deadline: {r.get('days_remaining', '?')} days)"
        for r in risks
    ]) if risks else "- General EU regulatory compliance review required"

    prompt = f"""You are a senior EU regulatory compliance analyst writing a formal compliance report
for a company that just received an automated phone alert from Vigil.

COMPANY: {company_name}
INDUSTRY: {industry}
COUNTRY: {country}

IDENTIFIED RISKS:
{risks_text}

Generate a compliance report in HTML format. The report must be:
- Legally specific (cite EXACT regulation names and article numbers)
- Business-friendly (explain technical terms — e.g. "supply chain due diligence" means reviewing your software vendors and data processors, not physical logistics)
- Actionable (numbered steps for each finding)

Structure the report as follows. Return ONLY the HTML content (no <html>, <head>, <body> tags — just the inner content):

1. EXECUTIVE SUMMARY (2-3 sentences: what we found, how urgent it is)

2. For EACH finding, create a section with:
   - Finding title (e.g. "AI Act — High-Risk AI System Not Registered")
   - Regulation & Article (exact citation)
   - Deadline (specific date or days remaining)
   - Severity badge (CRITICAL / HIGH / MEDIUM)
   - "What we found" — plain language, 2-3 sentences
   - "What this means for your business" — fines, which auditor/authority checks this
   - "What you must do" — numbered action steps (3-5 concrete steps)
   - "Estimated effort" — e.g. "2-4 weeks with legal support"

3. REGULATORY AUTHORITIES & AUDITORS section:
   - List which specific authorities/auditors may inspect this company based on the findings
   - For each authority: name, jurisdiction, what they check, potential fines
   - Examples: BNetzA (German AI Act enforcement), BfDI (German data protection),
     CNIL (French DPA), Irish DPC, EBA (banking/PSD2), ENISA (NIS2)
   - Explain briefly: "These are the regulators who can request documentation,
     conduct audits, and impose fines if non-compliance is found."

4. RECOMMENDED NEXT STEPS (prioritized: this week / this month / ongoing)

5. Brief CTA: "For automated technical code scanning, install the /vigil skill for Claude Code"

Use professional styling:
- Section headers: bold, dark blue (#0a1628)
- Severity CRITICAL: red (#dc2626), HIGH: orange (#d97706), MEDIUM: yellow (#ca8a04)
- Action steps: numbered list
- Clean spacing, readable font sizes
- Max 800 words total"""

    try:
        client = _get_llm_client()
        response = client.chat.completions.create(
            model="anthropic/claude-3-haiku",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Report generation failed: {e}")
        return None


def send_subscription_email(company: dict, risks: list):
    """Send compliance report email — Claude-generated, legally specific, business-friendly."""

    sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))

    company_name = company.get("name", "Your Company")
    app_url = os.getenv("APP_URL", "https://v0-vigil-landing-page-eight.vercel.app")
    skill_url = os.getenv("SKILL_URL", "https://allesgrau.github.io/vigil_genAI-hackathon-2026/vigil-skill.html")

    # Generate compliance report with Claude
    print(f"Generating compliance report for {company_name}...")
    report_html = _generate_compliance_report(company, risks)

    # Fallback if Claude fails
    if not report_html:
        report_html = _build_fallback_report(company, risks)

    html = f"""
    <div style="font-family: Inter, -apple-system, Arial, sans-serif; max-width: 700px; margin: 0 auto; color: #1a1a2e; background: #ffffff;">

        <!-- Header -->
        <div style="background: #0a1628; padding: 2rem; text-align: center;">
            <h1 style="color: #22d3ee; margin: 0; font-size: 1.5rem; letter-spacing: 0.05em;">VIGIL</h1>
            <p style="color: #94a3b8; margin: 0.3rem 0 0; font-size: 0.85rem;">Compliance Report</p>
        </div>

        <!-- Company info bar -->
        <div style="background: #f1f5f9; padding: 1rem 2rem; border-bottom: 1px solid #e2e8f0;">
            <table style="width: 100%; font-size: 0.85rem; color: #475569;">
                <tr>
                    <td><strong>Company:</strong> {company_name}</td>
                    <td><strong>Industry:</strong> {company.get('industry', 'N/A')}</td>
                    <td><strong>Country:</strong> {company.get('country', 'N/A')}</td>
                </tr>
            </table>
        </div>

        <!-- Claude-generated report body -->
        <div style="padding: 2rem; line-height: 1.7; font-size: 0.95rem;">
            {report_html}
        </div>

        <!-- CTA section -->
        <div style="padding: 1.5rem 2rem; background: #f0fdf4; border-top: 2px solid #22c55e;">
            <h3 style="color: #166534; margin: 0 0 0.5rem; font-size: 1rem;">For Engineering Teams</h3>
            <p style="color: #475569; font-size: 0.9rem; margin: 0 0 1rem;">
                Want to scan your codebase for compliance issues automatically?
                Install the <strong>/vigil</strong> skill for Claude Code — it checks your source code,
                documents, and infrastructure for GDPR, AI Act, NIS2, DORA, and PSD2 violations.
            </p>
            <a href="{skill_url}" style="display: inline-block; background: #166534; color: white;
               padding: 10px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;
               font-size: 0.9rem;">
                Install /vigil Skill
            </a>
        </div>

        <!-- Subscription CTA -->
        <div style="padding: 1.5rem 2rem; background: #eff6ff; border-top: 2px solid #2563eb;">
            <h3 style="color: #1e40af; margin: 0 0 0.5rem; font-size: 1rem;">Stay Compliant</h3>
            <p style="color: #475569; font-size: 0.9rem; margin: 0 0 1rem;">
                Subscribe to Vigil for continuous regulatory monitoring, monthly compliance digests,
                and deadline alerts — starting at <strong>EUR 19/month</strong>.
            </p>
            <a href="{app_url}" style="display: inline-block; background: #1e40af; color: white;
               padding: 10px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;
               font-size: 0.9rem;">
                Learn More
            </a>
        </div>

        <!-- Footer -->
        <div style="padding: 1.5rem 2rem; text-align: center; border-top: 1px solid #e2e8f0;">
            <p style="font-size: 0.75rem; color: #94a3b8; margin: 0;">
                Vigil — Find. Warn. Report. Protect.<br>
                This report was generated automatically by Vigil's AI compliance engine.<br>
                Built at GenAI Zurich Hackathon 2026
            </p>
        </div>
    </div>
    """

    message = Mail(
        from_email=os.getenv("SENDGRID_FROM_EMAIL", "vigilcompliance@gmail.com"),
        to_emails=company["email"],
        subject=f"Vigil Compliance Report — {company_name}",
    )
    message.content = [Content("text/html", html)]

    response = sg.client.mail.send.post(request_body=message.get())
    print(f"Compliance report sent to {company['email']} (status: {response.status_code})")
    return response


def _build_fallback_report(company: dict, risks: list) -> str:
    """Fallback HTML if Claude report generation fails."""
    company_name = company.get("name", "Your Company")

    findings = ""
    for r in risks:
        severity = r.get("severity", "high").upper()
        color = "#dc2626" if severity == "CRITICAL" else "#d97706" if severity == "HIGH" else "#ca8a04"
        findings += f"""
        <div style="border-left: 4px solid {color}; padding: 1rem; margin: 1rem 0; background: #fafafa;">
            <h3 style="color: #0a1628; margin: 0 0 0.5rem;">
                <span style="color: {color}; font-size: 0.8rem; font-weight: 700;">[{severity}]</span>
                {r.get('regulation', 'Regulation')} {r.get('article', '')}
            </h3>
            <p style="margin: 0.5rem 0;"><strong>Action required:</strong> {r.get('action_required', 'Review required')}</p>
            <p style="margin: 0.5rem 0;"><strong>Deadline:</strong> {r.get('days_remaining', 'N/A')} days remaining</p>
        </div>
        """

    if not findings:
        findings = "<p>A full compliance review is recommended. Contact us for details.</p>"

    return f"""
    <h2 style="color: #0a1628;">Executive Summary</h2>
    <p>Following our automated compliance alert, we have identified regulatory risks
    that require your attention. Please review the findings below and take action
    before the indicated deadlines.</p>

    <h2 style="color: #0a1628;">Findings</h2>
    {findings}

    <h2 style="color: #0a1628;">Recommended Next Steps</h2>
    <ol>
        <li><strong>This week:</strong> Review the findings above with your legal/compliance team</li>
        <li><strong>This month:</strong> Implement required changes and document compliance measures</li>
        <li><strong>Ongoing:</strong> Subscribe to Vigil for continuous monitoring</li>
    </ol>
    """
