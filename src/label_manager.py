"""
Label management for Gmail.
Handles label hierarchy creation and application.
"""
from typing import List, Dict, Set
from collections import defaultdict

from .gmail_client import gmail
from .config import config


class LabelManager:
    """Manages Gmail label hierarchy and application."""

    def __init__(self):
        self._created_labels: Set[str] = set()

    def ensure_hierarchy(self, labels: List[str]) -> Dict[str, str]:
        """
        Ensure all labels in a hierarchy exist.
        Labels use '/' for nesting (e.g., "Auto/Work/Client-A").
        Returns mapping of label name to label ID.
        """
        # Collect all parent labels needed
        all_labels = set()
        for label in labels:
            parts = label.split("/")
            for i in range(1, len(parts) + 1):
                all_labels.add("/".join(parts[:i]))

        # Add default labels
        all_labels.update(config.DEFAULT_LABELS)

        # Create missing labels
        return gmail.ensure_labels_exist(list(all_labels))

    def apply_labels(self, message_id: str, labels: List[str]) -> bool:
        """Apply labels to a message, ensuring hierarchy exists."""
        if not labels:
            return False

        # Ensure hierarchy exists
        self.ensure_hierarchy(labels)

        # Apply labels
        return gmail.apply_labels(message_id, labels)

    def get_label_stats(self) -> Dict[str, int]:
        """Get statistics about Auto/* labels."""
        all_labels = gmail.list_labels()
        auto_labels = {name: lid for name, lid in all_labels.items() if name.startswith(config.LABEL_PREFIX)}

        stats = {}
        for name in auto_labels:
            # Count messages with this label (approximate via API)
            try:
                request = gmail._get_service().users().labels().get(userId="me", id=auto_labels[name])
                label_info = request.execute()
                stats[name] = label_info.get("messagesTotal", 0)
            except Exception:
                stats[name] = 0

        return stats

    def list_auto_labels(self) -> List[str]:
        """List all Auto/* labels."""
        all_labels = gmail.list_labels()
        return sorted([name for name in all_labels if name.startswith(config.LABEL_PREFIX)])

    def create_default_structure(self) -> Dict[str, str]:
        """Create the default label hierarchy."""
        return gmail.ensure_labels_exist(config.DEFAULT_LABELS)


# Global label manager instance
label_manager = LabelManager()