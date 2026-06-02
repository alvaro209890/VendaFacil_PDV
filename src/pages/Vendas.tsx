import { useState, useEffect, useCallback } from "react";
import { FileText, ExternalLink, RefreshCw, Download } from "lucide-react";
import { listarVendas, obterVenda, getNotaDaVenda, emitirNfce, consultarNfce, listarClientes, getNfeDaVenda, emitirNfe, consultarNfe, baixarXmlNota } from "../lib/api";
import type { Cliente } from "../lib/api";
import type { Venda, NotaFiscal } from "../lib/api";

export default function VendasPage() {
  const [vendas, setVendas] = useState<Venda[]>([]);
  const [loading, setLoading] = useState(true);
  const [detalhe, setDetalhe] = useState<Venda | null>(null);
  const [nota, setNota] = useState<NotaFiscal | null>(null);
  const [nfe, setNfe] = useState<NotaFiscal | null>(null);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteNfe, setClienteNfe] = useState<number | "">("");
  const [emitindo, setEmitindo] = useState(false);
  const [cpf, setCpf] = useState("");

  const carregar = useCallback(async () => {
    try {
      const res = await listarVendas(100);
      setVendas(res.vendas);
      const cs = await listarClientes();
      setClientes(cs.clientes);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function verDetalhe(id: number) {
    try {
      const res = await obterVenda(id);
      setDetalhe(res.venda);
      const resNota = await getNotaDaVenda(id);
      setNota(resNota.nota);
      const resNfe = await getNfeDaVenda(id);
      setNfe(resNfe.nota);
      setCpf("");
      setClienteNfe("");
    } catch {
      // silent
    }
  }

  async function handleEmitir() {
    if (!detalhe) return;
    setEmitindo(true);
    try {
      const { nota: n } = await emitirNfce(detalhe.id, cpf);
      setNota(n);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setEmitindo(false);
    }
  }

  async function handleConsultar() {
    if (!nota) return;
    setEmitindo(true);
    try {
      const { nota: n } = await consultarNfce(nota.id);
      setNota(n);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setEmitindo(false);
    }
  }

  async function handleEmitirNfe() {
    if (!detalhe || !clienteNfe) return alert("Selecione o cliente destinatário da NF-e.");
    setEmitindo(true);
    try {
      const { nota: n } = await emitirNfe(detalhe.id, Number(clienteNfe));
      setNfe(n);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setEmitindo(false);
    }
  }

  const totalHoje = vendas
    .filter((v) => {
      const hoje = new Date().toLocaleDateString("pt-BR");
      const dataVenda = new Date(v.criado_em).toLocaleDateString("pt-BR");
      return dataVenda === hoje;
    })
    .reduce((s, v) => s + v.total, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row gap-3 lg:gap-4 h-full">
      {/* Lista */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-white font-bold text-base sm:text-lg">🧾 Histórico de Vendas</h2>
          <span className="text-slate-400 text-xs sm:text-sm">Hoje: R$ {totalHoje.toFixed(2)}</span>
        </div>

        <div className="flex-1 overflow-y-auto rounded-xl bg-slate-900 border border-slate-800">
          {vendas.length === 0 ? (
            <p className="text-slate-500 text-center py-8 sm:py-12 text-sm">Nenhuma venda realizada.</p>
          ) : (
            <>
              <div className="sm:hidden grid gap-2 p-2">
                {vendas.map((v) => (
                  <article key={v.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-white font-semibold">Venda #{v.id}</h3>
                        <p className="text-slate-400 text-xs mt-0.5">
                          {new Date(v.criado_em).toLocaleDateString("pt-BR")} às {new Date(v.criado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                        </p>
                        <span className="inline-flex mt-2 text-slate-300 text-2xs bg-slate-800 px-2 py-1 rounded-full capitalize">
                          {v.forma_pagamento}
                        </span>
                      </div>
                      <p className="text-brand-400 font-bold whitespace-nowrap">R$ {v.total.toFixed(2)}</p>
                    </div>
                    <button
                      onClick={() => verDetalhe(v.id)}
                      className="touch-target mt-3 w-full rounded-lg bg-slate-800 text-slate-200 text-sm active:scale-95"
                    >
                      Ver detalhes
                    </button>
                  </article>
                ))}
              </div>

              <table className="hidden sm:table w-full text-sm">
                <thead className="bg-slate-800 sticky top-0">
                  <tr className="text-slate-400 text-left">
                    <th className="p-3 font-medium">#</th>
                    <th className="p-3 font-medium">Data</th>
                    <th className="p-3 font-medium">Pagamento</th>
                    <th className="p-3 font-medium">Total</th>
                    <th className="p-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {vendas.map((v) => (
                    <tr key={v.id} className="border-t border-slate-800 hover:bg-slate-800/50">
                      <td className="p-3 text-white font-medium">{v.id}</td>
                      <td className="p-3 text-slate-300 whitespace-nowrap">
                        {new Date(v.criado_em).toLocaleDateString("pt-BR")}
                        <span className="text-slate-500 text-2xs block">
                          {new Date(v.criado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className="text-slate-300 text-xs bg-slate-800 px-2 py-0.5 rounded capitalize">{v.forma_pagamento}</span>
                      </td>
                      <td className="p-3 text-brand-400 font-bold whitespace-nowrap">R$ {v.total.toFixed(2)}</td>
                      <td className="p-3 text-right">
                        <button onClick={() => verDetalhe(v.id)} className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-slate-700 active:scale-95">Detalhes</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>

      {/* Detalhe da venda */}
      {detalhe && (
        <div className="w-full lg:w-96 bg-slate-900 border border-slate-800 rounded-xl p-3 sm:p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold text-sm sm:text-base">Venda #{detalhe.id}</h3>
            <button onClick={() => setDetalhe(null)} className="text-slate-400 hover:text-white text-lg active:scale-95">
              ×
            </button>
          </div>

          <div className="space-y-2 text-xs sm:text-sm mb-4">
            <div className="flex justify-between">
              <span className="text-slate-400">Data</span>
              <span className="text-white text-right">
                {new Date(detalhe.criado_em).toLocaleString("pt-BR")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Pagamento</span>
              <span className="text-white capitalize">{detalhe.forma_pagamento}</span>
            </div>
            {detalhe.observacao && (
              <div className="flex justify-between">
                <span className="text-slate-400">Obs</span>
                <span className="text-white text-right">{detalhe.observacao}</span>
              </div>
            )}
          </div>

          <h4 className="text-slate-400 text-2xs sm:text-xs font-medium mb-2 uppercase">Itens</h4>
          <div className="space-y-1 mb-4">
            {(detalhe.itens || []).map((item, idx) => (
              <div key={idx} className="flex justify-between bg-slate-800 rounded p-2 text-xs sm:text-sm">
                <div className="min-w-0">
                  <span className="text-white truncate block">{item.nome_produto}</span>
                  <span className="text-slate-500 ml-1">×{item.quantidade}</span>
                </div>
                <span className="text-brand-400 shrink-0 ml-2">R$ {item.subtotal.toFixed(2)}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-slate-700 pt-3 space-y-1 text-xs sm:text-sm">
            {detalhe.desconto > 0 && (
              <div className="flex justify-between text-green-400">
                <span>Desconto</span>
                <span>− R$ {detalhe.desconto.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold text-base sm:text-lg mb-4">
              <span className="text-white">Total</span>
              <span className="text-brand-400">R$ {detalhe.total.toFixed(2)}</span>
            </div>

            {/* Parte Fiscal */}
            <div className="pt-4 border-t border-slate-800">
              <h4 className="text-white font-bold text-xs mb-3 flex items-center gap-2">
                <FileText size={14} /> NFC-e (Cupom Fiscal)
              </h4>

              {!nota ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="CPF/CNPJ (opcional)"
                    value={cpf}
                    onChange={(e) => setCpf(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-white text-xs"
                  />
                  <button
                    onClick={handleEmitir}
                    disabled={emitindo}
                    className="w-full py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-bold rounded flex items-center justify-center gap-2"
                  >
                    {emitindo ? <RefreshCw size={14} className="animate-spin" /> : <ExternalLink size={14} />}
                    Emitir NFC-e
                  </button>
                </div>
              ) : (
                <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                      nota.status === "autorizada" ? "bg-emerald-500/10 text-emerald-400" :
                      nota.status === "rejeitada" ? "bg-red-500/10 text-red-400" :
                      "bg-amber-500/10 text-amber-400"
                    }`}>
                      {nota.status}
                    </span>
                    <button onClick={handleConsultar} disabled={emitindo} title="Atualizar status" className="text-slate-500 hover:text-white transition-colors">
                      <RefreshCw size={14} className={emitindo ? "animate-spin" : ""} />
                    </button>
                  </div>

                  {nota.numero && (
                    <p className="text-slate-400 text-[10px] mb-1">Série {nota.serie} • Nº {nota.numero}</p>
                  )}
                  {nota.chave && (
                    <p className="text-slate-500 text-[9px] font-mono break-all mb-2">{nota.chave}</p>
                  )}

                  <div className="flex flex-wrap gap-2 mt-3">
                    {nota.danfe_url && (
                      <a
                        href={nota.danfe_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-[10px] font-bold rounded flex items-center justify-center gap-1"
                      >
                        <ExternalLink size={12} /> DANFE
                      </a>
                    )}
                    {nota.xml_url && (
                      <a
                        href={nota.xml_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-[10px] font-bold rounded flex items-center justify-center gap-1"
                      >
                        XML
                      </a>
                    )}
                    {!nota.xml_url && nota.status === "autorizada" && (
                      <button
                        onClick={() => baixarXmlNota(nota.id).catch((e) => alert((e as Error).message))}
                        className="flex-1 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-[10px] font-bold rounded flex items-center justify-center gap-1"
                      >
                        <Download size={12} /> Baixar XML
                      </button>
                    )}
                  </div>

                  {nota.mensagem && nota.status !== "autorizada" && (
                    <p className="mt-3 text-[10px] text-red-400 bg-red-400/5 p-2 rounded border border-red-400/20">
                      {nota.mensagem}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-800 mt-4">
              <h4 className="text-white font-bold text-xs mb-3 flex items-center gap-2">
                <FileText size={14} /> NF-e modelo 55
              </h4>
              {!nfe ? (
                <div className="space-y-2">
                  <select
                    value={clienteNfe}
                    onChange={(e) => setClienteNfe(e.target.value ? Number(e.target.value) : "")}
                    className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-white text-xs"
                  >
                    <option value="">Cliente destinatário...</option>
                    {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
                  </select>
                  <button
                    onClick={handleEmitirNfe}
                    disabled={emitindo || !clienteNfe}
                    className="w-full py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white text-xs font-bold rounded flex items-center justify-center gap-2"
                  >
                    {emitindo ? <RefreshCw size={14} className="animate-spin" /> : <ExternalLink size={14} />}
                    Emitir NF-e
                  </button>
                </div>
              ) : (
                <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-amber-500/10 text-amber-400">{nfe.status}</span>
                    <button onClick={async () => { const r = await consultarNfe(nfe.id); setNfe(r.nota); }} disabled={emitindo} title="Atualizar status" className="text-slate-500 hover:text-white transition-colors">
                      <RefreshCw size={14} className={emitindo ? "animate-spin" : ""} />
                    </button>
                  </div>
                  {nfe.numero && <p className="text-slate-400 text-[10px] mb-1">Série {nfe.serie} • Nº {nfe.numero}</p>}
                  {nfe.chave && <p className="text-slate-500 text-[9px] font-mono break-all mb-2">{nfe.chave}</p>}
                  {nfe.mensagem && <p className="mt-3 text-[10px] text-amber-400 bg-amber-400/5 p-2 rounded border border-amber-400/20">{nfe.mensagem}</p>}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
