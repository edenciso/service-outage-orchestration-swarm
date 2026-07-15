from __future__ import annotations

import argparse
import json

from .config import Settings
from .orchestrator import MissionConductor
from .repository import MissionRepository
from .scenarios import list_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(prog="outage-swarm")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run a synthetic incident through the full control loop")
    demo.add_argument("scenario", nargs="?", default="cloud-region-retry-storm")
    sub.add_parser("scenarios", help="List synthetic scenarios")
    args = parser.parse_args()

    if args.command == "scenarios":
        print(json.dumps(list_scenarios(), indent=2))
        return

    settings = Settings.from_env()
    conductor = MissionConductor(MissionRepository(settings.db_path), settings)
    mission = conductor.create_from_scenario(args.scenario)
    print(f"Mission: {mission.id} | {mission.title}")
    print("\nHypotheses")
    for hypothesis in mission.hypotheses:
        print(f"  {hypothesis.confidence:.0%} | {hypothesis.title}")
    print("\nRecommendations")
    for recommendation in mission.recommendations:
        print(
            f"  #{recommendation.rank} {recommendation.expected_reward:.3f} | "
            f"{recommendation.title} [{recommendation.policy_decision.value}]"
        )


if __name__ == "__main__":
    main()
