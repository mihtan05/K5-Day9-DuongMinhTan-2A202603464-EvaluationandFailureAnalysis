"""Regression test from docs/trace_case.md: C-002@11, first wrong step = event 3 model_override
(ticket says 5 days, DB says 2). Must fail on seeded_regression and pass on fixed."""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


def _trial(shape, tmp_path, claim_id="C-002", seed=11):
    from lab9 import eval as ev, variants

    variants.register()
    spec = ev.load_spec()
    world, claims = ev.load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    return ev.make_task(shape, world, claims, labels, tmp_path)({"claim_id": claim_id, "seed": seed}), labels[claim_id]


def _grade(grader, trial, label):
    from pydantic_evals.evaluators import EvaluatorContext

    ctx = EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=label, output=trial,
                           duration=0.0, _span_tree=None, attributes={}, metrics={})
    return grader().evaluate(ctx).value


@pytest.mark.parametrize("shape, ok", [("seeded_regression", False), ("fixed", True)])
def test_c002_ticket_trust_fm03(tmp_path, shape, ok):
    from lab9.graders import DbFactKept, RefundAmountCorrect

    trial, label = _trial(shape, tmp_path)
    assert _grade(DbFactKept, trial, label) is ok
    assert _grade(RefundAmountCorrect, trial, label) is ok
