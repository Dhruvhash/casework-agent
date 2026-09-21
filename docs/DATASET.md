# Verified dataset inventory

Source: [HHGOA_IEEE Drive folder](https://drive.google.com/drive/folders/1YDJUW1fiE7Jx8R9KqknC4IcsED9zll2A), especially its `README.md`. The supplied CSVs were downloaded, scanned and loaded into the development graph. The row counts below were validated locally; graph ingestion evidence is in `results/tigergraph_load_report.json`.

| File | README description |
|---|---|
| `transactions.csv` | 590,742 rows; 393 original Vesta columns plus `customer_id`, `ts`, `channel`, `risk_score`; no fraud flag. |
| `identity.csv` | 144,432 online identity rows; joins by `TransactionID`; device type/info and encoded identity fields. |
| `closed_cases_history.csv` | 5,565 closed investigations (4,665 confirmed fraud, 900 cleared), including outcomes, pattern, affected transaction IDs, notes. |
| `case_pack.csv` | 20 November/December benchmark triggers. |
| `README.md` | Column groups, five patterns, policy R1–R10, regulatory links, and exact JSON answer format. |

Local validation confirmed all four CSV counts above and no malformed rows. The transaction table has `TransactionID`, `TransactionDT`, `TransactionAmt`, `ProductCD`, `card1`–`card6`, `addr1`–`addr2`, `P_emaildomain`, `R_emaildomain`, `C1`–`C14`, `D1`–`D15`, `M1`–`M9`, `V1`–`V339`, and the four added fields. The identity table has `TransactionID`, `id_01`–`id_38`, `DeviceType`, and `DeviceInfo`. Most encoded columns have no individual published meaning; they must remain labeled as unnamed signals.

The README describes `card_id` in the case pack and closed cases but does not specify a `card_id` column in `transactions.csv` or a complete derivation from `card1`–`card6`. The actual CSV confirms its absence. See [TIGERGRAPH_SCHEMA.md](TIGERGRAPH_SCHEMA.md) for the safe customer link and explicit card anchors. Never join a benchmark card to transactions by a guessed rule.

## Obtain the files

Open the Drive folder, select each of the five files, and choose **Download**. Place the original, unchanged files in `data/raw/` with the names above. Do not place public IEEE-CIS/Kaggle files here: the challenge forbids using them to recover outcomes. Run:

```powershell
python scripts/ingest/inspect.py
```

This reads all four CSVs, reports their columns and row counts, and exits nonzero for missing files, missing required columns, or malformed rows. It does not load TigerGraph.
