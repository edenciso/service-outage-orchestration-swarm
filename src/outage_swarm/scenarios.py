from __future__ import annotations

from copy import deepcopy

from .models import Edge, Node, Signal, SignalKind


BASE_NODES = [
    Node(id="web", label="Web Frontend", kind="service", criticality=0.9),
    Node(id="api", label="Public API", kind="service", criticality=1.0),
    Node(id="worker", label="Async Worker", kind="service", criticality=0.8),
    Node(id="queue", label="Work Queue", kind="data", criticality=0.8),
    Node(id="db", label="Primary Database", kind="data", criticality=1.0),
    Node(id="cdn", label="Edge CDN", kind="external_provider", provider="GlobalEdge", criticality=0.9),
    Node(id="cloud_east", label="Cloud us-east", kind="region", provider="NimbusCloud", region="us-east", criticality=1.0),
    Node(id="cloud_west", label="Cloud us-west", kind="region", provider="NimbusCloud", region="us-west", criticality=0.8),
    Node(id="ai_provider", label="AI Provider", kind="external_provider", provider="ModelWorks", criticality=0.7),
    Node(id="mobile_carrier", label="Mobile Carrier Cohort", kind="customer_cohort", provider="MetroCell", criticality=0.6),
]

BASE_EDGES = [
    Edge(source="web", target="cdn"),
    Edge(source="web", target="api"),
    Edge(source="api", target="cloud_east"),
    Edge(source="api", target="db"),
    Edge(source="api", target="ai_provider"),
    Edge(source="worker", target="queue"),
    Edge(source="worker", target="db"),
    Edge(source="worker", target="ai_provider"),
    Edge(source="queue", target="cloud_east"),
    Edge(source="db", target="cloud_east"),
    Edge(source="mobile_carrier", target="cdn"),
]

SCENARIOS = {
    "cdn-edge-degradation": {
        "title": "Elevated mobile errors through degraded CDN edge path",
        "severity": "SEV-1",
        "description": "External edge degradation creates carrier-concentrated customer pain.",
        "signals": [
            Signal(source="otel", node_id="web", kind=SignalKind.ERROR_RATE, value=0.22, baseline=0.01, trust=0.98, summary="Web 5xx rate elevated to 22%", dimensions={"region": "global"}),
            Signal(source="rum", node_id="mobile_carrier", kind=SignalKind.CUSTOMER_PAIN, value=0.74, baseline=0.05, trust=0.92, summary="Mobile cohort page failures concentrated on MetroCell", dimensions={"carrier": "MetroCell"}),
            Signal(source="cdn-status", node_id="cdn", kind=SignalKind.EXTERNAL_STATUS, value=0.81, baseline=0.0, trust=0.78, summary="CDN reports elevated origin fetch errors", dimensions={"provider": "GlobalEdge"}),
            Signal(source="synthetic", node_id="api", kind=SignalKind.LATENCY, value=0.46, baseline=0.12, trust=0.88, summary="API origin remains partially healthy but latency is rising"),
        ],
    },
    "cloud-region-retry-storm": {
        "title": "Partial cloud region failure amplified by queue retry storm",
        "severity": "SEV-1",
        "description": "A degraded regional substrate causes retries, queue growth, and API saturation.",
        "signals": [
            Signal(source="cloudwatch", node_id="cloud_east", kind=SignalKind.SATURATION, value=0.91, baseline=0.35, trust=0.97, summary="Compute saturation and instance impairment in us-east", dimensions={"region": "us-east"}),
            Signal(source="queue-metrics", node_id="queue", kind=SignalKind.QUEUE_DEPTH, value=0.88, baseline=0.18, trust=0.99, summary="Queue depth and retry attempts increasing exponentially", dimensions={"retry_pattern": "storm"}),
            Signal(source="otel", node_id="api", kind=SignalKind.ERROR_RATE, value=0.34, baseline=0.01, trust=0.99, summary="API timeout and 503 rate elevated"),
            Signal(source="otel", node_id="worker", kind=SignalKind.LATENCY, value=0.83, baseline=0.20, trust=0.97, summary="Worker completion latency exceeds SLO"),
            Signal(source="provider-status", node_id="cloud_east", kind=SignalKind.EXTERNAL_STATUS, value=0.64, baseline=0.0, trust=0.72, summary="Cloud provider investigating elevated errors in us-east"),
        ],
    },
    "ai-provider-latency": {
        "title": "AI provider latency cascading into application queues",
        "severity": "SEV-2",
        "description": "Third-party model latency creates queue backlog and degraded AI features.",
        "signals": [
            Signal(source="provider-probe", node_id="ai_provider", kind=SignalKind.LATENCY, value=0.93, baseline=0.22, trust=0.94, summary="AI provider p95 latency exceeds 25 seconds"),
            Signal(source="queue-metrics", node_id="queue", kind=SignalKind.QUEUE_DEPTH, value=0.69, baseline=0.18, trust=0.98, summary="AI job queue depth rising"),
            Signal(source="otel", node_id="worker", kind=SignalKind.SATURATION, value=0.72, baseline=0.32, trust=0.97, summary="Worker concurrency fully utilized"),
            Signal(source="support", node_id="web", kind=SignalKind.CUSTOMER_PAIN, value=0.48, baseline=0.04, trust=0.70, summary="Customers report AI generation timeouts"),
            Signal(source="provider-status", node_id="ai_provider", kind=SignalKind.EXTERNAL_STATUS, value=0.55, baseline=0.0, trust=0.62, summary="Provider status page notes degraded performance"),
        ],
    },
}


def list_scenarios() -> list[dict]:
    return [
        {"id": key, "title": value["title"], "severity": value["severity"], "description": value["description"]}
        for key, value in SCENARIOS.items()
    ]


def get_scenario(scenario_id: str) -> dict:
    if scenario_id not in SCENARIOS:
        raise KeyError(scenario_id)
    return deepcopy(SCENARIOS[scenario_id])


def graph() -> tuple[list[Node], list[Edge]]:
    return deepcopy(BASE_NODES), deepcopy(BASE_EDGES)
