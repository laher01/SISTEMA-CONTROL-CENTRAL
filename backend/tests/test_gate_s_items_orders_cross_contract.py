"""Offline contract examples for order progress vs invoice-item accounting.

These test a pure synthetic ledger, not production API/ORM implementations.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Invoice:
    identity: str
    tenant: str
    customer: str
    supplier: str
    owner: str
    currency: str
    amount: Decimal
    approved: bool = True
    active: bool = True


def summarize(
    invoices: list[Invoice],
    *,
    tenant: str,
    customer: str,
    owner: str,
    currency: str = "PEN",
) -> tuple[Decimal, dict[str, Decimal]]:
    """Deduplicate invoice identity and reject nonmatching scope/state."""
    relevant = [
        x
        for x in invoices
        if x.tenant == tenant
        and x.customer == customer
        and x.owner == owner
        and x.currency == currency
        and x.approved
        and x.active
    ]
    distinct = {x.identity: x for x in relevant}
    by_supplier: dict[str, Decimal] = {}
    for invoice in distinct.values():
        by_supplier[invoice.supplier] = (
            by_supplier.get(invoice.supplier, Decimal("0")) + invoice.amount
        )
    return sum(by_supplier.values(), Decimal("0")), by_supplier


def synthetic_invoice(**overrides: object) -> Invoice:
    base = {
        "identity": "FACT-F001-1",
        "tenant": "A",
        "customer": "CLIENTE-1",
        "supplier": "PROVEEDOR-1",
        "owner": "GESTOR-1",
        "currency": "PEN",
        "amount": Decimal("250"),
    }
    base.update(overrides)
    return Invoice(**base)


def test_fact_gre_voucher_and_ubl_lines_do_not_repeat_invoice_amount():
    invoice = synthetic_invoice()
    artifacts = [invoice, invoice, invoice]  # FACT, GRE and voucher references
    total, providers = summarize(artifacts, tenant="A", customer="CLIENTE-1", owner="GESTOR-1")
    assert total == Decimal("250")
    assert providers == {"PROVEEDOR-1": Decimal("250")}


def test_customer_supplier_allocation_with_distinct_facturas():
    entries = [
        synthetic_invoice(),
        synthetic_invoice(
            identity="FACT-F001-2",
            supplier="PROVEEDOR-2",
            amount=Decimal("350"),
        ),
    ]
    total, providers = summarize(entries, tenant="A", customer="CLIENTE-1", owner="GESTOR-1")
    assert total == Decimal("600")
    assert providers == {
        "PROVEEDOR-1": Decimal("250"),
        "PROVEEDOR-2": Decimal("350"),
    }


def test_hierarchy_tenant_and_customer_scope():
    entries = [
        synthetic_invoice(),
        synthetic_invoice(identity="OTHER-TENANT", tenant="B"),
        synthetic_invoice(identity="OTHER-CUSTOMER", customer="CLIENTE-2"),
        synthetic_invoice(identity="OTHER-GESTOR", owner="GESTOR-2"),
    ]
    total, _ = summarize(
        entries, tenant="A", customer="CLIENTE-1", owner="GESTOR-1"
    )
    assert total == Decimal("250")


def test_retired_and_pending_invoices_do_not_inflate_progress():
    entries = [
        synthetic_invoice(),
        synthetic_invoice(identity="RETIRED", active=False),
        synthetic_invoice(identity="PENDING", approved=False),
    ]
    total, _ = summarize(
        entries, tenant="A", customer="CLIENTE-1", owner="GESTOR-1"
    )
    assert total == Decimal("250")


def test_currency_is_not_mixed_in_progress_calculations():
    entries = [
        synthetic_invoice(),
        synthetic_invoice(identity="USD-1", currency="USD", amount=Decimal("500")),
    ]
    pen, _ = summarize(
        entries, tenant="A", customer="CLIENTE-1", owner="GESTOR-1"
    )
    usd, _ = summarize(entries, tenant="A", customer="CLIENTE-1", owner="GESTOR-1", currency="USD")
    assert (pen, usd) == (Decimal("250"), Decimal("500"))


def test_item_quantities_are_not_invoice_monetary_progress():
    invoice = synthetic_invoice()
    ubl_lines = [("KGM", Decimal("80")), ("NIU", Decimal("12"))]
    total, _ = summarize([invoice], tenant="A", customer="CLIENTE-1", owner="GESTOR-1")
    assert total == Decimal("250")
    assert sum((quantity for _, quantity in ubl_lines), Decimal("0")) != total
