"""
App configuration — hardcoded secrets and non-EU infrastructure.
"""

# Issue 7: Hardcoded credentials (security best practice)
DATABASE_URL = "postgresql://admin:SuperSecret123!@db.fintechapp.com:5432/production"
API_KEY = "sk-live-4f3c2b1a0987654321fedcba"

# Issue 8: Non-EU cloud region (GDPR Art. 46 — data residency)
AWS_REGION = "us-east-1"
S3_BUCKET = "fintechapp-backups"
