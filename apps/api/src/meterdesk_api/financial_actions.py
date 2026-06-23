from __future__ import annotations

from typing import Any


def build_action_fingerprint(
    *,
    ticket_id: str,
    action_type: str,
    amount_cents: int,
    currency: str,
    action_metadata: dict[str, Any],
) -> str:
    target = resolve_action_target(action_metadata)
    return (
        f"ticket:{ticket_id}|action:{action_type}|target:{target}|"
        f"amount:{amount_cents}|currency:{currency.upper()}"
    )


def resolve_action_target(action_metadata: dict[str, Any]) -> str:
    for key in ("target_charge_id", "credit_ledger_entry_id", "invoice_id"):
        value = action_metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"
