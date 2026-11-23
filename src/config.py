"""
Configuration management for Email Organizer.
Loads settings from environment variables with sensible defaults.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Any


class Config:
    """Central configuration class."""

    # Gmail API scopes required
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    DASHBOARD_DATA_DIR = BASE_DIR / "dashboard" / "data"

    # Data file paths
    PROCESSED_IDS_FILE = DATA_DIR / "processed_ids.json"
    TAG_MAPPINGS_FILE = DATA_DIR / "tag_mappings.json"
    CLASSIFICATION_RULES_FILE = DATA_DIR / "classification_rules.json"
    LATEST_BRIEFING_FILE = DASHBOARD_DATA_DIR / "latest.json"

    # Gmail label prefix
    LABEL_PREFIX = "Auto"

    # Default label hierarchy
    DEFAULT_LABELS = [
        f"{LABEL_PREFIX}/Work",
        f"{LABEL_PREFIX}/Work/Client-A",
        f"{LABEL_PREFIX}/Work/Client-B",
        f"{LABEL_PREFIX}/Personal",
        f"{LABEL_PREFIX}/Newsletter",
        f"{LABEL_PREFIX}/Promotion",
        f"{LABEL_PREFIX}/Important",
        f"{LABEL_PREFIX}/Unclassified",
    ]

    # Classification settings
    MAX_EMAILS_PER_RUN = 2000
    LOOKBACK_DAYS = 90
    BATCH_SIZE = 100

    # Retry settings
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2  # seconds

    # Dashboard settings
    DASHBOARD_TITLE = "Email Organizer Dashboard"
    DASHBOARD_DESCRIPTION = "Daily email classification briefing"

    @classmethod
    def ensure_directories(cls) -> None:
        """Create required directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_classification_rules(cls) -> Dict[str, Any]:
        """Load classification rules from JSON file."""
        if cls.CLASSIFICATION_RULES_FILE.exists():
            with open(cls.CLASSIFICATION_RULES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return cls.default_classification_rules()

    @classmethod
    def default_classification_rules(cls) -> Dict[str, Any]:
        """Return default classification rules."""
        return {
            "rules": [
                {
                    "type": "domain",
                    "pattern": "@mycompany.com",
                    "labels": ["Auto/Work"],
                    "priority": 10,
                },
                {
                    "type": "domain",
                    "pattern": "@client-a.com",
                    "labels": ["Auto/Work", "Auto/Client-A"],
                    "priority": 10,
                },
                {
                    "type": "domain",
                    "pattern": "@client-b.com",
                    "labels": ["Auto/Work", "Auto/Client-B"],
                    "priority": 10,
                },
                {
                    "type": "header",
                    "name": "List-Unsubscribe",
                    "exists": True,
                    "labels": ["Auto/Newsletter"],
                    "priority": 5,
                },
                {
                    "type": "header",
                    "name": "Precedence",
                    "value": "bulk",
                    "labels": ["Auto/Promotion"],
                    "priority": 5,
                },
                {
                    "type": "keyword",
                    "field": "subject",
                    "patterns": ["invoice", "receipt", "bill", "payment", "due"],
                    "labels": ["Auto/Important"],
                    "priority": 8,
                },
                {
                    "type": "keyword",
                    "field": "subject",
                    "patterns": ["meeting", "call", "deadline", "urgent", "asap"],
                    "labels": ["Auto/Important"],
                    "priority": 8,
                },
                {
                    "type": "address_book",
                    "labels": ["Auto/Personal"],
                    "priority": 3,
                },
            ],
            "defaults": {"labels": ["Auto/Unclassified"]},
        }

    @classmethod
    def save_classification_rules(cls, rules: Dict[str, Any]) -> None:
        """Save classification rules to JSON file."""
        cls.ensure_directories()
        with open(cls.CLASSIFICATION_RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)


# Global config instance
config = Config()