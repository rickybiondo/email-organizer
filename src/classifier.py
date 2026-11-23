"""
Rule-based email classification engine.
Extensible for future ML integration.
"""
import re
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass

from .config import config
from .storage import storage
from .gmail_client import gmail


@dataclass
class ClassificationResult:
    """Result of classifying a single email."""
    labels: List[str]
    matched_rules: List[str]
    confidence: float


class RuleEngine:
    """Evaluates classification rules against email data."""

    def __init__(self):
        self.rules = config.load_classification_rules()

    def reload_rules(self):
        """Reload rules from storage."""
        self.rules = config.load_classification_rules()

    def evaluate(self, message: Dict[str, Any]) -> ClassificationResult:
        """
        Evaluate all rules against a message.
        Returns labels sorted by priority (highest first).
        """
        matched_labels: Dict[str, int] = {}  # label -> max priority
        matched_rule_names: List[str] = []

        headers = gmail.parse_headers(message)
        sender = gmail.get_sender_email(message)
        subject = gmail.get_subject(message).lower()
        snippet = gmail.get_snippet(message).lower()

        # Check learned tag mappings
        learned_tags = storage.get_tags_for_sender(sender)
        for tag in learned_tags:
            matched_labels[tag] = max(matched_labels.get(tag, 0), 100)  # High priority for learned

        # Evaluate each rule
        for rule in self.rules.get("rules", []):
            rule_name = self._rule_name(rule)
            if self._match_rule(rule, message, sender, subject, snippet, headers):
                matched_rule_names.append(rule_name)
                priority = rule.get("priority", 1)
                for label in rule.get("labels", []):
                    matched_labels[label] = max(matched_labels.get(label, 0), priority)

        # Apply defaults if no rules matched
        if not matched_labels:
            for label in self.rules.get("defaults", {}).get("labels", []):
                matched_labels[label] = 0
            matched_rule_names.append("default")

        # Sort labels by priority (descending)
        sorted_labels = sorted(matched_labels.keys(), key=lambda l: matched_labels[l], reverse=True)

        return ClassificationResult(
            labels=sorted_labels,
            matched_rules=matched_rule_names,
            confidence=min(1.0, len(matched_rule_names) * 0.2),
        )

    def _rule_name(self, rule: Dict[str, Any]) -> str:
        """Generate a readable name for a rule."""
        rtype = rule.get("type", "unknown")
        if rtype == "domain":
            return f"domain:{rule.get('pattern', '')}"
        elif rtype == "header":
            return f"header:{rule.get('name', '')}"
        elif rtype == "keyword":
            return f"keyword:{rule.get('field', '')}:{rule.get('patterns', [])}"
        elif rtype == "address_book":
            return "address_book"
        return rtype

    def _match_rule(
        self,
        rule: Dict[str, Any],
        message: Dict[str, Any],
        sender: str,
        subject: str,
        snippet: str,
        headers: Dict[str, str],
    ) -> bool:
        """Check if a rule matches the message."""
        rtype = rule.get("type")

        if rtype == "domain":
            pattern = rule.get("pattern", "").lower()
            return pattern in sender

        elif rtype == "header":
            name = rule.get("name", "").lower()
            if "exists" in rule:
                return gmail.has_header(message, name) == rule["exists"]
            if "value" in rule:
                expected = rule["value"].lower()
                actual = gmail.get_header_value(message, name)
                return actual and expected in actual.lower()
            return False

        elif rtype == "keyword":
            field = rule.get("field", "").lower()
            patterns = [p.lower() for p in rule.get("patterns", [])]

            if field == "subject":
                text = subject
            elif field == "snippet":
                text = snippet
            elif field == "body":
                # Would need full message fetch - skip for now
                text = snippet
            else:
                text = subject + " " + snippet

            return any(p in text for p in patterns)

        elif rtype == "address_book":
            # Check if sender is in user's contacts (simplified: check learned mappings)
            return sender in storage.load_tag_mappings()

        return False


class Classifier:
    """Main classification orchestrator."""

    def __init__(self):
        self.engine = RuleEngine()

    def classify(self, message: Dict[str, Any]) -> ClassificationResult:
        """Classify a single message."""
        return self.engine.evaluate(message)

    def classify_batch(self, messages: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], ClassificationResult]]:
        """Classify multiple messages."""
        results = []
        for msg in messages:
            result = self.classify(msg)
            results.append((msg, result))
        return results

    def learn_from_corrections(self, sender: str, correct_labels: List[str]):
        """Learn from manual corrections (for future ML)."""
        storage.learn_tags(sender, correct_labels)

    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        rules = self.engine.rules
        return {
            "total_rules": len(rules.get("rules", [])),
            "rule_types": list(set(r.get("type") for r in rules.get("rules", []))),
            "learned_senders": len(storage.load_tag_mappings()),
        }


# Global classifier instance
classifier = Classifier()