from __future__ import annotations

import json
from pathlib import Path

from .models import MissionState


class OpenClawMissionBridge:
    """Filesystem handoff seam for OpenClaw agent workspaces.

    The local deterministic orchestrator is the executable default. In OpenClaw mode,
    mission packets can be deposited into isolated agent workspaces, where workspace
    skills constrain role behavior and tool usage.
    """

    def __init__(self, workspace_root: Path, enabled: bool = False):
        self.workspace_root = workspace_root
        self.enabled = enabled

    def publish(self, agent: str, mission: MissionState, task: str) -> Path | None:
        if not self.enabled:
            return None
        inbox = self.workspace_root / agent / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        path = inbox / f"{mission.id}.json"
        path.write_text(
            json.dumps(
                {"task": task, "mission": mission.model_dump(mode="json")}, indent=2
            ),
            encoding="utf-8",
        )
        return path
