from services.mock_store import MockStore
from skills.text_similarity import jaccard


def historical_intelligence(store: MockStore, alarm: dict) -> dict:
    rows = []

    for inc in store.incidents():
        if inc.get("state") != "Closed":
            continue

        score = (
            0.50 * jaccard(alarm.get("description", ""), inc.get("description", ""))
            + 0.25 * float(inc.get("IG") == alarm.get("IG"))
            + 0.25 * float(inc.get("equipment") == alarm.get("equipment"))
        )

        if score > 0:
            rows.append({**inc, "similarity": round(score, 3)})

    rows.sort(key=lambda x: x["similarity"], reverse=True)
    recurrence_count = sum(
        1 for x in rows if x.get("equipment") == alarm.get("equipment")
    )

    return {
        "items": rows[:5],
        "recurrence": recurrence_count >= 2,
        "recurrence_count": recurrence_count
    }
