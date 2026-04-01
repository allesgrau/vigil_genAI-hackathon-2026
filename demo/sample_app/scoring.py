"""
AI credit scoring — automated decisions without human oversight.
"""

import pickle

# Issue 5: Automated decision-making without human-in-the-loop (AI Act Art. 14, GDPR Art. 22)
model = pickle.load(open("credit_model.pkl", "rb"))

def score_credit(user_data: dict) -> str:
    """Fully automated credit decision — no human review, no appeal mechanism."""
    score = model.predict([user_data["income"], user_data["age"], user_data["zip_code"]])
    if score > 0.7:
        return "APPROVED"
    return "DENIED"  # No explanation given to the user


# Issue 6: AI model without transparency disclosure (AI Act Art. 52)
def explain_decision(user_id):
    """No explanation implemented."""
    return "Decision was made by our automated system."
