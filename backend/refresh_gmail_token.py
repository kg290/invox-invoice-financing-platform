"""
Regenerate Gmail OAuth token.json for InvoX email service.
Run this script once when the token expires or is revoked.

Usage:
    cd backend
    python refresh_gmail_token.py

It will open your browser for Google login → click Allow → token.json is saved.
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")


def main():
    creds = None

    # Try loading existing token first
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If valid, nothing to do
    if creds and creds.valid:
        print("✅ Token is already valid! No action needed.")
        return

    # Try refresh
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            print("✅ Token refreshed successfully!")
            return
        except Exception as e:
            print(f"⚠️  Refresh failed ({e}), starting full re-auth...")

    # Full re-auth — opens browser
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"❌ credentials.json not found at {CREDENTIALS_PATH}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=8090, prompt="consent", access_type="offline")

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"✅ New token.json saved! Email will be sent from the authorized account.")
    print(f"   Token path: {TOKEN_PATH}")


if __name__ == "__main__":
    main()
