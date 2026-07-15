---
name: outage-mission-role
description: Execute the bounded memory role in an outage choreography mission.
---

# Memory role

1. Read the mission packet from `inbox/`.
2. Perform only the memory responsibility.
3. Do not fabricate telemetry or provider status.
4. Attach signal IDs and field snapshot IDs to claims.
5. Return JSON containing `mission_id`, `actor`, `output`, `confidence`, and `limitations`.
6. Never call a production control API; only the execution broker may execute actions.
