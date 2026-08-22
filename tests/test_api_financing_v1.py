"""HTTP and OpenAPI contracts for the bounded v1 financing projection."""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from openapi_spec_validator import validate

from application.financing_projection import ApplicationFailure
from api.error_mapping import public_error_from_application
from api.main import app
from api import resource_limits
from api.routes import financing as financing_route
from domain.financing import replay_v3
from domain.values import FailureCode


_BASE_FINANCING: dict[str, object] = {
    "comparison_opening_cash": "20000.00",
    "property_price": "1500.00",
    "cash_down_payment": "300.00",
    "principal": "1200.00",
    "term_months": 12,
    "rate_value": "0.01",
    "rate_convention": "effective_monthly",
    "fgts_amount": None,
    "subsidy_amount": None,
    "tax_amount": None,
    "transaction_cost_amount": None,
    "fee_amount": None,
    "insurance_amount": None,
    "indexation": "not_requested",
    "extraordinary_amortization_amount": None,
}


def _payload(strategy: object = "sac", **changes: object) -> dict[str, object]:
    return {
        "strategy": strategy,
        "financing": {**_BASE_FINANCING, **changes},
    }


@pytest.mark.parametrize("strategy", ("sac", "price"))
def test_v1_projection_matches_the_explicit_v3_domain_trace(strategy: object) -> None:
    client = TestClient(app)
    payload = _payload(strategy, fee_amount="2.50")

    response = client.post("/api/v1/financing/calculations", json=payload)

    assert response.status_code == 200
    body = response.json()
    expected = json.loads(
        replay_v3.evaluate(
            replay_v3.canonical_json(cast(dict[str, object], payload["financing"])),
            cast(replay_v3.Strategy, strategy),
        )
    )
    assert body == {
        "api_version": "v1",
        "strategy": cast(str, strategy),
        "contract_schema_version": "financing-replay-v3",
        "engine_version": "financing-centavo-safe-v3",
        "ruleset_version": "financing-ruleset-v2",
        "contractual_schedule": expected["trace"]["contractual_schedule"],
        "comparison_ledger": expected["trace"]["comparison_ledger"],
    }
    assert "data_snapshot_id" not in body
    assert len(body["comparison_ledger"]) == 61


def test_v1_projection_is_deterministic_and_fee_zero_is_equivalent() -> None:
    client = TestClient(app)
    absent = client.post("/api/v1/financing/calculations", json=_payload())
    repeated = client.post("/api/v1/financing/calculations", json=_payload())
    explicit_zero = client.post(
        "/api/v1/financing/calculations", json=_payload(fee_amount="0.00")
    )

    assert absent.status_code == repeated.status_code == explicit_zero.status_code == 200
    assert absent.json() == repeated.json() == explicit_zero.json()


@pytest.mark.parametrize(
    ("changes", "status_code", "code"),
    (
        ({"property_price": "1501.00"}, 422, "invalid_input"),
        ({"rate_convention": "nominal_monthly"}, 422, "unsupported_rate_convention"),
        ({"fgts_amount": "1.00"}, 422, "unsupported_rule"),
        ({"insurance_amount": "1.00"}, 422, "unsupported_contract_clause"),
    ),
)
def test_domain_failures_have_stable_public_errors(
    changes: dict[str, object], status_code: int, code: str
) -> None:
    response = TestClient(app).post("/api/v1/financing/calculations", json=_payload(**changes))

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert "detail" not in response.json()
    assert "message_pt_br" in response.json()


@pytest.mark.parametrize(
    ("code", "status_code"),
    (
        ("invalid_input", 422),
        ("unsupported_rate_convention", 422),
        ("unsupported_rule", 422),
        ("unsupported_contract_clause", 422),
        ("infeasible_scenario", 422),
        ("incompatible_contract_version", 409),
    ),
)
def test_every_domain_failure_category_has_a_public_status(code: str, status_code: int) -> None:
    error = public_error_from_application(ApplicationFailure(cast(FailureCode, code)))

    assert error.status_code == status_code
    assert error.code == code


@pytest.mark.parametrize(
    "changes",
    (
        {"principal": "1234567890123456789.00"},
        {"rate_value": "1E+10"},
        {"rate_value": "1.1"},
        {"term_months": 601},
    ),
)
def test_public_resource_envelope_rejects_invalid_input_before_domain(
    changes: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_domain_execution(*_: object, **__: object) -> object:
        raise AssertionError("resource-rejected input reached the application use case")

    monkeypatch.setattr(
        financing_route, "calculate_v3_financing_projection", unexpected_domain_execution
    )
    response = TestClient(app).post("/api/v1/financing/calculations", json=_payload(**changes))

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


def test_oversized_body_uses_the_public_413_error() -> None:
    response = TestClient(app).post(
        "/api/v1/financing/calculations",
        content=b"{" + b"x" * resource_limits.MAX_REQUEST_BYTES + b"}",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


def test_maximum_admitted_projection_stays_within_the_response_budget() -> None:
    maximum = "999999999999999999.99"
    response = TestClient(app).post(
        "/api/v1/financing/calculations",
        json=_payload(
            comparison_opening_cash=maximum,
            property_price=maximum,
            cash_down_payment="0.00",
            principal=maximum,
            term_months=600,
            rate_value="1.000000000000",
            fee_amount=maximum,
        ),
    )

    assert response.status_code == 200
    assert len(response.content) <= resource_limits.MAX_RESPONSE_BYTES


def test_response_limit_uses_the_versioned_error_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resource_limits, "MAX_RESPONSE_BYTES", 1)

    response = TestClient(app).post("/api/v1/financing/calculations", json=_payload())

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


def test_openapi_is_valid_and_describes_only_the_v1_projection_contract() -> None:
    document = app.openapi()

    validate(document)
    assert set(document["paths"]) == {"/api/v1/financing/calculations"}
    operation = document["paths"]["/api/v1/financing/calculations"]["post"]
    assert set(operation["responses"]) >= {"200", "409", "413", "422", "500"}
    schema = document["components"]["schemas"]["FinancingInputV1"]
    assert "data_snapshot_id" not in schema["properties"]
    assert "data_snapshot_id" not in json.dumps(document)
    assert document["info"]["version"] == "1.0.0"


def test_domain_has_no_framework_or_application_imports() -> None:
    for path in Path("domain").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_names = [node.module]
            else:
                continue
            assert all(
                name != "fastapi"
                and not name.startswith("fastapi.")
                and name != "api"
                and not name.startswith("api.")
                and name != "application"
                and not name.startswith("application.")
                for name in imported_names
            ), path


def test_api_has_no_direct_domain_imports() -> None:
    for path in Path("api").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_names = [node.module]
            else:
                continue
            assert all(name != "domain" and not name.startswith("domain.") for name in imported_names), path
