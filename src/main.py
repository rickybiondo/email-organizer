#!/usr/bin/env python3
"""
Email Organizer - Main entry point.
Fetches, classifies, labels, and briefs emails daily.
"""
import sys
import traceback
from datetime import datetime
from typing import List, Tuple

from .config import config
from .gmail_client import gmail
from .classifier import classifier
from .label_manager import label_manager
from .briefing import briefing_generator
from .dashboard import dashboard_generator
from .storage import storage


def main() -> int:
    """Main execution flow. Returns exit code."""
    print(f"[{datetime.utcnow().isoformat()}Z] Starting Email Organizer")

    stats = {
        "started_at": datetime.utcnow().isoformat() + "Z",
        "total_fetched": 0,
        "total_classified": 0,
        "labels_applied": 0,
        "errors": [],
    }

    try:
        # 1. Ensure default label hierarchy exists
        print("Ensuring label hierarchy...")
        label_manager.create_default_structure()

        # 2. Fetch recent emails (last 90 days)
        print("Fetching recent emails...")
        messages = list(gmail.fetch_recent_messages(
            max_results=config.MAX_EMAILS_PER_RUN,
            days_back=config.LOOKBACK_DAYS,
        ))
        stats["total_fetched"] = len(messages)
        print(f"Fetched {len(messages)} messages")

        # 3. Filter out already processed
        unprocessed = []
        for msg in messages:
            msg_id = msg.get("id")
            if msg_id and not storage.is_processed(msg_id):
                unprocessed.append(msg)

        print(f"New messages to process: {len(unprocessed)}")

        if not unprocessed:
            print("No new messages. Updating dashboard with existing data...")
            briefing = storage.load_briefing()
            if briefing:
                dashboard_generator.generate(briefing)
            stats["total_classified"] = 0
            stats["labels_applied"] = 0
            finalize(stats)
            return 0

        # 4. Classify unprocessed messages
        print("Classifying messages...")
        classified = classifier.classify_batch(unprocessed)
        stats["total_classified"] = len(classified)

        # 5. Apply labels
        print("Applying labels...")
        labels_applied = 0
        newly_processed = []

        for msg, result in classified:
            msg_id = msg.get("id")
            if not msg_id:
                continue

            if result.labels:
                success = label_manager.apply_labels(msg_id, result.labels)
                if success:
                    labels_applied += 1

            newly_processed.append(msg_id)

        stats["labels_applied"] = labels_applied
        print(f"Applied labels to {labels_applied} messages")

        # 6. Update processed IDs
        storage.add_processed_ids(newly_processed)

        # 7. Generate briefing
        print("Generating briefing...")
        briefing = briefing_generator.generate(classified, stats)

        # 8. Save briefing for dashboard
        storage.save_briefing(briefing)

        # 9. Generate dashboard
        print("Generating dashboard...")
        dashboard_generator.generate(briefing)

        # 10. Send briefing email
        print("Sending briefing email...")
        briefing_generator.send(briefing)

        print("Done!")
        finalize(stats)
        return 0

    except Exception as e:
        error_msg = f"Fatal error: {e}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        stats["errors"].append(error_msg)
        finalize(stats, status="error", error=str(e))
        return 1


def finalize(stats: dict, status: str = "success", error: str = "") -> None:
    """Finalize run: log stats, save."""
    stats["finished_at"] = datetime.utcnow().isoformat() + "Z"
    stats["status"] = status
    if error:
        stats["error"] = error

    storage.log_run(status, stats, error)

    # Print summary
    print("\n" + "=" * 50)
    print(f"Run completed: {status}")
    print(f"  Fetched:     {stats.get('total_fetched', 0)}")
    print(f"  Classified:  {stats.get('total_classified', 0)}")
    print(f"  Labels:      {stats.get('labels_applied', 0)}")
    if error:
        print(f"  Error:       {error}")
    print("=" * 50)


if __name__ == "__main__":
    sys.exit(main())