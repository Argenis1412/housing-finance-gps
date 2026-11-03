"""Guarantee-focused tests for deterministic rent-plus-investment postings."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
from decimal import Decimal, ROUND_DOWN, localcontext
import json
import hashlib
from pathlib import Path
from typing import Callable, cast

import pytest

from domain.financing.contracts import ComparisonLedgerRow as FinancingLedgerRow
from domain.ledger import ComparisonLedgerRow
from domain.rent_plus_investment import (
    RentPlusInvestmentRequest,
    calculate_rent_plus_investment,
    normalize_rent_plus_investment_request,
)
from domain.values import DomainFailure


FIXTURE_PATH = Path("docs/fixtures/milestone-0-synthetic-regression.json")


def _base_request(**changes: object) -> RentPlusInvestmentRequest:
    values: dict[str, object] = {
        "comparison_opening_cash": "20000.00",
        "starting_monthly_rent": "100.00",
        "initial_invested_capital": "300.00",
        "monthly_contribution": "50.00",
        "rent_adjustment_rate_value": "0.10",
        "rent_adjustment_rate_convention": "effective_annual",
        "return_rate_value": "0.01",
        "return_rate_convention": "effective_monthly",
        "first_rent_adjustment_month": 13,
    }
    values.update(changes)
    return cast(Callable[..., RentPlusInvestmentRequest], RentPlusInvestmentRequest)(**values)


def _normalized(**changes: object):
    result = normalize_rent_plus_investment_request(_base_request(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def _failure(**changes: object) -> DomainFailure:
    result = normalize_rent_plus_investment_request(_base_request(**changes))
    assert isinstance(result, DomainFailure)
    return result


def _result(**changes: object):
    result = calculate_rent_plus_investment(_normalized(**changes))
    assert not isinstance(result, DomainFailure)
    return result


def test_synthetic_rent_plus_fixture_checkpoints_are_exact() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    rent_plus = fixture["fixtures"]["rent_plus_investment"]
    request = RentPlusInvestmentRequest(
        comparison_opening_cash=fixture["shared_conventions"]["comparison_opening_cash"],
        starting_monthly_rent=rent_plus["inputs"]["starting_monthly_rent"],
        initial_invested_capital=rent_plus["inputs"]["initial_invested_capital"],
        monthly_contribution=rent_plus["inputs"]["monthly_contribution"],
        rent_adjustment_rate_value=rent_plus["inputs"]["effective_annual_rent_adjustment"],
        rent_adjustment_rate_convention="effective_annual",
        return_rate_value=rent_plus["inputs"]["effective_monthly_net_return"],
        return_rate_convention="effective_monthly",
        first_rent_adjustment_month=rent_plus["inputs"]["first_rent_adjustment_month"],
    )
    normalized = normalize_rent_plus_investment_request(request)
    assert not isinstance(normalized, DomainFailure)
    result = calculate_rent_plus_investment(normalized)
    assert not isinstance(result, DomainFailure)
    for checkpoint in rent_plus["checkpoints"]:
        if "month" not in checkpoint:
            ledger = result.comparison_ledger[0]
            for name, expected in cast(dict[str, str], checkpoint["expected"]).items():
                assert getattr(ledger, name).as_string == expected, f"month 0 {name}"
            continue
        month = cast(int, checkpoint["month"])
        posting = result.monthly_postings[month - 1]
        ledger = result.comparison_ledger[month]
        for name, expected in cast(dict[str, str], checkpoint["expected"]).items():
            actual = getattr(posting, name) if name in {"rent", "investment_return"} else getattr(ledger, name)
            assert actual.as_string == expected, f"month {month} {name}"


def test_rent_plus_uses_the_neutral_ledger_and_full_comparison_domain() -> None:
    result = _result()
    assert FinancingLedgerRow is ComparisonLedgerRow
    assert isinstance(result.comparison_ledger[0], ComparisonLedgerRow)
    assert len(result.comparison_ledger) == 61
    assert len(result.monthly_postings) == 60
    assert result.comparison_ledger[-1].month == 60


def test_every_rent_plus_posting_and_ledger_identity_reconciles() -> None:
    result = _result()
    opening = result.comparison_ledger[0]
    assert opening.cash.amount == Decimal("19700.00")
    assert opening.liquid_financial_assets.amount == Decimal("300.00")
    assert opening.recoverable_transfer.amount == Decimal("300.00")
    assert opening.nonrecoverable_housing_cost.amount == Decimal("0.00")

    previous = opening
    for posting, ledger in zip(result.monthly_postings, result.comparison_ledger[1:], strict=True):
        assert posting.month == ledger.month
        assert posting.opening_liquid_financial_assets.amount == previous.liquid_financial_assets.amount
        assert posting.closing_liquid_financial_assets.amount == (
            posting.opening_liquid_financial_assets.amount
            + posting.investment_return.amount
            + posting.monthly_contribution.amount
        )
        assert ledger.cash.amount == previous.cash.amount - posting.rent.amount - posting.monthly_contribution.amount
        assert ledger.liquid_financial_assets.amount == posting.closing_liquid_financial_assets.amount
        assert ledger.recoverable_transfer.amount == posting.monthly_contribution.amount
        assert ledger.nonrecoverable_housing_cost.amount == posting.rent.amount
        assert ledger.property_value.amount == Decimal("0.00")
        assert ledger.total_liabilities.amount == Decimal("0.00")
        assert ledger.liquidity.amount == ledger.cash.amount + ledger.liquid_financial_assets.amount
        assert ledger.net_worth.amount == ledger.liquidity.amount
        assert ledger.cumulative_housing_cost.amount == (
            previous.cumulative_housing_cost.amount + posting.rent.amount
        )
        previous = ledger


def test_zero_capital_contribution_and_return_are_supported() -> None:
    result = _result(
        initial_invested_capital="0.00",
        monthly_contribution="0.00",
        return_rate_value="0",
    )
    assert result.comparison_ledger[0].cash.as_string == "20000.00"
    assert result.comparison_ledger[1].liquid_financial_assets.as_string == "0.00"
    assert result.monthly_postings[0].investment_return.as_string == "0.00"


def test_adjustment_after_the_comparison_horizon_is_valid_without_adjustment() -> None:
    result = _result(first_rent_adjustment_month=61)
    assert result.monthly_postings[-1].rent.as_string == "100.00"


def test_half_cent_return_and_rent_adjustment_post_exactly_half_up() -> None:
    result = _result(
        comparison_opening_cash="100.00",
        starting_monthly_rent="1.00",
        initial_invested_capital="1.00",
        monthly_contribution="0.00",
        rent_adjustment_rate_value="0.005",
        return_rate_value="0.005",
        first_rent_adjustment_month=2,
    )
    assert result.monthly_postings[0].investment_return.as_string == "0.01"
    assert result.monthly_postings[1].rent.as_string == "1.01"


def test_invalid_representations_signs_and_periods_fail_closed() -> None:
    for changes in (
        {"starting_monthly_rent": "1.0"},
        {"comparison_opening_cash": "-0.01"},
        {"initial_invested_capital": "-0.01"},
        {"monthly_contribution": "-0.01"},
        {"rent_adjustment_rate_value": "-0.01"},
        {"return_rate_value": "-0.01"},
        {"first_rent_adjustment_month": True},
        {"first_rent_adjustment_month": 1},
        {"investment_product": "unknown"},
    ):
        assert _failure(**changes).code == "invalid_input"


def test_rate_conventions_are_rejected_even_for_zero_rates() -> None:
    assert _failure(
        rent_adjustment_rate_value="0", rent_adjustment_rate_convention="effective_monthly"
    ).code == "unsupported_rate_convention"
    assert _failure(
        return_rate_value="0", return_rate_convention="effective_annual"
    ).code == "unsupported_rate_convention"


def test_closed_unsupported_requests_have_canonical_failure_categories() -> None:
    assert _failure(tax_amount="1.00").code == "unsupported_rule"
    assert _failure(tax_amount="1.0").code == "invalid_input"
    for name in ("investment_product", "withdrawal_restriction", "future_purchase"):
        assert _failure(**{name: "requested"}).code == "unsupported_contract_clause"
    assert _result(tax_amount="0.00") == _result()


def test_initial_and_monthly_cash_shortfalls_return_infeasible_without_result() -> None:
    initial = calculate_rent_plus_investment(
        _normalized(comparison_opening_cash="100.00", initial_invested_capital="100.01")
    )
    assert isinstance(initial, DomainFailure)
    assert initial.code == "infeasible_scenario"
    monthly = calculate_rent_plus_investment(
        _normalized(
            comparison_opening_cash="100.00",
            initial_invested_capital="0.00",
            starting_monthly_rent="100.00",
            monthly_contribution="0.01",
        )
    )
    assert isinstance(monthly, DomainFailure)
    assert monthly.code == "infeasible_scenario"


def test_rent_plus_outputs_are_deterministic_context_independent_and_immutable() -> None:
    normalized = _normalized()
    baseline = calculate_rent_plus_investment(normalized)
    assert not isinstance(baseline, DomainFailure)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert calculate_rent_plus_investment(normalized) == baseline
    try:
        setattr(baseline.monthly_postings[0], "month", 2)
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("monthly postings must be immutable")
    try:
        setattr(baseline, "comparison_ledger", ())
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("result collections must be immutable")


# Complete normalized input + output hashes captured from main 30ee36d before
# extraction. These do not compare two adapters sharing the new evaluator.
@pytest.mark.parametrize(("changes", "expected"), [
    ({}, "4da070284a13ec9a53019346fccc65e4f66dbafb6f0c89ba4d027e8e58ac6594"),
    ({"return_rate_value": "0", "rent_adjustment_rate_value": "0", "monthly_contribution": "0.00", "initial_invested_capital": "0.00"},
     "4237dbfbfb64ba2030770a0cc9f0122c017f155518ac21597e6346096b80cfe1"),
    ({"comparison_opening_cash": "100.00", "starting_monthly_rent": "1.00", "initial_invested_capital": "1.00", "monthly_contribution": "0.00", "rent_adjustment_rate_value": "0.005", "return_rate_value": "0.005", "first_rent_adjustment_month": 2},
     "c48197ece21642667358145eb121fe171ac8d19cc0e606d052aa8670e3440060"),
    ({"first_rent_adjustment_month": 61}, "4f3426dbac04ec9fe0b3c59e2b93b4bb88ce07cc86307f9da9ed4778df9ec6b3"),
    ({"initial_invested_capital": "20000.01"}, "01b1400656b2a5774132755da14c66b20ec975b47325a371cb44f0a66ce850b7"),
    ({"comparison_opening_cash": "0.00", "starting_monthly_rent": "1.00", "initial_invested_capital": "0.00", "monthly_contribution": "0.00", "return_rate_value": "0", "rent_adjustment_rate_value": "1e5000"},
     "9bd0a02d16c7f1f651a744916a70cd73381eb24f8603133d432d8f4497ca1061"),
    ({"starting_monthly_rent": "0.00"}, "5385a9c188eaa05d47277f31ca03e7f1472f1451a02a6ddfa9a436e334aa2c50"),
    ({"return_rate_value": 1}, "021fc3387f8539df483c1dffc0e27fc5766f82ffbd72deaf89797fbce15686d2"),
    ({"return_rate_convention": None}, "021fc3387f8539df483c1dffc0e27fc5766f82ffbd72deaf89797fbce15686d2"),
    ({"return_rate_value": "bad"}, "021fc3387f8539df483c1dffc0e27fc5766f82ffbd72deaf89797fbce15686d2"),
    ({"rent_adjustment_rate_value": "NaN"}, "a8f06ad121037dfed054d8996f0ab810c46893edad19e7f69e87507cd940f6d9"),
    ({"return_rate_value": "Infinity"}, "021fc3387f8539df483c1dffc0e27fc5766f82ffbd72deaf89797fbce15686d2"),
    ({"initial_invested_capital": "-0.00", "monthly_contribution": "-0.00"},
     "96b14e1ede89c30fc6f53a41725b6f0a36663b63296806d51a4546a9398a1e4f"),
    ({"return_rate_value": "1e-2", "rent_adjustment_rate_value": "1e-1"},
     "3d50880acbf2a0e2417e02b33f631bf819715e298e98722b5fe13fd89963f858"),
])
def test_pre_extraction_complete_rent_references(changes: dict[str, object], expected: str) -> None:
    normalized = normalize_rent_plus_investment_request(_base_request(**changes))
    outcome = {
        "normalized": asdict(normalized),
        "result": None if isinstance(normalized, DomainFailure) else asdict(calculate_rent_plus_investment(normalized)),
    }
    raw = json.dumps(outcome, default=lambda value: format(value, "f"), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(raw.encode()).hexdigest() == expected
