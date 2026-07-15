from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    dry_run: bool
    auto_execute: bool
    openclaw_mode: str
    openclaw_workspace: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("OUTAGE_SWARM_DB", "./data/outage_swarm.db")),
            dry_run=_bool("OUTAGE_SWARM_DRY_RUN", True),
            auto_execute=_bool("OUTAGE_SWARM_AUTO_EXECUTE", False),
            openclaw_mode=os.getenv("OUTAGE_SWARM_OPENCLAW_MODE", "disabled"),
            openclaw_workspace=Path(
                os.getenv("OUTAGE_SWARM_OPENCLAW_WORKSPACE", "./openclaw/workspaces")
            ),
        )
