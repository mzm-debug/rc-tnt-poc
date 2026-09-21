import uuid

from langgraph.types import Command

from graph.workflow import graph, store


def cfg():
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        }
    }


def initial(alarm_id: str):
    return {
        "execution_id": str(uuid.uuid4()),
        "alarm_id": alarm_id,
        "status": "NEW",
        "incident_id": None,
        "human_decision": None,
        "trace": [],
    }


def setup_function():
    store.reset()


def test_new_alarm_closes():
    result = graph.invoke(
        initial("AL-NEW-001"),
        config=cfg(),
    )
    assert result["status"] == "CLOSED"
    assert result["alarm_resolved"] is True


def test_duplicate_stops():
    before = len(store.incidents())
    result = graph.invoke(
        initial("AL-DUP-001"),
        config=cfg(),
    )
    after = len(store.incidents())
    assert result["status"] == "DUPLICATE_ATTACHED"
    assert result["incident_id"] == "INC0001001"
    assert before == after


def test_false_alarm_no_incident():
    before = len(store.incidents())
    result = graph.invoke(
        initial("AL-FALSE-001"),
        config=cfg(),
    )
    after = len(store.incidents())
    assert result["status"] == "NO_INCIDENT_REQUIRED"
    assert before == after


def test_tp_can_be_real_failure():
    result = graph.invoke(
        initial("AL-TP-REAL"),
        config=cfg(),
    )
    assert result["veracity"]["decision"] == "REAL_FAILURE_DURING_INTERVENTION"


def test_recurrence_interrupt_and_resume():
    config = cfg()
    result = graph.invoke(
        initial("AL-REC-001"),
        config=config,
    )
    assert "__interrupt__" in result

    final = graph.invoke(
        Command(resume=True),
        config=config,
    )
    assert final["status"] == "CLOSED"
    assert final["human_decision"] == "APPROVED"


def test_failed_reboot_falls_back_to_material_and_hitl():
    config = cfg()
    result = graph.invoke(
        initial("AL-FAIL-001"),
        config=config,
    )
    assert "__interrupt__" in result

    state = graph.get_state(config).values
    assert state["action_plan"]["action"] == "REPLACE_EQUIPMENT"
    assert state["material"]["stock"] == "AVAILABLE"

    final = graph.invoke(
        Command(resume=True),
        config=config,
    )
    assert final["status"] == "CLOSED"
