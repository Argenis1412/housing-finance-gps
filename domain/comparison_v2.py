"""Retained comparison authority over one explicit monthly funding profile."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
import re
from typing import cast

from domain import comparison_v1 as _basis
from domain import monthly_resources_v1 as _resources
from domain import rent_replay_v2 as _rent
from domain.consortium import replay_v1 as _codec
from domain.consortium import replay_v2 as _consortium
from domain.financing import replay_v4 as _financing


CONTRACT_SCHEMA_VERSION = "comparison-simulation-v2"
ENGINE_VERSION = "comparison-monthly-resources-v2"
RULESET_VERSION = "comparison-ruleset-v2"
_ORDER = ("sac", "price", "rent", "consortium")
_LIMITATIONS = (
    "synthetic_explicit_common_monthly_resources_not_complete_household_affordability",
    "only_rent_invests_and_receives_returns",
    "surplus_remains_cash_without_return",
    "no_automatic_redemption_credit_or_contribution_reduction",
    "no_post_horizon_cash_feasibility_claim",
    "no_universal_winner_or_private_case_validation",
    "snapshot_and_source_references_are_not_authentication",
    "declared_external_scope_does_not_detect_semantic_alias_double_counting",
)


def _versions(strategy: str) -> dict[str, object]:
    engine = (
        _financing
        if strategy in ("sac", "price")
        else _rent
        if strategy == "rent"
        else _consortium
    )
    return {
        "contract_schema_version": engine.CONTRACT_SCHEMA_VERSION,
        "engine_version": engine.ENGINE_VERSION,
        "ruleset_version": engine.RULESET_VERSION,
    }


def _child(
    strategy: str, value: object, profile: object
) -> tuple[dict[str, object], dict[str, object]]:
    wrapper: dict[str, object] = {"strategy_input": value, "monthly_resources": profile}
    raw_jcs = _codec.canonical_json(wrapper)
    evidence: dict[str, object] = {
        "strategy": strategy,
        "versions": _versions(strategy),
        "raw_request_jcs": raw_jcs,
    }
    try:
        raw = _resources.child_input(strategy, value)
    except _resources.Rejected as error:
        outcome = _resources.failure(error)
        evidence["admission_failure"] = outcome
        return outcome, evidence
    evidence["input_classification"] = _basis._classification(strategy, raw)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
    # Successor engines own wrapper, contract, cash and output semantics. Errors
    # outside their canonical failure types propagate to the creation boundary.
    sealed = (
        _financing.evaluate(raw_jcs, strategy)
        if strategy in ("sac", "price")
        else _rent.evaluate(raw_jcs)
        if strategy == "rent"
        else _consortium.evaluate(raw_jcs)
    )
    outcome = _codec.parse_canonical_object(sealed)
    _validate_child(outcome, strategy, _resources.normalize(profile))
    evidence["sealed_outcome_jcs"] = sealed
    return outcome, evidence


def _validate_child(
    outcome: dict[str, object], strategy: str, profile: dict[str, object]
) -> None:
    """Own the closed successor outcome boundary, including cash failures.

    No historical outcome validator can admit the new funding policy. Replay
    additionally compares every value with complete deterministic reexecution.
    """
    if outcome.get("kind") == "failure":
        if (
            outcome.keys() != {"kind", "code", "detail"}
            or outcome["code"]
            not in {
                "invalid_input",
                "unsupported_rate_convention",
                "unsupported_rule",
                "unsupported_contract_clause",
                "infeasible_scenario",
            }
            or not isinstance(outcome["detail"], str)
        ):
            raise ValueError("resource-aware child failure is invalid")
        return
    if outcome.get("kind") != "success" or outcome.keys() != {
        "kind",
        "normalized_input",
        "trace",
    }:
        raise ValueError("resource-aware child success is invalid")
    normalized = outcome["normalized_input"]
    trace = outcome["trace"]
    if (
        not isinstance(normalized, dict)
        or normalized.keys() != {"strategy_input", "monthly_resources"}
        or not isinstance(trace, dict)
    ):
        raise ValueError("resource-aware child evidence is invalid")
    admitted = cast(dict[str, object], normalized)
    if admitted["monthly_resources"] != profile:
        raise ValueError("child resources differ from common profile")
    _validate_normalized(strategy, admitted["strategy_input"])
    rows = cast(dict[str, object], trace)
    fields = {"comparison_ledger", "resource_postings"}
    fields |= (
        {"contractual_schedule"}
        if strategy in ("sac", "price")
        else {"monthly_postings"}
        if strategy == "rent"
        else {"contractual_schedule", "monthly_postings"}
    )
    if rows.keys() != fields:
        raise ValueError("resource-aware child trace is invalid")
    ledger = _rows(
        rows["comparison_ledger"], set(_resources.ledger_row(0, 0)) - {"month"}, 61, 0
    )
    posted = _rows(
        rows["resource_postings"],
        {
            "income_total",
            "external_expense_total",
            "available_resources",
            "opening_cash",
            "cash_after_external_expenses",
            "closing_cash",
        },
        60,
    )
    for month, (resource, posting) in enumerate(
        zip(cast(list[dict[str, object]], profile["months"]), posted, strict=True), 1
    ):
        if (
            any(
                posting[name] != resource[name]
                for name in (
                    "income_total",
                    "external_expense_total",
                    "available_resources",
                )
            )
            or posting["opening_cash"] != ledger[month - 1]["cash"]
            or posting["closing_cash"] != ledger[month]["cash"]
            or _resources.cents(posting["cash_after_external_expenses"])
            != _resources.cents(posting["opening_cash"])
            + _resources.cents(resource["available_resources"])
        ):
            raise ValueError("resource postings differ from common profile or ledger")
    strategy_input = cast(dict[str, object], admitted["strategy_input"])
    if strategy in ("sac", "price"):
        _rows(
            rows["contractual_schedule"],
            {
                "amortization",
                "closing_principal_balance",
                "fee",
                "interest",
                "opening_principal_balance",
                "payment",
            },
            cast(int, strategy_input["term_months"]),
        )
    elif strategy == "rent":
        _rows(
            rows["monthly_postings"],
            {
                "opening_liquid_financial_assets",
                "investment_return",
                "rent",
                "monthly_contribution",
                "closing_liquid_financial_assets",
            },
            60,
        )
    else:
        _rows(
            rows["contractual_schedule"],
            {
                "credit_component",
                "administration_fee",
                "reserve_fund",
                "insurance",
                "payment",
            },
            cast(int, strategy_input["term_months"]),
        )
        _rows(
            rows["monthly_postings"],
            {
                "contractual_payment",
                "waiting_housing_cost",
                "cash_top_up",
                "cash_outflow",
                "transferred_credit_right",
                "credit_letter_applied",
            },
            60,
        )


def _amount(value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]{2}", value) is not None
        and value != "-0.00"
    )


def _rows(
    value: object, fields: set[str], length: int, start: int = 1
) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(cast(list[object], value)) != length:
        raise ValueError("resource-aware child trace length is invalid")
    output: list[dict[str, object]] = []
    for month, item in enumerate(cast(list[object], value), start):
        if not isinstance(item, dict):
            raise ValueError("resource-aware child row is invalid")
        row = cast(dict[str, object], item)
        if (
            row.keys() != {"month", *fields}
            or type(row["month"]) is not int
            or row["month"] != month
            or not all(_amount(row[name]) for name in fields)
        ):
            raise ValueError("resource-aware child row is invalid")
        output.append(row)
    return output


def _validate_normalized(strategy: str, value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError("resource-aware normalized strategy is invalid")
    normalized = cast(dict[str, object], value)
    if strategy in ("sac", "price", "rent"):
        amounts = (
            {
                "comparison_opening_cash",
                "property_price",
                "principal",
                "cash_down_payment",
                "fee_amount",
            }
            if strategy != "rent"
            else {
                "comparison_opening_cash",
                "starting_monthly_rent",
                "initial_invested_capital",
                "monthly_contribution",
            }
        )
        rates = (
            {"effective_monthly_rate"}
            if strategy != "rent"
            else {"effective_annual_rent_adjustment", "effective_monthly_net_return"}
        )
        period = "term_months" if strategy != "rent" else "first_rent_adjustment_month"
        if (
            normalized.keys() != {*amounts, *rates, period}
            or not all(
                _amount(normalized[name]) and _resources.cents(normalized[name]) >= 0
                for name in amounts
            )
            or type(normalized[period]) is not int
            or cast(int, normalized[period]) < 1
        ):
            raise ValueError("resource-aware normalized strategy is invalid")
        for name in rates:
            rate = normalized[name]
            try:
                if not isinstance(rate, str) or not 0 <= Fraction(rate) <= 1:
                    raise ValueError("resource-aware normalized rate is invalid")
            except (ValueError, ZeroDivisionError) as error:
                raise ValueError("resource-aware normalized rate is invalid") from error
        return
    amounts = {
        "comparison_opening_cash",
        "property_price",
        "credit_letter",
        "cash_top_up",
    }
    declarations = {
        "term_months",
        "monthly_schedule",
        "credit_components_apply_to_credit_letter",
        "correction",
        "reserve_fund_treatment",
        "installment_schedule_treatment",
        "scenario_kind",
        "contemplation_month",
        "property_purchase_event",
        "waiting_housing_costs",
    }
    inputs = amounts | declarations | {"requested_features"}
    if normalized.keys() != inputs | {
        "input_classification",
        "reference_basis",
        "rule_conventions",
    } or not all(_amount(normalized[name]) for name in amounts):
        raise ValueError("resource-aware normalized consortium is invalid")
    # This exact projection has the retained raw structure, after checking every
    # successor field. Pinned normalization validates all nested contractual data.
    raw = {name: normalized[name] for name in inputs}
    try:
        checked = _codec._normalize(raw)  # pyright: ignore[reportPrivateUsage]  # Pinned support normalization.
    except _codec._Rejected as error:  # pyright: ignore[reportPrivateUsage]  # Pinned failure type.
        raise ValueError("resource-aware normalized consortium is invalid") from error
    checked["rule_conventions"] = {
        **cast(dict[str, object], checked["rule_conventions"]),
        "ruleset_version": _consortium.RULESET_VERSION,
    }
    if normalized != checked:
        raise ValueError("resource-aware normalized consortium is invalid")


def evaluate(raw_request_jcs: str) -> str:
    bound = _codec.parse_canonical_object(raw_request_jcs)
    if bound.keys() != {"metadata", "comparison"}:
        raise ValueError("comparison evidence structure is invalid")
    metadata = _basis.validate_metadata(bound["metadata"])
    try:
        request = _basis._object(bound["comparison"])  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        if request.keys() != {
            "shared",
            "constraints",
            "financing",
            "rent",
            "consortium",
            "monthly_resources",
        }:
            raise _resources.Rejected(
                "invalid_input", "comparison request fields are incomplete or unknown"
            )
        # Exactly the retained shape, after v2's closed boundary is checked.
        basis = {
            name: value
            for name, value in request.items()
            if name != "monthly_resources"
        }
        shared, constraints = _basis._shared(basis)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        resources = _resources.normalize(request["monthly_resources"])
        _basis._mismatches(basis, shared)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
    except (_basis._Rejected, _resources.Rejected) as error:  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        return _codec.canonical_json(
            {
                **{"kind": "failure", "code": error.code, "detail": error.detail},
                "metadata": metadata,
            }
        )
    alternatives: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    scores: dict[int, list[str]] = {}
    for strategy in _ORDER:
        outcome, child = _child(
            strategy,
            request["financing" if strategy in ("sac", "price") else strategy],
            request["monthly_resources"],
        )
        evidence.append(child)
        if outcome["kind"] == "failure":
            alternatives.append(
                {"strategy": strategy, "status": "domain_failure", "failure": outcome}
            )
            continue
        alternative = _basis._measure(strategy, outcome, constraints)  # pyright: ignore[reportPrivateUsage]  # Deliberately pinned retained helper.
        alternatives.append(alternative)
        if alternative["status"] == "eligible":
            metrics = cast(dict[str, object], alternative["metrics"])
            final = cast(dict[str, object], metrics["final_ledger_row"])
            scores.setdefault(_resources.cents(final["net_worth"]), []).append(strategy)
    groups = [scores[score] for score in sorted(scores, reverse=True)]
    eligible_count = sum(len(group) for group in groups)
    return _codec.canonical_json(
        {
            "kind": "success",
            "metadata": metadata,
            "normalized_input": {
                "shared": {
                    **shared,
                    **{
                        name: _resources.money(_resources.cents(shared[name]))
                        for name in (
                            "comparison_opening_cash",
                            "property_price",
                            "starting_monthly_rent",
                        )
                    },
                    "rent_adjustment_rate_value": format(
                        Decimal(cast(str, shared["rent_adjustment_rate_value"])), "f"
                    ),
                },
                "constraints": {
                    name: _resources.money(_resources.cents(value))
                    for name, value in constraints.items()
                },
                "monthly_resources": resources,
                "rule_conventions": {
                    "currency": "BRL",
                    "value_basis": "nominal",
                    "rounding": "ROUND_HALF_UP",
                    "comparison_horizon_months": 60,
                    "inflation": "documented_zero",
                    "property_appreciation": "documented_zero",
                    "transaction_costs": "documented_zero",
                    "reference_basis": "synthetic_contract_reference",
                    "monthly_posting_order": "opening_asset_return_then_common_resources_then_obligations_then_declared_contribution",
                    "surplus": "non_interest_bearing_cash",
                    "shortfall": "accumulated_cash_only_otherwise_exclude",
                },
                "input_classification": {
                    "shared": {
                        **_basis._classification("rent", shared),  # pyright: ignore[reportPrivateUsage]  # Pinned classification.
                        "property_price": "projected_assumption",
                    },
                    "constraints": {name: "user_constraint" for name in constraints},
                    "monthly_resources": "explicit_component_classifications_and_provenance",
                },
            },
            "alternatives": alternatives,
            "result": {
                "status": "no_eligible"
                if not eligible_count
                else "single_eligible"
                if eligible_count == 1
                else "compared",
                "objective": "maximize_net_worth_at_month_60",
                "ranking_groups": groups,
            },
            "trace": {"child_evidence": evidence, "limitations": list(_LIMITATIONS)},
        }
    )
