# Service Outage Orchestration Swarm v1.0

A runnable recommendation-first incident-response agent swarm that detects, correlates, localizes, and mitigates outages spanning internal services and external cloud, CDN, AI, and carrier dependencies. Built on the Hybrid Agentic Swarm Architecture (HAS) v1.

## What is implemented

- Mission intake from three synthetic outage scenarios, manual/alert API requests, provider-status updates, and incremental signals.
- Curated service/dependency graph.
- Stigmergic field channels for failure, causal suspicion, user pain, trust, congestion, and mitigation success.
- Top-three ranked hypotheses with evidence, confidence, affected nodes, and blast radius.
- Scout, router, repair, sentinel, and tuner worker ensemble.
- Ranked mitigations with reward, confidence, impact, risk, policy class, factors, field snapshot reference, and rollback plan.
- Policy-gated broker with four reversible action adapters:
  - feature flag toggle;
  - queue retry tuning;
  - service throttle adjustment;
  - bounded traffic shift.
- Human approval queue for P2 actions.
- Internal summary, status-page draft, and executive update.
- SQLite audit ledger, incident memory, and replay export.
- OpenClaw-compatible isolated workspaces and role skills.
- Browser-based mission-control UI.

## Scope optimization

The production stack is intentionally collapsed for v1.0. Redis, Postgres, NATS/Kafka, Ray, and OPA would increase setup cost without improving the first validation question: **Can a governed swarm produce credible, explainable, and safely executable outage mitigations faster than a human-only workflow?**

Each local component has an explicit replacement boundary, documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The product semantics are preserved; distributed scale and third-party control integrations are deferred.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn outage_swarm.api:app --reload
```

Open `http://localhost:8000`.

The broker runs in **dry-run mode by default**. It records the proposed state transition and rollback token but does not touch external infrastructure.

### Docker

```bash
docker compose up --build
```

### CLI demo

```bash
outage-swarm scenarios
outage-swarm demo cloud-region-retry-storm
```

### Tests

```bash
pytest
```

## API workflow

```bash
# Create and analyze a scenario
curl -s -X POST http://localhost:8000/api/missions/scenario/cloud-region-retry-storm

# Read the mission
curl -s http://localhost:8000/api/missions/<mission_id>

# Approve a P2 recommendation
curl -s -X POST http://localhost:8000/api/missions/<mission_id>/recommendations/<rec_id>/approve \
  -H 'Content-Type: application/json' \
  -d '{"actor":"incident-commander","decision":"approved","reason":"bounded canary"}'

# Execute through the broker
curl -s -X POST http://localhost:8000/api/missions/<mission_id>/recommendations/<rec_id>/execute \
  -H 'Content-Type: application/json' \
  -d '{"actor":"execution-broker"}'
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## OpenClaw integration path

The executable default is deterministic Python so the incident loop is reproducible and testable. The `openclaw/` directory includes isolated role workspaces, `AGENTS.md` constraints, custom `SKILL.md` packs, and a configuration example. Set:

```bash
export OUTAGE_SWARM_OPENCLAW_MODE=filesystem
export OUTAGE_SWARM_OPENCLAW_WORKSPACE=./openclaw/workspaces
```

The conductor will publish mission packets into the relevant workspace inbox. A production integration would replace filesystem handoff with Gateway sessions/tool calls while retaining the same typed mission contracts and broker boundary.

## Recommended v1.1 sequence

1. Add real read-only ingestors: Prometheus/OTel webhook, Cloudflare/AWS/OpenAI-style status adapters.
2. Replace the local policy evaluator with OPA/Rego while preserving current policy fixtures.
3. Connect one real reversible surface—LaunchDarkly or a queue configuration API—in a non-production environment.
4. Add operator feedback controls for hypothesis relevance and recommendation utility.
5. Run replay evaluation on 20–30 historical incidents before introducing Ray or learned policies.

## Safety model

- Only the execution broker owns action adapters.
- P2 actions require explicit approval.
- P3 actions are denied.
- All actions are reversible, scoped, and include a rollback token.
- Dry-run is the default.
- The system degrades safely to recommendation-only behavior.
