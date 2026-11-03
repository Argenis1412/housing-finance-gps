import type {components} from "./api.generated";

export type Result = components["schemas"]["ComparisonSimulationResultV1"];
type Request = components["schemas"]["ComparisonCreationRequestV1"];
const limit = 4_194_304;
const order = ["sac", "price", "rent", "consortium"];
const versions: Record<string, string[]> = {
  sac: ["financing-replay-v4", "financing-monthly-resources-v4", "financing-ruleset-v3"],
  price: ["financing-replay-v4", "financing-monthly-resources-v4", "financing-ruleset-v3"],
  rent: ["rent-plus-replay-v2", "rent-plus-monthly-resources-v2", "rent-plus-ruleset-v2"],
  consortium: ["consortium-replay-v2", "consortium-monthly-resources-v2", "consortium-ruleset-v2"],
};
const codes = ["invalid_input", "unsupported_rate_convention", "unsupported_rule", "unsupported_contract_clause", "infeasible_scenario", "incompatible_contract_version"];
const monetary = ["cash", "liquid_financial_assets", "consortium_credit_right_balance", "property_value", "financing_principal_balance", "consortium_credit_obligation_balance", "recoverable_transfer", "nonrecoverable_housing_cost", "total_liabilities", "home_equity", "liquidity", "net_worth", "cumulative_housing_cost"];
const amount = (v: unknown): v is string => typeof v === "string" && /^-?(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(v);
const object = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const array = (v: unknown): unknown[] => {if (!Array.isArray(v)) throw new Error("invalid_response"); return v;};
function check(test: unknown, code = "invalid_response"): asserts test {if (!test) throw new Error(code);}
function row(value: unknown, month?: number) {
  check(object(value) && Number.isInteger(value.month) && (month === undefined || value.month === month));
  check(monetary.every(key => amount(value[key])));
}
/** Structural/compatibility checks only. No financial validation or ranking. */
export function validateResult(value: unknown): Result {
  check(object(value));
  check(value.api_version === "v1" && value.kind === "simulation_result" && value.contract_schema_version === "comparison-simulation-v2" && value.engine_version === "comparison-monthly-resources-v2" && value.ruleset_version === "comparison-ruleset-v2", "incompatible_response");
  check(value.objective === "maximize_net_worth_at_month_60" && value.timezone === "America/Sao_Paulo", "incompatible_response");
  check(typeof value.data_snapshot_id === "string" && typeof value.calculated_at === "string");
  const children = array(value.children);
  check(children.length === 4);
  children.forEach((c, i) => {
    check(object(c) && c.strategy === order[i] && object(c.versions));
    check([c.versions.contract_schema_version, c.versions.engine_version, c.versions.ruleset_version].every((v, j) => v === versions[order[i]][j]), "incompatible_response");
    check(c.input_classification === undefined || (object(c.input_classification) && Object.values(c.input_classification).every(v => typeof v === "string")));
  });
  check(object(value.normalized_input) && object(value.normalized_input.shared) && object(value.normalized_input.constraints) && object(value.normalized_input.rule_conventions) && object(value.normalized_input.input_classification));
  const conventions = value.normalized_input.rule_conventions;
  for (const [key, expected] of Object.entries({currency: "BRL", value_basis: "nominal", rounding: "ROUND_HALF_UP", comparison_horizon_months: 60, inflation: "documented_zero", property_appreciation: "documented_zero", transaction_costs: "documented_zero", reference_basis: "synthetic_contract_reference", monthly_posting_order: "opening_asset_return_then_common_resources_then_obligations_then_declared_contribution", surplus: "non_interest_bearing_cash", shortfall: "accumulated_cash_only_otherwise_exclude"})) check(conventions[key] === expected, "incompatible_response");
  check(Object.values(value.normalized_input.constraints).every(amount));
  const resources = value.normalized_input.monthly_resources;
  check(object(resources) && resources.income_basis === "net_before_household_expenses" && resources.expense_scope === "strategy_independent_excluding_strategy_flows_and_netted_deductions");
  const months = array(resources.months);
  check(months.length === 60);
  months.forEach((m, i) => {
    check(object(m) && m.month === i + 1 && amount(m.income_total) && amount(m.external_expense_total) && amount(m.available_resources));
    for (const side of ["income_components", "external_expenses"]) array(m[side]).forEach(c => {
      check(object(c) && amount(c.amount) && typeof c.component_id === "string" && typeof c.source_reference === "string" && typeof c.source_as_of === "string");
      check(c.classification === "observed_data" ? c.assumption_reference === null : c.classification === "projected_assumption" && typeof c.assumption_reference === "string");
    });
  });
  const alternatives = array(value.alternatives);
  check(alternatives.length === 4);
  alternatives.forEach((a, i) => {
    check(object(a) && a.strategy === order[i]);
    if (a.status === "domain_failure") {
      check(object(a.failure) && codes.includes(String(a.failure.code)) && typeof a.failure.message_pt_br === "string");
      check(Object.keys(a).every(key => ["strategy", "status", "failure"].includes(key)));
      check(Object.keys(a.failure).every(key => ["code", "message_pt_br", "month", "phase"].includes(key)));
      check((a.failure.month === undefined) === (a.failure.phase === undefined));
      if (a.failure.month !== undefined) {
        check(a.failure.code === "infeasible_scenario" && typeof a.failure.month === "number" && Number.isInteger(a.failure.month) && a.failure.month >= 0 && a.failure.month <= 60);
        check(a.failure.month === 0 ? a.failure.phase === "opening_allocation" : typeof a.failure.phase === "string" && ["external_expenses", "strategy_obligations", "investment_contribution"].includes(a.failure.phase));
      }
      return;
    }
    check((a.status === "eligible" || a.status === "constraint_infeasible") && object(a.metrics));
    row(a.metrics.final_ledger_row, 60);
    check(amount(a.metrics.minimum_liquidity) && amount(a.metrics.maximum_monthly_housing_outflow));
    for (const key of ["minimum_liquidity_months", "maximum_monthly_housing_outflow_months"]) check(array(a.metrics[key]).every(Number.isInteger));
    const ledger = array(a.comparison_ledger);
    check(ledger.length === 61); ledger.forEach((r, n) => row(r, n));
    const outflows = array(a.monthly_housing_outflows);
    check(outflows.length === 60 && outflows.every(amount));
    array(a.violations).forEach(v => check(object(v) && ["cash_nonnegative", "minimum_liquidity", "maximum_monthly_housing_outflow"].includes(String(v.constraint)) && Number.isInteger(v.month) && amount(v.actual) && amount(v.threshold)));
  });
  check(["compared", "single_eligible", "no_eligible"].includes(String(value.status)));
  const groups = array(value.ranking_groups);
  groups.forEach(g => check(array(g).length > 0 && array(g).every(s => order.includes(String(s)))));
  // Membership/cardinality checks only; scores and group order remain engine-owned.
  const eligible = alternatives.filter(a => object(a) && a.status === "eligible").map(a => (a as Record<string, unknown>).strategy);
  const members = groups.flatMap(g => array(g));
  check(members.length === eligible.length && new Set(members).size === members.length && members.every(s => eligible.includes(s)));
  check(value.status === "no_eligible" ? eligible.length === 0 : value.status === "single_eligible" ? eligible.length === 1 : eligible.length >= 2);
  check(array(value.limitations).every(v => typeof v === "string") && object(value.declared_inputs));
  return value as Result;
}
const messages: Record<string, string> = {
  invalid_input: "Os dados de comparação são inválidos. Revise a base comum, o perfil e os custos de espera.",
  unsupported_rate_convention: "A convenção de taxa não é suportada. Revise as taxas declaradas.",
  unsupported_rule: "A regra solicitada não é suportada neste modelo sintético.",
  unsupported_contract_clause: "A cláusula informada não é suportada neste modelo sintético.",
  request_too_large: "A solicitação excede o limite de tamanho. Reduza as declarações e revise novamente.",
  response_too_large: "O resultado excede o limite de tamanho. Reduza as declarações e revise novamente.",
  internal_error: "Não foi possível processar a comparação. Tente novamente.",
  invalid_response: "A resposta não corresponde ao contrato esperado. Nenhum resultado foi apresentado.",
  incompatible_response: "As versões recebidas são incompatíveis com esta interface. Nenhum resultado foi apresentado.",
  network_error: "Não foi possível acessar a API local. Verifique se ela está em execução e tente novamente.",
  timeout: "A comparação excedeu o tempo de espera. Tente novamente.",
};
export function errorMessage(error: unknown): string {return messages[error instanceof Error ? error.message : ""] ?? messages.invalid_response;}
export async function compare(request: Request, signal: AbortSignal): Promise<Result> {
  let response: Response;
  try {response = await fetch("/api/v1/comparison/simulations", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request), cache: "no-store", signal});}
  catch {if (signal.aborted) throw signal.reason; throw new Error("network_error");}
  const reader = response.body?.getReader();
  check(reader);
  let size = 0; const chunks: Uint8Array[] = [];
  for (;;) {
    const {done, value} = await reader.read(); if (done) break;
    size += value.byteLength;
    if (size > limit) {await reader.cancel(); throw new Error("response_too_large");}
    chunks.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) {bytes.set(chunk, offset); offset += chunk.length;}
  let value: unknown;
  try {value = JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(bytes));} catch {throw new Error("invalid_response");}
  if (!response.ok) {
    check(object(value) && value.api_version === "v1" && typeof value.code === "string");
    throw new Error(value.code in messages ? value.code : "invalid_response");
  }
  return validateResult(value);
}
