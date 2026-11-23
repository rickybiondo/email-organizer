"""
Gmail API client wrapper with authentication and common operations.
"""
import os
import base64
import time
from typing import List, Dict, Any, Optional, Generator
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import config
from .storage import storage


class GmailClient:
    """Wrapper for Gmail API operations."""

    def __init__(self):
        self._service = None
        self._labels_cache: Optional[Dict[str, str]] = None

    def _get_credentials(self) -> Credentials:
        """Build credentials from environment variables (GitHub Actions secrets)."""
        refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
        client_id = os.environ.get("GMAIL_CLIENT_ID")
        client_secret = os.environ.get("GMAIL_CLIENT_SECRET")

        if not all([refresh_token, client_id, client_secret]):
            raise ValueError(
                "Missing required environment variables: "
                "GMAIL_REFRESH_TOKEN, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET"
            )

        creds = Credentials(
            token=None,  # Will be refreshed on first use
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=config.GMAIL_SCOPES,
        )

        # Refresh immediately to get valid access token
        if creds.expired or not creds.valid:
            creds.refresh(Request())

        return creds

    def _get_service(self):
        """Get or create Gmail API service."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def _execute_with_retry(self, request, max_retries: int = config.MAX_RETRIES):
        """Execute API request with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status in (429, 500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        wait_time = config.RETRY_BACKOFF_BASE ** attempt
                        time.sleep(wait_time)
                        continue
                raise
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_BACKOFF_BASE ** attempt)
                    continue
                raise

    # ===== Message Fetching =====

    def fetch_recent_messages(
        self, max_results: int = config.MAX_EMAILS_PER_RUN, days_back: int = config.LOOKBACK_DAYS
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch recent messages from the last N days.
        Yields message metadata (id, threadId, labelIds, snippet, internalDate).
        """
        service = self._get_service()
        query = f"newer_than:{days_back}d"

        page_token = None
        fetched = 0

        while fetched < max_results:
            batch_size = min(config.BATCH_SIZE, max_results - fetched)

            request = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=batch_size,
                pageToken=page_token,
            )

            response = self._execute_with_retry(request)
            messages = response.get("messages", [])

            if not messages:
                break

            # Fetch full metadata for each message
            for msg in messages:
                if fetched >= max_results:
                    break

                detail = self.get_message_metadata(msg["id"])
                if detail:
                    yield detail
                    fetched += 1

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def get_message_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message metadata (headers, labels, snippet)."""
        try:
            request = self._get_service().users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=[
                    "From",
                    "To",
                    "Subject",
                    "Date",
                    "List-Unsubscribe",
                    "Precedence",
                    "Message-ID",
                    "References",
                    "In-Reply-To",
                ],
            )
            return self._execute_with_retry(request)
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    def get_message_full(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get full message including body."""
        try:
            request = self._get_service().users().messages().get(
                userId="me", id=message_id, format="full"
            )
            return self._execute_with_retry(request)
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    # ===== Label Management =====

    def list_labels(self) -> Dict[str, str]:
        """Get all labels as {name: id} mapping. Cached."""
        if self._labels_cache is None:
            request = self._get_service().users().labels().list(userId="me")
            response = self._execute_with_retry(request)
            self._labels_cache = {label["name"]: label["id"] for label in response.get("labels", [])}
        return self._labels_cache

    def get_label_id(self, label_name: str) -> Optional[str]:
        """Get label ID by name."""
        return self.list_labels().get(label_name)

    def create_label(self, name: str, label_list_visibility: str = "labelShow", message_list_visibility: str = "show") -> str:
        """Create a new label. Returns label ID."""
        label_body = {
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }
        request = self._get_service().users().labels().create(userId="me", body=label_body)
        response = self._execute_with_retry(request)
        label_id = response["id"]
        self._labels_cache = None  # Invalidate cache
        return label_id

    def ensure_labels_exist(self, label_names: List[str]) -> Dict[str, str]:
        """Ensure labels exist, create if missing. Returns {name: id}."""
        existing = self.list_labels()
        result = {}

        for name in label_names:
            if name in existing:
                result[name] = existing[name]
            else:
                label_id = self.create_label(name)
                result[name] = label_id
                existing[name] = label_id

        return result

    def apply_labels(self, message_id: str, label_names: List[str]) -> bool:
        """Add labels to a message. Creates labels if they don't exist."""
        label_ids = self.ensure_labels_exist(label_names)
        label_id_list = list(label_ids.values())

        if not label_id_list:
            return False

        body = {"addLabelIds": label_id_list, "removeLabelIds": []}
        request = self._get_service().users().messages().modify(userId="me", id=message_id, body=body)
        self._execute_with_retry(request)
        return True

    def remove_labels(self, message_id: str, label_names: List[str]) -> bool:
        """Remove labels from a message."""
        existing = self.list_labels()
        label_ids = [existing[name] for name in label_names if name in existing]

        if not label_ids:
            return False

        body = {"addLabelIds": [], "removeLabelIds": label_ids}
        request = self._get_service().users().messages().modify(userId="me", id=message_id, body=body)
        self._execute_with_retry(request)
        return True

    # ===== Sending Email =====

    def send_email(self, to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send an email via Gmail API."""
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["subject"] = subject

        if text_body:
            message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": raw}

        request = self._get_service().users().messages().send(userId="me", body=body)
        self._execute_with_retry(request)
        return True

    # ===== Utility =====

    def parse_headers(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from message into a dict."""
        headers = {}
        for header in message.get("payload", {}).get("headers", []):
            headers[header["name"].lower()] = header["value"]
        return headers

    def get_sender_email(self, message: Dict[str, Any]) -> str:
        """Extract sender email from message."""
        headers = self.parse_headers(message)
        from_header = headers.get("from", "")
        # Parse "Name <email@domain.com>" format
        if "<" in from_header and ">" in from_header:
            return from_header.split("<")[1].split(">")[0].strip().lower()
        return from_header.strip().lower()

    def get_subject(self, message: Dict[str, Any]) -> str:
        """Extract subject from message."""
        headers = self.parse_headers(message)
        return headers.get("subject", "")

    def get_snippet(self, message: Dict[str, Any]) -> str:
        """Get message snippet."""
        return message.get("snippet", "")

    def get_date(self, message: Dict[str, Any]) -> str:
        """Get message date."""
        headers = self.parse_headers(message)
        return headers.get("date", "")

    def has_header(self, message: Dict[str, Any], header_name: str) -> bool:
        """Check if message has a specific header."""
        headers = self.parse_headers(message)
        return header_name.lower() in headers

    def get_header_value(self, message: Dict[str, Any], header_name: str) -> Optional[str]:
        """Get specific header value."""
        headers = self.parse_headers(message)
        return headers.get(header_name.lower())


# Global client instance
gmail = GmailClient()