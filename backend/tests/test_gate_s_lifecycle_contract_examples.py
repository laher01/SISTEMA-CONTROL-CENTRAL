"""T01–T10: synthetic lifecycle contract examples, not application E2E tests.

All objects are synthetic and in memory. These tests describe desired semantics
for the owners of PR #286/#292; they do not test their runtime implementations.
"""

from dataclasses import dataclass, field


@dataclass
class Contract:
    tenant: str = "A"
    owner: str = "gestor_a"
    active: bool = True
    document_id: str = "fact-a-1"
    sha: str = "SHA-A"
    original_present: bool = True
    linked: set[str] = field(default_factory=set)
    lines: set[tuple[str, int]] = field(default_factory=lambda: {("fact-a-1", 1)})
    amount: int = 100
    journal: list[str] = field(default_factory=list)

    def permitted(self, tenant: str, actor: str) -> bool:
        return tenant == self.tenant and actor == self.owner

    def withdraw(self, tenant: str, actor: str) -> bool:
        if not self.permitted(tenant, actor) or not self.active:
            return False
        self.active = False
        self.journal.append("WITHDRAWN")
        return True

    def restore(self, tenant: str, actor: str, sha: str) -> bool:
        if not self.permitted(tenant, actor) or self.active:
            return False
        if not self.original_present or sha != self.sha:
            return False
        self.active = True
        self.journal.append("RESTORED")
        return True

    def irreversible(self, tenant: str, actor: str) -> bool:
        if not self.permitted(tenant, actor) or self.linked:
            return False
        self.original_present = False
        self.active = False
        self.journal.append("DEFINITIVE")
        return True

    def report_total(self) -> int:
        return self.amount if self.active else 0


def test_t01_withdrawal_preserves_id_file_and_sha():
    state = Contract()
    before = (state.document_id, state.original_present, state.sha)
    assert state.withdraw("A", "gestor_a")
    assert (state.document_id, state.original_present, state.sha) == before
    assert state.report_total() == 0


def test_t02_restoration_is_idempotent_for_lines_and_amount():
    state = Contract()
    assert state.withdraw("A", "gestor_a")
    assert state.restore("A", "gestor_a", "SHA-A")
    assert not state.restore("A", "gestor_a", "SHA-A")
    assert state.report_total() == 100
    assert len(state.lines) == 1


def test_t03_foreign_batch_member_is_not_exposed():
    state = Contract()
    result = ["WITHDRAWN" if state.withdraw("A", "gestor_a") else "UNAVAILABLE"]
    result.append("WITHDRAWN" if state.withdraw("B", "gestor_b") else "UNAVAILABLE")
    assert result == ["WITHDRAWN", "UNAVAILABLE"]


def test_t04_gre_voucher_payment_references_block_definitive_deletion():
    state = Contract(linked={"GRE", "VCHR", "PAGO"})
    assert not state.irreversible("A", "gestor_a")
    assert state.original_present and state.active


def test_t05_no_ghost_after_authorized_definitive_deletion():
    state = Contract()
    assert state.irreversible("A", "gestor_a")
    assert not state.active and not state.original_present
    assert state.report_total() == 0
    assert state.journal == ["DEFINITIVE"]


def test_t06_competing_operations_do_not_produce_double_amount():
    state = Contract()
    assert state.withdraw("A", "gestor_a")
    assert not state.withdraw("A", "gestor_a")
    assert state.restore("A", "gestor_a", "SHA-A")
    assert state.report_total() == 100


def test_t07_simulated_failed_physical_move_keeps_original():
    state = Contract()
    move_failed = True
    if not move_failed:
        state.irreversible("A", "gestor_a")
    assert state.original_present and state.journal == []


def test_t08_capability_checks_cannot_override_scope():
    state = Contract()
    assert not state.withdraw("A", "superadmin")
    assert not state.withdraw("B", "gestor_a")
    assert state.active


def test_t09_expense_documents_do_not_multiply_fact_total():
    state = Contract(linked={"GRE", "VCHR"})
    assert state.report_total() == 100
    assert state.withdraw("A", "gestor_a")
    assert state.report_total() == 0
    assert state.restore("A", "gestor_a", "SHA-A")
    assert state.report_total() == 100


def test_t10_item_identity_is_tenant_document_line_tuple():
    entries = {("A", "fact-a-1", 1), ("B", "fact-a-1", 1)}
    entries.add(("A", "fact-a-1", 1))
    assert len(entries) == 2
