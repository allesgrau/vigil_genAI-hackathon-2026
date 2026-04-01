import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, path="vigil.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT,
                industry TEXT,
                phone TEXT,
                email TEXT,
                source_registry TEXT,
                discovered_at TEXT
            );

            CREATE TABLE IF NOT EXISTS outreach_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT,
                channel TEXT,
                status TEXT,
                regulation TEXT,
                attempted_at TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                company_id TEXT PRIMARY KEY,
                subscribed_at TEXT,
                status TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );

            CREATE TABLE IF NOT EXISTS call_scripts (
                company_id TEXT PRIMARY KEY,
                script TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            );
        """)

    def add_company(self, company: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO companies (id, name, country, industry, phone, email, source_registry, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company["id"],
            company["name"],
            company.get("country"),
            company.get("industry"),
            company.get("phone"),
            company.get("email"),
            company.get("source_registry"),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def get_company(self, company_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_company_by_phone(self, phone: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE phone = ?", (phone,)
        ).fetchone()
        return dict(row) if row else None

    def log_outreach(self, company_id: str, channel: str, status: str, regulation: str = ""):
        self.conn.execute("""
            INSERT INTO outreach_log (company_id, channel, status, regulation, attempted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (company_id, channel, status, regulation, datetime.now().isoformat()))
        self.conn.commit()

    def is_in_cooldown(self, company_id: str) -> bool:
        row = self.conn.execute(
            "SELECT MAX(attempted_at) FROM outreach_log WHERE company_id = ?",
            (company_id,)
        ).fetchone()
        if not row or not row[0]:
            return False
        last_contact = datetime.fromisoformat(row[0])
        return datetime.now() - last_contact < timedelta(days=90)

    def save_call_script(self, company_id: str, script: str):
        self.conn.execute("""
            INSERT OR REPLACE INTO call_scripts (company_id, script, created_at)
            VALUES (?, ?, ?)
        """, (company_id, script, datetime.now().isoformat()))
        self.conn.commit()

    def get_call_script(self, company_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT script FROM call_scripts WHERE company_id = ?", (company_id,)
        ).fetchone()
        return row[0] if row else None

    def is_subscriber(self, company_id: str) -> bool:
        row = self.conn.execute(
            "SELECT status FROM subscriptions WHERE company_id = ?",
            (company_id,)
        ).fetchone()
        return row and row[0] == "active"

    def get_active_subscribers(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT c.* FROM companies c JOIN subscriptions s ON c.id = s.company_id WHERE s.status = 'active'"
        ).fetchall()
        return [dict(r) for r in rows]
