def require_subscription(payload):
    return {
        "ok": False,
        "allowed": False,
        "error": "billing_not_integrated",
        "message": "Billing and verified subscription entitlements are not integrated; paid access cannot be confirmed.",
        "upgrade_target": "pro",
    }
