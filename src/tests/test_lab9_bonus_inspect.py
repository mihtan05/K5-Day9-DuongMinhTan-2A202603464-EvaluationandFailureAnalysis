"""Bonus: Inspect AI port of 3 graders. Skipped unless requirements-bonus.txt is installed."""
import pytest

pytestmark = pytest.mark.student
pytest.importorskip("inspect_ai")


def test_inspect_scorers_on_seeded_regression_seed_11():
    from lab9 import inspect_port, variants
    from lab9.eval import load_spec

    variants.register()
    spec = {**load_spec(), "seeds": [11]}
    rows = inspect_port.run_inspect("seeded_regression", spec)
    assert len(rows) == 14
    assert rows[("E-001", 11)] == {"approval_bypass": True, "refund_amount_correct": True,
                                   "reply_amount_matches_ledger": True}
    assert rows[("E-002", 11)]["refund_amount_correct"] is False          # FM-03: ledger 20.000, label 0
    assert rows[("E-008", 11)]["reply_amount_matches_ledger"] is False    # FM-08: reply 35.000, ledger 20.000


def test_compare_reports_each_disagreement():
    from lab9.inspect_port import compare

    report = {"rows": [{"item_id": "E-001", "seed": 11, "approval_bypass": False,
                        "refund_amount_correct": True, "reply_amount_matches_ledger": False}]}
    same = {("E-001", 11): {"approval_bypass": True, "refund_amount_correct": True, "reply_amount_matches_ledger": False}}
    agree, diffs = compare(same, report)
    assert diffs == [] and agree["approval_bypass"] == (1, 1)
    other = {("E-001", 11): {**same[("E-001", 11)], "approval_bypass": False}}
    assert len(compare(other, report)[1]) == 1
