import { useEffect, useState } from "react";
import { ClipboardCopy, RefreshCw } from "lucide-react";
import { getDiagnosticoLocal, type DiagnosticoLocal } from "../lib/api";

const dataLocal = (iso: string | null) => iso ? new Date(iso).toLocaleString("pt-BR") : "Sem registro";
const integridade = (ok: boolean) => ok ? "Íntegro" : "Falhou";
const mb = (bytes: number) => `${(bytes / 1_048_576).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB`;

function linhas(d: DiagnosticoLocal): [string, string][] {
  const { banco, fiscal, ultimo_backup: backup } = d;
  return [
    ["Versão", d.versao],
    ["Banco", banco.caminho],
    ["Tamanho", mb(banco.bytes)],
    ["Espaço livre", mb(banco.livre_bytes)],
    ["Integridade do banco", integridade(banco.integro)],
    ["Último backup", backup ? `${backup.nome} · ${dataLocal(backup.criado_em)} · ${integridade(backup.integro)}` : "Sem registro"],
    ["Ambiente fiscal", fiscal.ambiente ?? "Sem configuração"],
    ["Certificado", fiscal.certificado_valido === null ? "Ausente" : fiscal.certificado_valido ? "Válido" : "Inválido"],
    ["Vencimento do certificado", dataLocal(fiscal.certificado_vence_em)],
    ["SEFAZ-MT", fiscal.sefaz.cstat ? `cStat ${fiscal.sefaz.cstat}` : fiscal.sefaz.situacao],
    ["Notas pendentes", String(fiscal.pendentes ?? "Sem registro")],
    ["Notas em contingência", String(fiscal.contingencia ?? "Sem registro")],
    ["Última sincronização confirmada", dataLocal(d.ultima_sincronizacao)],
  ];
}

export default function Diagnostico() {
  const [dados, setDados] = useState<DiagnosticoLocal>();
  const [carregando, setCarregando] = useState(true);
  const [mensagem, setMensagem] = useState("");

  async function atualizar() {
    setCarregando(true);
    setMensagem("");
    try {
      setDados(await getDiagnosticoLocal());
    } catch (erro) {
      setMensagem(erro instanceof Error ? erro.message : "Falha ao carregar o diagnóstico.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => { void atualizar(); }, []);
  const resumo = dados ? linhas(dados) : [];

  async function copiar() {
    try {
      await navigator.clipboard.writeText(resumo.map(([nome, valor]) => `${nome}: ${valor}`).join("\n"));
      setMensagem("Diagnóstico copiado.");
    } catch {
      setMensagem("Não foi possível acessar a área de transferência.");
    }
  }

  return (
    <section className="mx-auto max-w-4xl space-y-5">
      <h1 className="text-2xl font-bold text-white">Diagnóstico</h1>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={atualizar} disabled={carregando}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm disabled:opacity-50">
          <RefreshCw size={16} /> Atualizar
        </button>
        <button type="button" onClick={copiar} disabled={!dados || carregando}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
          <ClipboardCopy size={16} /> Copiar diagnóstico
        </button>
      </div>
      <p role="status" className="text-sm text-slate-300">{carregando ? "Carregando diagnóstico…" : mensagem}</p>
      {dados && (
        <dl className="divide-y divide-slate-800 rounded-xl border border-slate-800 bg-slate-900/60">
          {resumo.map(([nome, valor]) => (
            <div key={nome} className="grid gap-1 p-3 sm:grid-cols-[14rem_1fr]">
              <dt className="text-sm text-slate-400">{nome}</dt>
              <dd className="min-w-0 break-all text-sm text-slate-100">{valor}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
