from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from graph.workflow import (
    current_state,
    new_execution,
    resume_execution,
)
from services.mock_store import MockStore
from skills.duplicate_detection import detect_duplicate
from skills.historical_intelligence import historical_intelligence

app = FastAPI(
    title="RC TNT LangGraph POC",
    version="0.1.0",
)
store = MockStore()

UI = (
    Path(__file__).resolve().parents[1]
    / "frontend"
    / "index.html"
)


class ResumeRequest(BaseModel):
    approved: bool


class IncidentSkillRequest(BaseModel):
    incident_id: str


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): _jsonable(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "value"):
        return _jsonable(value.value)
    return value


def _result_payload(execution_id: str, result: dict) -> dict:
    interrupt_payload = None

    if "__interrupt__" in result and result["__interrupt__"]:
        first = result["__interrupt__"][0]
        interrupt_payload = _jsonable(first)

    state = current_state(execution_id)

    return {
        "execution_id": execution_id,
        "state": _jsonable(state),
        "interrupt": interrupt_payload,
    }


@app.get("/", response_class=HTMLResponse)
def home():
    return UI.read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "engine": "langgraph",
        "storage": "xlsx",
    }


@app.get("/api/alarms")
def alarms():
    return store.list_alarms()


@app.get("/api/incidents")
def incidents():
    return store.incidents()


@app.post("/api/reset")
def reset():
    store.reset()
    return {"status": "reset"}


@app.post("/api/workflows/rc-tnt/{alarm_id}")
def start_workflow(alarm_id: str):
    try:
        execution_id, result = new_execution(alarm_id)
        return _result_payload(execution_id, result)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Alarm not found",
        )


@app.post("/api/workflows/{execution_id}/resume")
def resume_workflow(execution_id: str, req: ResumeRequest):
    try:
        result = resume_execution(
            execution_id,
            req.approved,
        )
        return _result_payload(execution_id, result)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.post("/api/skills/duplicate")
def duplicate(req: IncidentSkillRequest):
    inc = next(
        (
            x for x in store.incidents()
            if x["number"] == req.incident_id
        ),
        None,
    )

    if not inc:
        raise HTTPException(
            status_code=404,
            detail="INC not found",
        )

    pseudo_alarm = {
        "IG": inc["IG"],
        "PS": inc["PS"],
        "equipment": inc["equipment"],
        "description": inc["description"],
        "alarm": inc["short_description"],
    }

    return detect_duplicate(store, pseudo_alarm)


@app.post("/api/skills/history")
def history(req: IncidentSkillRequest):
    inc = next(
        (
            x for x in store.incidents()
            if x["number"] == req.incident_id
        ),
        None,
    )

    if not inc:
        raise HTTPException(
            status_code=404,
            detail="INC not found",
        )

    pseudo_alarm = {
        "IG": inc["IG"],
        "PS": inc["PS"],
        "equipment": inc["equipment"],
        "description": inc["description"],
        "alarm": inc["short_description"],
    }

    return historical_intelligence(
        store,
        pseudo_alarm,
    )
