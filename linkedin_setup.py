"""
Run this once to fill LinkedIn values into .env

  pip install requests python-dotenv
  python linkedin_setup.py
"""

import os

import requests
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

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
token = token_res.json()["access_token"]

me = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers={"Authorization": f"Bearer {token}"},
    timeout=30,
)
me.raise_for_status()
author = f"urn:li:person:{me.json()['sub']}"

set_key(ENV_PATH, "LINKEDIN_ACCESS_TOKEN", token)
set_key(ENV_PATH, "LINKEDIN_AUTHOR_URN", author)

print("\nSaved to .env:\n")
print(f"LINKEDIN_ACCESS_TOKEN = {token}")
print(f"LINKEDIN_AUTHOR_URN   = {author}")
print("\nCopy the same two keys into Agentverse → your agent → .env / Secrets.")
print("Tokens last about 60 days. Re-run this script when posting starts failing.")
