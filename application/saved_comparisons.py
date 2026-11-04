"""Versioned synthetic evidence storage use cases, independent of HTTP and SQLite."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Protocol, cast
from uuid import uuid4

from application.comparison_simulation import ComparisonApplicationFailure, project_comparison_v2_envelope
from domain.comparison import ComparisonSimulationEnvelope, create_comparison_v2_envelope
from domain.consortium.replay_v1 import canonical_json, parse_canonical_object


MAX_RECORD_BYTES = 16_777_216
_OPERATION = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_AGGREGATE = ("comparison-simulation-v2", "comparison-monthly-resources-v2", "comparison-ruleset-v2")
_VERSION_FIELDS = ("contract_schema_version", "engine_version", "ruleset_version")
_CHILDREN = {
    "sac": ("financing-replay-v4", "financing-monthly-resources-v4", "financing-ruleset-v3"),
    "price": ("financing-replay-v4", "financing-monthly-resources-v4", "financing-ruleset-v3"),
    "rent": ("rent-plus-replay-v2", "rent-plus-monthly-resources-v2", "rent-plus-ruleset-v2"),
    "consortium": ("consortium-replay-v2", "consortium-monthly-resources-v2", "consortium-ruleset-v2"),
}
_FAILURES = {"invalid_input", "unsupported_rate_convention", "unsupported_rule", "unsupported_contract_clause", "infeasible_scenario", "incompatible_contract_version"}


class SavedComparisonError(Exception):
    """Safe application/storage category; never carries user data or SQL detail."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True, slots=True)
class StoredComparison:
    simulation_id: str
    saved_at: str
    record_jcs: str
    sha256: str


@dataclass(frozen=True, slots=True)
class PreparedSave:
    created: bool
    body: bytes


class ComparisonTransaction(Protocol):
    def find(self, simulation_id: str) -> tuple[bool, StoredComparison | None]: ...
    def insert(self, record: StoredComparison) -> None: ...
    def summaries(self, limit: int, offset: int) -> list[tuple[str, str]]: ...
    def delete(self, simulation_id: str) -> None: ...


class ComparisonRepository(Protocol):
    def transaction(self, *, write: bool = False) -> AbstractContextManager[ComparisonTransaction]: ...


def validate_operation_id(value: str) -> None:
    if not _OPERATION.fullmatch(value):
        raise SavedComparisonError("invalid_input", 422)


def _clock() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("object required")
    return cast(dict[str, object], value)


def _failure(value: object) -> None:
    failure = _object(value)
    if failure.keys() != {"kind", "code", "detail"} or failure["kind"] != "failure" or failure["code"] not in _FAILURES or not isinstance(failure["detail"], str):
        raise ValueError("invalid sealed failure")


def _amount(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]{2}", value) is not None and value != "-0.00"


def _rows(value: object, fields: set[str], length: int, start: int = 1) -> None:
    if not isinstance(value, list) or len(cast(list[object], value)) != length:
        raise ValueError("incomplete evidence rows")
    for month, item in enumerate(cast(list[object], value), start):
        row = _object(item)
        if row.keys() != {"month", *fields} or type(row["month"]) is not int or row["month"] != month or not all(_amount(row[name]) for name in fields):
            raise ValueError("invalid evidence row shape")


def _profile(value: object) -> None:
    profile = _object(value)
    if profile.keys() != {"income_basis", "expense_scope", "months"} or not isinstance(profile["income_basis"], str) or not isinstance(profile["expense_scope"], str):
        raise ValueError("invalid stored profile")
    months = profile["months"]
    if not isinstance(months, list) or len(cast(list[object], months)) != 60:
        raise ValueError("incomplete stored profile")
    for month, value in enumerate(cast(list[object], months), 1):
        row = _object(value)
        if row.keys() != {"month", "income_components", "external_expenses", "income_total", "external_expense_total", "available_resources"} or type(row["month"]) is not int or row["month"] != month or not all(_amount(row[name]) for name in ("income_total", "external_expense_total", "available_resources")):
            raise ValueError("invalid stored profile row")
        for side in ("income_components", "external_expenses"):
            components = row[side]
            if not isinstance(components, list):
                raise ValueError("invalid stored components")
            for value in cast(list[object], components):
                component = _object(value)
                if component.keys() != {"component_id", "amount", "classification", "source_reference", "source_as_of", "assumption_reference"} or not _amount(component["amount"]) or not all(isinstance(component[key], str) for key in ("component_id", "source_reference", "source_as_of", "classification")):
                    raise ValueError("invalid component shape")
                if not (component["classification"] == "observed_data" and component["assumption_reference"] is None or component["classification"] == "projected_assumption" and isinstance(component["assumption_reference"], str)):
                    raise ValueError("invalid component classification")


def _child_success(sealed: dict[str, object], strategy: str, profile: object) -> None:
    normalized = _object(sealed["normalized_input"])
    if normalized.keys() != {"strategy_input", "monthly_resources"} or normalized["monthly_resources"] != profile:
        raise ValueError("incomplete normalized child")
    inputs = _object(normalized["strategy_input"])
    amounts = {"comparison_opening_cash", "property_price", "principal", "cash_down_payment", "fee_amount"} if strategy in {"sac", "price"} else {"comparison_opening_cash", "starting_monthly_rent", "initial_invested_capital", "monthly_contribution"} if strategy == "rent" else {"comparison_opening_cash", "property_price", "credit_letter", "cash_top_up"}
    if not all(_amount(inputs[name]) for name in amounts):
        raise ValueError("invalid normalized monetary shape")
    if strategy != "consortium":
        rates = {"effective_monthly_rate"} if strategy != "rent" else {"effective_annual_rent_adjustment", "effective_monthly_net_return"}
        period = "term_months" if strategy != "rent" else "first_rent_adjustment_month"
        if inputs.keys() != amounts | rates | {period} or type(inputs[period]) is not int or not all(isinstance(inputs[name], str) for name in rates):
            raise ValueError("invalid normalized child fields")
    else:
        strings = {"correction", "reserve_fund_treatment", "installment_schedule_treatment", "scenario_kind", "reference_basis"}
        booleans = {"credit_components_apply_to_credit_letter", "property_purchase_event"}
        fields = amounts | strings | booleans | {"term_months", "contemplation_month", "monthly_schedule", "waiting_housing_costs", "requested_features", "input_classification", "rule_conventions"}
        if inputs.keys() != fields or not all(isinstance(inputs[name], str) for name in strings) or not all(type(inputs[name]) is bool for name in booleans) or type(inputs["contemplation_month"]) is not int:
            raise ValueError("invalid normalized consortium fields")
        classification = _object(inputs["input_classification"])
        if classification.keys() != fields - {"reference_basis", "rule_conventions", "input_classification"} or not all(isinstance(value, str) for value in classification.values()):
            raise ValueError("incomplete consortium classification")
        conventions = _object(inputs["rule_conventions"])
        if conventions.keys() != {"comparison_months", "currency", "period", "rounding", "ruleset_version", "value_basis"} or conventions["comparison_months"] != 60 or not all(isinstance(conventions[key], str) for key in conventions if key != "comparison_months"):
            raise ValueError("incomplete consortium conventions")
        features = inputs["requested_features"]
        if not isinstance(features, list) or not all(isinstance(value, str) for value in cast(list[object], features)):
            raise ValueError("invalid features shape")
        _rows(inputs["waiting_housing_costs"], {"amount"}, min(inputs["contemplation_month"], 60))
    term = inputs.get("term_months", 60)
    if type(term) is not int or not 1 <= term <= 600:
        raise ValueError("invalid schedule length")
    if strategy == "consortium":
        _rows(inputs["monthly_schedule"], {"credit_component", "administration_fee", "reserve_fund", "insurance"}, term)
    trace = _object(sealed["trace"])
    fields = {"comparison_ledger", "resource_postings"} | ({"contractual_schedule"} if strategy in {"sac", "price"} else {"monthly_postings"} if strategy == "rent" else {"contractual_schedule", "monthly_postings"})
    if trace.keys() != fields:
        raise ValueError("incomplete child trace")
    _rows(trace["comparison_ledger"], {"cash", "liquid_financial_assets", "consortium_credit_right_balance", "property_value", "financing_principal_balance", "consortium_credit_obligation_balance", "recoverable_transfer", "nonrecoverable_housing_cost", "total_liabilities", "home_equity", "liquidity", "net_worth", "cumulative_housing_cost"}, 61, 0)
    _rows(trace["resource_postings"], {"income_total", "external_expense_total", "available_resources", "opening_cash", "cash_after_external_expenses", "closing_cash"}, 60)
    if strategy in {"sac", "price"}:
        _rows(trace["contractual_schedule"], {"amortization", "closing_principal_balance", "fee", "interest", "opening_principal_balance", "payment"}, term)
    elif strategy == "rent":
        _rows(trace["monthly_postings"], {"opening_liquid_financial_assets", "investment_return", "rent", "monthly_contribution", "closing_liquid_financial_assets"}, 60)
    else:
        _rows(trace["contractual_schedule"], {"credit_component", "administration_fee", "reserve_fund", "insurance", "payment"}, term)
        _rows(trace["monthly_postings"], {"contractual_payment", "waiting_housing_cost", "cash_top_up", "cash_outflow", "transferred_credit_right", "credit_letter_applied"}, 60)


def _structure(envelope: ComparisonSimulationEnvelope) -> None:
    """Codec/shape/identity checks only; no financial normalization or arithmetic."""
    raw = parse_canonical_object(envelope.raw_request_jcs)
    outcome = parse_canonical_object(envelope.sealed_outcome_jcs)
    metadata = {"data_snapshot_id": envelope.data_snapshot_id, "calculated_at": envelope.calculated_at, "timezone": envelope.timezone}
    if raw.keys() != {"metadata", "comparison"} or raw["metadata"] != metadata or outcome.get("metadata") != metadata:
        raise ValueError("metadata mismatch")
    comparison = _object(raw["comparison"])
    if comparison.keys() != {"shared", "constraints", "financing", "rent", "consortium", "monthly_resources"}:
        raise ValueError("invalid comparison shape")
    if outcome.keys() != {"kind", "metadata", "normalized_input", "alternatives", "result", "trace"} or outcome["kind"] != "success":
        raise ValueError("only aggregate successes are stored")
    normalized = _object(outcome["normalized_input"])
    _profile(normalized["monthly_resources"])
    trace = _object(outcome["trace"])
    if trace.keys() != {"child_evidence", "limitations"}:
        raise ValueError("invalid trace")
    alternatives = outcome["alternatives"]
    if not isinstance(alternatives, list) or len(cast(list[object], alternatives)) != 4:
        raise ValueError("invalid aggregate alternatives")
    for strategy, value in zip(_CHILDREN, cast(list[object], alternatives), strict=True):
        alternative = _object(value)
        if alternative["strategy"] != strategy:
            raise ValueError("invalid aggregate strategy")
        if alternative["status"] == "domain_failure":
            if alternative.keys() != {"strategy", "status", "failure"}:
                raise ValueError("invalid aggregate failure")
            _failure(alternative["failure"])
        elif alternative["status"] not in {"eligible", "constraint_infeasible"} or alternative.keys() != {"strategy", "status", "metrics", "violations", "comparison_ledger", "monthly_housing_outflows"}:
            raise ValueError("invalid complete alternative shape")
    children = trace["child_evidence"]
    if not isinstance(children, list) or len(cast(list[object], children)) != 4:
        raise ValueError("invalid child evidence")
    for (strategy, expected), value in zip(_CHILDREN.items(), cast(list[object], children), strict=True):
        child = _object(value)
        versions = _object(child["versions"])
        if child["strategy"] != strategy or versions.keys() != set(_VERSION_FIELDS):
            raise ValueError("invalid child identity")
        if tuple(versions[field] for field in _VERSION_FIELDS) != expected:
            raise SavedComparisonError("incompatible_contract_version", 409)
        child_raw = parse_canonical_object(child["raw_request_jcs"])
        if child_raw != {"strategy_input": comparison["financing" if strategy in {"sac", "price"} else strategy], "monthly_resources": comparison["monthly_resources"]}:
            raise ValueError("child request mismatch")
        base = {"strategy", "versions", "raw_request_jcs"}
        if "admission_failure" in child:
            if child.keys() != base | {"admission_failure"}:
                raise ValueError("invalid admission evidence")
            _failure(child["admission_failure"])
        else:
            if child.keys() != base | {"input_classification", "sealed_outcome_jcs"}:
                raise ValueError("invalid child seal")
            _object(child["input_classification"])
            sealed = parse_canonical_object(child["sealed_outcome_jcs"])
            if sealed.get("kind") == "failure":
                _failure(sealed)
            elif sealed.keys() == {"kind", "normalized_input", "trace"} and sealed["kind"] == "success":
                _child_success(sealed, strategy, normalized["monthly_resources"])
            else:
                raise ValueError("invalid sealed child shape")


def decode_record(record: StoredComparison, simulation_id: str) -> ComparisonSimulationEnvelope:
    """Recover supported evidence; never execute a retained evaluator."""
    try:
        if len(record.record_jcs.encode("utf-8")) > MAX_RECORD_BYTES or hashlib.sha256(record.record_jcs.encode("utf-8")).hexdigest() != record.sha256:
            raise ValueError("record integrity failure")
        wrapper = parse_canonical_object(record.record_jcs)
        if wrapper.keys() != {"record_schema_version", "simulation_id", "saved_at", "envelope"}:
            raise ValueError("invalid record fields")
        if wrapper["record_schema_version"] != "saved-comparison-v1":
            raise SavedComparisonError("incompatible_storage_version", 409)
        if wrapper["simulation_id"] != simulation_id or record.simulation_id != simulation_id or wrapper["saved_at"] != record.saved_at:
            raise ValueError("index metadata mismatch")
        validate_operation_id(simulation_id)
        timestamp = record.saved_at
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp):
            raise ValueError("invalid saved timestamp")
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        fields = _object(wrapper["envelope"])
        if fields.keys() != {*_VERSION_FIELDS, "data_snapshot_id", "calculated_at", "timezone", "raw_request_jcs", "sealed_outcome_jcs"} or any(not isinstance(v, str) for v in fields.values()):
            raise ValueError("invalid envelope fields")
        if tuple(fields[field] for field in _VERSION_FIELDS) != _AGGREGATE:
            raise SavedComparisonError("incompatible_contract_version", 409)
        envelope = ComparisonSimulationEnvelope(**cast(dict[str, str], fields))
        _structure(envelope)
        return envelope
    except SavedComparisonError as error:
        if error.code == "invalid_input":
            raise SavedComparisonError("stored_simulation_corrupt", 500) from None
        raise
    except Exception:
        raise SavedComparisonError("stored_simulation_corrupt", 500) from None


def _presentation(record: StoredComparison, simulation_id: str) -> dict[str, object]:
    try:
        result = project_comparison_v2_envelope(decode_record(record, simulation_id))
        if isinstance(result, ComparisonApplicationFailure):
            raise SavedComparisonError("stored_simulation_corrupt", 500)
        return {"api_version": "v1", "kind": "saved_comparison", "simulation_id": simulation_id, "saved_at": record.saved_at, "result": result}
    except SavedComparisonError:
        raise
    except Exception:
        raise SavedComparisonError("stored_simulation_corrupt", 500) from None



def save_comparison(
    repository: ComparisonRepository, operation_id: str, comparison: dict[str, object],
    prepare_response: Callable[[dict[str, object]], bytes], *,
    clock: Callable[[], str] = _clock,
    snapshot_factory: Callable[[], str] = lambda: f"comparison-{uuid4()}",
) -> PreparedSave:
    """Serialize a checked response inside the transaction; return only after commit."""
    validate_operation_id(operation_id)
    raw = canonical_json(comparison)
    with repository.transaction(write=True) as transaction:
        known, record = transaction.find(operation_id)
        if record is not None and not known:
            raise SavedComparisonError("stored_simulation_corrupt", 500)
        if known:
            if record is None:
                raise SavedComparisonError("simulation_deleted", 410)
            envelope = decode_record(record, operation_id)
            if parse_canonical_object(envelope.raw_request_jcs)["comparison"] != parse_canonical_object(raw):
                raise SavedComparisonError("operation_id_conflict", 409)
        else:
            envelope = create_comparison_v2_envelope(raw_request_jcs=raw, data_snapshot_id=snapshot_factory(), calculated_at=clock())
            outcome = parse_canonical_object(envelope.sealed_outcome_jcs)
            if outcome["kind"] == "failure":
                raise SavedComparisonError(cast(str, outcome["code"]), 422)
            saved_at = clock()
            encoded = canonical_json({"record_schema_version": "saved-comparison-v1", "simulation_id": operation_id, "saved_at": saved_at, "envelope": asdict(envelope)})
            if len(encoded.encode("utf-8")) > MAX_RECORD_BYTES:
                raise SavedComparisonError("evidence_too_large", 422)
            record = StoredComparison(operation_id, saved_at, encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest())
        try:
            body = prepare_response(_presentation(record, operation_id))
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            if known:
                raise SavedComparisonError("stored_simulation_corrupt", 500) from None
            raise
        except SavedComparisonError as error:
            if not known and error.code in {"stored_simulation_corrupt", "incompatible_contract_version", "incompatible_storage_version"}:
                raise RuntimeError("new comparison evidence failed its pinned structure") from None
            raise
        if not known:
            transaction.insert(record)
    return PreparedSave(not known, body)


def read_comparison(repository: ComparisonRepository, simulation_id: str) -> dict[str, object]:
    with repository.transaction() as transaction:
        known, record = transaction.find(simulation_id)
        if record is None:
            raise SavedComparisonError("simulation_deleted" if known else "simulation_not_found", 410 if known else 404)
        return _presentation(record, simulation_id)


def list_comparisons(repository: ComparisonRepository, limit: int = 20, offset: int = 0) -> dict[str, object]:
    if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 50 or not 0 <= offset <= 9_007_199_254_740_991:
        raise SavedComparisonError("invalid_input", 422)
    with repository.transaction() as transaction:
        rows = transaction.summaries(limit + 1, offset)
    return {"api_version": "v1", "kind": "saved_comparison_list", "items": [{"simulation_id": sid, "saved_at": saved_at} for sid, saved_at in rows[:limit]], "next_offset": offset + limit if len(rows) > limit else None}


def delete_comparison(repository: ComparisonRepository, simulation_id: str) -> None:
    with repository.transaction(write=True) as transaction:
        known, record = transaction.find(simulation_id)
        if not known and record is None:
            raise SavedComparisonError("simulation_not_found", 404)
        transaction.delete(simulation_id)
