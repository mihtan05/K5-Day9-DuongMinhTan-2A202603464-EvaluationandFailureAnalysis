"""M7 extra traps beyond the public ones (run with -k advanced)."""
import copy

import pytest

pytestmark = pytest.mark.student

ROWS = [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": i != 3 or s != 1, "slices": ["money_movement"] if i < 2 else []}
        for i in range(4) for s in (1, 2)]
SPEC = {"eval_set_version": "v2", "eval_set": "x.jsonl", "seeds": [1, 2],
        "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True, "threshold": {"min": 0.8}}],
        "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.97, "blocking": True}]}


def _report(rows):
    return {"manifest": {"eval_set_sha": "x", "items": 4, "seeds": [1, 2]}, "rows": rows,
            "metrics": {"pass_rate": sum(r["pass_rate"] for r in rows) / len(rows)}, "evaluator_failures": []}


@pytest.fixture
def gate():
    from lab9 import gate

    return gate


@pytest.fixture
def base():
    return _report(copy.deepcopy(ROWS))


def test_clean_report_passes(gate, base):
    assert gate.integrity_check(base, base, SPEC, SPEC) == []


def test_duplicated_row_replacing_a_failing_one(gate, base):
    rows = [r for r in copy.deepcopy(ROWS) if r["pass_rate"]]
    rows.append(copy.deepcopy(rows[0]))              # same count, failing row swapped for a duplicate
    assert gate.integrity_check(_report(rows), base, SPEC)


def test_evaluator_failures_on_green_run(gate, base):
    pr = copy.deepcopy(base)
    pr["evaluator_failures"] = ["E-001@1:RefundAmountCorrect:boom"]
    assert gate.integrity_check(pr, base, SPEC)


def test_hand_edited_metric(gate, base):
    pr = copy.deepcopy(base)
    pr["metrics"]["pass_rate"] = 1.0
    assert gate.integrity_check(pr, base, SPEC)


def test_item_relabelled_out_of_slice(gate, base):
    pr = copy.deepcopy(base)
    for r in pr["rows"]:
        if r["item_id"] == "E-001":
            r["slices"] = []
    assert gate.integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("loosen", [
    lambda s: s["slices"][0].update(min=0.5),
    lambda s: s["slices"].clear(),
    lambda s: s["metrics"][0].update(blocking=False),
    lambda s: s["metrics"].clear(),
    lambda s: s.update(eval_set_version="v2b"),       # renaming the version to escape the ratchet
    lambda s: s.update(seeds=[1]),
])
def test_ratchet(gate, base, loosen):
    spec = copy.deepcopy(SPEC)
    loosen(spec)
    assert gate.integrity_check(base, base, spec, SPEC)


def test_slice_floor_blocks_one_bad_money_item(gate, base):
    rows = copy.deepcopy(ROWS)
    rows[0]["pass_rate"] = False                     # E-000 is in money_movement
    blocked, _ = gate.slice_check(_report(rows), base, SPEC)
    assert blocked == ["slice:money_movement/pass_rate"]
