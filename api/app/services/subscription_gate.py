def require_subscription(payload):
    is_paid = bool(payload.get("is_paid", False))
    if is_paid:
        return {"ok": True, "allowed": True, "message": "Auto-save enabled."}
    return {
        "ok": False,
        "allowed": False,
        "error": "subscription_required",
        "message": "Auto-save to Object DNA is available for paid accounts.",
        "upgrade_target": "pro",
    }
