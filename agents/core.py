def prequalify(alarm: dict) -> dict:
    return {
        "domain": "TNT",
        "equipment": alarm["equipment"],
        "symptom": alarm["alarm"],
        "severity": alarm["severity"],
        "search_terms": [alarm["IG"], alarm["PS"], alarm["alarm"]],
    }


def decide_veracity(alarm: dict, interventions: list[dict]) -> dict:
    tp = interventions[0] if interventions else None

    if alarm.get("scenario") == "false":
        return {
            "decision": "EXPLAINED_BY_INTERVENTION",
            "confidence": 0.94,
            "reason": "L'alarme est cohérente avec une maintenance connue."
        }

    if tp and tp.get("can_cause_failure") == "yes":
        return {
            "decision": "REAL_FAILURE_DURING_INTERVENTION",
            "confidence": 0.86,
            "reason": "Un TP est actif mais il peut avoir provoqué une panne réelle."
        }

    if tp and tp.get("can_cause_failure") == "no":
        return {
            "decision": "EXPLAINED_BY_INTERVENTION",
            "confidence": 0.91,
            "reason": "Le contexte intervention explique l'alarme."
        }

    return {
        "decision": "VALID",
        "confidence": 0.90,
        "reason": "Aucune explication alternative suffisante."
    }


def propose_resolution(recurrence: bool, dma_rules: list[dict]) -> dict:
    if recurrence:
        return {
            "action": "REPLACE_EQUIPMENT",
            "reason": "Plusieurs incidents historiques similaires indiquent une récidive."
        }

    recommended = dma_rules[0]["action"] if dma_rules else "REBOOT"
    if recommended == "REBOOT":
        return {
            "action": "REBOOT_TRANSMITTER",
            "reason": "Runbook DMA et historique compatibles avec un reboot contrôlé."
        }

    return {
        "action": "MANUAL_DIAGNOSIS",
        "reason": "Aucune action automatique sûre disponible."
    }


def make_action_plan(resolution: dict) -> dict:
    action = resolution["action"]

    if action == "REPLACE_EQUIPMENT":
        return {
            "action": action,
            "steps": ["prepare_DI", "replace_equipment", "verify_return_to_normal"]
        }

    if action == "REBOOT_TRANSMITTER":
        return {
            "action": action,
            "steps": ["reboot", "wait", "verify_alarm"]
        }

    return {
        "action": action,
        "steps": ["manual_diagnosis"]
    }
