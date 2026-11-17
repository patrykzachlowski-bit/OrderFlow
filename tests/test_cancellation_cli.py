"""Testy anulowania z menu – brak zapisu do rzeczywistych plików JSON."""
from copy import deepcopy
from datetime import datetime, timedelta
import builtins

import main


def _order(status="NEW", minutes_old=0, payment="CASH_ON_DELIVERY"):
    return {
        "id": "ORD-0050",
        "customer_id": "CUS-001",
        "status": status,
        "created_at": (datetime.now() - timedelta(minutes=minutes_old)).isoformat(timespec="seconds"),
        "payment_method": payment,
        "delivery_method": "COURIER",
        "items": [],
        "total": 0.0,
    }


def _set_up(monkeypatch, orders, answers):
    saved = []
    values = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(values))
    monkeypatch.setattr(main, "load_orders", lambda: orders)
    monkeypatch.setattr(main, "save_orders", lambda data: saved.append(deepcopy(data)))
    return saved


def test_confirmed_new_saves_once(monkeypatch, capsys):
    orders = [_order()]
    saved = _set_up(monkeypatch, orders, ["ORD-0050", "tak"])
    main.handle_order_cancellation()
    assert orders[0]["status"] == "CANCELLED"
    assert len(saved) == 1
    assert "Anulowano" in capsys.readouterr().out


def test_refused_confirmation_no_save(monkeypatch):
    orders = [_order()]
    saved = _set_up(monkeypatch, orders, ["ORD-0050", "nie"])
    main.handle_order_cancellation()
    assert orders[0]["status"] == "NEW"
    assert saved == []


def test_expired_paid_cannot_be_cancelled(monkeypatch, capsys):
    orders = [_order(status="PAID", minutes_old=31)]
    saved = _set_up(monkeypatch, orders, ["ORD-0050"])
    main.handle_order_cancellation()
    assert orders[0]["status"] == "PAID"
    assert saved == []
    assert "limit" in capsys.readouterr().out.lower()


def test_card_paid_shows_refund_notice(monkeypatch, capsys):
    orders = [_order(status="PAID", minutes_old=2, payment="CARD")]
    saved = _set_up(monkeypatch, orders, ["ORD-0050", "t"])
    main.handle_order_cancellation()
    assert saved
    assert orders[0]["status"] == "CANCELLED"
    assert "ręczny zwrot" in capsys.readouterr().out


def test_cod_no_refund_notice(monkeypatch, capsys):
    orders = [_order(payment="CASH_ON_DELIVERY")]
    _set_up(monkeypatch, orders, ["ORD-0050", "t"])
    main.handle_order_cancellation()
    assert "ręczny zwrot" not in capsys.readouterr().out


def test_nonexistent_order_no_save(monkeypatch):
    orders = [_order()]
    saved = _set_up(monkeypatch, orders, ["ORD-9999"])
    main.handle_order_cancellation()
    assert saved == []


def test_status_changed_between_checks(monkeypatch):
    orders = [_order()]
    saved = []
    reads = [deepcopy(orders), [_order(status="SHIPPED")]]
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(iter(["ORD-0050", "t"])))
    # Distinct prompts require distinct answers.
    answers = iter(["ORD-0050", "t"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))
    monkeypatch.setattr(main, "load_orders", lambda: reads.pop(0))
    monkeypatch.setattr(main, "save_orders", lambda data: saved.append(data))
    main.handle_order_cancellation()
    assert saved == []
