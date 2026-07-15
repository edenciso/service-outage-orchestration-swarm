# Architecture

```mermaid
flowchart LR
  A[Alert / status / manual intake] --> C[Master Conductor]
  C --> F[Field substrate]
  C --> G[Dependency graph]
  F --> S1[Scout]
  F --> S2[Router]
  F --> S3[Repair]
  F --> S4[Sentinel]
  F --> S5[Tuner]
  G --> S1
  S1 --> P[Mitigation Planner]
  S2 --> P
  S3 --> P
  S4 --> P
  S5 --> P
  P --> PE[Policy Engine]
  PE -->|P1| EB[Execution Broker]
  PE -->|P2| AP[Approval Queue]
  AP --> EB
  PE -->|P3| O[Observe only]
  EB --> FF[Feature flags]
  EB --> QR[Queue retry]
  EB --> TH[Throttle]
  EB --> TS[Traffic shift]
  C --> COM[Communications]
  C --> MEM[Memory + replay]
```

## Prototype substitutions

| PRD production component | v1.0 implementation | Upgrade boundary |
|---|---|---|
| OpenClaw runtime | Deterministic Python conductor plus OpenClaw workspace/skill bridge | Replace role methods with Gateway-routed agents |
| Redis field store | In-process field snapshot aggregate | `FieldSubstrate` interface |
| Postgres | SQLite JSON aggregate store | `MissionRepository` interface |
| NATS/Kafka | In-process ordered mission events | Emit repository events to durable bus |
| Ray workers | Synchronous specialized worker ensemble | Put each worker behind a Ray task/actor |
| OPA | Local policy evaluator with OPA-compatible decision boundary | Replace `PolicyEngine.evaluate` |
| Production APIs | Dry-run adapters and control-state simulator | Replace individual adapters only |

The substitutions minimize setup and failure modes without collapsing the architectural boundaries that matter for validation.
