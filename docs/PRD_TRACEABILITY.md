# PRD traceability

| Requirement | Prototype implementation | Verification |
|---|---|---|
| FR-1 Mission intake | Scenario, manual, alert-webhook alias, provider-status, and signal endpoints | API + UI |
| FR-2 Correlation | `CorrelationAgent` ranks top three hypotheses | `test_mission_flow.py` |
| FR-3 Dependency mapping | Curated node/edge graph in `scenarios.py` | UI SVG graph |
| FR-4 Swarm recommendations | Scout, router, repair, sentinel, tuner ensemble | API + UI |
| FR-5 Policy gating | `PolicyEngine` P1/P2/P3 decisions | policy gate test |
| FR-6 Bounded execution | Four adapters in `execution.py` | action-type test |
| FR-7 Approval workflow | Approval endpoint and audit event | policy gate test |
| FR-8 Communications | Internal, status-page, executive drafts | UI panel |
| FR-9 Memory capture | SQLite memory record on mission close | close test |
| FR-10 Replay | Full JSON replay endpoint | close test |
| NFR auditability | Actor, mission, recommendation, action, rollback IDs | timeline and replay |
| NFR resilience | Dry-run default; policy denial; broker-only execution | configuration + tests |
| NFR explainability | evidence, factors, field snapshot ID, rollback plan | recommendation model |
