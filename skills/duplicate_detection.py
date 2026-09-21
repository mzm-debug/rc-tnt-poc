from services.mock_store import MockStore
from skills.text_similarity import jaccard


def detect_duplicate(store: MockStore, alarm: dict) -> dict:
    candidates = [
        i for i in store.incidents()
        if i.get("state") != "Closed"
        and (
            i.get("IG") == alarm.get("IG")
            or i.get("PS") == alarm.get("PS")
            or i.get("equipment") == alarm.get("equipment")
        )
    ]

    scored = []
    for inc in candidates:
        score = (
            0.35 * jaccard(alarm.get("description", ""), inc.get("description", ""))
            + 0.40 * float(inc.get("IG") == alarm.get("IG"))
            + 0.25 * float(inc.get("equipment") == alarm.get("equipment"))
        )
        scored.append({
            "incident": inc["number"],
            "score": round(score, 3),
            "reason": {
                "same_ig": inc.get("IG") == alarm.get("IG"),
                "same_equipment": inc.get("equipment") == alarm.get("equipment"),
            }
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0] if scored else None

    if best and best["score"] >= 0.70:
        return {
            "decision": "DUPLICATE",
            "candidate": best["incident"],
            "confidence": best["score"],
            "candidates": scored
        }

    return {
        "decision": "NOT_DUPLICATE",
        "candidate": None,
        "confidence": round(1 - (best["score"] if best else 0), 3),
        "candidates": scored
    }
