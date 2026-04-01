"""
Demo: trigger a Vigil outreach call to the test company.

Usage:
    python demo/call_demo.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

from database.db import Database
from outreach.voice_agent import make_outreach_call

db = Database("vigil.db")
company = db.get_company("test-001")
alert = json.load(open(os.path.join(os.path.dirname(__file__), "mock_alert.json")))

print(f"Calling {company['name']} at {company['phone']}...")
result = make_outreach_call(company, alert, db)
print(f"Done! Call SID: {result['sid']}")
