import {test, expect} from "@playwright/test";
import {execFileSync} from "node:child_process";
import {resolve} from "node:path";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {validateResult, compare, errorMessage} from "../lib/api";
import {createRequest, formErrors, initialForm, updateValue} from "../lib/form-state";
import Results from "../components/results";

test("consumer rejects incompatible tuples, malformed bodies and fabricated partial outcomes", async ({request, page}) => {
  const raw = execFileSync("uv", ["run", "python", "-c", "import json; from tests.test_monthly_resources_comparison import raw_request; print(json.dumps({'comparison':raw_request()}))"], {cwd: resolve(".."), encoding: "utf8"});
  const response = await request.post("http://127.0.0.1:8000/api/v1/comparison/simulations", {data: JSON.parse(raw)});
  expect(response.status()).toBe(200);
  const valid = await response.json();
  expect(validateResult(valid).status).toBe("compared");
  for (const section of ["shared", "constraints", "financing", "rent", "consortium", "monthly_resources"]) {
    const missing = structuredClone(valid); delete missing.declared_inputs[section];
    expect(() => validateResult(missing)).toThrow("invalid_response");
  }
  const emptyViolation = structuredClone(valid); emptyViolation.alternatives[0].status = "constraint_infeasible"; emptyViolation.ranking_groups = [["price"], ["consortium"], ["rent"]];
  expect(() => validateResult(emptyViolation)).toThrow("invalid_response");
  const eligibleViolation = structuredClone(valid); eligibleViolation.alternatives[0].violations = [{constraint: "minimum_liquidity", month: 0, actual: "0.00", threshold: "1.00"}];
  expect(() => validateResult(eligibleViolation)).toThrow("invalid_response");
  eligibleViolation.alternatives[0].status = "constraint_infeasible"; eligibleViolation.ranking_groups = [["price"], ["consortium"], ["rent"]];
  expect(validateResult(eligibleViolation).status).toBe("compared");
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

  const incomplete = JSON.parse(raw);
  delete incomplete.comparison.consortium.monthly_schedule[0].credit_component;
  const excludedResponse = await request.post("http://127.0.0.1:8000/api/v1/comparison/simulations", {data: incomplete});
  expect(excludedResponse.status()).toBe(200);
  const excludedResult = validateResult(await excludedResponse.json());
  await page.setContent(renderToStaticMarkup(createElement(Results, {result: excludedResult, edit: () => {}})));
  await page.getByText("Examinar condições declaradas e suas classificações", {exact: true}).click();
  await expect(page.getByRole("heading", {name: "Consórcio: Excluída: dados inválidos", exact: true})).toBeVisible();
  const submitted = page.getByRole("table", {name: "Cronograma de consórcio enviado", exact: true});
  await expect(submitted.getByRole("row").nth(1).getByRole("cell").nth(1)).toHaveText("Não informado");
  await expect(page.getByRole("table", {name: "Custos de espera enviados", exact: true})).toBeVisible();
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
    for (const code of ["constructor", "toString", "__proto__"]) {
      globalThis.fetch = async () => new Response(JSON.stringify({api_version: "v1", code}), {status: 422});
      await expect(compare(input, new AbortController().signal)).rejects.toThrow("invalid_response");
      expect(errorMessage(new Error(code))).toBe(errorMessage(new Error("invalid_response")));
    }
  } finally {globalThis.fetch = original;}
});

test("nonzero rates reach the real API through createRequest at the adjustment boundary", async ({request}) => {
  let form = initialForm();
  const values = {opening: "200,00", property: "60,00", rent: "1,00", adjustment: "0,05", firstAdjustment: "2", minimum: "0,00", maximum: "200,00", principal: "60,00", down: "0,00", financeTerm: "60", financeRate: "0,001", fee: "0,00", invested: "0,00", contribution: "0,00", return: "0,002", letter: "60,00", consortiumTerm: "60", contemplation: "1", topup: "0,00", scenario: "early"};
  for (const [key, value] of Object.entries(values)) form = updateValue(form, key, value);
  form.months = form.months.map(m => ({...m, income_components: [], external_expenses: []}));
  form.schedule = form.schedule.map(r => ({...r, credit_component: "1.00", administration_fee: "0.00", reserve_fund: "0.00", insurance: "0.00"}));
  form.waiting = [{month: 1, amount: "1.00"}]; form.scopeConfirmed = form.supportConfirmed = true;
  expect(formErrors(form)).toEqual([]);
  const input = createRequest(form);
  const response = await request.post("http://127.0.0.1:8000/api/v1/comparison/simulations", {data: input});
  expect(response.status()).toBe(200);
  const result = validateResult(await response.json());
  expect(result.alternatives.every(a => a.status !== "domain_failure")).toBe(true);
  expect(result.declared_inputs.shared).toMatchObject({rent_adjustment_rate_value: "0.05", first_rent_adjustment_month: 2});
  form = updateValue(form, "firstAdjustment", "1");
  expect(formErrors(form)).toContain("Primeiro mês de reajuste: informe um mês inteiro maior que 1.");
  const rejected = await request.post("http://127.0.0.1:8000/api/v1/comparison/simulations", {data: createRequest(form)});
  expect(rejected.status()).toBe(422);
  expect((await rejected.json()).code).toBe("invalid_input");
});
