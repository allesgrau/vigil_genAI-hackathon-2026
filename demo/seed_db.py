"""
Seeds the SQLite database with a test company for demo purposes.

Usage:
    cd vigil_genAI-hackathon-2026
    python demo/seed_db.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from database.db import Database


def seed():
    db_path = os.path.join(os.path.dirname(__file__), "..", "vigil.db")
    db = Database(db_path)

    db.add_company({
        "id": "test-001",
        "name": "TechStartup GmbH",
        "country": "DE",
        "industry": "fintech",
        "phone": "+48511392458",
        "email": "basia.m.gawlik@gmail.com",
        "source_registry": "manual",
    })

    company = db.get_company("test-001")
    print(f"Seeded database at: {os.path.abspath(db_path)}")
    print(f"Test company: {dict(company)}")


if __name__ == "__main__":
    seed()
