"""Synthetic invariants for orders vs items; not dashboard runtime tests."""

from decimal import Decimal

import pytest


def progress(authorized: Decimal | None, invoices: list[tuple[str, Decimal]]) -> Decimal | None:
    """Contract example: deduplicate invoice identity, keep unassigned budgets undefined."""
    if authorized is None or authorized <= 0:
        return None
    distinct = dict(invoices)
    return sum(distinct.values(), Decimal("0")) * Decimal("100") / authorized


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("9999", "99.99"),
        ("10000", "100"),
        ("12000", "120"),
        ("12001", "120.01"),
    ],
)
def test_synthetic_threshold_percentage(amount: str, expected: str):
    value = progress(Decimal("10000"), [("FACT-1", Decimal(amount))])
    assert value == Decimal(expected)


def test_same_invoice_linked_to_gre_and_voucher_is_counted_once():
    value = progress(
        Decimal("10000"),
        [("FACT-A", Decimal("3500")), ("FACT-A", Decimal("3500"))],
    )
    assert value == Decimal("35")


def test_unassigned_global_budget_is_not_a_fictitious_percentage():
    assert progress(None, [("FACT-A", Decimal("100"))]) is None


def test_total_is_weighted_by_authorized_amount_not_mean_percentage():
    a = progress(Decimal("100"), [("A", Decimal("100"))])
    b = progress(Decimal("900"), [("B", Decimal("0"))])
    total = progress(
        Decimal("1000"), [("A", Decimal("100")), ("B", Decimal("0"))]
    )
    assert a == 100 and b == 0
    assert total == 10


def test_item_quantities_are_not_invoice_amounts():
    amount = Decimal("100")
    kg = Decimal("75")
    percentage = progress(Decimal("200"), [("FACT-1", amount)])
    assert percentage == 50
    assert kg != amount
