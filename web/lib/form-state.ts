import type {components} from "./api.generated";

export type Component = components["schemas"]["ResourceComponentV1"];
export type ResourceMonth = {month: number; income_components: Component[] | null; external_expenses: Component[] | null};
export type ScheduleRow = {month: number; credit_component: string; administration_fee: string; reserve_fund: string; insurance: string};
export type FormState = {
  values: Record<string, string>;
  months: ResourceMonth[];
  schedule: ScheduleRow[];
  waiting: {month: number; amount: string}[];
  scheduleCache: ScheduleRow[];
  waitingCache: {month: number; amount: string}[];
  scopeConfirmed: boolean;
  supportConfirmed: boolean;
};
export const fieldGroups: {title: string; fields: [string, string, "money" | "rate" | "month"][]}[] = [
  {title: "Base comum e limites", fields: [
    ["opening", "Caixa inicial comum", "money"], ["property", "Preço comum do imóvel", "money"],
    ["rent", "Aluguel mensal inicial", "money"], ["adjustment", "Reajuste efetivo anual (decimal)", "rate"],
    ["firstAdjustment", "Primeiro mês de reajuste", "month"], ["minimum", "Liquidez mínima", "money"],
    ["maximum", "Desembolso habitacional mensal máximo", "money"],
  ]},
  {title: "Financiamento SAC e Price", fields: [
    ["principal", "Principal financiado", "money"], ["down", "Entrada em dinheiro", "money"],
    ["financeTerm", "Prazo do financiamento (meses)", "month"],
    ["financeRate", "Juros efetivos mensais (decimal)", "rate"], ["fee", "Tarifa mensal fixa", "money"],
  ]},
  {title: "Aluguel com investimento", fields: [
    ["invested", "Investimento inicial", "money"], ["contribution", "Aporte mensal obrigatório", "money"],
    ["return", "Retorno líquido efetivo mensal (decimal)", "rate"],
  ]},
  {title: "Cenário sintético de consórcio", fields: [
    ["letter", "Carta de crédito", "money"], ["consortiumTerm", "Prazo do consórcio (meses)", "month"],
    ["contemplation", "Mês explícito de contemplação", "month"], ["topup", "Complemento da compra em dinheiro", "money"],
  ]},
];
export function initialForm(): FormState {
  return {values: {}, months: Array.from({length: 60}, (_, i) => ({month: i + 1, income_components: null, external_expenses: null})), schedule: [], waiting: [], scheduleCache: [], waitingCache: [], scopeConfirmed: false, supportConfirmed: false};
}
export function period(value: string | undefined): number {
  return value && /^[0-9]{1,3}$/.test(value) && Number(value) >= 1 && Number(value) <= 600 ? Number(value) : 0;
}
function monthInteger(value: string): number {
  return /^[0-9]+$/.test(value) && Number.isSafeInteger(Number(value)) && Number(value) > 0 ? Number(value) : 0;
}
export function updateValue(form: FormState, key: string, value: string): FormState {
  const next = {...form, values: {...form.values, [key]: value}};
  if (key === "consortiumTerm") {
    // Keep declarations while the user clears/types a period. Only active rows
    // enter review/request; expanding again restores previously entered rows.
    next.scheduleCache = Array.from({length: Math.max(period(value), form.schedule.length, form.scheduleCache.length)}, (_, i) => form.schedule[i] ?? form.scheduleCache[i] ?? {month: i + 1, credit_component: "", administration_fee: "", reserve_fund: "", insurance: ""});
    next.schedule = next.scheduleCache.slice(0, period(value));
  }
  if (key === "contemplation" || key === "consortiumTerm") {
    const count = Math.min(period(next.values.contemplation), 60);
    next.waitingCache = Array.from({length: Math.max(count, form.waiting.length, form.waitingCache.length)}, (_, i) => form.waiting[i] ?? form.waitingCache[i] ?? {month: i + 1, amount: ""});
    next.waiting = next.waitingCache.slice(0, count);
  }
  return next;
}
export function decimal(value: string): string {return value.trim().replace(",", ".");}
export function formErrors(form: FormState): string[] {
  const errors: string[] = [];
  for (const group of fieldGroups) for (const [key, label, kind] of group.fields) {
    const value = decimal(form.values[key] ?? "");
    const valid = kind === "money" ? /^[+-]?[0-9]{1,18}\.[0-9]{2}$/.test(value) : kind === "rate" ? /^(?:0(?:\.[0-9]{1,12})?|1(?:\.0{1,12})?)$/.test(value) : key === "firstAdjustment" ? monthInteger(value) > 1 : period(value) > 0;
    if (!valid) errors.push(`${label}: informe ${kind === "money" ? "um valor com dois centavos decimais" : kind === "rate" ? "uma taxa decimal entre 0 e 1, sem porcentagem ou zeros iniciais" : key === "firstAdjustment" ? "um mês inteiro maior que 1" : "um mês inteiro entre 1 e 600"}.`);
  }
  if (!form.values.scenario) errors.push("Escolha o rótulo do cenário de contemplação.");
  if (form.months.some(m => m.income_components === null || m.external_expenses === null)) errors.push("Declare renda e despesas de todos os 60 meses, inclusive listas vazias.");
  if (!form.schedule.length || form.schedule.some(r => [r.credit_component, r.administration_fee, r.reserve_fund, r.insurance].some(v => !/^[+-]?[0-9]{1,18}\.[0-9]{2}$/.test(decimal(v))))) errors.push("Complete os quatro valores de cada linha do cronograma de consórcio.");
  if (!form.waiting.length || form.waiting.some(r => !/^[+-]?[0-9]{1,18}\.[0-9]{2}$/.test(decimal(r.amount)))) errors.push("Declare os custos de espera até a contemplação, limitados ao mês 60.");
  if (!form.scopeConfirmed || !form.supportConfirmed) errors.push("Confirme a composição do perfil e o suporte sintético antes de revisar.");
  return errors;
}
export function copyComponent(form: FormState, side: "income_components" | "external_expenses", component: Component, from: number, to: number): FormState {
  const other = side === "income_components" ? "external_expenses" : "income_components";
  if (form.months.some(m => m[other]?.some(c => c.component_id === component.component_id))) throw new Error("Essa identificação já pertence ao outro lado do perfil. Use a identidade correta do fluxo.");
  return {...form, months: form.months.map(m => m.month < from || m.month > to ? m : {...m, [side]: [...(m[side] ?? []).filter(c => c.component_id !== component.component_id), {...component}]})};
}
export function createRequest(form: FormState): components["schemas"]["ComparisonCreationRequestV1"] {
  const v = (key: string) => decimal(form.values[key]);
  const shared = {comparison_opening_cash: v("opening"), property_price: v("property"), starting_monthly_rent: v("rent"), rent_adjustment_rate_value: v("adjustment"), rent_adjustment_rate_convention: "effective_annual", first_rent_adjustment_month: monthInteger(v("firstAdjustment"))};
  return {comparison: {
    shared, constraints: {minimum_liquidity: v("minimum"), maximum_monthly_housing_outflow: v("maximum")},
    financing: {comparison_opening_cash: shared.comparison_opening_cash, property_price: shared.property_price, principal: v("principal"), cash_down_payment: v("down"), term_months: period(v("financeTerm")), rate_value: v("financeRate"), rate_convention: "effective_monthly", fee_amount: v("fee"), fgts_amount: null, subsidy_amount: null, tax_amount: null, transaction_cost_amount: null, insurance_amount: null, indexation: "documented_zero", extraordinary_amortization_amount: null},
    rent: {comparison_opening_cash: shared.comparison_opening_cash, starting_monthly_rent: shared.starting_monthly_rent, initial_invested_capital: v("invested"), monthly_contribution: v("contribution"), rent_adjustment_rate_value: shared.rent_adjustment_rate_value, rent_adjustment_rate_convention: shared.rent_adjustment_rate_convention, first_rent_adjustment_month: shared.first_rent_adjustment_month, return_rate_value: v("return"), return_rate_convention: "effective_monthly", tax_amount: null, investment_product: "not_requested", withdrawal_restriction: "not_requested", future_purchase: "not_requested"},
    consortium: {comparison_opening_cash: shared.comparison_opening_cash, property_price: shared.property_price, credit_letter: v("letter"), term_months: period(v("consortiumTerm")), monthly_schedule: form.schedule.map(r => ({month: r.month, credit_component: decimal(r.credit_component), administration_fee: decimal(r.administration_fee), reserve_fund: decimal(r.reserve_fund), insurance: decimal(r.insurance)})), credit_components_apply_to_credit_letter: true, correction: "documented_zero", reserve_fund_treatment: "nonrecoverable_no_refund", installment_schedule_treatment: "fixed_independent_of_contemplation", scenario_kind: form.values.scenario, contemplation_month: period(v("contemplation")), property_purchase_event: true, cash_top_up: v("topup"), waiting_housing_costs: form.waiting.map(r => ({month: r.month, amount: decimal(r.amount)})), requested_features: []},
    monthly_resources: {income_basis: "net_before_household_expenses", expense_scope: "strategy_independent_excluding_strategy_flows_and_netted_deductions", months: form.months.map(m => ({month: m.month, income_components: m.income_components, external_expenses: m.external_expenses}))},
  }};
}
