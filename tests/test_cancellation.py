"""Regresja reguł anulowania wg Product Ownera, sesja 17.11.2026."""
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from cancellation import evaluate_cancellation, load_cancellation_policy, mark_order_cancelled


@pytest.fixture
def policy():
    return load_cancellation_policy()


@pytest.fixture
def order():
    return {
        "id": "ORD-0041",
        "customer_id": "CUS-001",
        "status": "NEW",
        "created_at": "2026-11-17T14:00:00",
        "payment_method": "CASH_ON_DELIVERY",
        "delivery_method": "COURIER",
        "items": [{"product_id": "PRD-001", "quantity": 1, "unit_price": 32.9}],
        "total": 32.9,
    }


def test_new_without_time_limit_and_only_status_updated(order, policy):
    original = deepcopy(order)
    assert mark_order_cancelled([order], order["id"], policy, now=datetime(2029, 1, 1)).allowed
    assert order["status"] == "CANCELLED"
    assert {k: v for k, v in order.items() if k != "status"} == {
        k: v for k, v in original.items() if k != "status"
    }


@pytest.mark.parametrize("status", ["SHIPPED", "DELIVERED", "CANCELLED"])
def test_denied_status_does_not_change_data(order, policy, status):
    order["status"] = status
    before = deepcopy(order)
    assert mark_order_cancelled([order], order["id"], policy).code == "DENIED"
    assert order == before


@pytest.mark.parametrize("status,minutes", [("PAID", 30), ("PROCESSING", 15)])
def test_time_boundaries_inclusive(order, policy, status, minutes):
    order["status"] = status
    start = datetime.fromisoformat(order["created_at"])
    assert evaluate_cancellation([order], order["id"], policy, now=start).allowed
    assert evaluate_cancellation([order], order["id"], policy, now=start + timedelta(minutes=minutes)).allowed
    before = deepcopy(order)
    assert mark_order_cancelled([order], order["id"], policy, now=start + timedelta(minutes=minutes, seconds=1)).code == "TIME_LIMIT"
    assert order == before


@pytest.mark.parametrize("bad_id", ["foo", "ORD-", "ORD-1", "", "1234", None])
def test_invalid_id(order, policy, bad_id):
    before = deepcopy(order)
    assert mark_order_cancelled([order], bad_id, policy).code == "INVALID_ID"
    assert order == before


def test_missing_order(order, policy):
    assert mark_order_cancelled([order], "ORD-9999", policy).code == "NOT_FOUND"


def test_repeated_cancellation_does_not_modify_data(order, policy):
    assert mark_order_cancelled([order], order["id"], policy).allowed
    before = deepcopy(order)
    assert mark_order_cancelled([order], order["id"], policy).code == "DENIED"
    assert order == before


@pytest.mark.parametrize("payment,has_notice", [
    ("CARD", True),
    ("TRANSFER", True),
    ("CASH_ON_DELIVERY", False),
])
def test_payment_notice(order, policy, payment, has_notice):
    order["payment_method"] = payment
    decision = evaluate_cancellation([order], order["id"], policy)
    assert decision.allowed
    assert bool(decision.payment_notice) is has_notice


def test_bad_created_at_for_paid(order, policy):
    order["status"] = "PAID"
    order["created_at"] = "invalid"
    assert evaluate_cancellation([order], order["id"], policy).code == "INVALID_DATE"


def test_future_created_at_for_processing(order, policy):
    order["status"] = "PROCESSING"
    start = datetime.fromisoformat(order["created_at"])
    assert evaluate_cancellation([order], order["id"], policy, now=start - timedelta(seconds=1)).code == "FUTURE_DATE"


def test_unknown_status_fail_closed(order, policy):
    order["status"] = "MYSTERY"
    before = deepcopy(order)
    assert mark_order_cancelled([order], order["id"], policy).code == "INVALID_POLICY"
    assert order == before


def test_unconfigured_rule_fail_closed(order, policy):
    order["status"] = "PAID"
    policy["statuses"]["PAID"]["allowed"] = None
    assert mark_order_cancelled([order], order["id"], policy).code == "INVALID_POLICY"


def test_payment_does_not_change_cancellation_eligibility(order, policy):
    order["status"] = "PAID"
    start = datetime.fromisoformat(order["created_at"])
    for method in ("CARD", "TRANSFER", "CASH_ON_DELIVERY"):
        order["payment_method"] = method
        assert evaluate_cancellation([order], order["id"], policy, now=start + timedelta(minutes=29)).allowed
