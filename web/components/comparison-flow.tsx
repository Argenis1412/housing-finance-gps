"use client";

import {useRef, useState} from "react";
import Link from "next/link";
import {compare, errorMessage, type Result} from "../lib/api";
import {createRequest, fieldGroups, formErrors, initialForm, updateValue, type FormState} from "../lib/form-state";
import MonthlyProfile from "./monthly-profile";
import ConsortiumSchedule from "./consortium-schedule";
import Review from "./review";
import Results from "./results";

export default function ComparisonFlow() {
  const [form, setForm] = useState(initialForm);
  const [reviewed, setReviewed] = useState<FormState | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [errors, setErrors] = useState<string[]>([]), [failure, setFailure] = useState("");
  const [loading, setLoading] = useState(false);
  const sequence = useRef(0), controller = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null), errorSummary = useRef<HTMLDivElement>(null);
  function invalidate() {sequence.current++; controller.current?.abort(); setReviewed(null); setResult(null); setFailure(""); setLoading(false);}
  function change(next: FormState) {invalidate(); setForm(next); setErrors([]);}
  function review() {
    const missing = formErrors(form); setErrors(missing);
    if (missing.length) {requestAnimationFrame(() => errorSummary.current?.focus()); return;}
    setReviewed(structuredClone(form)); setFailure(""); requestAnimationFrame(() => heading.current?.focus());
  }
  async function run() {
    if (!reviewed) return;
    const current = ++sequence.current;
    const active = new AbortController(); controller.current = active;
    setFailure(""); setLoading(true);
    const timeout = setTimeout(() => active.abort(new Error("timeout")), 30_000);
    try {
      const value = await compare(createRequest(reviewed), active.signal);
      if (current === sequence.current) {setResult(value); requestAnimationFrame(() => heading.current?.focus());}
    } catch (error) {if (current === sequence.current) setFailure(errorMessage(active.signal.aborted ? active.signal.reason : error));}
    finally {clearTimeout(timeout); if (current === sequence.current) setLoading(false);}
  }
  const stage = result ? 3 : reviewed ? 2 : 1;
  return <main><header className="masthead"><Link href="/" className="wordmark">Housing Finance GPS</Link><span>Comparação sintética local</span></header><div className="page-intro"><p className="purpose">Uma decisão de moradia, quatro caminhos</p><h1 ref={heading} tabIndex={-1}>{stage === 1 ? "Declare o cenário que você quer comparar" : stage === 2 ? "Confira as declarações antes de calcular" : "Entenda o resultado deste cenário"}</h1><p>Compare SAC, Price, aluguel com investimento e um cenário explícito de consórcio em 60 meses.</p></div>
    <ol className="steps" aria-label="Etapas da comparação">{["Entrada", "Revisão", "Resultado"].map((s, i) => <li key={s} aria-current={stage === i + 1 ? "step" : undefined}><span>{i + 1}</span>{s}</li>)}</ol>
    <aside className="session-notice">Sessão temporária: recarregar ou fechar a página apaga as declarações e o resultado. Use somente dados sintéticos. Este modelo não valida propostas reais nem capacidade financeira familiar.</aside>
    {errors.length > 0 && <div className="error-summary" role="alert" aria-label="Erros de preenchimento" tabIndex={-1} ref={errorSummary}><h2>Revise os campos antes de continuar</h2><ul>{errors.map(e => <li key={e}>{e}</li>)}</ul></div>}
    {failure && <div role="alert" aria-label="Falha na comparação" className="error-summary"><h2>A comparação não foi apresentada</h2><p>{failure}</p><button type="button" onClick={run}>Tentar comparação novamente</button></div>}
    {loading && <p role="status" className="loading">Calculando no backend local. Você pode editar os dados para cancelar esta execução.</p>}
    {result ? <Results result={result} edit={invalidate}/> : reviewed ? <Review form={reviewed} edit={invalidate} run={run} loading={loading}/> : <>
      <form autoComplete="off" onSubmit={e => {e.preventDefault(); review();}} noValidate>
        <section className="panel"><h2>Valores e condições do cenário</h2><p>Valores monetários com dois decimais, sem separador de milhar. Taxas em decimal: por exemplo, 0,01 representa 1%. Zeros também precisam ser declarados.</p>{fieldGroups.map(g => <fieldset key={g.title}><legend>{g.title}</legend><div className="field-grid">{g.fields.map(([key, label, kind]) => <label key={key}>{label}<input name={key} inputMode={kind === "month" ? "numeric" : "decimal"} value={form.values[key] ?? ""} placeholder={kind === "money" ? "0,00" : undefined} onChange={e => change(updateValue(form, key, e.target.value))}/></label>)}</div></fieldset>)}<label className="select-strategy">Rótulo do cenário de contemplação<select value={form.values.scenario ?? ""} onChange={e => change(updateValue(form, "scenario", e.target.value))}><option value="">Escolha explicitamente</option><option value="early">Antecipado</option><option value="intermediate">Intermediário</option><option value="late">Tardio</option></select></label><p className="hint">O rótulo não inventa uma data ou probabilidade. Principal, entrada, carta e complemento são valores declarados separadamente; o backend confere as relações.</p></section>
        <MonthlyProfile form={form} change={change}/><ConsortiumSchedule form={form} change={change}/>
        <section className="panel"><h2>Confirmações necessárias</h2><label className="check"><input type="checkbox" checked={form.scopeConfirmed} onChange={e => change({...form, scopeConfirmed: e.target.checked})}/><span>Declaro renda líquida após tributos e contribuições. As despesas externas são independentes das estratégias, não repetem deduções já descontadas e não incluem aluguel, parcelas, aportes ou reserva de caixa. Todo o saldo derivado entra na comparação.</span></label><label className="check"><input type="checkbox" checked={form.supportConfirmed} onChange={e => change({...form, supportConfirmed: e.target.checked})}/><span>Confirmo o recorte sintético: sem FGTS, subsídio, custos de transação, inflação, valorização, correção, seguro de financiamento ou amortização extra. Consórcio com crédito aplicado à carta, reserva sem devolução, parcelas independentes da contemplação e compra no mês declarado. Somente aluguel investe; não há resgate ou redução automática do aporte.</span></label><button type="submit">Revisar declarações</button></section>
      </form>
    </>}
    <footer>Simulação de apoio ao entendimento. Não é proposta, aprovação ou recomendação financeira.</footer>
  </main>;
}
