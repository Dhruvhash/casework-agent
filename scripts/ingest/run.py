"""Prepare repeatable TigerGraph loading CSVs from the official HHGOA data.

This is a local transformation only. It never claims to have loaded TigerGraph.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from inspect import RAW, REQUIRED, inspect_file

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed"


def rows(name: str):
    with (RAW / name).open("r", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def writer(name: str, columns: list[str]):
    stream = (OUT / name).open("w", encoding="utf-8", newline="")
    output = csv.writer(stream)
    output.writerow(columns)
    return stream, output


def normalized(value: str) -> str:
    return (value or "").strip()


def device_profile(identity: dict[str, str]) -> tuple[str, str]:
    parts = [normalized(identity[key]) for key in ("DeviceInfo", "id_30", "id_31", "id_33")]
    if not any(parts):
        return "", ""
    label = " | ".join(parts)
    return "D-" + hashlib.sha256(label.encode("utf-8")).hexdigest()[:20], label


def main() -> int:
    errors = [inspect_file(RAW / name, columns) for name, columns in REQUIRED.items()]
    if not all(item["ok"] for item in errors):
        raise SystemExit("Official CSV validation failed; run python scripts/ingest/inspect.py")
    OUT.mkdir(parents=True, exist_ok=True)

    # Only explicit labels can anchor a transaction to a card.
    anchors: dict[str, str] = {}
    anchor_sources: dict[str, set[str]] = defaultdict(set)
    card_customer: dict[str, str] = {}
    def add_anchor(txn: str, card: str, customer: str, source: str):
        txn, card, customer = map(normalized, (txn, card, customer))
        if not txn or not card or not customer:
            return
        if txn in anchors and anchors[txn] != card:
            raise ValueError(f"Conflicting card anchors for transaction {txn}")
        if card in card_customer and card_customer[card] != customer:
            raise ValueError(f"Conflicting customers for card {card}")
        anchors[txn] = card
        anchor_sources[txn].add(source)
        card_customer[card] = customer

    closed_cases = list(rows("closed_cases_history.csv"))
    case_pack = list(rows("case_pack.csv"))
    for case in closed_cases:
        card_customer[normalized(case["card_id"])] = normalized(case["customer_id"])
        for txn in case["txn_ids"].split("|"):
            add_anchor(txn, case["card_id"], case["customer_id"], "closed_case:" + case["case_id"])
    for case in case_pack:
        add_anchor(case["flagged_txn_id"], case["card_id"], case["customer_id"], "case_pack:" + case["case_id"])

    identity_by_txn = {normalized(row["TransactionID"]): row for row in rows("identity.csv")}
    customers: set[str] = set()
    devices: dict[str, str] = {}
    emails: set[str] = set()
    regions: set[str] = set()
    seen_txn: set[str] = set()
    previous_by_customer: dict[str, str] = {}
    counts = defaultdict(int)

    names = {
        "transactions.csv": ["txn_id", "customer_id", "ts", "amount_usd", "channel", "risk_score", "product_code", "issuer_code_card1", "billing_region", "p_emaildomain", "r_emaildomain", "source_transaction_id"],
        "customer_transaction_edges.csv": ["customer_id", "txn_id"],
        "known_card_transaction_edges.csv": ["card_id", "txn_id", "provenance"],
        "next_customer_transaction_edges.csv": ["prior_txn_id", "next_txn_id"],
        "device_transaction_edges.csv": ["txn_id", "device_id", "device_new", "proxy_type"],
        "email_transaction_edges.csv": ["txn_id", "email_domain", "role"],
        "region_transaction_edges.csv": ["txn_id", "billing_region"],
    }
    opened = {name: writer(name, columns) for name, columns in names.items()}
    try:
        outputs = {name: pair[1] for name, pair in opened.items()}
        for row in rows("transactions.csv"):
            txn = normalized(row["TransactionID"])
            customer = normalized(row["customer_id"])
            if not txn or not customer:
                raise ValueError("TransactionID/customer_id missing in transactions.csv")
            if txn in seen_txn:
                raise ValueError(f"Duplicate TransactionID {txn}")
            seen_txn.add(txn)
            if txn in anchors and card_customer[anchors[txn]] != customer:
                raise ValueError(f"Anchor customer mismatch for transaction {txn}")
            customers.add(customer)
            outputs["transactions.csv"].writerow([txn, customer, row["ts"], row["TransactionAmt"], row["channel"], row["risk_score"], row["ProductCD"], row["card1"], row["addr1"], row["P_emaildomain"], row["R_emaildomain"], txn])
            outputs["customer_transaction_edges.csv"].writerow([customer, txn])
            counts["transactions"] += 1
            if txn in anchors:
                outputs["known_card_transaction_edges.csv"].writerow([anchors[txn], txn, "|".join(sorted(anchor_sources[txn]))])
                counts["known_card_transaction_edges"] += 1
            if customer in previous_by_customer:
                outputs["next_customer_transaction_edges.csv"].writerow([previous_by_customer[customer], txn])
            previous_by_customer[customer] = txn
            identity = identity_by_txn.get(txn)
            if identity:
                device_id, label = device_profile(identity)
                if device_id:
                    devices[device_id] = label
                    outputs["device_transaction_edges.csv"].writerow([txn, device_id, identity["id_15"], identity["id_23"]])
                    counts["device_transaction_edges"] += 1
            email_roles: dict[str, list[str]] = defaultdict(list)
            for field, role in (("P_emaildomain", "purchaser"), ("R_emaildomain", "recipient")):
                email = normalized(row[field]).lower()
                if email:
                    emails.add(email)
                    email_roles[email].append(role)
            # A simple edge has one value per transaction/domain pair. Preserve
            # both roles when purchaser and recipient share the same domain.
            for email, roles in email_roles.items():
                outputs["email_transaction_edges.csv"].writerow([txn, email, "|".join(roles)])
            region = normalized(row["addr1"])
            if region:
                regions.add(region)
                outputs["region_transaction_edges.csv"].writerow([txn, region])
    finally:
        for stream, _ in opened.values():
            stream.close()

    unknown_identity = set(identity_by_txn) - seen_txn
    unknown_anchors = set(anchors) - seen_txn
    if unknown_identity or unknown_anchors:
        raise ValueError(f"Unmatched identity rows: {len(unknown_identity)}; unmatched card anchors: {len(unknown_anchors)}")

    for name, header, records in (
        ("customers.csv", ["customer_id"], ((x,) for x in sorted(customers))),
        ("cards.csv", ["card_id", "customer_id"], ((c, card_customer[c]) for c in sorted(card_customer))),
        ("devices.csv", ["device_id", "profile"], ((d, devices[d]) for d in sorted(devices))),
        ("email_domains.csv", ["email_domain"], ((x,) for x in sorted(emails))),
        ("billing_regions.csv", ["billing_region"], ((x,) for x in sorted(regions))),
        ("closed_cases.csv", ["case_id", "customer_id", "card_id", "outcome", "pattern", "exposure_usd", "analyst_notes"], ((c[k] for k in ("case_id", "customer_id", "card_id", "outcome", "pattern", "exposure_usd", "analyst_notes")) for c in closed_cases)),
    ):
        stream, output = writer(name, header)
        with stream:
            output.writerows(records)
    stream, output = writer("closed_case_transaction_edges.csv", ["case_id", "txn_id"])
    with stream:
        for case in closed_cases:
            for txn in case["txn_ids"].split("|"):
                if normalized(txn):
                    output.writerow([normalized(case["case_id"]), normalized(txn)])
    stats = dict(counts)
    stats.update({"customers": len(customers), "cards_explicitly_named": len(card_customer), "device_profiles": len(devices), "email_domains": len(emails), "billing_regions": len(regions), "closed_cases": len(closed_cases), "benchmark_cases": len(case_pack), "identity_rows": len(identity_by_txn), "card_mapping": "explicit anchors only; all other card membership unknown", "loaded_to_tigergraph": False})
    (OUT / "ingestion_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
