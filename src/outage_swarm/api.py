from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .models import ApprovalRequest, ExecutionRequest, ManualMissionRequest, MissionState, Signal, SignalKind
from .orchestrator import MissionConductor
from .repository import MissionRepository
from .scenarios import list_scenarios

settings = Settings.from_env()
repository = MissionRepository(settings.db_path)
conductor = MissionConductor(repository, settings)

app = FastAPI(
    title="Service Outage Choreography Swarm",
    version="1.0.0",
    description="Recommendation-first hybrid agentic swarm MVP",
)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "dry_run": settings.dry_run,
        "openclaw_mode": settings.openclaw_mode,
    }


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    return list_scenarios()


@app.get("/api/missions", response_model=list[MissionState])
def missions() -> list[MissionState]:
    return repository.list()


@app.post("/api/missions/scenario/{scenario_id}", response_model=MissionState)
def create_scenario(scenario_id: str) -> MissionState:
    try:
        return conductor.create_from_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown scenario")


@app.post("/api/intake/alert", response_model=MissionState)
def intake_alert(request: ManualMissionRequest) -> MissionState:
    """Webhook-shaped mission intake alias for alert managers."""
    return conductor.create_manual(request.title, request.severity, request.signals)


@app.post("/api/missions/manual", response_model=MissionState)
def create_manual(request: ManualMissionRequest) -> MissionState:
    return conductor.create_manual(request.title, request.severity, request.signals)


@app.get("/api/missions/{mission_id}", response_model=MissionState)
def mission(mission_id: str) -> MissionState:
    item = repository.get(mission_id)
    if not item:
        raise HTTPException(status_code=404, detail="Mission not found")
    return item


@app.post("/api/missions/{mission_id}/signals", response_model=MissionState)
def ingest_signal(mission_id: str, signal: Signal) -> MissionState:
    try:
        return conductor.add_signal(mission_id, signal)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission not found")


@app.post("/api/missions/{mission_id}/provider-status", response_model=MissionState)
def ingest_provider_status(mission_id: str, signal: Signal) -> MissionState:
    if signal.kind != SignalKind.EXTERNAL_STATUS:
        raise HTTPException(status_code=422, detail="Provider-status signals must use kind=external_status")
    try:
        return conductor.add_signal(mission_id, signal)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission not found")


@app.post("/api/missions/{mission_id}/analyze", response_model=MissionState)
def analyze(mission_id: str) -> MissionState:
    try:
        return conductor.analyze(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission not found")


@app.post("/api/missions/{mission_id}/recommendations/{recommendation_id}/approve", response_model=MissionState)
def approve(
    mission_id: str,
    recommendation_id: str,
    request: ApprovalRequest,
) -> MissionState:
    try:
        return conductor.approve(
            mission_id,
            recommendation_id,
            request.actor,
            request.decision,
            request.reason,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission or recommendation not found")


@app.post("/api/missions/{mission_id}/recommendations/{recommendation_id}/execute", response_model=MissionState)
def execute(
    mission_id: str,
    recommendation_id: str,
    request: ExecutionRequest,
) -> MissionState:
    try:
        return conductor.execute(mission_id, recommendation_id, request.actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission or recommendation not found")
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/missions/{mission_id}/close", response_model=MissionState)
def close(mission_id: str) -> MissionState:
    try:
        return conductor.close(mission_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission not found")


@app.get("/api/missions/{mission_id}/replay")
def replay(mission_id: str) -> JSONResponse:
    try:
        return JSONResponse(repository.export_replay(mission_id))
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission not found")
