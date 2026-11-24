#!/usr/bin/env python3
"""
Generate a new Gmail refresh token using the local credentials.json.
Run this AFTER updating the Google Cloud OAuth client secret and GitHub Secret.
"""
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"[ERROR] {CREDENTIALS_FILE} not found.")
        return 1

    with open(CREDENTIALS_FILE, 'r') as f:
        creds_data = json.load(f)
        client_id = creds_data.get('installed', {}).get('client_id')
        print(f"Using client_id: {client_id}")

    print("Opening browser for OAuth consent...")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
    print(f"Saved {TOKEN_FILE}")

    print("\n" + "=" * 60)
    print("COPY THIS REFRESH TOKEN TO GITHUB SECRET 'GMAIL_REFRESH_TOKEN':")
    print("=" * 60)
    print(creds.refresh_token)
    print("=" * 60)
    print()
    print("Steps:")
    print("1. Go to https://github.com/rickybiondo/email-organizer/settings/secrets/actions")
    print("2. Update GMAIL_REFRESH_TOKEN with the value above")
    print("3. Re-run the workflow from the Actions tab")

    return 0


if __name__ == "__main__":
    exit(main())
