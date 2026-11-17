"""Dedykowana operacja anulowania zamówienia – OrderFlow, wersja A.

Źródło wymagań: Product Owner, REF-A-20261117-DP4-7CYCZ4G7, 17.11.2026.
Zmienia się wyłącznie status; potwierdzenie i zapis obsługuje warstwa UI.
"""
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from orders import find_order_by_id
from validation import is_valid_identifier

DEFAULT_POLICY_FILE = Path(__file__).resolve().parent / "data" / "cancellation_policy.json"


@dataclass(frozen=True)
class CancellationDecision:
    allowed: bool
    code: str
    message: str
    payment_notice: Optional[str] = None


def load_cancellation_policy(path=None):
    """Brak reguł lub ich nieprawidłowa struktura uniemożliwiają anulowanie."""
    location = Path(path) if path is not None else DEFAULT_POLICY_FILE
    with location.open("r", encoding="utf-8") as stream:
        policy = json.load(stream)
    if not isinstance(policy, dict) or not isinstance(policy.get("statuses"), dict):
        raise ValueError("Nieprawidłowy plik reguł anulowania.")
    if not isinstance(policy.get("payment_notices"), dict):
        raise ValueError("Brak polityki obsługi płatności.")
    return policy


def evaluate_cancellation(orders, order_id, policy, now=None):
    """Sprawdź status, czas i metodę płatności bez modyfikowania zamówienia."""
    if not is_valid_identifier(order_id, "ORD"):
        return CancellationDecision(False, "INVALID_ID", "ID musi mieć format ORD-0001.")
    order = find_order_by_id(orders, order_id)
    if order is None:
        return CancellationDecision(False, "NOT_FOUND", "Nie znaleziono zamówienia.")

    status = order.get("status")
    rule = policy.get("statuses", {}).get(status)
    if not isinstance(rule, dict) or type(rule.get("allowed")) is not bool:
        return CancellationDecision(False, "INVALID_POLICY", "Nieznana lub nieprawidłowa reguła anulowania.")
    if not rule["allowed"]:
        return CancellationDecision(False, "DENIED", f"Nie można anulować zamówienia w statusie {status}.")

    limit = rule.get("max_age_minutes")
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit < 0:
            return CancellationDecision(False, "INVALID_POLICY", "Nieprawidłowy limit czasu anulowania.")
        try:
            created_at = datetime.fromisoformat(order["created_at"])
            current = now if now is not None else datetime.now()
            elapsed = (current - created_at).total_seconds()
        except (KeyError, TypeError, ValueError, OverflowError):
            return CancellationDecision(False, "INVALID_DATE", "Nieprawidłowa data utworzenia zamówienia.")
        if elapsed < 0:
            return CancellationDecision(False, "FUTURE_DATE", "Data zamówienia jest w przyszłości.")
        if elapsed > limit * 60:
            return CancellationDecision(False, "TIME_LIMIT", f"Minął limit {limit:g} minut od utworzenia zamówienia.")

    payment = order.get("payment_method")
    needs_notice = policy["payment_notices"].get(payment)
    if type(needs_notice) is not bool:
        return CancellationDecision(False, "INVALID_POLICY", "Nieznana reguła dla metody płatności.")
    notice = (
        "Wymagany ręczny zwrot środków – OrderFlow nie wykonuje automatycznego zwrotu."
        if needs_notice else None
    )
    return CancellationDecision(True, "ALLOWED", "Zamówienie może zostać anulowane.", notice)


def mark_order_cancelled(orders, order_id, policy, now=None):
    """Ponownie sprawdź warunki i zaktualizuj tylko pole status."""
    decision = evaluate_cancellation(orders, order_id, policy, now=now)
    if decision.allowed:
        order = find_order_by_id(orders, order_id)
        order["status"] = "CANCELLED"
    return decision
