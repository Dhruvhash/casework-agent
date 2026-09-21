import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class IngestTests(unittest.TestCase):
    def test_each_benchmark_trigger_has_an_explicit_card_edge(self):
        benchmark = read_rows(RAW / "case_pack.csv")
        edges = {row["txn_id"]: row for row in read_rows(OUT / "known_card_transaction_edges.csv")}
        self.assertEqual(len(benchmark), 20)
        for case in benchmark:
            edge = edges[case["flagged_txn_id"]]
            self.assertEqual(edge["card_id"], case["card_id"])
            self.assertIn("case_pack:" + case["case_id"], edge["provenance"])


    def test_preparation_does_not_claim_graph_load_or_infer_all_cards(self):
        stats = json.loads((OUT / "ingestion_stats.json").read_text(encoding="utf-8"))
        self.assertFalse(stats["loaded_to_tigergraph"])
        self.assertLess(stats["known_card_transaction_edges"], stats["transactions"])
        self.assertEqual(stats["transactions"], 590742)


if __name__ == "__main__":
    unittest.main()
