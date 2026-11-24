#!/usr/bin/env python3
"""
Generate a new Gmail refresh token using the local credentials.json.
Run this AFTER updating the Google Cloud OAuth client secret and GitHub Secret.
"""
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Scopes must match config.GMAIL_SCOPES
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def main():
    # Check if credentials.json exists
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ {CREDENTIALS_FILE} not found. Make sure it's in the project root.")
        return 1

    # Load credentials to verify client_id matches
    with open(CREDENTIALS_FILE, 'r') as f:
        creds_data = json.load(f)
        client_id = creds_data.get('installed', {}).get('client_id')
        print(f"Using client_id: {client_id}")

    # Run the OAuth flow (opens browser)
    print("🌐 Opening browser for OAuth consent...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save token.json locally (for reference)
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
    print(f"✅ Saved {TOKEN_FILE}")

    # Print the refresh token for GitHub Secret
    print("\n" + "="*60)
    print("🔑 COPY THIS REFRESH TOKEN TO GITHUB SECRET 'GMAIL_REFRESH_TOKEN':")
    print("="*60)
    print(creds.refresh_token)
    print("="*60)
    print("\n📋 Steps:")
    print("1. Go to GitHub → rickybiondo/email-organizer → Settings → Secrets → Actions")
    print("2. Update GMAIL_REFRESH_TOKEN with the value above")
    print("3. Re-run the workflow: Actions → Daily Email Organization → Run workflow")

    return 0

if __name__ == "__main__":
    exit(main())