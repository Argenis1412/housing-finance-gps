"""Historical byte references and complete monthly-resource evidence verification."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, asdict, replace
from decimal import ROUND_DOWN, localcontext
import hashlib
from pathlib import Path
from typing import cast

import pytest

from domain import comparison_v2, rent_replay_v2
from domain.comparison import (
    create_comparison_v1_envelope,
    create_comparison_v2_envelope,
    replay_comparison,
)
from domain.consortium import replay_v1 as codec
from domain.consortium import replay_v2 as consortium
from domain.financing import replay_v4 as financing
from domain.values import DomainFailure
from tests.test_comparison_domain import (
    raw_request as historical_raw,
    synthetic_request,
)
from tests.test_monthly_resources_comparison import (
    children,
    envelope,
    outcome,
    raw_request,
    request,
    result,
)


def test_prechange_complete_historical_comparison_hashes_and_replay() -> None:
    # Captured on clean ef68b98 before production changes; hash all envelope bytes.
    base = synthetic_request()
    cases = [
        historical_raw(),
        {},
        historical_raw(
            replace(base, rent=replace(base.rent, initial_invested_capital="200.01"))
        ),
        historical_raw(
            replace(base, financing=replace(base.financing, insurance_amount="1.00"))
        ),
        historical_raw(
            replace(
                base,
                financing=replace(
                    base.financing,
                    cash_down_payment="59.99",
                    principal="0.01",
                    fee_amount="0.01",
                ),
            )
        ),
    ]
    hashes = [
        "0e99914b18a6c561212f0f5f64447001afe9199da9d019bf833edc828588e20a",
        "486ed2cdca0579bd0636dcfa422820eb2d1c7e4730eec77ceaf1a735c61a3e4d",
        "5c009f562b8a3b3a938a1842cfe6ab74549d17415f34bbeabbd392ff81b441ad",
        "ac5e5926b22cb4cea85d5fef4d967f8b455aeb39ee76301f7d5e6ee91703d63a",
        "716fa1db8fab5b82b0724d47891ee9533732ac4e06548d0694036e729b455442",
    ]
    for raw, expected in zip(cases, hashes, strict=True):
        value = create_comparison_v1_envelope(
            raw_request_jcs=codec.canonical_json(raw),
            data_snapshot_id="synthetic-historical-reference",
            calculated_at="2026-11-03T12:00:00Z",
        )
        assert (
            hashlib.sha256(codec.canonical_json(asdict(value)).encode()).hexdigest()
            == expected
        )
        if raw:
            assert not isinstance(replay_comparison(value), DomainFailure)
        else:
            assert replay_comparison(value) == DomainFailure(
                "invalid_input", "comparison request fields are incomplete or unknown"
            )


def test_new_versions_bind_planned_resources_for_success_and_failure() -> None:
    actual = result()
    assert replay_comparison(actual.envelope) == actual
    sealed = codec.parse_canonical_object(actual.envelope.sealed_outcome_jcs)
    engines = [
        "financing-monthly-resources-v4",
        "financing-monthly-resources-v4",
        "rent-plus-monthly-resources-v2",
        "consortium-monthly-resources-v2",
    ]
    assert [
        cast(dict[str, object], e["versions"])["engine_version"]
        for e in children(sealed)
    ] == engines
    assert actual.envelope.contract_schema_version == "comparison-simulation-v2"
    for raw in ({}, raw_request(request("0.00", "1.00", "0.00"))):
        value = envelope(raw)
        verified = replay_comparison(value)
        assert verified != DomainFailure(
            "incompatible_contract_version",
            "historical comparison equivalence cannot be proven",
        )
    # The new boundary does not inject a zero profile into a historical request.
    assert outcome(historical_raw())["kind"] == "failure"


@pytest.mark.parametrize(
    "field", ["contract_schema_version", "engine_version", "ruleset_version"]
)
def test_version_tuple_is_selected_before_parsing(field: str) -> None:
    value = replace(envelope(), **{field: "unknown"}, raw_request_jcs="not-json")
    verified = replay_comparison(value)
    assert (
        isinstance(verified, DomainFailure)
        and verified.code == "incompatible_contract_version"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "parent_amount",
        "parent_composition",
        "parent_timing",
        "child_amount",
        "child_composition",
        "child_provenance",
        "child_convention",
        "child_versions",
        "child_outcome",
        "resource_posting",
        "resource_total",
        "metric",
        "group",
        "metadata",
        "unknown_outcome",
        "noncanonical",
    ],
)
def test_complete_reexecution_rejects_tampering_despite_identical_snapshot(
    mutation: str,
) -> None:
    value = envelope()
    bound = codec.parse_canonical_object(value.raw_request_jcs)
    sealed = codec.parse_canonical_object(value.sealed_outcome_jcs)
    raw = cast(dict[str, object], bound["comparison"])
    entry = children(sealed)[0]
    wrapper = codec.parse_canonical_object(entry["raw_request_jcs"])
    parent_profile = cast(dict[str, object], raw["monthly_resources"])
    child_profile = cast(dict[str, object], wrapper["monthly_resources"])
    profile = parent_profile if mutation.startswith("parent") else child_profile
    months = cast(list[dict[str, object]], profile["months"])
    component = cast(list[dict[str, object]], months[0]["income_components"])[0]
    if mutation in ("parent_amount", "child_amount"):
        component["amount"] = "3.01"
    elif mutation in ("parent_composition", "child_composition"):
        # Equal totals and net resources still do not prove equal composition.
        component["component_id"] = "income-replaced"
    elif mutation == "parent_timing":
        component["amount"] = "2.00"
        cast(list[dict[str, object]], months[1]["income_components"])[0]["amount"] = (
            "4.00"
        )
    elif mutation == "child_provenance":
        component["source_reference"] = "different-source"
    elif mutation == "child_convention":
        profile["income_basis"] = "gross"
    elif mutation == "child_versions":
        cast(dict[str, object], entry["versions"])["ruleset_version"] = (
            "financing-ruleset-v2"
        )
    elif mutation == "child_outcome":
        entry["sealed_outcome_jcs"] = "{}"
    elif mutation == "resource_posting":
        child = codec.parse_canonical_object(entry["sealed_outcome_jcs"])
        cast(
            list[dict[str, object]],
            cast(dict[str, object], child["trace"])["resource_postings"],
        )[0]["available_resources"] = "2.01"
        entry["sealed_outcome_jcs"] = codec.canonical_json(child)
    elif mutation == "resource_total":
        common = cast(
            dict[str, object],
            cast(dict[str, object], sealed["normalized_input"])["monthly_resources"],
        )
        cast(list[dict[str, object]], common["months"])[0]["income_total"] = "3.01"
    elif mutation == "metric":
        cast(
            dict[str, object],
            cast(list[dict[str, object]], sealed["alternatives"])[0]["metrics"],
        )["minimum_liquidity"] = "0.00"
    elif mutation == "group":
        cast(dict[str, object], sealed["result"])["ranking_groups"] = [["rent"]]
    elif mutation == "metadata":
        cast(dict[str, object], bound["metadata"])["data_snapshot_id"] = "different"
    elif mutation == "unknown_outcome":
        sealed["unadmitted"] = True
    if mutation in (
        "child_amount",
        "child_composition",
        "child_provenance",
        "child_convention",
    ):
        entry["raw_request_jcs"] = codec.canonical_json(wrapper)
    verified = replay_comparison(
        replace(
            value,
            raw_request_jcs=codec.canonical_json(bound),
            sealed_outcome_jcs=codec.canonical_json(sealed)
            + (" " if mutation == "noncanonical" else ""),
        )
    )
    assert (
        isinstance(verified, DomainFailure)
        and verified.code == "incompatible_contract_version"
    )


@pytest.mark.parametrize("exception", [ValueError, RuntimeError, ArithmeticError])
def test_unexpected_creation_errors_propagate_and_replay_fails_closed(
    monkeypatch: pytest.MonkeyPatch, exception: type[Exception]
) -> None:
    value = envelope()

    def broken(*args: object) -> str:
        raise exception("injected execution error")

    monkeypatch.setattr(financing, "evaluate", broken)
    with pytest.raises(exception, match="injected execution"):
        envelope()
    verified = replay_comparison(value)
    assert (
        isinstance(verified, DomainFailure)
        and verified.code == "incompatible_contract_version"
    )
    raw = raw_request()
    cast(dict[str, object], raw["financing"])["principal"] = None
    assert outcome(raw)["kind"] == "success"


def test_immutable_inputs_results_and_decimal_context_independence() -> None:
    value = request()
    value = replace(
        value,
        financing=replace(value.financing, cash_down_payment="1.01", principal="58.99"),
    )
    baseline = result(value)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert result(value) == baseline
        assert replay_comparison(baseline.envelope) == baseline
    with pytest.raises(FrozenInstanceError):
        setattr(value.monthly_resources.months[0], "month", 2)
    with pytest.raises(FrozenInstanceError):
        setattr(baseline.envelope, "engine_version", "changed")


@pytest.mark.parametrize(
    "raw", ["[]", '{"x":1,"x":1}', '{"x":1.0}', '{"x":NaN}', '{ "x": 1 }']
)
def test_noncanonical_raw_never_creates_new_evidence(raw: str) -> None:
    with pytest.raises(ValueError):
        create_comparison_v2_envelope(
            raw_request_jcs=raw,
            data_snapshot_id="synthetic",
            calculated_at="2026-11-03T12:00:00Z",
        )


def test_retained_dependency_boundaries_and_no_closed_cash_overlay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from domain import rent_replay_v1
    from domain.consortium import replay_v1
    from domain.financing import replay_v3

    value = envelope()

    def broken(*args: object) -> None:
        raise AssertionError("closed cash execution used")

    monkeypatch.setattr(rent_replay_v1, "calculate", broken)
    monkeypatch.setattr(replay_v1, "_trace", broken)
    monkeypatch.setattr(replay_v3, "_ledger", broken)
    assert not isinstance(replay_comparison(value), DomainFailure)
    expected: dict[str, set[tuple[str, str]]] = {
        "domain/monthly_resources_v1.py": set(),
        "domain/financing/replay_v4.py": {
            ("domain", "monthly_resources_v1"),
            ("domain.consortium", "replay_v1"),
            ("domain.financing", "replay_v3"),
        },
        "domain/rent_replay_v2.py": {
            ("domain", "monthly_resources_v1"),
            ("domain", "rent_replay_v1"),
            ("domain.consortium", "replay_v1"),
        },
        "domain/consortium/replay_v2.py": {
            ("domain", "monthly_resources_v1"),
            ("domain.consortium", "replay_v1"),
        },
        "domain/comparison_v2.py": {
            ("domain", "comparison_v1"),
            ("domain", "monthly_resources_v1"),
            ("domain", "rent_replay_v2"),
            ("domain.consortium", "replay_v1"),
            ("domain.consortium", "replay_v2"),
            ("domain.financing", "replay_v4"),
        },
    }
    for name, permitted in expected.items():
        tree = ast.parse(Path(name).read_text())
        imports = {
            (node.module, alias.name)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("domain")
            for alias in node.names
        }
        assert imports == permitted


@pytest.mark.parametrize("strategy", ["sac", "rent", "consortium"])
def test_successors_reject_unclosed_wrappers_and_non_objects(strategy: str) -> None:
    def evaluate(raw: str) -> str:
        if strategy == "sac":
            return financing.evaluate(raw, "sac")
        return (rent_replay_v2 if strategy == "rent" else consortium).evaluate(raw)

    with pytest.raises(ValueError):
        evaluate("[]")
    assert codec.parse_canonical_object(evaluate("{}"))["code"] == "invalid_input"


def test_invalid_bound_structure_and_successor_outcome_do_not_hide_execution_bugs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError):
        comparison_v2.evaluate("{}")

    def broken(*args: object) -> str:
        return codec.canonical_json(
            {"kind": "failure", "code": "unknown", "detail": "invalid"}
        )

    monkeypatch.setattr(financing, "evaluate", broken)
    with pytest.raises(ValueError, match="child failure"):
        envelope()


@pytest.mark.parametrize("strategy", ["sac", "rent", "consortium"])
@pytest.mark.parametrize(
    "mutation",
    [
        "normalized_type",
        "normalized_extra",
        "profile_binding",
        "strategy_type",
        "strategy_unknown",
        "strategy_amount",
        "ledger_extra",
        "resource_missing",
        "posting_amount",
        "posting_month",
        "posting_binding",
        "trace_length",
    ],
)
def test_closed_successor_outcomes_reject_nested_execution_defects(
    monkeypatch: pytest.MonkeyPatch,
    strategy: str,
    mutation: str,
) -> None:
    original = envelope()
    sealed = codec.parse_canonical_object(original.sealed_outcome_jcs)
    index = {"sac": 0, "rent": 2, "consortium": 3}[strategy]
    child = codec.parse_canonical_object(children(sealed)[index]["sealed_outcome_jcs"])
    normalized = cast(dict[str, object], child["normalized_input"])
    trace = cast(dict[str, object], child["trace"])
    ledger = cast(list[dict[str, object]], trace["comparison_ledger"])
    postings = cast(list[dict[str, object]], trace["resource_postings"])
    if mutation == "normalized_type":
        child["normalized_input"] = None
    elif mutation == "normalized_extra":
        normalized["extra"] = True
    elif mutation == "profile_binding":
        normalized["monthly_resources"] = {}
    elif mutation == "strategy_type":
        normalized["strategy_input"] = None
    elif mutation == "strategy_unknown":
        cast(dict[str, object], normalized["strategy_input"])["extra"] = True
    elif mutation == "strategy_amount":
        cast(dict[str, object], normalized["strategy_input"])[
            "comparison_opening_cash"
        ] = "invalid"
    elif mutation == "ledger_extra":
        ledger[0]["extra"] = True
    elif mutation == "resource_missing":
        del postings[0]["available_resources"]
    elif mutation == "posting_amount":
        postings[0]["income_total"] = "NaN"
    elif mutation == "posting_month":
        postings[0]["month"] = True
    elif mutation == "posting_binding":
        postings[0]["income_total"] = "3.01"
    elif mutation == "trace_length":
        ledger.pop()

    def broken(*args: object) -> str:
        return codec.canonical_json(child)

    engine = (
        financing
        if strategy == "sac"
        else rent_replay_v2
        if strategy == "rent"
        else consortium
    )
    monkeypatch.setattr(engine, "evaluate", broken)
    with pytest.raises(ValueError):
        envelope()
    verified = replay_comparison(original)
    assert (
        isinstance(verified, DomainFailure)
        and verified.code == "incompatible_contract_version"
    )
