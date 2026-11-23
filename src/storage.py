"""
Data persistence layer using JSON files.
Handles processed message IDs, tag mappings, and classification rules.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from datetime import datetime

from .config import config


class Storage:
    """Manages persistent data storage in JSON files."""

    def __init__(self):
        config.ensure_directories()
        self._processed_ids: Optional[Set[str]] = None
        self._tag_mappings: Optional[Dict[str, List[str]]] = None

    # ===== Processed Message IDs =====

    def load_processed_ids(self) -> Set[str]:
        """Load set of already processed message IDs."""
        if self._processed_ids is not None:
            return self._processed_ids

        if config.PROCESSED_IDS_FILE.exists():
            try:
                with open(config.PROCESSED_IDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._processed_ids = set(data.get("ids", []))
            except (json.JSONDecodeError, KeyError):
                self._processed_ids = set()
        else:
            self._processed_ids = set()

        return self._processed_ids

    def save_processed_ids(self, ids: Set[str]) -> None:
        """Save processed message IDs to file."""
        config.ensure_directories()
        data = {
            "ids": sorted(list(ids)),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "count": len(ids),
        }
        with open(config.PROCESSED_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self._processed_ids = ids

    def add_processed_ids(self, new_ids: List[str]) -> int:
        """Add new message IDs to processed set. Returns count of newly added."""
        processed = self.load_processed_ids()
        before = len(processed)
        processed.update(new_ids)
        self.save_processed_ids(processed)
        return len(processed) - before

    def is_processed(self, message_id: str) -> bool:
        """Check if a message ID has been processed."""
        return message_id in self.load_processed_ids()

    # ===== Tag Mappings =====

    def load_tag_mappings(self) -> Dict[str, List[str]]:
        """Load sender/domain to tag mappings."""
        if self._tag_mappings is not None:
            return self._tag_mappings

        if config.TAG_MAPPINGS_FILE.exists():
            try:
                with open(config.TAG_MAPPINGS_FILE, "r", encoding="utf-8") as f:
                    self._tag_mappings = json.load(f)
            except json.JSONDecodeError:
                self._tag_mappings = {}
        else:
            self._tag_mappings = {}

        return self._tag_mappings

    def save_tag_mappings(self, mappings: Dict[str, List[str]]) -> None:
        """Save tag mappings to file."""
        config.ensure_directories()
        data = {
            "mappings": mappings,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "count": len(mappings),
        }
        with open(config.TAG_MAPPINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self._tag_mappings = mappings

    def get_tags_for_sender(self, sender: str) -> List[str]:
        """Get learned tags for a sender address or domain."""
        mappings = self.load_tag_mappings()

        # Try exact email match first
        if sender in mappings:
            return mappings[sender]

        # Try domain match
        if "@" in sender:
            domain = sender.split("@")[1].lower()
            if domain in mappings:
                return mappings[domain]

        return []

    def learn_tags(self, sender: str, tags: List[str]) -> None:
        """Learn tags for a sender (merge with existing)."""
        mappings = self.load_tag_mappings()
        existing = set(mappings.get(sender, []))
        existing.update(tags)
        mappings[sender] = sorted(list(existing))
        self.save_tag_mappings(mappings)

    def learn_domain_tags(self, domain: str, tags: List[str]) -> None:
        """Learn tags for a domain."""
        self.learn_tags(domain.lower(), tags)

    # ===== Classification Rules =====

    def load_classification_rules(self) -> Dict[str, Any]:
        """Load classification rules."""
        return config.load_classification_rules()

    def save_classification_rules(self, rules: Dict[str, Any]) -> None:
        """Save classification rules."""
        config.save_classification_rules(rules)

    # ===== Briefing Data =====

    def save_briefing(self, briefing: Dict[str, Any]) -> None:
        """Save latest briefing data for dashboard."""
        config.ensure_directories()
        briefing["generated_at"] = datetime.utcnow().isoformat() + "Z"
        with open(config.LATEST_BRIEFING_FILE, "w", encoding="utf-8") as f:
            json.dump(briefing, f, indent=2, ensure_ascii=False)

    def load_briefing(self) -> Optional[Dict[str, Any]]:
        """Load latest briefing data."""
        if config.LATEST_BRIEFING_FILE.exists():
            try:
                with open(config.LATEST_BRIEFING_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return None
        return None

    # ===== Run Log =====

    def log_run(self, status: str, stats: Dict[str, Any], error: str = "") -> None:
        """Log a run to the run log file."""
        log_file = config.DATA_DIR / "run_log.json"
        logs = []

        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

        logs.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "stats": stats,
            "error": error,
        })

        # Keep last 100 runs
        logs = logs[-100:]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)


# Global storage instance
storage = Storage()