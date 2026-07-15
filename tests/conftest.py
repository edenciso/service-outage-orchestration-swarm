from __future__ import annotations

from pathlib import Path

import pytest

from outage_swarm.config import Settings
from outage_swarm.orchestrator import MissionConductor
from outage_swarm.repository import MissionRepository


@pytest.fixture
def conductor(tmp_path: Path) -> MissionConductor:
    settings = Settings(
        db_path=tmp_path / "test.db",
        dry_run=True,
        auto_execute=False,
        openclaw_mode="disabled",
        openclaw_workspace=tmp_path / "openclaw",
    )
    return MissionConductor(MissionRepository(settings.db_path), settings)
