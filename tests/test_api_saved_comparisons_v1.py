"""Additive HTTP persistence contracts, safe admission and precommit failures."""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import json
import hashlib
from pathlib import Path
import sqlite3
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openapi_spec_validator import validate
import pytest

from api.main import create_app
from api import resource_limits
from api.routes import saved_comparisons as route
from application import saved_comparisons as application
from infrastructure.sqlite_comparisons import SqliteComparisonRepository, migrate_comparisons
from tests.test_monthly_resources_comparison import raw_request
from tests.test_saved_comparisons import ID
from domain.consortium.replay_v1 import canonical_json


PATH = "/api/v1/comparison/saved-simulations"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    path = tmp_path / "http.sqlite3"
    migrate_comparisons(path)
    return TestClient(create_app(comparison_repository=SqliteComparisonRepository(path)))


def payload() -> dict[str, object]:
    return {"operation_id": ID, "comparison": raw_request()}


def test_save_retry_restart_read_and_delete_are_distinct(client: TestClient) -> None:
    response = client.post(PATH, json=payload())
    assert response.status_code == 201
    value = response.json()
    assert value["kind"] == "saved_comparison" and value["simulation_id"] == ID
    assert response.headers["cache-control"] == "no-store"
    assert "raw_request_jcs" not in json.dumps(value)
    assert client.post(PATH, json=payload()).content == response.content
    assert client.post(PATH, json=payload()).status_code == 200
    reopened = TestClient(create_app(comparison_repository=cast(FastAPI, client.app).state.comparison_repository))
    assert reopened.get(f"{PATH}/{ID}").content == response.content
    projection = client.post("/api/v1/comparison/simulations", json={"comparison": raw_request()}).json()
    for key in ("alternatives", "normalized_input", "ranking_groups", "children", "declared_inputs"):
        assert value["result"][key] == projection[key]
    assert client.get(PATH).json()["items"] == [{"simulation_id": ID, "saved_at": value["saved_at"]}]
    assert client.delete(f"{PATH}/{ID}").status_code == 204
    assert client.delete(f"{PATH}/{ID}").status_code == 204
    assert client.get(PATH).json()["items"] == []
    assert client.get(f"{PATH}/{ID}").status_code == 410
    assert client.post(PATH, json=payload()).status_code == 410


@pytest.mark.parametrize("suffix", ["", "/"])
@pytest.mark.parametrize("body", [b'{"operation_id":"a","operation_id":"b"}', b'{"comparison":1.0}', b'{"comparison":1e0}', b'{"comparison":9007199254740992}', b'{"comparison":"\\ud800"}'])
def test_representation_failures_never_call_application(client: TestClient, monkeypatch: pytest.MonkeyPatch, suffix: str, body: bytes) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("admission bypass")
    monkeypatch.setattr(route, "save_comparison", forbidden)
    response = client.post(PATH + suffix, content=body)
    assert response.status_code == 422 and response.json()["code"] == "invalid_input"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("case", ["response_limit", "evidence_limit", "presenter", "model", "global"])
def test_precommit_failures_leave_no_payload_or_reserved_operation(client: TestClient, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    request = payload()
    if case == "response_limit":
        monkeypatch.setattr(resource_limits, "COMPARISON_MAX_RESPONSE_BYTES", 1)
    elif case == "evidence_limit":
        monkeypatch.setattr(application, "MAX_RECORD_BYTES", 1)
    elif case == "presenter":
        def broken(_: object) -> bytes:
            raise RuntimeError("synthetic private diagnostic")
        monkeypatch.setattr(route, "_prepare", broken)
    elif case == "model":
        original = application.project_comparison_v2_envelope
        def malformed(envelope: object) -> object:
            value = original(envelope)  # type: ignore[arg-type]
            assert isinstance(value, dict)
            value["kind"] = "invalid"
            return value
        monkeypatch.setattr(application, "project_comparison_v2_envelope", malformed)
    else:
        raw = raw_request()
        raw["monthly_resources"] = None
        request["comparison"] = raw
    response = client.post(PATH, json=request)
    assert response.status_code == (500 if case in {"presenter", "model"} else 422)
    with cast(FastAPI, client.app).state.comparison_repository.transaction() as transaction:
        assert transaction.find(ID) == (False, None)
    assert "private diagnostic" not in response.text


def test_global_failure_and_local_exclusions_keep_current_meaning(client: TestClient) -> None:
    raw = raw_request()
    raw["financing"] = None
    response = client.post(PATH, json={"operation_id": ID, "comparison": raw})
    assert response.status_code == 201
    assert response.json()["result"]["alternatives"][0]["status"] == "domain_failure"
    assert client.get(f"{PATH}/{ID}").json() == response.json()
    other = raw_request()
    assert client.post(PATH, json={"operation_id": ID, "comparison": other}).json()["code"] == "operation_id_conflict"


@pytest.mark.parametrize("mutation", ["index_date", "presentation_money", "presentation_failure"])
def test_corrupt_record_is_isolated_discoverable_and_deletable(client: TestClient, mutation: str) -> None:
    second = "00000000-0000-4000-8000-000000000002"
    assert client.post(PATH, json=payload()).status_code == 201
    assert client.post(PATH, json={**payload(), "operation_id": second}).status_code == 201
    with sqlite3.connect(cast(FastAPI, client.app).state.comparison_repository.path) as connection:
        trigger = connection.execute("SELECT sql FROM sqlite_master WHERE name='immutable_saved_comparisons'").fetchone()[0]
        connection.execute("DROP TRIGGER immutable_saved_comparisons")
        if mutation == "index_date":
            connection.execute("UPDATE saved_comparisons SET saved_at='broken' WHERE simulation_id=?", (ID,))
        else:
            row = connection.execute("SELECT record_jcs FROM saved_comparisons WHERE simulation_id=?", (ID,)).fetchone()[0]
            wrapper = json.loads(row)
            outcome = json.loads(wrapper["envelope"]["sealed_outcome_jcs"])
            if mutation == "presentation_money":
                outcome["alternatives"][0]["metrics"]["final_ledger_row"]["cash"] = "invalid-money"
            else:
                outcome["alternatives"][0] = {"strategy": "sac", "status": "domain_failure", "failure": {"kind": "failure", "code": [], "detail": "synthetic failure"}}
            wrapper["envelope"]["sealed_outcome_jcs"] = canonical_json(outcome)
            encoded = canonical_json(wrapper)
            connection.execute("UPDATE saved_comparisons SET record_jcs=?,sha256=? WHERE simulation_id=?", (encoded, hashlib.sha256(encoded.encode()).hexdigest(), ID))
        connection.execute(trigger)
    assert len(client.get(PATH).json()["items"]) == 2
    assert client.get(f"{PATH}/{ID}").json()["code"] == "stored_simulation_corrupt"
    assert client.post(PATH, json=payload()).json()["code"] == "stored_simulation_corrupt"
    assert client.get(f"{PATH}/{second}").status_code == 200
    assert client.delete(f"{PATH}/{ID}").status_code == 204


def test_safe_configuration_errors_do_not_break_transient_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HFGPS_DB_PATH", raising=False)
    client = TestClient(create_app())
    response = client.get(PATH)
    assert response.status_code == 503 and response.json()["code"] == "storage_not_configured"
    assert response.headers["cache-control"] == "no-store"
    monkeypatch.setenv("HFGPS_DB_PATH", str(tmp_path / "absent.sqlite3"))
    assert client.get(PATH).json()["code"] == "storage_not_initialized"
    assert not (tmp_path / "absent.sqlite3").exists()
    assert client.post("/api/v1/comparison/simulations", json={"comparison": raw_request()}).status_code == 200


@pytest.mark.parametrize("path", [PATH, PATH + "/"])
def test_body_limits_before_execution_and_safe_validation(client: TestClient, path: str) -> None:
    response = client.post(path, content=b" " * 1_048_577)
    assert response.status_code == 413 and response.json()["code"] == "request_too_large"
    assert client.get(PATH + "?limit=51").status_code == 422
    assert client.get(PATH + "?offset=-1").status_code == 422
    assert client.get(PATH + "/invalid-id").status_code == 422
    unknown = "00000000-0000-4000-8000-000000000099"
    assert client.get(PATH + "/" + unknown).status_code == 404
    assert client.delete(PATH + "/" + unknown).status_code == 404


def test_openapi_is_additive_with_explicit_saved_models(client: TestClient) -> None:
    document = cast(FastAPI, client.app).openapi()
    validate(document)
    assert set(document["paths"][PATH]) == {"get", "post"}
    assert set(document["paths"][PATH + "/{simulation_id}"]) == {"get", "delete"}
    assert document["info"]["version"] == "1.2.0"
    assert "raw_request_jcs" not in json.dumps(document)
