"use client";

import {useState} from "react";
import {copyComponent, decimal, type Component, type FormState} from "../lib/form-state";

type Side = "income_components" | "external_expenses";
export default function MonthlyProfile({form, change}: {form: FormState; change: (next: FormState) => void}) {
  const [selected, select] = useState(1);
  const [side, setSide] = useState<Side>("income_components");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [from, setFrom] = useState("1"); const [to, setTo] = useState("60");
  const [preview, setPreview] = useState<{component: Component | null; from: number; to: number; side: Side} | null>(null);
  const [error, setError] = useState("");
  const month = form.months[selected - 1];
  const update = (key: string, value: string) => {setPreview(null); setDraft({...draft, [key]: value});};
  function prepare(empty = false) {
    setError("");
    const start = Number(from), end = Number(to);
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end > 60 || start > end) {setError("Escolha um intervalo entre os meses 1 e 60."); return;}
    const id = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
    const timestamp = draft.source_as_of ?? "";
    const validDate = /^(?!0000)[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/.test(timestamp) && !Number.isNaN(Date.parse(timestamp)) && new Date(timestamp).toISOString() === timestamp.replace("Z", ".000Z");
    if (!empty && (!id.test(draft.component_id ?? "") || !id.test(draft.source_reference ?? "") || !/^[+-]?[0-9]{1,18}\.[0-9]{2}$/.test(decimal(draft.amount ?? "")) || !validDate || !["observed_data", "projected_assumption"].includes(draft.classification) || (draft.classification === "projected_assumption" && !id.test(draft.assumption_reference ?? "")))) {setError("Complete valor, classificação e proveniência. Use identificações sem espaços e a data UTC no formato indicado."); return;}
    const component: Component | null = empty ? null : {component_id: draft.component_id, amount: decimal(draft.amount), classification: draft.classification as Component["classification"], source_reference: draft.source_reference, source_as_of: draft.source_as_of, assumption_reference: draft.classification === "observed_data" ? null : draft.assumption_reference};
    try {if (component) copyComponent(form, side, component, start, end); setPreview({component, from: start, to: end, side});}
    catch (e) {setError((e as Error).message);}
  }
  function confirm() {
    if (!preview) return;
    try {
      change(preview.component ? copyComponent(form, preview.side, preview.component, preview.from, preview.to) : {...form, months: form.months.map(m => m.month < preview.from || m.month > preview.to ? m : {...m, [preview.side]: []})});
      setPreview(null); setError("");
    } catch (e) {setError((e as Error).message);}
  }
  return <section className="panel" aria-labelledby="profile-title">
    <div className="section-heading"><div><h2 id="profile-title">Renda e despesas nos 60 meses</h2><p>Informe valores líquidos após tributos e contribuições. Despesas externas não incluem moradia, parcelas, aportes ou deduções já descontadas.</p></div><span className="completion">{form.months.filter(m => m.income_components !== null && m.external_expenses !== null).length} de 60 declarados</span></div>
    <nav className="month-strip" aria-label="Meses do perfil">{form.months.map(m => <button type="button" key={m.month} aria-label={`Mês ${m.month}: ${m.income_components !== null && m.external_expenses !== null ? "declarado" : "incompleto"}`} aria-current={selected === m.month ? "step" : undefined} data-complete={m.income_components !== null && m.external_expenses !== null} onClick={() => select(m.month)}>{m.month}</button>)}</nav>
    <div className="profile-columns">
      <div><h3>Declarações do mês {selected}</h3>{(["income_components", "external_expenses"] as Side[]).map(s => <div className="flow-list" key={s}><h4>{s === "income_components" ? "Renda líquida" : "Despesas externas"}</h4>{month[s] === null ? <p className="muted">Ainda não declarado.</p> : month[s]!.length === 0 ? <p>Nenhum componente declarado.</p> : month[s]!.map(c => <div className="component-item" key={c.component_id}><strong>{c.component_id}</strong><span>{c.amount} BRL · {c.classification === "observed_data" ? "Dado observado" : "Premissa projetada"}</span><small>Fonte: {c.source_reference}, {c.source_as_of}{c.assumption_reference ? `; premissa: ${c.assumption_reference}` : ""}</small><div className="button-row"><button type="button" className="quiet" onClick={() => {setSide(s); setDraft({...c, assumption_reference: c.assumption_reference ?? ""}); setFrom(String(selected)); setTo(String(selected)); setPreview(null);}}>Editar este componente</button><button type="button" className="quiet" onClick={() => {setPreview(null); change({...form, months: form.months.map(m => m.month !== selected ? m : {...m, [s]: m[s]!.filter(item => item.component_id !== c.component_id)})});}}>Remover do mês {selected}</button></div></div>)}</div>)}</div>
      <div className="editor"><h3>Declarar componente ou ausência</h3><label>Tipo de fluxo<select value={side} onChange={e => {setSide(e.target.value as Side); setPreview(null);}}><option value="income_components">Renda líquida</option><option value="external_expenses">Despesa externa</option></select></label>
        <div className="field-grid">{[["component_id", "Identificação do componente"], ["amount", "Valor do componente"], ["source_reference", "Referência da fonte"], ["source_as_of", "Data da fonte em UTC"]].map(([key, label]) => <label key={key}>{label}<input value={draft[key] ?? ""} onChange={e => update(key, e.target.value)} placeholder={key === "source_as_of" ? "AAAA-MM-DDTHH:mm:ssZ" : key === "amount" ? "0,00" : undefined}/></label>)}
          <label>Classificação<select aria-label="Classificação" value={draft.classification ?? ""} onChange={e => update("classification", e.target.value)}><option value="">Escolha explicitamente</option><option value="observed_data">Dado observado</option><option value="projected_assumption">Premissa projetada</option></select></label>
          {draft.classification === "projected_assumption" && <label>Referência da premissa<input value={draft.assumption_reference ?? ""} onChange={e => update("assumption_reference", e.target.value)}/></label>}
        </div><p className="hint">Use referências sem nomes pessoais ou documentos. Uma data futura não determina a classificação.</p>
        <div className="range"><label>Do mês<input inputMode="numeric" value={from} onChange={e => {setFrom(e.target.value); setPreview(null);}}/></label><label>Até o mês<input inputMode="numeric" value={to} onChange={e => {setTo(e.target.value); setPreview(null);}}/></label></div>
        <div className="button-row"><button type="button" onClick={() => prepare()}>Revisar aplicação do componente</button><button type="button" className="secondary" onClick={() => prepare(true)}>Declarar ausência neste intervalo</button></div>
        {error && <p role="alert" aria-label="Erro do perfil" className="error">{error}</p>}
      </div>
    </div>
    {preview && <section className="preview" aria-label="Revisar cópia do perfil"><h3>Confirme as declarações dos meses {preview.from} a {preview.to}</h3><p>{preview.side === "income_components" ? "Renda líquida" : "Despesas externas"}: {preview.component ? "a mesma identificação será substituída; outros componentes permanecem." : "a lista completa será esvaziada nos meses selecionados."}</p><details><summary>Declaração a aplicar</summary><pre>{JSON.stringify(preview.component ?? [], null, 2)}</pre></details><div className="scroll-table"><table><caption>Declarações atuais dos destinos</caption><thead><tr><th>Mês</th><th>Componentes atuais</th></tr></thead><tbody>{form.months.filter(m => m.month >= preview.from && m.month <= preview.to).map(m => <tr key={m.month}><td>{m.month}</td><td>{JSON.stringify(m[preview.side])}</td></tr>)}</tbody></table></div><div className="button-row"><button type="button" onClick={confirm}>Confirmar declarações do perfil</button><button type="button" className="secondary" onClick={() => setPreview(null)}>Cancelar cópia</button></div></section>}
  </section>;
}
