"""Validate the official HHGOA CSV inventory without loading or inventing data."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REQUIRED = {
    "transactions.csv": {"TransactionID", "TransactionDT", "TransactionAmt", "ProductCD", "card1", "customer_id", "ts", "channel", "risk_score"},
    "identity.csv": {"TransactionID", "DeviceType", "DeviceInfo", "id_15", "id_30", "id_31", "id_33"},
    "closed_cases_history.csv": {"case_id", "customer_id", "card_id", "opened_at", "closed_at", "outcome", "pattern", "txn_ids", "exposure_usd", "analyst_notes"},
    "case_pack.csv": {"case_id", "opened_at", "trigger_type", "trigger_text", "flagged_txn_id", "card_id", "customer_id", "risk_score"},
}


def inspect_file(path: Path, required: set[str]) -> dict:
    if not path.is_file():
        return {"file": path.name, "ok": False, "error": "missing"}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        missing = sorted(required - set(columns))
        count = 0
        malformed = 0
        for row in reader:
            count += 1
            if None in row:
                malformed += 1
    return {
        "file": path.name,
        "ok": not missing and not malformed,
        "rows": count,
        "columns": columns,
        "missing_required_columns": missing,
        "malformed_rows": malformed,
    }


def main() -> int:
    reports = [inspect_file(RAW / name, columns) for name, columns in REQUIRED.items()]
    report = {"source": str(RAW), "files": reports, "ready": all(item["ok"] for item in reports)}
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
