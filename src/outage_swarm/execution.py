from __future__ import annotations

from typing import Any
from uuid import uuid4

from .models import ActionRecord, ActionType, MissionState, Recommendation


class ActionAdapter:
    action_type: ActionType

    def execute(self, mission: MissionState, recommendation: Recommendation, dry_run: bool) -> dict[str, Any]:
        raise NotImplementedError


class FeatureFlagAdapter(ActionAdapter):
    action_type = ActionType.FEATURE_FLAG_TOGGLE

    def execute(self, mission: MissionState, recommendation: Recommendation, dry_run: bool) -> dict[str, Any]:
        flag = recommendation.parameters["flag"]
        previous = mission.control_state.setdefault("feature_flags", {}).get(flag, False)
        if not dry_run:
            mission.control_state["feature_flags"][flag] = recommendation.parameters["enabled"]
        return {"previous": previous, "new": recommendation.parameters["enabled"], "flag": flag}


class QueueRetryAdapter(ActionAdapter):
    action_type = ActionType.QUEUE_RETRY_TUNING

    def execute(self, mission: MissionState, recommendation: Recommendation, dry_run: bool) -> dict[str, Any]:
        previous = mission.control_state.get("queue_retry", {"retry_multiplier": 1.0, "jitter_ms": 100})
        new = {
            "retry_multiplier": recommendation.parameters["retry_multiplier"],
            "jitter_ms": recommendation.parameters["jitter_ms"],
        }
        if not dry_run:
            mission.control_state["queue_retry"] = new
        return {"previous": previous, "new": new}


class ThrottleAdapter(ActionAdapter):
    action_type = ActionType.SERVICE_THROTTLE

    def execute(self, mission: MissionState, recommendation: Recommendation, dry_run: bool) -> dict[str, Any]:
        throttles = mission.control_state.setdefault("throttles", {})
        previous = throttles.get(recommendation.target, 100)
        new = recommendation.parameters["limit_percent"]
        if not dry_run:
            throttles[recommendation.target] = new
        return {"previous": previous, "new": new, "service": recommendation.target}


class TrafficShiftAdapter(ActionAdapter):
    action_type = ActionType.BOUNDED_TRAFFIC_SHIFT

    def execute(self, mission: MissionState, recommendation: Recommendation, dry_run: bool) -> dict[str, Any]:
        shifts = mission.control_state.setdefault("traffic_shifts", {})
        previous = shifts.get(recommendation.target, {"destination": None, "percent": 0})
        new = {
            "destination": recommendation.parameters["destination"],
            "percent": recommendation.parameters["percent"],
        }
        if not dry_run:
            shifts[recommendation.target] = new
        return {"previous": previous, "new": new, "source": recommendation.target}


class ExecutionBroker:
    """The only component allowed to invoke control adapters."""

    EFFECTIVENESS = {
        ActionType.FEATURE_FLAG_TOGGLE: 0.52,
        ActionType.QUEUE_RETRY_TUNING: 0.74,
        ActionType.SERVICE_THROTTLE: 0.49,
        ActionType.BOUNDED_TRAFFIC_SHIFT: 0.67,
    }

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.adapters = {
            adapter.action_type: adapter
            for adapter in (
                FeatureFlagAdapter(),
                QueueRetryAdapter(),
                ThrottleAdapter(),
                TrafficShiftAdapter(),
            )
        }

    def execute(self, mission: MissionState, recommendation: Recommendation, actor: str) -> ActionRecord:
        adapter = self.adapters[recommendation.action_type]
        result = adapter.execute(mission, recommendation, self.dry_run)
        result["simulated_effectiveness"] = self.EFFECTIVENESS[recommendation.action_type]
        return ActionRecord(
            recommendation_id=recommendation.id,
            action_type=recommendation.action_type,
            target=recommendation.target,
            parameters=recommendation.parameters,
            actor=actor,
            dry_run=self.dry_run,
            status="simulated" if self.dry_run else "executed",
            result=result,
            rollback_token=f"rbk_{uuid4().hex[:16]}",
        )
