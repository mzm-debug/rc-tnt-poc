from __future__ import annotations
from typing import Any, Literal, TypedDict


class RCTNTState(TypedDict, total=False):
    execution_id: str
    alarm_id: str
    alarm: dict[str, Any]

    prequalification: dict[str, Any]
    duplicate: dict[str, Any]
    context: dict[str, Any]
    veracity: dict[str, Any]

    incident_id: str | None
    history: list[dict[str, Any]]
    recurrence: bool

    resolution: dict[str, Any]
    action_plan: dict[str, Any]
    policy: dict[str, Any]
    human_decision: Literal["APPROVED", "REJECTED"] | None

    action_result: dict[str, Any]
    alarm_resolved: bool
    material: dict[str, Any] | None
    closure: dict[str, Any]

    status: str
    trace: list[dict[str, Any]]
