"""Public creation contract, fail-closed representation and legacy isolation."""

from __future__ import annotations

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from dataclasses import replace
import json
from typing import cast

from fastapi.testclient import TestClient
from httpx import Response
from openapi_spec_validator import validate
import pytest

from api.main import app
from api import resource_limits
from api.routes import comparisons
from tests.test_monthly_resources_comparison import raw_request, request
from tests.test_monthly_resources_domain import component


PATH = "/api/v1/comparison/simulations"


def post(raw: dict[str, object] | None = None) -> Response:
    return TestClient(app).post(PATH, json={"comparison": raw if raw is not None else raw_request()})


def test_http_exposes_sealed_metrics_versions_and_resources_without_envelope() -> None:
    response = post()
    assert response.status_code == 200
    value = response.json()
    assert value["kind"] == "simulation_result" and value["status"] == "compared"
    assert value["ranking_groups"] == [["sac", "price"], ["consortium"], ["rent"]]
    assert value["normalized_input"]["monthly_resources"]["months"][0]["available_resources"] == "2.00"
    assert all(len(a["comparison_ledger"]) == 61 for a in value["alternatives"])
    assert response.headers["cache-control"] == "no-store"
    assert not {"raw_request_jcs", "sealed_outcome_jcs", "simulation_id"} & value.keys()


@pytest.mark.parametrize("key,value,index", [
    ("financing", None, 0), ("financing", {"principal": True}, 0),
    ("rent", [], 2), ("consortium", "not-an-object", 3),
])
def test_child_structural_failure_is_local(key: str, value: object, index: int) -> None:
    raw = raw_request()
    raw[key] = value
    response = post(raw)
    assert response.status_code == 200
    alternative = response.json()["alternatives"][index]
    assert alternative["status"] == "domain_failure"
    assert set(alternative) == {"strategy", "status", "failure"}
    assert "detail" not in alternative["failure"]


def test_unknown_consortium_clause_reaches_support_rejection() -> None:
    raw = raw_request()
    cast(dict[str, object], raw["consortium"])["cash_bid"] = "1.00"
    response = post(raw)
    assert response.status_code == 200
    assert response.json()["alternatives"][3]["failure"]["code"] == "unsupported_contract_clause"


def test_shared_failure_precedence_and_full_profile_admission_remain_global() -> None:
    raw = raw_request()
    cast(dict[str, object], raw["shared"])["rent_adjustment_rate_convention"] = "nominal_annual"
    raw["monthly_resources"] = None
    response = post(raw)
    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_rate_convention"
    raw = raw_request(request("0.00", "1.00", "0.00"))
    cast(list[dict[str, object]], cast(dict[str, object], raw["monthly_resources"])["months"])[-1]["income_components"] = None
    response = post(raw)
    assert response.status_code == 422
    assert set(response.json()) == {"api_version", "code", "message_pt_br"}


@pytest.mark.parametrize("body", [
    b'{"comparison":{},"comparison":{}}', b'{"comparison":{"shared":{"x":1,"x":2}}}',
    b'{"comparison":1.0}', b'{"comparison":1e0}', b'{"comparison":NaN}',
    b'{"comparison":Infinity}', b'{"comparison":9007199254740992}',
    b'{"comparison":"\\ud800"}', b'{"comparison":{"\\ud800":null}}', b'\xff',
    b'{', b'[' * 100 + b'0' + b']' * 100,
])
def test_ambiguous_representation_never_executes_application(body: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_: object, **__: object) -> object:
        raise AssertionError("application must not run")
    monkeypatch.setattr(comparisons, "create_comparison_simulation", forbidden)
    response = TestClient(app).post(PATH, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["api_version"] == "v1" and response.json()["code"] == "invalid_input"


def test_noncanonical_http_json_is_canonicalized_and_observed_null_is_preserved() -> None:
    value = request()
    first, *rest = value.monthly_resources.months
    value = replace(value, monthly_resources=replace(value.monthly_resources, months=(replace(first, income_components=(component("income-a", "3.00", projected=False),)), *rest)))
    response = TestClient(app).post(PATH, content=json.dumps({"comparison": raw_request(value)}, indent=2).encode(), headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    item = response.json()["normalized_input"]["monthly_resources"]["months"][0]["income_components"][0]
    assert item["assumption_reference"] is None


def test_versioned_errors_include_validation_body_limit_and_response_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    response = TestClient(app).post(PATH, json={})
    assert response.status_code == 422 and response.json()["api_version"] == "v1"
    response = TestClient(app).post(PATH, content=b" " * (resource_limits.COMPARISON_MAX_REQUEST_BYTES + 1))
    assert response.status_code == 413 and response.json()["code"] == "request_too_large"
    monkeypatch.setattr(resource_limits, "COMPARISON_MAX_RESPONSE_BYTES", 1)
    response = post()
    assert response.status_code == 422 and response.json()["code"] == "response_too_large"


def test_trailing_slash_uses_comparison_admission_before_redirect() -> None:
    client = TestClient(app)
    response = client.post(PATH + "/", content=b" " * 8_193 + json.dumps({"comparison": raw_request()}).encode(), headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    response = client.post(PATH + "/", content=b" " * (resource_limits.COMPARISON_MAX_REQUEST_BYTES + 1))
    assert response.status_code == 413
    assert response.json()["api_version"] == "v1"
    assert response.json()["code"] == "request_too_large"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("container", ["array", "object"])
@pytest.mark.parametrize("leaf", [b"", b"0"])
def test_json_container_depth_boundary_includes_empty_containers(container: str, leaf: bytes) -> None:
    def nested(depth: int) -> bytes:
        if container == "array":
            return b"[" * depth + leaf + b"]" * depth
        return b'{"x":' * (depth - 1) + (b'{"x":0}' if leaf else b"{}") + b"}" * (depth - 1)
    resource_limits._admit_comparison_json(nested(64))  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match="JSON depth"):
        resource_limits._admit_comparison_json(nested(65))  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("boundary", ["middleware", "route"])
def test_unexpected_errors_are_safe_and_not_logged(boundary: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    def broken(*_: object, **__: object) -> object:
        raise RuntimeError("synthetic-secret-diagnostic")
    monkeypatch.setattr(resource_limits if boundary == "middleware" else comparisons, "_admit_comparison_json" if boundary == "middleware" else "create_comparison_simulation", broken)
    response = post()
    assert response.status_code == 500 and response.json()["code"] == "internal_error"
    assert "synthetic-secret-diagnostic" not in response.text + caplog.text


def test_openapi_is_valid_and_describes_precise_result_and_permissive_semantic_input() -> None:
    schema = app.openapi()
    validate(schema)
    operation = schema["paths"][PATH]["post"]
    assert set(operation["responses"]) >= {"200", "413", "422", "500"}
    assert "maxLength" not in json.dumps(schema["components"]["schemas"]["ComparisonLedgerV1"])


def test_all_infeasible_is_success_without_partial_metrics() -> None:
    response = post(raw_request(request("0.00", "0.00", "0.00")))
    assert response.status_code == 200 and response.json()["status"] == "no_eligible"
    assert response.json()["ranking_groups"] == []
    assert all(set(a) == {"strategy", "status", "failure"} for a in response.json()["alternatives"])


def test_single_eligible_keeps_exclusions_and_no_secondary_order() -> None:
    raw = raw_request()
    raw["financing"] = None
    raw["consortium"] = None
    response = post(raw)
    assert response.status_code == 200
    assert response.json()["status"] == "single_eligible"
    assert response.json()["ranking_groups"] == [["rent"]]
