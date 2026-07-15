from outage_swarm.models import ActionType, PolicyDecision


def test_scenario_produces_ranked_hypotheses_and_all_action_types(conductor):
    mission = conductor.create_from_scenario("cloud-region-retry-storm")
    assert len(mission.hypotheses) == 3
    assert mission.hypotheses[0].confidence > 0.6
    assert len(mission.recommendations) >= 4
    action_types = {item.action_type for item in mission.recommendations}
    assert ActionType.FEATURE_FLAG_TOGGLE in action_types
    assert ActionType.QUEUE_RETRY_TUNING in action_types
    assert ActionType.SERVICE_THROTTLE in action_types
    assert ActionType.BOUNDED_TRAFFIC_SHIFT in action_types
    assert all(item.rollback_plan for item in mission.recommendations)
    assert all(item.field_snapshot_id for item in mission.recommendations)


def test_policy_gate_requires_approval_for_traffic_shift(conductor):
    mission = conductor.create_from_scenario("cdn-edge-degradation")
    rec = next(item for item in mission.recommendations if item.action_type == ActionType.BOUNDED_TRAFFIC_SHIFT)
    assert rec.policy_decision == PolicyDecision.REQUIRE_APPROVAL
    try:
        conductor.execute(mission.id, rec.id, "broker")
        assert False, "execution should have been blocked"
    except PermissionError:
        pass
    conductor.approve(mission.id, rec.id, "incident-commander", "approved", "bounded canary")
    mission = conductor.execute(mission.id, rec.id, "broker")
    assert len(mission.actions) == 1
    assert mission.actions[0].dry_run is True
    assert mission.actions[0].rollback_token


def test_close_captures_memory_and_replay(conductor):
    mission = conductor.create_from_scenario("ai-provider-latency")
    auto = next(item for item in mission.recommendations if item.policy_decision == PolicyDecision.ALLOW)
    mission = conductor.execute(mission.id, auto.id, "broker")
    mission = conductor.close(mission.id)
    assert mission.memory_id is not None
    replay = conductor.repository.export_replay(mission.id)
    assert replay["schema_version"] == "1.0"
    assert replay["evaluation"]["executed_actions"] == 1
