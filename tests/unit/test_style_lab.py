import pytest
from scripts.style_lab import reserve


def test_budget_rejects_excess_before_submission():
    ledger = {'reserved_requests': 0}
    reserve(ledger, 1)
    with pytest.raises(ValueError, match='exhausted'):
        reserve(ledger, 1)
    assert ledger['reserved_requests'] == 1


@pytest.mark.parametrize('limit', [0, 17, -1, True])
def test_initial_budget_bounds(limit):
    ledger = {'reserved_requests': 0}
    with pytest.raises(ValueError):
        reserve(ledger, limit)
    assert ledger['reserved_requests'] == 0
