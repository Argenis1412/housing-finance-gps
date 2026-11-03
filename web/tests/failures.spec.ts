import {test, expect} from "@playwright/test";
import {execFileSync} from "node:child_process";
import {resolve} from "node:path";
import {validateResult, compare, errorMessage} from "../lib/api";

test("consumer rejects incompatible tuples, malformed bodies and fabricated partial outcomes", async ({request}) => {
  const raw = execFileSync("uv", ["run", "python", "-c", "import json; from tests.test_monthly_resources_comparison import raw_request; print(json.dumps({'comparison':raw_request()}))"], {cwd: resolve(".."), encoding: "utf8"});
  const response = await request.post("http://127.0.0.1:8000/api/v1/comparison/simulations", {data: JSON.parse(raw)});
  expect(response.status()).toBe(200);
  const valid = await response.json();
  expect(validateResult(valid).status).toBe("compared");
  for (const key of ["api_version", "contract_schema_version", "engine_version", "ruleset_version"]) {
    expect(() => validateResult({...valid, [key]: "unknown"})).toThrow("incompatible_response");
  }
  const wrongChild = structuredClone(valid); wrongChild.children[2].versions.ruleset_version = "unknown";
  expect(() => validateResult(wrongChild)).toThrow("incompatible_response");
  const partial = structuredClone(valid); partial.alternatives[0] = {strategy: "sac", status: "domain_failure", failure: {code: "infeasible_scenario", message_pt_br: "safe"}, metrics: {}};
  expect(() => validateResult(partial)).toThrow("invalid_response");
  const badMoney = structuredClone(valid); badMoney.alternatives[0].metrics.final_ledger_row.cash = 1;
  expect(() => validateResult(badMoney)).toThrow("invalid_response");
  expect(() => validateResult({...valid, ranking_groups: [[]]})).toThrow("invalid_response");
  for (const groups of [[["sac", "sac"], ["rent"], ["consortium"]], [["sac"], ["rent"], ["consortium"]]]) expect(() => validateResult({...valid, ranking_groups: groups})).toThrow("invalid_response");
  expect(() => validateResult({...valid, status: "single_eligible"})).toThrow("invalid_response");
  expect(() => validateResult({...valid, status: "no_eligible"})).toThrow("invalid_response");
  const excluded = structuredClone(valid); excluded.alternatives[0].status = "constraint_infeasible";
  expect(() => validateResult(excluded)).toThrow("invalid_response");
  const failed = structuredClone(valid); failed.alternatives[0] = {strategy: "sac", status: "domain_failure", failure: {code: "infeasible_scenario", message_pt_br: "safe"}}; failed.ranking_groups = [["price"], ["consortium"], ["rent"]];
  expect(validateResult(failed).status).toBe("compared");
  failed.alternatives[0].monthly_housing_outflows = ["1.00"];
  expect(() => validateResult(failed)).toThrow("invalid_response");
  delete failed.alternatives[0].monthly_housing_outflows;
  failed.alternatives[0].failure.phase = "external_expenses";
  expect(() => validateResult(failed)).toThrow("invalid_response");
  const wrongBasis = structuredClone(valid); wrongBasis.normalized_input.rule_conventions.comparison_horizon_months = 61;
  expect(() => validateResult(wrongBasis)).toThrow("incompatible_response");
});

test("transport failures and oversize responses never become eligibility results", async () => {
  const original = globalThis.fetch;
  const input = {comparison: {shared: null, constraints: null, financing: null, rent: null, consortium: null, monthly_resources: null}};
  try {
    globalThis.fetch = async () => new Response("{");
    await expect(compare(input, new AbortController().signal)).rejects.toThrow("invalid_response");
    globalThis.fetch = async () => new Response(" ".repeat(4_194_305));
    await expect(compare(input, new AbortController().signal)).rejects.toThrow("response_too_large");
    globalThis.fetch = async () => {throw new Error("private response");};
    await expect(compare(input, new AbortController().signal)).rejects.toThrow("network_error");
    expect(errorMessage(new Error("timeout"))).toContain("tempo de espera");
  } finally {globalThis.fetch = original;}
});
