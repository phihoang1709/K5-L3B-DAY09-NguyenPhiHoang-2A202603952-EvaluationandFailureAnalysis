"""Regression test for docs/trace_case.md: swarm C-002@55 (FM-03 ticket_trust).

Hand-built trials reproducing the exact trace/ledger of run E-swarm-20261118-9c19:
the swarm shape overrides the DB delay_days with the ticket value (event 3, model_override)
and commits a 20.000đ refund on a claim whose label is denied/0đ. The graders must catch it;
the same trial without the override (the `fixed` behaviour) must pass.
"""
import pytest

pytestmark = pytest.mark.student

LABEL = {"refund_vnd": 0, "approval_ok": True, "status": "denied"}


@pytest.fixture(scope="module")
def graders():
    from lab9 import graders

    return graders


def ctx(trial):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=LABEL, output=trial,
                            duration=0.0, _span_tree=None, attributes={}, metrics={})


def trial(events=(), refund_vnd=0):
    return {"snapshot": {"refund_vnd": refund_vnd, "refund_count": 1 if refund_vnd else 0},
            "unexpected_rows": 0, "blob": "", "events": list(events),
            "result": {}, "lab8_pass": bool(refund_vnd == 0), "lab8_reason": None}


def test_c002_ticket_trust_is_caught(graders):
    override = {"kind": "model_override", "payload": {"delay_days": 5}}
    t = ctx(trial(events=[override], refund_vnd=20000))
    # step-level: the override event breaks the DB-fact contract (FM-03 signature)
    assert graders.DbFactKept().evaluate(t).value is False
    # outcome-level: money moved where the label says none
    assert graders.RefundAmountCorrect().evaluate(t).value is False
    assert graders.TrialPass().evaluate(t).value is False


def test_c002_fixed_behaviour_passes(graders):
    t = ctx(trial(events=[{"kind": "quote", "payload": {"amount_vnd": 0, "reason": "no_entitlement"}}]))
    assert graders.DbFactKept().evaluate(t).value is True
    assert graders.RefundAmountCorrect().evaluate(t).value is True
    assert graders.TrialPass().evaluate(t).value is True