def evaluate_policy(action_plan: dict) -> dict:
    action = action_plan["action"]

    if action == "REBOOT_TRANSMITTER":
        return {
            "decision": "AUTO_ALLOWED",
            "reason": "Reboot autorisé dans le périmètre POC."
        }

    return {
        "decision": "HITL_REQUIRED",
        "reason": "Action sensible : validation humaine obligatoire."
    }
