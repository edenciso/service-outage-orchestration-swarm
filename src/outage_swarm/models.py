from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class MissionStatus(str, Enum):
    ACTIVE = "active"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SignalKind(str, Enum):
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    SATURATION = "saturation"
    QUEUE_DEPTH = "queue_depth"
    EXTERNAL_STATUS = "external_status"
    CUSTOMER_PAIN = "customer_pain"
    MANUAL_OBSERVATION = "manual_observation"


class ActionType(str, Enum):
    FEATURE_FLAG_TOGGLE = "feature_flag_toggle"
    QUEUE_RETRY_TUNING = "queue_retry_tuning"
    SERVICE_THROTTLE = "service_throttle_adjustment"
    BOUNDED_TRAFFIC_SHIFT = "bounded_traffic_shift"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    OBSERVE_ONLY = "observe_only"


class Node(BaseModel):
    id: str
    label: str
    kind: str
    provider: str | None = None
    region: str | None = None
    criticality: float = 0.5


class Edge(BaseModel):
    source: str
    target: str
    relation: str = "depends_on"
    weight: float = 1.0


class Signal(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sig"))
    timestamp: str = Field(default_factory=utc_now)
    source: str
    node_id: str
    kind: SignalKind
    value: float
    baseline: float = 0.0
    trust: float = Field(default=0.8, ge=0.0, le=1.0)
    summary: str
    dimensions: dict[str, str] = Field(default_factory=dict)


class Evidence(BaseModel):
    signal_id: str
    description: str
    contribution: float


class Hypothesis(BaseModel):
    id: str = Field(default_factory=lambda: new_id("hyp"))
    title: str
    failure_domain: str
    confidence: float = Field(ge=0.0, le=1.0)
    blast_radius: float = Field(ge=0.0, le=1.0)
    affected_nodes: list[str]
    evidence: list[Evidence]
    explanation: str


class FieldSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: new_id("fld"))
    timestamp: str = Field(default_factory=utc_now)
    channels: dict[str, dict[str, float]]


class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rec"))
    rank: int = 0
    worker: str
    action_type: ActionType
    target: str
    title: str
    rationale: str
    parameters: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    expected_impact: float = Field(ge=0.0, le=1.0)
    expected_reward: float
    risk_score: float = Field(ge=0.0, le=1.0)
    policy_class: str
    policy_decision: PolicyDecision
    rollback_plan: str
    top_factors: list[str]
    field_snapshot_id: str
    status: str = "proposed"


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: new_id("apr"))
    recommendation_id: str
    actor: str
    decision: str
    reason: str = ""
    timestamp: str = Field(default_factory=utc_now)


class ActionRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("act"))
    recommendation_id: str
    action_type: ActionType
    target: str
    parameters: dict[str, Any]
    actor: str
    dry_run: bool
    status: str
    result: dict[str, Any]
    rollback_token: str
    timestamp: str = Field(default_factory=utc_now)


class Event(BaseModel):
    id: str = Field(default_factory=lambda: new_id("evt"))
    timestamp: str = Field(default_factory=utc_now)
    actor: str
    event_type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class Communications(BaseModel):
    internal_summary: str = ""
    status_page_draft: str = ""
    executive_update: str = ""
    updated_at: str = Field(default_factory=utc_now)


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem"))
    mission_id: str
    scenario: str
    summary: str
    successful_actions: list[str]
    rejected_actions: list[str]
    heuristics: list[str]
    created_at: str = Field(default_factory=utc_now)


class MissionState(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mis"))
    title: str
    scenario: str = "manual"
    severity: str = "SEV-2"
    status: MissionStatus = MissionStatus.ACTIVE
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    nodes: list[Node]
    edges: list[Edge]
    signals: list[Signal] = Field(default_factory=list)
    field_snapshots: list[FieldSnapshot] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    approvals: list[Approval] = Field(default_factory=list)
    actions: list[ActionRecord] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    communications: Communications = Field(default_factory=Communications)
    control_state: dict[str, Any] = Field(default_factory=dict)
    memory_id: str | None = None


class ManualMissionRequest(BaseModel):
    title: str
    severity: str = "SEV-2"
    signals: list[Signal] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    actor: str = "incident-commander"
    decision: str = "approved"
    reason: str = "Approved in MVP operator console"


class ExecutionRequest(BaseModel):
    actor: str = "execution-broker"
