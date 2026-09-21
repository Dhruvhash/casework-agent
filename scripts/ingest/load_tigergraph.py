"""Load prepared CSVs into Savanna with a GSQL loading job and verify results.

Credentials stay in .env. The REST loading endpoint accepts batches of JSON
records, avoiding CSV quoting ambiguities. Existing primary IDs are upserted.
Only HHG_LoadPrepared_v1 is created/updated; no graph data is deleted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "results" / "tigergraph_load_report.json"
CHECKPOINT = ROOT / "results" / "tigergraph_load_checkpoint.json"
JOB = "HHG_LoadPrepared_v1"
NUMERIC = {"amount_usd", "risk_score", "exposure_usd"}


class Mapping:
    def __init__(self, kind, name, fields, endpoints=()):
        self.kind, self.name = kind, name
        self.fields, self.endpoints = fields, endpoints


def vertex(name, *fields):
    return Mapping("VERTEX", name, fields)


def edge(name, source, target, *fields):
    return Mapping("EDGE", name, fields, (source, target))


TASKS = [
    ("customers", [vertex("HHG_Customer", "customer_id")]),
    ("cards", [vertex("HHG_Card", "card_id"),
               edge("HHG_OWNS", "HHG_Customer", "HHG_Card", "customer_id", "card_id")]),
    ("transactions", [vertex("HHG_Transaction", "txn_id", "ts", "amount_usd", "channel", "risk_score", "product_code", "issuer_code_card1", "billing_region", "p_emaildomain", "r_emaildomain", "source_transaction_id")]),
    ("devices", [vertex("HHG_DeviceProfile", "device_id", "profile")]),
    ("email_domains", [vertex("HHG_EmailDomain", "email_domain")]),
    ("billing_regions", [vertex("HHG_BillingRegion", "billing_region")]),
    ("closed_cases", [vertex("HHG_ClosedCase", "case_id", "outcome", "pattern", "exposure_usd", "analyst_notes"),
                      edge("HHG_CLOSED_CASE_ON_CARD", "HHG_ClosedCase", "HHG_Card", "case_id", "card_id")]),
    ("customer_transaction_edges", [edge("HHG_HAS_TRANSACTION", "HHG_Customer", "HHG_Transaction", "customer_id", "txn_id")]),
    ("known_card_transaction_edges", [edge("HHG_KNOWN_CARD_TRANSACTION", "HHG_Card", "HHG_Transaction", "card_id", "txn_id", "provenance")]),
    ("next_customer_transaction_edges", [edge("HHG_NEXT_CUSTOMER_TRANSACTION", "HHG_Transaction", "HHG_Transaction", "prior_txn_id", "next_txn_id")]),
    ("device_transaction_edges", [edge("HHG_FROM_DEVICE", "HHG_Transaction", "HHG_DeviceProfile", "txn_id", "device_id", "device_new", "proxy_type")]),
    ("email_transaction_edges", [edge("HHG_HAS_EMAIL_DOMAIN", "HHG_Transaction", "HHG_EmailDomain", "txn_id", "email_domain", "role")]),
    ("region_transaction_edges", [edge("HHG_BILLED_IN", "HHG_Transaction", "HHG_BillingRegion", "txn_id", "billing_region")]),
    ("closed_case_transaction_edges", [edge("HHG_CLOSED_CASE_INVOLVES", "HHG_ClosedCase", "HHG_Transaction", "case_id", "txn_id")]),
]


def rows(stem):
    with (DATA / f"{stem}.csv").open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def fingerprint(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def preflight():
    vertices, expected, counts, samples, hashes = {}, {}, {}, {}, {}
    for stem, mappings in TASKS:
        hashes[stem] = fingerprint(DATA / f"{stem}.csv")
        ids = {m.name: set() for m in mappings}
        for m in mappings:
            if m.kind == "VERTEX":
                vertices[m.name] = ids[m.name]
        count = 0
        for row in rows(stem):
            count += 1
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Malformed CSV: {stem}, row {count}")
            for mapping in mappings:
                values = [row[f] for f in mapping.fields]
                key = values[0] if mapping.kind == "VERTEX" else tuple(values[:2])
                if not all(values[:1 if mapping.kind == 'VERTEX' else 2]):
                    raise ValueError(f"Empty ID: {stem}, row {count}")
                if key in ids[mapping.name]:
                    raise ValueError(f"Duplicate ID or edge: {stem}, row {count}")
                ids[mapping.name].add(key)
                for f in mapping.fields:
                    if f in NUMERIC and not math.isfinite(float(row[f])):
                        raise ValueError(f"Invalid numeric {f}: {stem}, row {count}")
                if mapping.kind == "EDGE":
                    for t, v in zip(mapping.endpoints, values[:2]):
                        if v not in vertices[t]:
                            raise ValueError(f"Missing {t} endpoint in {stem}, row {count}")
            if count == 1:
                samples[stem] = [row]
            elif count == 101:
                samples[stem].append(row)
            last = row
        if not count:
            raise ValueError(f"Empty prepared file: {stem}")
        if last != samples[stem][-1]:
            samples[stem].append(last)
        counts[stem] = count
        for m in mappings:
            expected[m.name] = len(ids[m.name])
            if m.kind == "VERTEX":
                vertices[m.name] = ids[m.name]
    # Ensure the NEXT edges really follow nondecreasing transaction timestamps.
    tx = {r["txn_id"]: (r["customer_id"], r["ts"]) for r in rows("transactions")}
    for r in rows("next_customer_transaction_edges"):
        a, b = tx[r["prior_txn_id"]], tx[r["next_txn_id"]]
        if a[0] != b[0] or a[1] > b[1]:
            raise ValueError("NEXT transaction edge violates customer/time order")
    print("Preflight passed: unique IDs, valid endpoints, finite numbers, chronological links.", flush=True)
    return expected, counts, samples, hashes


class Client:
    def __init__(self):
        load_dotenv(ROOT / ".env")
        self.host = os.environ["TG_HOST"].rstrip("/")
        self.graph = os.environ["TG_GRAPHNAME"]
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["GSQL-TIMEOUT"] = "120000"
        secret, token = os.getenv("TG_SECRET"), os.getenv("TG_API_TOKEN")
        if secret:
            self.session.headers["Authorization"] = "GSQL-Secret " + secret
        elif token:
            self.session.headers["Authorization"] = "Bearer " + token
        else:
            raise ValueError("TG_SECRET or TG_API_TOKEN is required")

    def request(self, method, path, **kwargs):
        for attempt in range(3):
            try:
                response = self.session.request(method, self.host + path, timeout=(15, 180), **kwargs)
                if response.status_code in (502, 503, 504) and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                body = response.json()
                if not response.ok or body.get("error"):
                    raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {body.get('message', '')[:500]}")
                return body
            except (requests.ConnectionError, requests.Timeout):
                if attempt == 2:
                    raise RuntimeError(f"Network failure accessing {path}") from None
                time.sleep(3 * (attempt + 1))
        raise RuntimeError("Request retries exhausted")

    def counts(self):
        result = {}
        for fn, key in (("stat_vertex_number", "v_type"), ("stat_edge_number", "e_type")):
            body = self.request("POST", f"/restpp/builtins/{self.graph}", json={"function": fn, "type": "*"})
            result.update({r[key]: r["count"] for r in body["results"]})
        return result


def job_text(graph):
    lines = [f"CREATE LOADING JOB {JOB} FOR GRAPH {graph} {{"]
    for stem, mappings in TASKS:
        lines.append(f"  DEFINE FILENAME {stem};")
    for stem, mappings in TASKS:
        for m in mappings:
            values = ", ".join('$"' + f + '"' for f in m.fields)
            lines.append(f'  LOAD {stem} TO {m.kind} {m.name} VALUES ({values}) USING JSON_FILE="true";')
    return "\n".join(lines + ["}"])


def assert_clean(body, expected_rows, mappings):
    result = body.get("results", [])
    if not result or not all("statistics" in r for r in result):
        raise RuntimeError("Loading response did not contain detailed statistics")
    object_counts = {}
    valid_lines = 0
    for entry in result:
        stat = entry["statistics"]
        if "parsingStatistics" in stat:
            parsed = stat["parsingStatistics"]
            stat = {**parsed["fileLevel"], **parsed["objectLevel"]}
        valid_lines += stat.get("validLine", 0)
        for key, value in stat.items():
            if isinstance(value, (int, float)) and key != "validLine" and value:
                raise RuntimeError(f"Loading rejected data: {key}={value}")
        for kind in ("vertex", "edge"):
            for obj in stat.get(kind, []):
                for key, value in obj.items():
                    if key not in ("typeName", "validObject") and isinstance(value, (int, float)) and value:
                        raise RuntimeError(f"Invalid {obj['typeName']} attribute: {key}={value}")
                object_counts[obj["typeName"]] = object_counts.get(obj["typeName"], 0) + obj.get("validObject", 0)
    if valid_lines != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} accepted lines, received {valid_lines}")
    for m in mappings:
        if object_counts.get(m.name) != expected_rows:
            raise RuntimeError(f"Unexpected accepted object count for {m.name}: {object_counts}")
    return object_counts


def verify_samples(client, samples, schema):
    checked = 0
    attrs = {x["Name"]: [a["AttributeName"] for a in x["Attributes"]] for x in schema}
    for stem, mappings in TASKS:
        for m in mappings:
            for row in samples[stem]:
                if m.kind == "VERTEX":
                    path = f"/restpp/graph/{client.graph}/vertices/{m.name}/{quote(row[m.fields[0]], safe='')}"
                    values = m.fields[1:]
                else:
                    src, dst = m.endpoints
                    path = f"/restpp/graph/{client.graph}/edges/{src}/{quote(row[m.fields[0]], safe='')}/{m.name}/{dst}/{quote(row[m.fields[1]], safe='')}"
                    values = m.fields[2:]
                result = client.request("GET", path)["results"]
                if len(result) != 1:
                    raise RuntimeError(f"Expected one stored sample for {m.name}")
                stored = result[0]["attributes"]
                for attr, column in zip(attrs[m.name], values):
                    want = float(row[column]) if column in NUMERIC else row[column]
                    got = stored.get(attr)
                    equal = math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-9) if isinstance(want, float) and isinstance(got, (int, float)) else got == want
                    if not equal:
                        raise RuntimeError(f"Stored sample differs: {m.name}.{attr}")
                checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--batch-size", type=int, default=10000)
    args = parser.parse_args()
    expected, counts, samples, hashes = preflight()
    if args.preflight_only:
        print(json.dumps(counts, indent=2))
        return
    client = Client()
    before = client.counts()
    vs = client.request("GET", "/gsql/v1/schema/vertices", params={"graph": client.graph})["results"]
    es = client.request("GET", "/gsql/v1/schema/edges", params={"graph": client.graph})["results"]
    live = {x["Name"]: x for x in vs + es}
    for _, mappings in TASKS:
        for m in mappings:
            if m.name not in live or len(live[m.name]["Attributes"]) != len(m.fields) - (1 if m.kind == "VERTEX" else 2):
                raise RuntimeError(f"Schema mismatch: {m.name}")
    for e in es:
        if e["Name"] in expected:
            reverse = e.get("Config", {}).get("REVERSE_EDGE")
            if reverse:
                expected[reverse] = expected[e["Name"]]
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "graph": client.graph,
              "before": before, "expected": expected, "source_rows": counts, "files": {}, "verified": False}
    write_json(REPORT, report)
    script = job_text(client.graph)
    script_path = ROOT / "tigergraph" / "loading" / "load_prepared.gsql"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script + "\n", encoding="utf-8")
    identity = hashlib.sha256((client.host + client.graph + script).encode()).hexdigest()
    checkpoint = json.loads(CHECKPOINT.read_text()) if CHECKPOINT.exists() else {}
    if checkpoint.get("identity") != identity:
        checkpoint = {"identity": identity, "completed": {}}
    if not args.verify_only:
        jobs = client.request("GET", "/gsql/v1/loading-jobs", params={"graph": client.graph})["jobNames"]
        api_script = script.replace(f" FOR GRAPH {client.graph}", "", 1)
        client.request("PUT" if JOB in jobs else "POST", "/gsql/v1/loading-jobs", params={"graph": client.graph}, data=api_script.encode(), headers={"Content-Type": "text/plain"})
        print("GSQL loading job ready.", flush=True)
        for stem, mappings in TASKS:
            if checkpoint["completed"].get(stem) == hashes[stem] and all(before.get(m.name) == expected[m.name] for m in mappings):
                report["files"][stem] = {"rows": counts[stem], "status": "previously_uploaded"}
                print(f"Verified checkpoint: {stem}", flush=True)
                continue
            batch, done, objects = [], 0, {}
            def upload():
                nonlocal done
                payload = ("\n".join(json.dumps(r, ensure_ascii=True, separators=(",", ":")) for r in batch) + "\n").encode()
                response = client.request("POST", f"/restpp/ddl/{client.graph}", params={"tag": JOB, "filename": stem, "ack": "all"}, data=payload, headers={"Content-Type": "application/json"})
                accepted = assert_clean(response, len(batch), mappings)
                for key, value in accepted.items():
                    objects[key] = objects.get(key, 0) + value
                done += len(batch)
                print(f"{stem}: {done:,}/{counts[stem]:,} rows accepted", flush=True)
            for row in rows(stem):
                batch.append(row)
                if len(batch) >= args.batch_size:
                    upload()
                    batch = []
            if batch:
                upload()
            if fingerprint(DATA / f"{stem}.csv") != hashes[stem]:
                raise RuntimeError(f"Source file changed during upload: {stem}")
            report["files"][stem] = {"rows": done, "accepted_objects": objects, "rejected_rows": 0, "sha256": hashes[stem]}
            checkpoint["completed"][stem] = hashes[stem]
            write_json(CHECKPOINT, checkpoint)
            write_json(REPORT, report)
    after = client.counts()
    report["after"] = after
    errors = {name: {"expected": number, "actual": after.get(name)} for name, number in expected.items() if after.get(name) != number}
    report["count_errors"] = errors
    write_json(REPORT, report)
    if errors:
        raise RuntimeError(f"Graph count verification failed: {errors}")
    report["samples_checked"] = verify_samples(client, samples, vs + es)
    report["verified"] = True
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    write_json(REPORT, report)
    print(f"VERIFIED: all {len(expected)} vertex/edge counts and {report['samples_checked']} stored samples match.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"LOAD FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
