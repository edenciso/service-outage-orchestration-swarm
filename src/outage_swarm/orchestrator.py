from __future__ import annotations

from collections import defaultdict

from .communications import CommunicationsAgent
from .config import Settings
from .correlation import CorrelationAgent
from .execution import ExecutionBroker
from .field import FieldSubstrate
from .models import (
    Approval,
    Event,
    MemoryRecord,
    MissionState,
    MissionStatus,
    PolicyDecision,
    Signal,
    utc_now,
)
from .openclaw_adapter import OpenClawMissionBridge
from .policy import PolicyEngine
from .repository import MissionRepository
from .scenarios import get_scenario, graph
from .swarm import SwarmRecommendationEngine


class MissionConductor:
    def __init__(self, repository: MissionRepository, settings: Settings):
        self.repository = repository
        self.settings = settings
        self.field = FieldSubstrate()
        self.correlation = CorrelationAgent()
        self.policy = PolicyEngine()
        self.swarm = SwarmRecommendationEngine(self.policy)
        self.execution = ExecutionBroker(dry_run=settings.dry_run)
        self.communications = CommunicationsAgent()
        self.openclaw = OpenClawMissionBridge(
            settings.openclaw_workspace,
            enabled=settings.openclaw_mode.lower() == "filesystem",
        )

    def create_from_scenario(self, scenario_id: str) -> MissionState:
        scenario = get_scenario(scenario_id)
        nodes, edges = graph()
        mission = MissionState(
            title=scenario["title"],
            scenario=scenario_id,
            severity=scenario["severity"],
            nodes=nodes,
            edges=edges,
            signals=scenario["signals"],
            control_state=self._default_control_state(),
        )
        self._event(mission, "master-conductor", "mission.created", "Mission created from synthetic scenario", {"scenario": scenario_id})
        self.repository.save(mission)
        return self.analyze(mission.id)

    def create_manual(self, title: str, severity: str, signals: list[Signal]) -> MissionState:
        nodes, edges = graph()
        mission = MissionState(
            title=title,
            severity=severity,
            nodes=nodes,
            edges=edges,
            signals=signals,
            control_state=self._default_control_state(),
        )
        self._event(mission, "master-conductor", "mission.created", "Manual mission created")
        self.repository.save(mission)
        return self.analyze(mission.id)

    def add_signal(self, mission_id: str, signal: Signal) -> MissionState:
        mission = self._require(mission_id)
        mission.signals.append(signal)
        self._event(mission, "signal-ingestor", "signal.ingested", signal.summary, {"signal_id": signal.id})
        self.repository.save(mission)
        return self.analyze(mission_id)

    def analyze(self, mission_id: str) -> MissionState:
        mission = self._require(mission_id)
        snapshot = self.field.build(
            [node.id for node in mission.nodes], mission.edges, mission.signals
        )
        mission.field_snapshots.append(snapshot)
        mission.hypotheses = self.correlation.correlate(
            mission.nodes, mission.edges, mission.signals, snapshot
        )
        memory_bias = self._memory_bias()
        mission.recommendations = self.swarm.recommend(
            mission.nodes,
            mission.signals,
            mission.hypotheses,
            snapshot,
            memory_bias,
        )
        mission.communications = self.communications.draft(mission)
        mission.updated_at = utc_now()
        self._event(
            mission,
            "correlation-agent",
            "analysis.completed",
            f"Produced {len(mission.hypotheses)} hypotheses and {len(mission.recommendations)} recommendations",
            {"field_snapshot_id": snapshot.id},
        )
        self.openclaw.publish("conductor", mission, "Review and coordinate mission state")
        self.openclaw.publish("correlation", mission, "Validate evidence and ranked failure domains")
        self.openclaw.publish("planner", mission, "Review mitigation ranking and policy metadata")
        self.openclaw.publish("communications", mission, "Review validated incident communications")
        self.repository.save(mission)
        return mission

    def approve(self, mission_id: str, recommendation_id: str, actor: str, decision: str, reason: str) -> MissionState:
        mission = self._require(mission_id)
        recommendation = self._recommendation(mission, recommendation_id)
        approval = Approval(
            recommendation_id=recommendation_id,
            actor=actor,
            decision=decision,
            reason=reason,
        )
        mission.approvals.append(approval)
        recommendation.status = "approved" if decision == "approved" else "rejected"
        self._event(mission, actor, "approval.recorded", f"Recommendation {decision}", {"recommendation_id": recommendation_id})
        mission.updated_at = utc_now()
        self.repository.save(mission)
        return mission

    def execute(self, mission_id: str, recommendation_id: str, actor: str) -> MissionState:
        mission = self._require(mission_id)
        if mission.status == MissionStatus.CLOSED:
            raise PermissionError("Closed missions cannot execute actions")
        recommendation = self._recommendation(mission, recommendation_id)
        if recommendation.policy_decision == PolicyDecision.DENY:
            raise PermissionError("Recommendation is denied by policy")
        if recommendation.policy_decision == PolicyDecision.REQUIRE_APPROVAL:
            approved = any(
                item.recommendation_id == recommendation_id and item.decision == "approved"
                for item in mission.approvals
            )
            if not approved:
                raise PermissionError("Recommendation requires approval before execution")
        if recommendation.status in {"executed", "simulated"}:
            return mission
        action = self.execution.execute(mission, recommendation, actor)
        mission.actions.append(action)
        recommendation.status = action.status
        mission.status = MissionStatus.MITIGATING
        latest = mission.field_snapshots[-1]
        effectiveness = float(action.result["simulated_effectiveness"])
        mission.field_snapshots.append(
            self.field.apply_mitigation(latest, recommendation.target, effectiveness)
        )
        self._event(
            mission,
            "execution-broker",
            "action.executed",
            f"{action.status.title()}: {recommendation.title}",
            {"action_id": action.id, "rollback_token": action.rollback_token},
        )
        mission.communications = self.communications.draft(mission)
        mission.updated_at = utc_now()
        self.repository.save(mission)
        return mission

    def close(self, mission_id: str) -> MissionState:
        mission = self._require(mission_id)
        mission.status = MissionStatus.CLOSED
        successful = [
            item.action_type.value for item in mission.actions if item.status in {"executed", "simulated"}
        ]
        rejected = [
            rec.action_type.value for rec in mission.recommendations if rec.status == "rejected"
        ]
        top = mission.hypotheses[0].title if mission.hypotheses else "No hypothesis recorded"
        memory = MemoryRecord(
            mission_id=mission.id,
            scenario=mission.scenario,
            summary=f"{mission.title}. Leading hypothesis: {top}. Actions: {', '.join(successful) or 'none'}.",
            successful_actions=successful,
            rejected_actions=rejected,
            heuristics=self._derive_heuristics(mission),
        )
        self.repository.save_memory(memory)
        mission.memory_id = memory.id
        self.openclaw.publish("memory", mission, "Curate reusable incident memory and replay heuristics")
        self._event(mission, "memory-curator", "mission.closed", "Incident memory and replay artifacts captured", {"memory_id": memory.id})
        mission.communications = self.communications.draft(mission)
        mission.updated_at = utc_now()
        self.repository.save(mission)
        return mission

    def _memory_bias(self) -> dict[str, float]:
        aggregate: dict[str, list[float]] = defaultdict(list)
        for memory in self.repository.list_memories():
            for action in memory.successful_actions:
                aggregate[action].append(1.0)
            for action in memory.rejected_actions:
                aggregate[action].append(-0.4)
        return {
            action: sum(values) / len(values) for action, values in aggregate.items() if values
        }

    @staticmethod
    def _derive_heuristics(mission: MissionState) -> list[str]:
        heuristics = []
        if any(signal.dimensions.get("retry_pattern") == "storm" for signal in mission.signals):
            heuristics.append("When queue growth coincides with regional errors, test retry damping before adding capacity.")
        if any(action.action_type.value == "bounded_traffic_shift" for action in mission.actions):
            heuristics.append("Use a 10% canary traffic shift to validate provider causality before broader failover.")
        if not heuristics:
            heuristics.append("Prefer reversible actions with explicit TTLs and recorded rollback state.")
        return heuristics

    @staticmethod
    def _default_control_state() -> dict:
        return {
            "feature_flags": {"degraded_mode": False},
            "queue_retry": {"retry_multiplier": 1.0, "jitter_ms": 100},
            "throttles": {},
            "traffic_shifts": {},
        }

    @staticmethod
    def _event(mission: MissionState, actor: str, event_type: str, message: str, data: dict | None = None) -> None:
        mission.events.append(Event(actor=actor, event_type=event_type, message=message, data=data or {}))

    def _require(self, mission_id: str) -> MissionState:
        mission = self.repository.get(mission_id)
        if not mission:
            raise KeyError(mission_id)
        return mission

    @staticmethod
    def _recommendation(mission: MissionState, recommendation_id: str):
        for recommendation in mission.recommendations:
            if recommendation.id == recommendation_id:
                return recommendation
        raise KeyError(recommendation_id)
