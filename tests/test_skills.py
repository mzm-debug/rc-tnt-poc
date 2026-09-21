from services.mock_store import MockStore
from skills.duplicate_detection import detect_duplicate
from skills.historical_intelligence import historical_intelligence


def test_duplicate_detection():
    store = MockStore()
    store.reset()
    alarm = store.get_alarm("AL-DUP-001")
    out = detect_duplicate(store, alarm)
    assert out["decision"] == "DUPLICATE"
    assert out["candidate"] == "INC0001001"


def test_history_detects_recurrence():
    store = MockStore()
    store.reset()
    alarm = store.get_alarm("AL-REC-001")
    out = historical_intelligence(store, alarm)
    assert out["recurrence"] is True
    assert out["recurrence_count"] >= 2
