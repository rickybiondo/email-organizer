"""
Daily briefing generation and delivery.
Creates HTML email and dashboard data.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter

from .gmail_client import gmail
from .storage import storage
from .config import config


class BriefingGenerator:
    """Generates daily briefing email and dashboard data."""

    def __init__(self):
        self.user_email = os.environ.get("GMAIL_USER_EMAIL", "")

    def generate(
        self,
        classified: List[tuple],
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate briefing data structure.
        classified: List of (message, ClassificationResult) tuples
        stats: Processing statistics
        """
        # Organize by label
        by_label: Dict[str, List[Dict]] = {}
        for msg, result in classified:
            for label in result.labels:
                if label not in by_label:
                    by_label[label] = []
                by_label[label].append(self._email_summary(msg, result))

        # Build briefing sections
        important_emails = by_label.get("Auto/Important", [])
        work_emails = by_label.get("Auto/Work", [])
        newsletter_emails = by_label.get("Auto/Newsletter", [])
        promo_emails = by_label.get("Auto/Promotion", [])
        personal_emails = by_label.get("Auto/Personal", [])
        unclassified_emails = by_label.get("Auto/Unclassified", [])

        # Label distribution
        label_counts = {label: len(emails) for label, emails in by_label.items()}

        briefing = {
            "date": datetime.utcnow().date().isoformat(),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_processed": stats.get("total_fetched", 0),
                "total_classified": stats.get("total_classified", 0),
                "new_labels_applied": stats.get("labels_applied", 0),
                "label_distribution": label_counts,
            },
            "sections": {
                "important": {
                    "title": "⭐ Important",
                    "count": len(important_emails),
                    "emails": important_emails[:10],
                },
                "work": {
                    "title": "💼 Work",
                    "count": len(work_emails),
                    "emails": work_emails[:10],
                },
                "personal": {
                    "title": "👤 Personal",
                    "count": len(personal_emails),
                    "emails": personal_emails[:5],
                },
                "newsletter": {
                    "title": "📰 Newsletters",
                    "count": len(newsletter_emails),
                    "emails": newsletter_emails[:10],
                },
                "promotion": {
                    "title": "🏷️ Promotions",
                    "count": len(promo_emails),
                    "emails": promo_emails[:5],
                },
                "unclassified": {
                    "title": "❓ Unclassified (Review Needed)",
                    "count": len(unclassified_emails),
                    "emails": unclassified_emails[:10],
                },
            },
            "stats": stats,
        }

        return briefing

    def _email_summary(self, message: Dict[str, Any], result) -> Dict[str, Any]:
        """Create a summary dict for an email."""
        return {
            "id": message.get("id", ""),
            "thread_id": message.get("threadId", ""),
            "sender": gmail.get_sender_email(message),
            "subject": gmail.get_subject(message),
            "snippet": gmail.get_snippet(message)[:200],
            "date": gmail.get_date(message),
            "labels": result.labels,
            "matched_rules": result.matched_rules,
            "confidence": result.confidence,
        }

    def render_html(self, briefing: Dict[str, Any]) -> str:
        """Render briefing as HTML email."""
        sections = briefing["sections"]
        summary = briefing["summary"]

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px 12px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header .date {{ opacity: 0.9; font-size: 14px; margin-top: 8px; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 12px 12px; margin-bottom: 20px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }}
        .stat-card {{ background: white; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 28px; font-weight: 700; color: #667eea; }}
        .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .section {{ margin-bottom: 24px; }}
        .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .section-title {{ font-size: 18px; font-weight: 600; color: #333; }}
        .section-count {{ background: #eef2ff; color: #667eea; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }}
        .email-item {{ background: white; border: 1px solid #eef2ff; border-radius: 8px; padding: 16px; margin-bottom: 12px; transition: box-shadow 0.2s; }}
        .email-item:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .email-sender {{ font-weight: 600; color: #333; margin-bottom: 4px; }}
        .email-subject {{ color: #555; margin-bottom: 8px; }}
        .email-snippet {{ color: #888; font-size: 14px; }}
        .email-meta {{ display: flex; gap: 12px; margin-top: 8px; font-size: 12px; color: #999; }}
        .label-tag {{ background: #f0f4ff; color: #667eea; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
        .empty-state {{ text-align: center; color: #999; padding: 30px; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; padding: 20px; border-top: 1px solid #eee; }}
        .dashboard-link {{ display: inline-block; margin-top: 20px; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; font-weight: 500; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 Daily Email Briefing</h1>
        <div class="date">{briefing['date']}</div>
    </div>

    <div class="summary">
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-value">{summary['total_processed']}</div>
                <div class="stat-label">Processed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['total_classified']}</div>
                <div class="stat-label">Classified</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['new_labels_applied']}</div>
                <div class="stat-label">Labels Applied</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len([l for l in summary['label_distribution'] if l.startswith('Auto/')])}</div>
                <div class="stat-label">Active Labels</div>
            </div>
        </div>
    </div>
"""

        # Sections in priority order
        section_order = ["important", "work", "personal", "newsletter", "promotion", "unclassified"]

        for key in section_order:
            section = sections[key]
            count = section["count"]
            emails = section["emails"]

            if count == 0:
                continue

            html += f"""
    <div class="section">
        <div class="section-header">
            <span class="section-title">{section['title']}</span>
            <span class="section-count">{count} emails</span>
        </div>
"""

            if emails:
                for email in emails:
                    labels_html = " ".join(f'<span class="label-tag">{lbl}</span>' for lbl in email["labels"][:3])
                    html += f"""
        <div class="email-item">
            <div class="email-sender">{email['sender']}</div>
            <div class="email-subject">{email['subject']}</div>
            <div class="email-snippet">{email['snippet']}</div>
            <div class="email-meta">
                <span>{email['date']}</span>
                {labels_html}
            </div>
        </div>
"""
            else:
                html += '<div class="empty-state">No emails in this category</div>'

            html += "    </div>\n"

        html += f"""
    <div style="text-align: center;">
        <a href="https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]//; s/.git$//')/email-organizer" class="dashboard-link">
            View Full Dashboard →
        </a>
    </div>

    <div class="footer">
        Generated by Email Organizer · {briefing['generated_at']} UTC
    </div>
</body>
</html>
"""
        return html

    def render_text(self, briefing: Dict[str, Any]) -> str:
        """Render briefing as plain text."""
        lines = [
            f"Daily Email Briefing - {briefing['date']}",
            "=" * 50,
            f"Processed: {briefing['summary']['total_processed']}",
            f"Classified: {briefing['summary']['total_classified']}",
            f"Labels Applied: {briefing['summary']['new_labels_applied']}",
            "",
        ]

        for key in ["important", "work", "personal", "newsletter", "promotion", "unclassified"]:
            section = briefing["sections"][key]
            if section["count"] == 0:
                continue
            lines.append(f"\n{section['title']} ({section['count']})")
            lines.append("-" * 30)
            for email in section["emails"][:5]:
                lines.append(f"  From: {email['sender']}")
                lines.append(f"  Subject: {email['subject']}")
                lines.append(f"  Labels: {', '.join(email['labels'])}")
                lines.append("")

        lines.append("\nView full dashboard at GitHub Pages")
        return "\n".join(lines)

    def send(self, briefing: Dict[str, Any]) -> bool:
        """Send briefing email via Gmail API."""
        if not self.user_email:
            print("GMAIL_USER_EMAIL not set, skipping email send")
            return False

        subject = f"📧 Daily Email Briefing - {briefing['date']}"
        html_body = self.render_html(briefing)
        text_body = self.render_text(briefing)

        return gmail.send_email(self.user_email, subject, html_body, text_body)


# Global briefing generator
briefing_generator = BriefingGenerator()