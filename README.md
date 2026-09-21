# Casework — TigerGraph Agentic Fraud Investigation

A local investigation console for the Hacker House Goa benchmark. Casework combines TigerGraph graph traversal, native vector search, official TigerGraph MCP, a local language model, and deterministic approval rules.

## What it does

- Investigates a supplied trigger using customer history, explicitly attributed card transactions, device neighbors and historical cases.
- Detects testing sequences, unusual online activity, new-device signals, out-of-region activity, mixed-channel takeover hypotheses and coordinated new-device/proxy motifs.
- Records uncertainty and explicit simulated verification responses; recommendations never execute banking operations.
- Produces the required case JSON, initial/final action routes and policy-required SAR draft.
- Saves the case and versioned investigation memory to TigerGraph. Future investigations retrieve earlier generated memory with its simulation disclaimer.
- Shows evidence, graph relationships, actions, SAR drafts and execution traces in a browser.

Probabilities are transparent heuristics, not calibrated estimates. Pattern hypotheses are not confirmed outcomes. No hidden benchmark labels or public Kaggle outcomes are used.

## Run locally

Requires Python 3.11+, TigerGraph Savanna with the supplied dataset loaded, and Ollama with `llama3.2:3b` and `nomic-embed-text`.

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Fill in your own TigerGraph host, graph and secret.
python -m scripts.deploy_agent
python -m scripts.deploy_memory
python -m scripts.agent.generate_cases
python -m uvicorn ui.server:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. On an existing prepared graph, skip deployment and ingestion.
For a fresh graph, follow [data loading](docs/DATA_LOADING.md) and deploy [the schema](tigergraph/schema/schema.gsql) first. Put the organizer-provided files in `data/raw/`; the large dataset and credentials are excluded from Git.

### Explicit simulation

```powershell
python -m scripts.agent.generate_cases --case HHG-010 --response denied
python -m scripts.agent.generate_cases --case HHG-010 --response confirmed
python -m scripts.agent.generate_cases --case HHG-010 --response no_reply_24h
```

These are assumptions for the challenge, not received customer replies. Rerunning a case updates its current answer and appends a versioned memory record. Run the default benchmark again to restore pending-response answers.

## Architecture

```mermaid
flowchart LR
  UI[Local console] --> A[Bounded investigator]
  A --> MCP[Official TigerGraph MCP]
  MCP --> G[As-of GSQL context]
  MCP --> V[Native vector search]
  G --> F[Features and graph motifs]
  V --> L[Grounded LLM planner/reviewer]
  L --> P[Policy and approval routing]
  F --> P
  P --> J[Validated case and SAR JSON]
  J --> M[Graph case and versioned memory]
  M --> V
```

The model chooses a retrieval query and an evidence request and reviews retrieved evidence. It cannot execute arbitrary GSQL or financial actions. Policy code controls action routing. Original historical labels remain separate from generated memory.

## Verification and deliverables

```powershell
python -m pytest -q -p no:cacheprovider
python -m scripts.audit_submission
```

- [20 answer files](cases/)
- [Technical blog](docs/BLOG_POST.md)
- [Submission audit](docs/SUBMISSION_AUDIT.md)
- [Model configuration](docs/MODEL_CONFIGURATION.md)
- [Demo materials](docs/demo/)

Execution results and publication status should be checked against the latest audit. Unit tests establish specific behavior, not hidden-label accuracy.

## Important modeling limits

The dataset does not give a card ID for every transaction. Only explicit historical and trigger anchors form card-transaction edges. Customer history is not silently relabeled as card history. Generic device profiles and email domains are not unique people or merchants. Merchant identity and settlement status are absent, so recurring-merchant and cleared-purchase rules require additional verified evidence.

Savanna auto-start and auto-suspend should remain enabled. Credentials stay in `.env`; the console binds to loopback and should not be exposed publicly without authentication.

## GitHub Upload Guide (Step-by-Step)

Follow these steps to publish this repository to your GitHub account:

### Step 1: Install & Authenticate GitHub CLI
If you haven't logged in yet:
```powershell
gh auth login
```
Select **GitHub.com** -> **HTTPS** -> **Login with a web browser**. Enter the 8-digit device code provided in your browser and authorize the application.

### Step 2: Create Remote Repository and Push
Run the single command below from the project root directory:
```powershell
gh repo create casework-agent --public --source=. --remote=origin --push
```
*Alternatively, if you already created an empty repository on GitHub manually:*
```powershell
git remote add origin https://github.com/YOUR_USERNAME/casework-agent.git
git branch -M master
git push -u origin master
```

### Step 3: Verify Your Upload
Check your remote repo status:
```powershell
git status
git remote -v
```

---

## Demo Video & Assets

An edited, narrated 4.5-minute demo video is built and included in the repository:
- **Video File**: [`docs/demo/casework-demo.mp4`](file:///d:/AIML/HHG_Task_4/docs/demo/casework-demo.mp4)
- **Manifest**: [`docs/demo/video_manifest.json`](file:///d:/AIML/HHG_Task_4/docs/demo/video_manifest.json)
- **Scenes & Narration**: 8 application walkthrough scenes covering uncertain trigger investigation, evidence request, policy routing, SAR draft generation, memory preservation, and multi-customer motif queries.

To rebuild or re-narrate the demo video:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_audio.ps1
python -m scripts.build_demo
```

---

## Attribution

IEEE-CIS/Vesta dataset with challenge additions by TigerGraph. See the organizer-provided README for the authoritative benchmark and policy. Regulatory context is attributed in retrieved documents and the blog.

