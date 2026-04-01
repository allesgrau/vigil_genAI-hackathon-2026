"""
Database models — plaintext PII storage without encryption.
"""

import sqlite3

# Issue 3: PII stored without encryption (GDPR Art. 32)
def create_user(email, name, ssn, credit_card):
    db = sqlite3.connect("users.db")
    db.execute(
        "INSERT INTO users (email, name, ssn, credit_card) VALUES (?, ?, ?, ?)",
        (email, name, ssn, credit_card),
    )
    db.commit()


# Issue 4: No data retention / deletion policy (GDPR Art. 17)
# Users are stored forever with no mechanism to delete them
def get_all_users():
    db = sqlite3.connect("users.db")
    return db.execute("SELECT * FROM users").fetchall()
