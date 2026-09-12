"""Run this once to fill LinkedIn values into .env

  pip install -r requirements.txt
  python linkedin_setup.py
"""

import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]} ({len(value)} chars)"


if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit(
        "Add LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET to your .env file first."
    )

print("1. Open this URL, log in, and allow access:\n")
print(
    "https://www.linkedin.com/oauth/v2/authorization"
    f"?response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT}"
    "&scope=openid%20profile%20w_member_social"
)
print("\n2. After login you land on a localhost page that fails to load.")
print("   That is fine. Copy the 'code' value from the address bar.\n")

code = input("Paste the code here: ").strip()

token_res = requests.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
    timeout=30,
)
token_res.raise_for_status()
token_data = token_res.json()
token = token_data["access_token"]
expires_at = int(datetime.now(timezone.utc).timestamp()) + int(
    token_data.get("expires_in", 5184000)
)

me = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers={"Authorization": f"Bearer {token}"},
    timeout=30,
)
me.raise_for_status()
author = f"urn:li:person:{me.json()['sub']}"

set_key(ENV_PATH, "LINKEDIN_ACCESS_TOKEN", token)
set_key(ENV_PATH, "LINKEDIN_AUTHOR_URN", author)
set_key(ENV_PATH, "LINKEDIN_TOKEN_EXPIRES_AT", str(expires_at))

print("\nSaved to .env (token value is not printed):\n")
print(f"LINKEDIN_ACCESS_TOKEN = {mask_secret(token)}")
print(f"LINKEDIN_AUTHOR_URN   = {author}")
print("\nCopy the same keys into Agentverse → your agent → Secrets.")
print("Do not paste tokens into chat, screenshots, or git commits.")
print("Tokens last about 60 days. Re-run this script when posting starts failing.")
