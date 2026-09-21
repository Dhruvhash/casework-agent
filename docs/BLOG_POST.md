# From an uncertain alert to an auditable recommendation with TigerGraph

## What I built

Casework is an agentic fraud-investigation prototype for the TigerGraph Hacker House Goa challenge. It starts with a transaction alert, retrieves customer and card history, examines relationships, consults past investigations, and produces an internal case, next actions and a suspicious-activity-report draft when the challenge policy requires one.

The interface makes uncertainty visible. An analyst can review the evidence, choose an explicitly simulated verification response, and see how the recommendation changes. No customer messages, card blocks or regulatory filings are actually sent.

## Architecture

A Python investigator orchestrates the official TigerGraph MCP server over stdio. GSQL queries retrieve evidence as of the case opening time. Native TigerGraph vector search retrieves policy text and closed-case narratives. The installed Nomic model supplies embeddings; Ollama's Llama 3.2 3B model plans retrieval and reviews evidence. OpenAI is an optional provider, not required for the demonstrated local configuration.

The model proposes a semantic search query and the type of additional evidence to request. The code validates structured outputs and applies deterministic policy rules. This separates flexible retrieval from permission-sensitive recommendations.

## How TigerGraph is used

Transactions, customers, cards, device profiles, regions and closed cases form the evidence graph. The loader preserves only explicit card attribution from the supplied historical cases and trigger records. It does not assume that every customer transaction belongs to the triggered card.

The investigation traverses customer history and known card transactions, then device neighbors and related historical records. Connected components, degree and shared-origin motifs summarize the retrieved neighborhood. A coordinated motif requires several customers, new device flags and anonymous or hidden proxy attributes; merely sharing a common phone/browser profile is insufficient.

TigerGraph also holds a native 768-dimensional vector index over historical narratives and policy material. Retrieved documents and graph evidence enter the model's review context. Versioned generated investigations are stored separately and can be retrieved by later investigations with an explicit warning that simulated outcomes are not ground truth. A time filter prevents later generated investigations from leaking into earlier cases.

## The agentic workflow

1. Accept the supplied risk, customer-report or analyst trigger.
2. Retrieve the as-of graph neighborhood.
3. Compute transparent behavioral features and relationship motifs.
4. Ask the language model what memory and additional evidence are relevant.
5. Retrieve historical, policy and generated-case memory.
6. Record initial policy recommendations.
7. Apply an explicitly selected simulated response, if provided.
8. Reapply policy and record what changed.
9. Validate the answer, persist the graph case and preserve a versioned record.

The policy layer enforces L1/L2 routes and distinguishes an internal case from a report. A simulated denial can change verification into a block recommendation and, above the policy threshold, an L2 report draft. Confirmation clears the flagged activity. No-reply handling preserves uncertainty and escalates exposed cases.

## What I learned

The hardest part was evidence provenance. Customer identifiers, card identifiers and generic device profiles are not interchangeable. Treating them as interchangeable would produce confident but unsupported investigations.

Cloud lifecycle also matters: a starting workspace may return an HTML page with a successful HTTP status. The client therefore requires structured JSON and verifies persistence. MCP responses can contain Markdown and documents with their own code fences; parsing must decode the JSON value rather than split on fence strings.

A small local model is useful for grounded planning, but policy enforcement and structured-output validation remain necessary. CPU inference avoids the GPU compatibility failure encountered on this development machine, at the cost of longer runs.

## Evaluation and limits

The repository contains policy boundary and workflow regression tests plus case validation. These tests are not an accuracy score. The hidden benchmark outcomes are unavailable, and fraud probabilities remain uncalibrated heuristics.

Account-takeover and coordinated-abuse detections are hypotheses supported by defined signals. The dataset lacks merchant identity and settlement status, so the system does not pretend that a repeated product is a recurring merchant charge or that a purchase has cleared. Generated memory never becomes a confirmed historical label merely because the agent wrote it.

The latest submission audit reports actual benchmark completion and publication status. Claims of correctness should be limited to the evidence in those reports.

## What I would improve

I would calibrate risk estimates on a time-separated historical validation set, add authenticated analyst approval and evidence intake, validate more adversarial scenarios, and evaluate retrieval precision and policy adherence across larger case sets. A production version would need access controls, retention policy, a durable event log, monitoring and human governance beyond this local hackathon prototype.

## References

- [GitHub Repository](https://github.com/Dhruvhash/casework-agent)
- [TigerGraph MCP](https://github.com/tigergraph/tigergraph-mcp)
- [FFIEC red flags](https://bsaaml.ffiec.gov/manual/Appendices/07): contextual guidance that red flags prompt investigation rather than establish guilt.
- The organizer-provided dataset README supplies the challenge's thresholds, action identifiers and answer contract. Those thresholds are not presented as general legal advice.

