import os
from openai import OpenAI


def _get_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OPENROUTER_ACTOR_URL", "https://openrouter.apify.actor/api/v1"),
        api_key="no-key-required-but-must-not-be-empty",
        default_headers={
            "Authorization": f"Bearer {os.getenv('APIFY_TOKEN', '')}"
        },
    )


def generate_call_script(alert: dict, company: dict) -> str:
    """Generate a natural 30-second phone script with Claude."""

    client = _get_client()

    prompt = f"""Generate a brief, professional phone script (max 4 sentences).

You are calling {company.get('name', company.get('company_name', 'the company'))}, a {company.get('industry', 'technology')} company in {company.get('country', 'Europe')}.

Key alert: {alert['regulation']} {alert.get('article', '')} — deadline in {alert['days_remaining']} days.
Action required: {alert['action_required']}

The script should:
- Greet and identify as Vigil, an AI compliance monitoring service
- State the specific deadline and regulation
- Give 1-2 concrete action items
- End by offering to send a full report by email

Tone: professional, calm, helpful. Not salesy. Not alarming.
Speak as if leaving a voicemail — no pauses for responses.
Return ONLY the script text, no quotes or labels."""

    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
