import { useCallback, useEffect, useState } from "react";
import {
  getConfigFiscal,
  obterExtratoCliente,
  type ExtratoCliente as Extrato,
} from "../lib/api";
import {
  baixarCsvExtrato,
  baixarPdfExtrato,
  dataHora,
  hojeCuiaba,
  somaDias,
  type LojaExtrato,
} from "../lib/extrato-export";
import { moeda } from "../lib/numeros";
import { rotuloForma } from "../lib/rotulos";

interface Props {
  clienteId: number;
  clienteNome?: string;
  onFechar: () => void;
}

const SITUACAO_CONTA: Record<string, string> = {
  pendente: "bg-yellow-900/30 text-yellow-400 border-yellow-800",
  parcial: "bg-blue-900/30 text-blue-400 border-blue-800",
  pago: "bg-green-900/30 text-green-400 border-green-800",
  cancelado: "bg-slate-800 text-slate-500 border-slate-700",
};

export default function ExtratoClienteModal({ clienteId, clienteNome, onFechar }: Props) {
  const [extrato, setExtrato] = useState<Extrato | null>(null);
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [loja, setLoja] = useState<LojaExtrato>({});

  const carregar = useCallback(async (de: string, ate: string) => {
    setCarregando(true);
    setErro(null);
    try {
      setExtrato(await obterExtratoCliente(clienteId, de || undefined, ate || undefined));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  }, [clienteId]);

  useEffect(() => {
    void carregar("", "");
  }, [carregar]);

  useEffect(() => {
    getConfigFiscal()
      .then(({ config }) => setLoja({
        nome: config.nome_fantasia || config.razao_social,
        razao: config.razao_social,
        cnpj: config.cnpj,
        ie: config.inscricao_estadual,
        endereco: [config.logradouro, config.numero, config.bairro, config.municipio, config.uf]
          .filter(Boolean).join(", "),
      }))
      .catch(() => undefined);
  }, []);

  function atalho(periodo: "hoje" | "7" | "30" | "tudo") {
    const hoje = hojeCuiaba();
    if (periodo === "tudo") {
      setInicio("");
      setFim("");
      void carregar("", "");
      return;
    }
    const de = periodo === "hoje" ? hoje : somaDias(hoje, periodo === "7" ? -6 : -29);
    setInicio(de);
    setFim(hoje);
    void carregar(de, hoje);
  }

  const nome = extrato?.cliente.nome || clienteNome || "Cliente";

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[60] p-2 sm:p-4" onClick={onFechar}>
      <div
        className="bg-slate-900 rounded-2xl w-full max-w-3xl border border-slate-800 shadow-2xl flex flex-col max-h-[94vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 p-4 border-b border-slate-800">
          <div className="min-w-0">
            <h2 className="text-base sm:text-lg font-bold text-white truncate">Extrato de compras</h2>
            <p className="text-xs sm:text-sm text-slate-400 truncate">{nome}</p>
          </div>
          <button onClick={onFechar} className="text-slate-400 hover:text-white text-xl leading-none px-1 active:scale-95">✕</button>
        </div>

        <div className="overflow-y-auto p-4 space-y-3">
          {/* Filtro */}
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex gap-1.5">
              {([
                ["hoje", "Hoje"], ["7", "7 dias"], ["30", "30 dias"], ["tudo", "Tudo"],
              ] as const).map(([chave, rotulo]) => (
                <button
                  key={chave}
                  onClick={() => atalho(chave)}
                  className="px-2.5 py-1.5 rounded-lg text-2xs sm:text-xs font-medium bg-slate-800 text-slate-300 hover:text-white border border-slate-700 active:scale-95"
                >
                  {rotulo}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1.5 ml-auto">
              <input
                type="date"
                value={inicio}
                onChange={(e) => setInicio(e.target.value)}
                className="px-2 py-1.5 bg-slate-800 text-white rounded-lg border border-slate-700 text-2xs sm:text-xs"
                aria-label="Início"
              />
              <span className="text-slate-500 text-xs">até</span>
              <input
                type="date"
                value={fim}
                onChange={(e) => setFim(e.target.value)}
                className="px-2 py-1.5 bg-slate-800 text-white rounded-lg border border-slate-700 text-2xs sm:text-xs"
                aria-label="Fim"
              />
              <button
                onClick={() => void carregar(inicio, fim)}
                className="px-3 py-1.5 rounded-lg text-2xs sm:text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white active:scale-95"
              >
                Filtrar
              </button>
            </div>
          </div>

          {erro && <div className="p-3 rounded-lg text-sm bg-red-900/50 text-red-400">{erro}</div>}

          {carregando ? (
            <div className="flex items-center justify-center py-10">
              <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !extrato ? null : (
            <>
              {/* Resumo */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-800">
                  <p className="text-2xs text-slate-400 uppercase">Compras</p>
                  <p className="text-white font-semibold text-sm sm:text-base">{extrato.resumo.compras}</p>
                </div>
                <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-800">
                  <p className="text-2xs text-slate-400 uppercase">Total comprado</p>
                  <p className="text-brand-400 font-semibold text-sm sm:text-base">{moeda(extrato.resumo.total)}</p>
                </div>
                <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-800">
                  <p className="text-2xs text-slate-400 uppercase">Fiado</p>
                  <p className="text-white font-semibold text-sm sm:text-base">{moeda(extrato.resumo.fiado_total)}</p>
                </div>
                <div className="bg-slate-800/60 rounded-xl p-2.5 border border-slate-800">
                  <p className="text-2xs text-slate-400 uppercase">Em aberto</p>
                  <p className={`font-semibold text-sm sm:text-base ${extrato.resumo.fiado_pendente > 0 ? "text-yellow-400" : "text-green-400"}`}>
                    {moeda(extrato.resumo.fiado_pendente)}
                  </p>
                </div>
              </div>

              {extrato.resumo.ultima && (
                <p className="text-2xs text-slate-500">
                  Primeira compra: {dataHora(extrato.resumo.primeira!)} · Última: {dataHora(extrato.resumo.ultima)}
                </p>
              )}

              {/* Compras */}
              {extrato.compras.length === 0 ? (
                <p className="text-center py-8 text-slate-500 text-sm">Nenhuma compra no período.</p>
              ) : (
                <div className="space-y-2">
                  {extrato.compras.map((compra) => (
                    <div key={compra.id} className="bg-slate-950/40 rounded-xl p-3 border border-slate-800">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="text-xs sm:text-sm text-white font-medium">
                          {dataHora(compra.criado_em)}
                        </span>
                        <span className="text-2xs text-slate-500">Venda #{compra.id}</span>
                        <span className="text-2xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{rotuloForma(compra.forma_pagamento)}</span>
                        {compra.status !== "concluida" && (
                          <span className="text-2xs px-1.5 py-0.5 rounded bg-red-900/40 text-red-400">{compra.status}</span>
                        )}
                        {compra.conta && (
                          <span className={`text-2xs px-1.5 py-0.5 rounded border ${SITUACAO_CONTA[compra.conta.status] || ""}`}>
                            Fiado {compra.conta.status} · {moeda(compra.conta.valor_pendente)}
                          </span>
                        )}
                        {compra.nota && (
                          <span className="text-2xs text-slate-500">NFC-e {compra.nota.numero ?? "-"} {compra.nota.status || ""}</span>
                        )}
                        <span className="ml-auto text-sm font-semibold text-brand-400">{moeda(compra.total)}</span>
                      </div>
                      <ul className="mt-1.5 space-y-0.5">
                        {(compra.itens || []).map((item, indice) => (
                          <li key={`${compra.id}-${indice}`} className="flex justify-between gap-2 text-xs text-slate-300">
                            <span className="min-w-0 truncate">
                              <span className="text-slate-500">{Number(item.quantidade || 0)}×</span> {item.nome_produto}
                              {item.unidade_venda ? <span className="text-slate-500"> {item.unidade_venda}</span> : null}
                            </span>
                            <span className="shrink-0 text-slate-400">{moeda(item.subtotal)}</span>
                          </li>
                        ))}
                        {!(compra.itens || []).length && (
                          <li className="text-xs text-slate-500">(itens não registrados nesta venda)</li>
                        )}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="p-3 sm:p-4 border-t border-slate-800 flex flex-wrap gap-2">
          <button
            onClick={() => extrato && baixarPdfExtrato(extrato, loja)}
            disabled={!extrato}
            className="flex-1 sm:flex-none px-3 py-2 rounded-lg text-xs sm:text-sm font-medium bg-brand-600 hover:bg-brand-500 text-white active:scale-95 disabled:opacity-40"
          >
            Baixar PDF
          </button>
          <button
            onClick={() => extrato && baixarCsvExtrato(extrato)}
            disabled={!extrato}
            className="flex-1 sm:flex-none px-3 py-2 rounded-lg text-xs sm:text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 active:scale-95 disabled:opacity-40"
          >
            Baixar CSV (Excel)
          </button>
          <button
            onClick={onFechar}
            className="flex-1 sm:flex-none sm:ml-auto px-3 py-2 rounded-lg text-xs sm:text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 active:scale-95"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
