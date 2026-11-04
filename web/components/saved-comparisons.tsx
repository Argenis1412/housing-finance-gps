"use client";

import Link from "next/link";
import {useEffect, useRef, useState} from "react";
import {errorMessage} from "../lib/api";
import {deleteSaved, displaySavedTime, listSaved, readSaved, type SavedList, type SavedResult} from "../lib/saved-api";
import Results from "./results";

export default function SavedComparisons() {
  const [list, setList] = useState<SavedList | null>(null), [selected, setSelected] = useState<SavedResult | null>(null);
  const [offset, setOffset] = useState(0), [failure, setFailure] = useState("");
  const [loading, setLoading] = useState(true), [confirmation, setConfirmation] = useState<string | null>(null);
  const sequence = useRef(0), controller = useRef<AbortController | null>(null), heading = useRef<HTMLHeadingElement>(null);
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {if (confirmation !== null) dialog.current?.focus();}, [confirmation]);
  async function load(action: (signal: AbortSignal) => Promise<void>) {
    const current = ++sequence.current; controller.current?.abort();
    const active = new AbortController(); controller.current = active;
    setLoading(true); setFailure("");
    try {await action(active.signal);} catch (error) {
      if (current === sequence.current) setFailure(errorMessage(error));
    } finally {if (current === sequence.current) setLoading(false);}
  }
  function refresh(next = offset) {
    setSelected(null); setConfirmation(null);
    return load(async signal => {
      const value = await listSaved(next, signal);
      if (!signal.aborted) {setList(value); setOffset(next);}
    });
  }
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    void listSaved(0, active.signal).then(value => {
      if (!active.signal.aborted) setList(value);
    }).catch(error => {
      if (!active.signal.aborted) setFailure(errorMessage(error));
    }).finally(() => {if (!active.signal.aborted) setLoading(false);});
    return () => {active.abort(); controller.current?.abort();};
  }, []);
  function open(simulationId: string) {
    setSelected(null); setConfirmation(null);
    void load(async signal => {
      const value = await readSaved(simulationId, signal);
      if (!signal.aborted) {setSelected(value); requestAnimationFrame(() => heading.current?.focus());}
    });
  }
  function remove(simulationId: string) {
    void load(async signal => {
      await deleteSaved(simulationId, signal);
      if (signal.aborted) return;
      // Clear the viewed artifact immediately after confirmed deletion, even if refreshing fails.
      setSelected(null); setConfirmation(null); setList(null);
      const value = await listSaved(0, signal);
      if (!signal.aborted) {setList(value); setOffset(0);}
    });
  }
  return <main><header className="masthead"><Link className="wordmark" href="/">Housing Finance GPS</Link><Link href="/">Nova comparação</Link></header>
    <div className="page-intro"><h1 tabIndex={-1} ref={heading}>Comparações salvas</h1><p>Resultados sintéticos guardados no banco local. Reabrir apresenta o histórico sem recalcular nem verificar por replay.</p></div>
    <aside className="session-notice">A lista mostra data de gravação em UTC e identificador do índice. A integridade do artefato é conferida ao abrir. Os registros ficam salvos até exclusão explícita. Use somente dados sintéticos.</aside>
    {loading && <p role="status">Acessando o banco local…</p>}
    {failure && <div role="alert" aria-label="Falha nas comparações salvas" className="error-summary"><p>{failure}</p><p>Se uma exclusão perdeu a confirmação, ela pode ter sido concluída. Atualize a lista para conferir.</p></div>}
    <div className="button-row"><button className="secondary" onClick={() => refresh()} disabled={loading}>Atualizar lista</button>{selected && <button className="secondary" onClick={() => {setSelected(null); setConfirmation(null);}}>Voltar à lista</button>}</div>
    {confirmation !== null && <section className="panel" role="alertdialog" tabIndex={-1} ref={dialog} aria-labelledby="delete-title" aria-describedby="delete-detail"><h2 id="delete-title">Excluir comparação {confirmation.slice(0, 8)}?</h2><p id="delete-detail">As declarações e o resultado serão removidos do aplicativo. Esta ação não pode ser desfeita. Apenas o identificador aleatório será mantido para impedir novas tentativas atrasadas.</p><div className="button-row"><button disabled={loading} onClick={() => remove(confirmation)}>Confirmar exclusão</button><button className="secondary" disabled={loading} onClick={() => setConfirmation(null)}>Cancelar exclusão</button></div></section>}
    {selected ? <><section className="panel"><p>Histórico salvo em {selected.saved_at}. Identificador: {selected.simulation_id}.</p><button className="secondary" disabled={loading} onClick={() => setConfirmation(selected.simulation_id)}>Excluir esta comparação</button></section><Results result={selected.result}/></> : list && <section className="panel"><h2>Resultados locais</h2>{list.items.length === 0 ? <p>Nenhuma comparação salva nesta página.</p> : <ul>{list.items.map(item => <li key={item.simulation_id}><p>Gravada em {displaySavedTime(item.saved_at)} — {item.simulation_id.slice(0, 8)}</p><div className="button-row"><button disabled={loading} onClick={() => open(item.simulation_id)}>Abrir {item.simulation_id.slice(0, 8)}</button><button className="secondary" disabled={loading} onClick={() => setConfirmation(item.simulation_id)}>Excluir {item.simulation_id.slice(0, 8)}</button></div></li>)}</ul>}<div className="button-row">{offset > 0 && <button className="secondary" disabled={loading} onClick={() => refresh(Math.max(0, offset - 20))}>Página anterior</button>}{list.next_offset !== null && <button className="secondary" disabled={loading} onClick={() => refresh(list.next_offset!)}>Próxima página</button>}</div></section>}
    <footer>Simulação de apoio ao entendimento. Não valida propostas reais nem capacidade financeira familiar.</footer>
  </main>;
}
