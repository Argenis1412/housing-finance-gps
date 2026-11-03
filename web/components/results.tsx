"use client";

import {useState} from "react";
import type {components} from "../lib/api.generated";
import type {Result} from "../lib/api";
import {money, names, phaseNames} from "../lib/formatting";

type Complete = components["schemas"]["CompleteAlternativeV1"];
type Alternative = Result["alternatives"][number];
const labels: Record<string, string> = {minimum_liquidity: "Liquidez mínima", maximum_monthly_housing_outflow: "Desembolso habitacional máximo", cash_nonnegative: "Caixa não negativo"};
const metrics: [string, (a: Complete) => string][] = [
  ["Patrimônio líquido no mês 60", a => money(a.metrics.final_ledger_row.net_worth)],
  ["Caixa no mês 60", a => money(a.metrics.final_ledger_row.cash)],
  ["Ativos financeiros líquidos", a => money(a.metrics.final_ledger_row.liquid_financial_assets)],
  ["Direito de crédito de consórcio", a => money(a.metrics.final_ledger_row.consortium_credit_right_balance)],
  ["Dívida no mês 60", a => money(a.metrics.final_ledger_row.total_liabilities)],
  ["Patrimônio imobiliário no mês 60", a => money(a.metrics.final_ledger_row.home_equity)],
  ["Custo habitacional acumulado", a => money(a.metrics.final_ledger_row.cumulative_housing_cost)],
  ["Liquidez mínima", a => money(a.metrics.minimum_liquidity)],
  ["Meses da liquidez mínima", a => a.metrics.minimum_liquidity_months.join(", ")],
  ["Maior desembolso habitacional", a => money(a.metrics.maximum_monthly_housing_outflow)],
  ["Meses do maior desembolso", a => a.metrics.maximum_monthly_housing_outflow_months.join(", ")],
];
const limitations: Record<string, string> = {
  synthetic_explicit_common_monthly_resources_not_complete_household_affordability: "Comparação sintética com recursos explícitos. Não valida capacidade financeira familiar.",
  only_rent_invests_and_receives_returns: "Somente aluguel investe e recebe rendimentos.",
  surplus_remains_cash_without_return: "Sobras permanecem em caixa sem rendimento.",
  no_automatic_redemption_credit_or_contribution_reduction: "Não há resgate automático, crédito ou redução do aporte.",
  no_post_horizon_cash_feasibility_claim: "Não se afirma viabilidade financeira após o mês 60.",
  no_universal_winner_or_private_case_validation: "Não há vencedor universal nem validação do caso privado real.",
  snapshot_and_source_references_are_not_authentication: "Snapshot e referências identificam declarações; não autenticam fontes.",
  declared_external_scope_does_not_detect_semantic_alias_double_counting: "A declaração de despesas externas não detecta duplicidade entre fluxos com identificações diferentes.",
};
const inputLabels: Record<string, string> = {
  comparison_opening_cash: "Caixa inicial", property_price: "Preço do imóvel", starting_monthly_rent: "Aluguel inicial",
  rent_adjustment_rate_value: "Taxa de reajuste anual (decimal)", rent_adjustment_rate_convention: "Convenção de reajuste",
  first_rent_adjustment_month: "Primeiro mês de reajuste", minimum_liquidity: "Liquidez mínima", maximum_monthly_housing_outflow: "Desembolso habitacional máximo",
  cash_down_payment: "Entrada em dinheiro", principal: "Principal", term_months: "Prazo em meses", rate_value: "Taxa mensal (decimal)", rate_convention: "Convenção de juros",
  fee_amount: "Tarifa mensal fixa", initial_invested_capital: "Investimento inicial", monthly_contribution: "Aporte mensal obrigatório", return_rate_value: "Retorno líquido mensal (decimal)", return_rate_convention: "Convenção de retorno",
  credit_letter: "Carta de crédito", scenario_kind: "Cenário de contemplação", contemplation_month: "Mês de contemplação", property_purchase_event: "Compra no mês declarado", cash_top_up: "Complemento em dinheiro",
  fgts_amount: "FGTS", subsidy_amount: "Subsídio", tax_amount: "Tributos adicionais", transaction_cost_amount: "Custos de transação", insurance_amount: "Seguro de financiamento", indexation: "Indexação", extraordinary_amortization_amount: "Amortização extra",
  investment_product: "Produto de investimento", withdrawal_restriction: "Restrição de resgate", future_purchase: "Compra futura", credit_components_apply_to_credit_letter: "Crédito aplicado à carta", correction: "Correção", reserve_fund_treatment: "Tratamento da reserva", installment_schedule_treatment: "Tratamento das parcelas",
};
const classifications: Record<string, string> = {observed_data: "Dado observado", contractual_data: "Dado contratual", projected_assumption: "Premissa projetada", rule_request: "Declaração de regra", user_constraint: "Restrição do usuário"};
const declarations: Record<string, string> = {effective_monthly: "Efetiva mensal", effective_annual: "Efetiva anual", documented_zero: "Zero documentado", not_requested: "Não solicitado", early: "Antecipado", intermediate: "Intermediário", late: "Tardio", nonrecoverable_no_refund: "Sem devolução", fixed_independent_of_contemplation: "Fixas, independentes da contemplação"};
function status(a: Alternative): string {
  if (a.status === "domain_failure") return a.failure.code === "infeasible_scenario" ? "Excluída por insuficiência de caixa" : "Excluída: entrada ou regra não suportada";
  return a.status === "eligible" ? "Elegível" : "Excluída por restrição";
}
export default function Results({result, edit}: {result: Result; edit: () => void}) {
  const [selected, setSelected] = useState("sac");
  const alternative = result.alternatives.find(a => a.strategy === selected)!;
  const groups = result.ranking_groups;
  return <section aria-labelledby="result-title"><div className="section-heading"><div><h2 id="result-title">Quatro caminhos, as mesmas origens</h2><p>Objetivo: maior patrimônio líquido no mês 60, dentro das restrições declaradas.</p></div><button type="button" className="secondary" onClick={edit}>Editar dados e revisar novamente</button></div>
    <div className="outcome" role="status"><h3>{result.status === "no_eligible" ? "Nenhuma alternativa elegível neste cenário" : result.status === "single_eligible" ? `Única alternativa elegível: ${names[groups[0][0]]}` : groups[0].length > 1 ? `Empate no primeiro grupo: ${groups[0].map(s => names[s]).join(" e ")}` : `Maior patrimônio entre as elegíveis: ${names[groups[0][0]]}`}</h3><p>Somente aluguel investe e recebe rendimentos. Sobras ficam em caixa sem rendimento; não há resgate automático, crédito ou redução do aporte.</p>{result.status === "single_eligible" && <p>Ser a única elegível não demonstra superioridade às alternativas excluídas.</p>}</div>
    {groups.length > 0 && <p className="group-summary">Alternativas elegíveis em ordem do objetivo: {groups.map((g, i) => <span key={i}>{i > 0 ? "; " : ""}{g.map(s => names[s]).join(" = ")}</span>)}.</p>}
    <div className="scroll-table matrix"><table><caption>Comparação no horizonte de 60 meses</caption><thead><tr><th>Métrica</th>{result.alternatives.map(a => <th key={a.strategy}>{names[a.strategy]}<small>{status(a)}</small></th>)}</tr></thead><tbody>{metrics.map(([label, render]) => <tr key={label}><th>{label}</th>{result.alternatives.map(a => <td key={a.strategy}>{a.status === "domain_failure" ? "Sem resultado completo" : render(a)}</td>)}</tr>)}</tbody></table></div>
    <div className="mobile-alternatives">{result.alternatives.map(a => <article key={a.strategy}><h3>{names[a.strategy]}</h3><p>{status(a)}</p>{a.status !== "domain_failure" && <dl>{metrics.map(([label, render]) => <div key={label}><dt>{label}</dt><dd>{render(a)}</dd></div>)}</dl>}</article>)}</div>
    <section className="panel"><h3>Elegibilidade e motivos de exclusão</h3>{result.alternatives.map(a => <div className="alternative-reason" key={a.strategy}><h4>{names[a.strategy]}: {status(a)}</h4>{a.status === "domain_failure" ? <><p>{a.failure.message_pt_br}</p>{a.failure.month !== undefined && a.failure.month !== null && a.failure.phase && <p>Caixa insuficiente no mês {a.failure.month}, durante {phaseNames[a.failure.phase]}.</p>}</> : a.violations.length > 0 ? <details><summary>Ver todas as {a.violations.length} violações</summary><div className="scroll-table"><table><thead><tr><th>Restrição</th><th>Mês</th><th>Valor</th><th>Limite</th></tr></thead><tbody>{a.violations.map((v, i) => <tr key={i}><td>{labels[v.constraint]}</td><td>{v.month}</td><td>{money(v.actual)}</td><td>{money(v.threshold)}</td></tr>)}</tbody></table></div></details> : <p>Restrições atendidas no horizonte calculado.</p>}</div>)}</section>
    <section className="panel"><h3>Recursos mensais comuns</h3><p>Renda líquida menos despesas externas. Recursos negativos consomem caixa acumulado; não são custo habitacional.</p><details><summary>Examinar os 60 meses e a proveniência</summary><div className="scroll-table"><table><thead><tr><th>Mês</th><th>Renda líquida</th><th>Despesas externas</th><th>Recursos disponíveis</th><th>Componentes e fontes</th></tr></thead><tbody>{result.normalized_input.monthly_resources.months.map(m => <tr key={m.month}><th>{m.month}</th><td>{money(m.income_total)}</td><td>{money(m.external_expense_total)}</td><td>{money(m.available_resources)}</td><td>{[...m.income_components, ...m.external_expenses].map(c => <p key={c.component_id}>{c.component_id}: {money(c.amount)}, {c.classification === "observed_data" ? "observado" : "projetado"}; fonte {c.source_reference}, {c.source_as_of}{c.assumption_reference ? `; premissa ${c.assumption_reference}` : ""}</p>)}</td></tr>)}</tbody></table></div></details></section>
    <section className="panel"><h3>Linha mensal de cada alternativa</h3><label className="select-strategy">Alternativa<select value={selected} onChange={e => setSelected(e.target.value)}>{result.alternatives.map(a => <option key={a.strategy} value={a.strategy}>{names[a.strategy]}</option>)}</select></label>{alternative.status === "domain_failure" ? <p>Esta alternativa não produziu linhas completas. Não há resultado parcial.</p> : <details><summary>Examinar os meses 0 a 60</summary><div className="scroll-table"><table><thead><tr><th>Mês</th><th>Caixa</th><th>Ativos líquidos</th><th>Direito de crédito</th><th>Imóvel</th><th>Dívida</th><th>Liquidez</th><th>Patrimônio imobiliário</th><th>Patrimônio líquido</th><th>Custo acumulado</th><th>Desembolso habitacional</th></tr></thead><tbody>{alternative.comparison_ledger.map(r => <tr key={r.month}><th>{r.month}</th>{[r.cash, r.liquid_financial_assets, r.consortium_credit_right_balance, r.property_value, r.total_liabilities, r.liquidity, r.home_equity, r.net_worth, r.cumulative_housing_cost].map((v, i) => <td key={i}>{money(v)}</td>)}<td>{r.month === 0 ? "Não se aplica" : money(alternative.monthly_housing_outflows[r.month - 1])}</td></tr>)}</tbody></table></div></details>}</section>
    <section className="panel"><h3>Declarações usadas nesta comparação</h3><p>Confira especialmente a alocação inicial, o aporte e o retorno do aluguel: apenas essa alternativa investe. Valores e classificações abaixo vêm da resposta desta execução.</p><details><summary>Examinar condições declaradas e suas classificações</summary>{([['shared', 'Base comum'], ['constraints', 'Restrições'], ['financing', 'SAC e Price'], ['rent', 'Aluguel com investimento'], ['consortium', 'Consórcio']] as const).map(([key, label]) => {
      const raw = result.declared_inputs[key];
      const sourceClass = key === 'shared' || key === 'constraints' ? result.normalized_input.input_classification[key] : result.children.find(c => c.strategy === (key === 'financing' ? 'sac' : key))?.input_classification;
      const classification: Record<string, string> = {};
      if (sourceClass && typeof sourceClass === 'object' && !Array.isArray(sourceClass)) for (const [field, value] of Object.entries(sourceClass)) if (typeof value === 'string') classification[field] = value;
      return <section key={key}><h4>{label}</h4>{raw !== null && typeof raw === 'object' && !Array.isArray(raw) ? <dl>{Object.entries(raw).filter(([, value]) => value === null || ['string', 'number', 'boolean'].includes(typeof value)).map(([field, value]) => <div key={field}><dt>{inputLabels[field] ?? field}{classification?.[field] && <small> — {classifications[classification[field]] ?? classification[field]}</small>}</dt><dd>{value === null ? 'Não solicitado' : typeof value === 'boolean' ? value ? 'Sim' : 'Não' : declarations[String(value)] ?? String(value)}</dd></div>)}</dl> : <p>Declaração fora da estrutura esperada, preservada como exclusão.</p>}</section>;
    })}</details></section>
    <section className="panel"><h3>Premissas, limitações e versões</h3><p>Valores nominais em BRL, arredondamento HALF UP a centavos, sem inflação, valorização ou custos de transação. Recursos entram antes das obrigações; o aporte de aluguel é integral e seu rendimento usa o investimento de abertura.</p><ul>{result.limitations.map(id => <li key={id}>{limitations[id] ?? `Limitação adicional informada pelo motor: ${id}`}</li>)}</ul><details><summary>Identificação desta execução e versões retidas</summary><dl><div><dt>Snapshot transitório</dt><dd>{result.data_snapshot_id}</dd></div><div><dt>Calculado em UTC</dt><dd>{result.calculated_at}</dd></div><div><dt>Timezone de referência</dt><dd>{result.timezone}</dd></div><div><dt>Comparação: contrato / motor / regras</dt><dd>{result.contract_schema_version}<br/>{result.engine_version}<br/>{result.ruleset_version}</dd></div>{result.children.map(c => <div key={c.strategy}><dt>{names[c.strategy]}: contrato / motor / regras</dt><dd>{c.versions.contract_schema_version}<br/>{c.versions.engine_version}<br/>{c.versions.ruleset_version}</dd></div>)}</dl></details></section>
  </section>;
}
