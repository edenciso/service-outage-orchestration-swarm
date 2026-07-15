from outage_swarm.field import FieldSubstrate
from outage_swarm.models import Edge, Signal, SignalKind


def test_field_deposits_and_diffuses_failure():
    substrate = FieldSubstrate()
    snapshot = substrate.build(
        ["provider", "api"],
        [Edge(source="api", target="provider")],
        [Signal(source="probe", node_id="provider", kind=SignalKind.EXTERNAL_STATUS, value=.9, trust=.9, summary="provider degraded")],
    )
    assert snapshot.channels["provider"]["causal_suspicion"] > 0.7
    assert snapshot.channels["api"]["causal_suspicion"] > 0.0
