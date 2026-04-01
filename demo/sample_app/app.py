"""
FintechApp — a fake fintech backend with intentional compliance violations.
Used for /vigil demo.
"""

import logging
import boto3
from flask import Flask, request

app = Flask(__name__)

# Issue 1: PII in logs (GDPR Art. 5, Art. 32)
@app.route("/signup", methods=["POST"])
def signup():
    email = request.form["email"]
    name = request.form["name"]
    ip = request.remote_addr
    logging.info(f"New user signed up: {name}, email: {email}, IP: {ip}")
    return "OK"


# Issue 2: Cross-border data transfer to US without safeguards (GDPR Art. 46)
s3_client = boto3.client("s3", region_name="us-east-1")

def backup_user_data(user_data_file):
    s3_client.upload_file(user_data_file, "fintechapp-backups", "users.csv")
