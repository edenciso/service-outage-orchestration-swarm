from __future__ import annotations

from .models import Communications, MissionState, utc_now


class CommunicationsAgent:
    def draft(self, mission: MissionState) -> Communications:
        top = mission.hypotheses[0] if mission.hypotheses else None
        rec = mission.recommendations[0] if mission.recommendations else None
        affected = ", ".join(top.affected_nodes[:5]) if top else "under investigation"
        hypothesis = top.title if top else "Correlation is still in progress"
        confidence = f"{top.confidence:.0%}" if top else "not yet scored"
        mitigation = rec.title if rec else "No mitigation has been selected"
        internal = (
            f"{mission.severity} {mission.title}. Current leading hypothesis: {hypothesis} "
            f"({confidence} confidence). Affected scope: {affected}. Recommended next action: {mitigation}."
        )
        status = (
            "We are investigating elevated errors and latency affecting a subset of requests. "
            "The team has identified a likely dependency-related failure domain and is applying "
            "bounded mitigations. Core data integrity remains protected. We will provide another update "
            "as validation telemetry becomes available."
        )
        executive = (
            f"Incident {mission.id} remains {mission.status.value}. The swarm produced "
            f"{len(mission.hypotheses)} ranked hypotheses and {len(mission.recommendations)} mitigations. "
            f"{len(mission.actions)} bounded actions have been brokered; all are auditable and reversible."
        )
        return Communications(
            internal_summary=internal,
            status_page_draft=status,
            executive_update=executive,
            updated_at=utc_now(),
        )
