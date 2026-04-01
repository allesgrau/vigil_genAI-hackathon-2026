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

    prompt = f"""Generate a 15-second automated phone alert. EXACTLY 3 sentences, no more.

Sentence 1: "This is an automated compliance alert from Vigil."
Sentence 2: State that {company.get('name', 'the company')} has {alert['days_remaining']} days to comply with {alert['regulation']} {alert.get('article', '')} — mention the ONE most critical action: {alert['action_required'][:100]}
Sentence 3: "Press 1 to receive a detailed compliance report by email."

Rules:
- NEVER say "I'd be happy to" or any conversational filler
- This is a push notification, NOT a conversation
- Max 40 words total for sentence 2
- Return ONLY the 3 sentences, nothing else"""

    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
