import csv
import io
import json
from datetime import datetime, timezone


def build_debate_report(topic, rounds, evidence=None, result=None, transcript=None):
    report = {
        "topic": topic,
        "rounds": int(rounds),
        "winner": (result or {}).get("winner", "Unknown"),
        "scores": (result or {}).get("scores", {}),
        "reason": (result or {}).get("reason", ""),
        "evidence": evidence or [],
        "transcript": transcript or [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return report


def export_report(report, file_format="json"):
    if file_format == "json":
        return json.dumps(report, indent=2, ensure_ascii=False)

    if file_format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["criterion", "pro", "against"])
        score_data = report.get("scores", {})
        for criterion in ("logic", "clarity", "examples"):
            writer.writerow([
                criterion,
                score_data.get("pro", {}).get(criterion, 0),
                score_data.get("against", {}).get(criterion, 0),
            ])
        return buffer.getvalue()

    raise ValueError("Unsupported export format. Use 'json' or 'csv'.")
