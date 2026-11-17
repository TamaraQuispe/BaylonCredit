"""Pure V6 pre-model policy; callers must validate numeric feature types first."""

PENDING_FIELDS = (
    "pending_overdue", "pending_current", "outstanding", "utilization", "overdue_rate",
)


def pre_model_decision(features):
    """Return a business guard decision, or None when model evaluation is eligible."""
    if any(features[name] is not None and features[name] > 0 for name in PENDING_FIELDS):
        return {
            "decision": "blocked_pending_balance",
            "reason": ("Existe saldo pendiente actual o vencido, incluso parcial; "
                       "no se evalua un nuevo credito."),
            "requires_manual_review": False,
        }
    if any(features[name] is None for name in PENDING_FIELDS):
        return {
            "decision": "requires_owner_review",
            "reason": ("Falta confirmar la ausencia de saldo pendiente; "
                       "requiere revision del propietario."),
            "requires_manual_review": True,
        }
    if features["paid_credits"] is None or features["paid_credits"] == 0:
        return {
            "decision": "requires_owner_review",
            "reason": ("No hay creditos totalmente pagados confirmados; "
                       "requiere revision del propietario."),
            "requires_manual_review": True,
        }
    return None
