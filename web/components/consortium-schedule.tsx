"use client";

import {useState} from "react";
import {decimal, type FormState, type ScheduleRow} from "../lib/form-state";

const columns = [["credit_component", "Crédito"], ["administration_fee", "Administração"], ["reserve_fund", "Fundo de reserva"], ["insurance", "Seguro"]] as const;
export default function ConsortiumSchedule({form, change}: {form: FormState; change: (next: FormState) => void}) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [from, setFrom] = useState("1"), [to, setTo] = useState("1");
  const [waitingFrom, setWaitingFrom] = useState("1"), [waitingTo, setWaitingTo] = useState("1"), [waitingAmount, setWaitingAmount] = useState("");
  const [preview, setPreview] = useState<{kind: "schedule" | "waiting"; from: number; to: number; amounts: Record<string, string>} | null>(null);
  const [error, setError] = useState("");
  function prepare(kind: "schedule" | "waiting") {
    const start = Number(kind === "schedule" ? from : waitingFrom), end = Number(kind === "schedule" ? to : waitingTo);
    const amounts = kind === "schedule" ? Object.fromEntries(columns.map(([key]) => [key, decimal(draft[key] ?? "")])) : {amount: decimal(waitingAmount)};
    const length = kind === "schedule" ? form.schedule.length : form.waiting.length;
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end > length || start > end || Object.values(amounts).some(v => !/^[+-]?[0-9]{1,18}\.[0-9]{2}$/.test(v))) {setError("Informe o intervalo existente e todos os valores com dois centavos decimais, incluindo zeros explícitos."); return;}
    setError(""); setPreview({kind, from: start, to: end, amounts});
  }
  function confirm() {
    if (!preview) return;
    if (preview.kind === "schedule") change({...form, schedule: form.schedule.map(r => r.month < preview.from || r.month > preview.to ? r : {...r, ...preview.amounts} as ScheduleRow)});
    else change({...form, waiting: form.waiting.map(r => r.month < preview.from || r.month > preview.to ? r : {...r, amount: preview.amounts.amount})});
    setPreview(null);
  }
  return <section className="panel" aria-labelledby="schedule-title"><h2 id="schedule-title">Cronograma declarado do consórcio</h2><p>Preencha cada componente, inclusive zeros. O backend confere a reconciliação; a interface não calcula parcelas ou resíduos.</p>
    {form.schedule.length === 0 ? <p className="muted">Informe o prazo do consórcio para abrir as linhas.</p> : <><div className="editor"><h3>Repetir valores declarados no cronograma</h3><div className="field-grid">{columns.map(([key, label]) => <label key={key}>{label} por mês<input value={draft[key] ?? ""} onChange={e => {setDraft({...draft, [key]: e.target.value}); setPreview(null);}} placeholder="0,00"/></label>)}</div><div className="range"><label>Do mês do cronograma<input value={from} onChange={e => {setFrom(e.target.value); setPreview(null);}}/></label><label>Até o mês do cronograma<input value={to} onChange={e => {setTo(e.target.value); setPreview(null);}}/></label></div><button type="button" onClick={() => prepare("schedule")}>Revisar cópia do cronograma</button></div>
    <details><summary>Editar as {form.schedule.length} linhas individualmente</summary><div className="scroll-table"><table><caption>Valores contratuais sintéticos declarados</caption><thead><tr><th>Mês</th>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{form.schedule.map(r => <tr key={r.month}><th>{r.month}</th>{columns.map(([key, label]) => <td key={key}><input aria-label={`${label}, mês ${r.month}`} value={r[key]} onChange={e => change({...form, schedule: form.schedule.map(row => row.month === r.month ? {...row, [key]: e.target.value} : row)})}/></td>)}</tr>)}</tbody></table></div></details></>}
    <h3>Custos de espera declarados</h3><p>Inclua o mês de compra. Os valores devem coincidir com o aluguel projetado da base comum; não há preenchimento automático de reajustes.</p>
    {form.waiting.length > 0 && <><div className="range"><label>Valor de espera a repetir<input value={waitingAmount} onChange={e => {setWaitingAmount(e.target.value); setPreview(null);}}/></label><label>Do mês de espera<input value={waitingFrom} onChange={e => {setWaitingFrom(e.target.value); setPreview(null);}}/></label><label>Até o mês de espera<input value={waitingTo} onChange={e => {setWaitingTo(e.target.value); setPreview(null);}}/></label></div><button type="button" onClick={() => prepare("waiting")}>Revisar cópia dos custos de espera</button><details><summary>Editar os {form.waiting.length} meses de espera</summary><div className="field-grid">{form.waiting.map(r => <label key={r.month}>Espera, mês {r.month}<input value={r.amount} onChange={e => change({...form, waiting: form.waiting.map(row => row.month === r.month ? {...row, amount: e.target.value} : row)})}/></label>)}</div></details></>}
    {error && <p role="alert" aria-label="Erro do cronograma" className="error">{error}</p>}
    {preview && <section className="preview" aria-label="Revisar cópia do cronograma"><h3>Substituir declarações dos meses {preview.from} a {preview.to}</h3><pre>{JSON.stringify(preview.amounts, null, 2)}</pre><details><summary>Ver declarações atuais dos destinos</summary><pre>{JSON.stringify((preview.kind === "schedule" ? form.schedule : form.waiting).filter(r => r.month >= preview.from && r.month <= preview.to), null, 2)}</pre></details><div className="button-row"><button type="button" onClick={confirm}>Confirmar cópia do cronograma</button><button type="button" className="secondary" onClick={() => setPreview(null)}>Cancelar cópia</button></div></section>}
  </section>;
}
