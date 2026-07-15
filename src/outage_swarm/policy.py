from __future__ import annotations

from dataclasses import dataclass

from .models import ActionType, PolicyDecision


@dataclass(frozen=True)
class PolicyResult:
    policy_class: str
    decision: PolicyDecision
    reason: str


class PolicyEngine:
    """OPA-compatible policy boundary implemented locally for the prototype."""

    def evaluate(
        self,
        action_type: ActionType,
        risk_score: float,
        expected_impact: float,
        parameters: dict,
    ) -> PolicyResult:
        reversible = bool(parameters.get("reversible", True))
        scope = float(parameters.get("max_scope", 0.1))
        if not reversible:
            return PolicyResult("P3", PolicyDecision.DENY, "Non-reversible actions are outside MVP scope")
        if action_type == ActionType.BOUNDED_TRAFFIC_SHIFT and scope > 0.25:
            return PolicyResult("P3", PolicyDecision.DENY, "Traffic shifts above 25% are prohibited")
        if risk_score <= 0.25 and scope <= 0.10 and expected_impact >= 0.35:
            return PolicyResult("P1", PolicyDecision.ALLOW, "Low-risk, reversible, narrowly bounded action")
        if risk_score <= 0.58 and scope <= 0.25:
            return PolicyResult("P2", PolicyDecision.REQUIRE_APPROVAL, "Reversible action requires incident commander approval")
        return PolicyResult("P3", PolicyDecision.DENY, "Risk or scope exceeds prototype guardrails")
