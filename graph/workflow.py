from __future__ import annotations

import uuid
from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agents.core import (
    decide_veracity,
    make_action_plan,
    prequalify,
    propose_resolution,
)
from graph.state import RCTNTState
from policies.action_policy import evaluate_policy
from services.mock_store import MockStore
from skills.duplicate_detection import detect_duplicate
from skills.historical_intelligence import historical_intelligence

store = MockStore()


def _trace(state: RCTNTState, node: str, payload: dict | None = None) -> list[dict]:
    trace = list(state.get("trace", []))
    trace.append({"node": node, "payload": payload or {}})
    return trace


def receive_alarm(state: RCTNTState) -> dict:
    alarm = store.get_alarm(state["alarm_id"])
    return {
        "alarm": alarm,
        "status": "RUNNING",
        "trace": _trace(state, "receive_alarm", alarm),
    }


def ack_alarm(state: RCTNTState) -> dict:
    alarm = store.update_alarm(
        state["alarm_id"],
        assigned_to="agent IA",
        ack="yes",
    )
    return {
        "alarm": alarm,
        "trace": _trace(state, "ack_alarm", {"assigned_to": "agent IA"}),
    }


def prequalification_agent(state: RCTNTState) -> dict:
    out = prequalify(state["alarm"])
    return {
        "prequalification": out,
        "trace": _trace(state, "prequalification_agent", out),
    }


def duplicate_skill(state: RCTNTState) -> dict:
    out = detect_duplicate(store, state["alarm"])
    updates = {
        "duplicate": out,
        "trace": _trace(state, "duplicate_skill", out),
    }

    if out["decision"] == "DUPLICATE":
        updates["incident_id"] = out["candidate"]
        updates["status"] = "DUPLICATE_ATTACHED"

    return updates


def route_duplicate(state: RCTNTState) -> Literal["duplicate", "new"]:
    return "duplicate" if state["duplicate"]["decision"] == "DUPLICATE" else "new"


def duplicate_end(state: RCTNTState) -> dict:
    return {
        "trace": _trace(
            state,
            "attach_existing_incident",
            {"incident_id": state["incident_id"]},
        )
    }


def enrich_context(state: RCTNTState) -> dict:
    alarm = state["alarm"]
    context = {
        "servicenow": {
            "open_incidents_for_ig": [
                x["number"]
                for x in store.incidents()
                if x.get("IG") == alarm["IG"] and x.get("state") != "Closed"
            ]
        },
        "dataminer": alarm,
        "dma": store.dma_rules(alarm["alarm"]),
        "diabolo": store.active_interventions(
            alarm["site"],
            alarm["equipment"],
        ),
    }

    return {
        "context": context,
        "trace": _trace(state, "context_enrichment", context),
    }


def veracity_agent(state: RCTNTState) -> dict:
    out = decide_veracity(
        state["alarm"],
        state["context"]["diabolo"],
    )
    return {
        "veracity": out,
        "trace": _trace(state, "veracity_agent", out),
    }


def route_veracity(state: RCTNTState) -> Literal["explained", "valid"]:
    decision = state["veracity"]["decision"]
    if decision in {"FALSE_ALARM", "EXPLAINED_BY_INTERVENTION"}:
        return "explained"
    return "valid"


def explained_alarm_end(state: RCTNTState) -> dict:
    return {
        "status": "NO_INCIDENT_REQUIRED",
        "trace": _trace(state, "explained_alarm_end"),
    }


def create_incident(state: RCTNTState) -> dict:
    a = state["alarm"]

    payload = {
        "IG": a["IG"],
        "PS": a["PS"],
        "short_description": f'{a["alarm"]} - {a["equipment"]}',
        "description": (
            f'{a["description"]}. '
            f'IG={a["IG"]}, PS={a["PS"]}, site={a["site"]}.'
        ),
        "state": "In Progress",
        "resolution_notes": "",
        "equipment": a["equipment"],
        "site": a["site"],
        "age_days": 0,
    }

    inc = store.create_incident(payload)

    return {
        "incident_id": inc["number"],
        "trace": _trace(state, "create_incident", inc),
    }


def history_skill(state: RCTNTState) -> dict:
    out = historical_intelligence(store, state["alarm"])
    return {
        "history": out["items"],
        "recurrence": out["recurrence"],
        "trace": _trace(state, "historical_intelligence_skill", out),
    }


def resolution_agent(state: RCTNTState) -> dict:
    resolution = propose_resolution(
        state.get("recurrence", False),
        state["context"]["dma"],
    )
    return {
        "resolution": resolution,
        "trace": _trace(state, "resolution_agent", resolution),
    }


def action_planner(state: RCTNTState) -> dict:
    plan = make_action_plan(state["resolution"])
    return {
        "action_plan": plan,
        "trace": _trace(state, "action_planner", plan),
    }


def policy_engine(state: RCTNTState) -> dict:
    policy = evaluate_policy(state["action_plan"])
    return {
        "policy": policy,
        "trace": _trace(state, "policy_engine", policy),
    }


def route_policy(state: RCTNTState) -> Literal["auto", "hitl"]:
    return (
        "hitl"
        if state["policy"]["decision"] == "HITL_REQUIRED"
        else "auto"
    )


def human_approval(state: RCTNTState) -> Command[Literal["execute_action", "rejected_end"]]:
    decision = interrupt({
        "type": "human_approval",
        "incident_id": state.get("incident_id"),
        "alarm_id": state["alarm_id"],
        "question": "Autoriser cette action ?",
        "action_plan": state["action_plan"],
        "policy": state["policy"],
        "material": state.get("material"),
    })

    approved = bool(decision)
    return Command(
        update={
            "human_decision": "APPROVED" if approved else "REJECTED",
            "trace": _trace(
                state,
                "human_approval",
                {"approved": approved},
            ),
        },
        goto="execute_action" if approved else "rejected_end",
    )


def rejected_end(state: RCTNTState) -> dict:
    return {
        "status": "REJECTED_BY_HUMAN",
        "trace": _trace(state, "rejected_end"),
    }


def execute_action(state: RCTNTState) -> dict:
    action = state["action_plan"]["action"]
    alarm = state["alarm"]

    if action == "REBOOT_TRANSMITTER":
        resulting_status = (
            "Active"
            if alarm.get("scenario") == "fail"
            else "Cleared"
        )
        alarm = store.update_alarm(
            state["alarm_id"],
            last_action="REBOOT",
            status=resulting_status,
        )

    elif action == "REPLACE_EQUIPMENT":
        alarm = store.update_alarm(
            state["alarm_id"],
            last_action="REPLACE_EQUIPMENT",
            status="Cleared",
        )

    else:
        alarm = store.update_alarm(
            state["alarm_id"],
            last_action="MANUAL_DIAGNOSIS",
        )

    result = {
        "action": action,
        "alarm_status": alarm["status"],
    }

    return {
        "alarm": alarm,
        "action_result": result,
        "trace": _trace(state, "execute_action", result),
    }


def check_alarm(state: RCTNTState) -> dict:
    alarm = store.get_alarm(state["alarm_id"])
    resolved = alarm["status"] == "Cleared"

    return {
        "alarm": alarm,
        "alarm_resolved": resolved,
        "trace": _trace(
            state,
            "check_alarm_after_delay",
            {"resolved": resolved},
        ),
    }


def route_resolved(state: RCTNTState) -> Literal["resolved", "fallback"]:
    return "resolved" if state["alarm_resolved"] else "fallback"


def material_recommendation(state: RCTNTState) -> dict:
    material = store.material_for(state["alarm"]["equipment"])

    resolution = {
        "action": "REPLACE_EQUIPMENT",
        "reason": "Le reboot n'a pas rétabli l'alarme.",
    }

    plan = make_action_plan(resolution)
    policy = evaluate_policy(plan)

    return {
        "material": material,
        "resolution": resolution,
        "action_plan": plan,
        "policy": policy,
        "trace": _trace(
            state,
            "material_recommendation",
            material or {"stock": "UNKNOWN"},
        ),
    }


def close_incident(state: RCTNTState) -> dict:
    note = (
        f'Résolu par {state["action_plan"]["action"]}. '
        f'Retour à la normale confirmé.'
    )

    if state.get("incident_id"):
        store.close_incident(state["incident_id"], note)

    closure = {"resolution_note": note}

    return {
        "closure": closure,
        "status": "CLOSED",
        "trace": _trace(state, "close_incident", closure),
    }


def build_graph():
    builder = StateGraph(RCTNTState)

    builder.add_node("receive_alarm", receive_alarm)
    builder.add_node("ack_alarm", ack_alarm)
    builder.add_node("prequalification_agent", prequalification_agent)
    builder.add_node("duplicate_skill", duplicate_skill)
    builder.add_node("duplicate_end", duplicate_end)
    builder.add_node("enrich_context", enrich_context)
    builder.add_node("veracity_agent", veracity_agent)
    builder.add_node("explained_alarm_end", explained_alarm_end)
    builder.add_node("create_incident", create_incident)
    builder.add_node("history_skill", history_skill)
    builder.add_node("resolution_agent", resolution_agent)
    builder.add_node("action_planner", action_planner)
    builder.add_node("policy_engine", policy_engine)
    builder.add_node("human_approval", human_approval)
    builder.add_node("rejected_end", rejected_end)
    builder.add_node("execute_action", execute_action)
    builder.add_node("check_alarm", check_alarm)
    builder.add_node("material_recommendation", material_recommendation)
    builder.add_node("close_incident", close_incident)

    builder.add_edge(START, "receive_alarm")
    builder.add_edge("receive_alarm", "ack_alarm")
    builder.add_edge("ack_alarm", "prequalification_agent")
    builder.add_edge("prequalification_agent", "duplicate_skill")

    builder.add_conditional_edges(
        "duplicate_skill",
        route_duplicate,
        {
            "duplicate": "duplicate_end",
            "new": "enrich_context",
        },
    )
    builder.add_edge("duplicate_end", END)

    builder.add_edge("enrich_context", "veracity_agent")
    builder.add_conditional_edges(
        "veracity_agent",
        route_veracity,
        {
            "explained": "explained_alarm_end",
            "valid": "create_incident",
        },
    )
    builder.add_edge("explained_alarm_end", END)

    builder.add_edge("create_incident", "history_skill")
    builder.add_edge("history_skill", "resolution_agent")
    builder.add_edge("resolution_agent", "action_planner")
    builder.add_edge("action_planner", "policy_engine")

    builder.add_conditional_edges(
        "policy_engine",
        route_policy,
        {
            "auto": "execute_action",
            "hitl": "human_approval",
        },
    )

    builder.add_edge("rejected_end", END)
    builder.add_edge("execute_action", "check_alarm")

    builder.add_conditional_edges(
        "check_alarm",
        route_resolved,
        {
            "resolved": "close_incident",
            "fallback": "material_recommendation",
        },
    )

    builder.add_edge("material_recommendation", "human_approval")
    builder.add_edge("close_incident", END)

    return builder.compile(checkpointer=InMemorySaver())


graph = build_graph()


def new_execution(alarm_id: str) -> tuple[str, dict]:
    execution_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": execution_id,
        }
    }

    initial: RCTNTState = {
        "execution_id": execution_id,
        "alarm_id": alarm_id,
        "status": "NEW",
        "incident_id": None,
        "human_decision": None,
        "trace": [],
    }

    result = graph.invoke(initial, config=config)
    return execution_id, result


def resume_execution(execution_id: str, approved: bool) -> dict:
    config = {
        "configurable": {
            "thread_id": execution_id,
        }
    }
    return graph.invoke(
        Command(resume=approved),
        config=config,
    )


def current_state(execution_id: str) -> dict:
    config = {
        "configurable": {
            "thread_id": execution_id,
        }
    }
    snapshot = graph.get_state(config)
    return dict(snapshot.values)
