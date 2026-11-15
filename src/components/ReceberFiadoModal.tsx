import { useCallback, useEffect, useRef, useState } from 'react';
import { Banknote, CreditCard, Smartphone, X } from 'lucide-react';
import { lerNumeroPtBr } from '../lib/numeros';
import { moeda } from "../lib/numeros";
import {
  cancelarCobrancaFiado, consultarCobrancaFiado, criarCobrancaFiado, gerarPixFiado,
  getConfigMaquininha, listarContasReceber, pagarContaReceber, FORMAS_RECEBIMENTO,
  type CobrancaFiado, type ConfigMaquininha, type ContaReceber, type FormaRecebimento,
  type PixFiado, type ResultadoCobrancaFiado,
} from '../lib/api';

const campo = 'w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-white disabled:opacity-60';
const botao = 'rounded-lg px-4 py-2.5 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed';
type Props = { conta: ContaReceber; pixSalvo?: PixFiado; onFechar: () => void; onConcluido: () => void };
type Manual = { valor: number; forma: FormaRecebimento; referencia: string };

function recuperarManual(conta: ContaReceber): Manual | null {
  try {
    const salvo = JSON.parse(sessionStorage.getItem(`vf_fiado_${conta.id}`) || 'null') as Manual | null;
    if (salvo && conta.pagamentos?.some(p => p.referencia === `manual:${salvo.referencia}`)) {
      sessionStorage.removeItem(`vf_fiado_${conta.id}`);
      return null;
    }
    return salvo;
  } catch { return null; }
}

export default function ReceberFiadoModal({ conta, pixSalvo, onFechar, onConcluido }: Props) {
  const [manual, setManual] = useState(() => recuperarManual(conta));
  const [valorTexto, setValorTexto] = useState((manual?.valor ?? pixSalvo?.valor ?? conta.cobranca_pendente?.valor ?? conta.valor_pendente).toFixed(2).replace('.', ','));
  const [forma, setForma] = useState<FormaRecebimento>(manual?.forma ?? (pixSalvo ? 'pix' : undefined) ?? conta.cobranca_pendente?.forma ?? 'dinheiro');
  const [canal, setCanal] = useState('padrao');
  const [config, setConfig] = useState<ConfigMaquininha | null>(null);
  const [configPronta, setConfigPronta] = useState(false);
  const [cobranca, setCobranca] = useState<CobrancaFiado | null>(conta.cobranca_pendente ?? null);
  const [estado, setEstado] = useState('OPEN');
  const [pix, setPix] = useState<PixFiado | null>(pixSalvo ?? null);
  const [conferido, setConferido] = useState(false);
  const [busy, setBusy] = useState(false);
  const [aviso, setAviso] = useState('');
  const [copiado, setCopiado] = useState(false);
  const operando = useRef(false);
  const concluido = useRef(false);
  const valor = lerNumeroPtBr(valorTexto, 2);
  const pointDisponivel = !!(config?.habilitado && config.device_id);
  const usaPoint = forma !== 'dinheiro' && (canal === 'point' || (canal === 'padrao' && forma !== 'pix' && pointDisponivel));
  const usaQr = forma === 'pix' && (canal === 'padrao' || canal === 'qr');
  const bloqueado = busy || !!cobranca || !!pix || !!manual;

  useEffect(() => {
    let ativo = true;
    getConfigMaquininha().then(r => { if (ativo) setConfig(r.config); })
      .catch(() => { if (ativo) setAviso('Não foi possível consultar a configuração da Point. Feche e tente novamente para usar a integração.'); })
      .finally(() => { if (ativo) setConfigPronta(true); });
    return () => { ativo = false; };
  }, []);

  const finalizar = useCallback(() => {
    if (concluido.current) return;
    concluido.current = true;
    sessionStorage.removeItem(`vf_fiado_${conta.id}`);
    sessionStorage.removeItem(`vf_fiado_point_${conta.id}`);
    onConcluido();
  }, [conta.id, onConcluido]);

  const aplicar = useCallback((r: ResultadoCobrancaFiado) => {
    setEstado(r.state);
    if (r.cobranca.status === 'pago') {
      finalizar();
    } else if (r.cobranca.status !== 'pendente') {
      sessionStorage.removeItem(`vf_fiado_point_${conta.id}`);
      setCobranca(null);
      setAviso('Cobrança encerrada sem pagamento. A dívida continua em aberto.');
    } else {
      setCobranca(r.cobranca);
    }
  }, [finalizar, conta.id]);

  useEffect(() => {
    if (!cobranca) return;
    let ativo = true;
    let timer: ReturnType<typeof setTimeout>;
    async function consultar() {
      if (!operando.current) {
        operando.current = true;
        try {
          const r = await consultarCobrancaFiado(conta.id, cobranca!.id);
          if (ativo) { setAviso(''); aplicar(r); }
        } catch (err) {
          if (ativo) setAviso(`${(err as Error).message} A cobrança continua pendente; vamos consultar novamente.`);
        } finally { operando.current = false; }
      }
      if (ativo) timer = setTimeout(() => { void consultar(); }, 2500);
    }
    timer = setTimeout(() => { void consultar(); }, 1500);
    return () => { ativo = false; clearTimeout(timer); };
  }, [cobranca?.id, conta.id, aplicar]); // eslint-disable-line react-hooks/exhaustive-deps

  async function receber() {
    if (operando.current) return;
    if (valor === null || valor <= 0) { setAviso('Valor deve ser maior que zero.'); return; }
    if (!manual && valor > conta.valor_pendente) { setAviso('Pagamento maior que o pendente.'); return; }
    operando.current = true;
    setBusy(true); setAviso('');
    try {
      if (usaPoint && !manual) {
        const chave = `vf_fiado_point_${conta.id}`;
        const referencia = sessionStorage.getItem(chave) || crypto.randomUUID();
        sessionStorage.setItem(chave, referencia);
        aplicar(await criarCobrancaFiado(conta.id, valor, forma, referencia));
      } else if (usaQr && !pix && !manual) {
        setPix((await gerarPixFiado(conta.id, valor)).pix);
        setConferido(false);
      } else {
        const dados = manual ?? { valor, forma, referencia: pix?.id ?? crypto.randomUUID() };
        setManual(dados);
        sessionStorage.setItem(`vf_fiado_${conta.id}`, JSON.stringify(dados));
        await pagarContaReceber(conta.id, dados);
        finalizar();
      }
    } catch (err) {
      setAviso((err as Error).message);
      // Criação pode ter chegado à Point antes de uma falha na resposta: recuperar a reserva.
      if (usaPoint) {
        try {
          const r = await listarContasReceber();
          const atual = r.contas.find(c => c.id === conta.id);
          const pendente = atual?.cobranca_pendente;
          if (pendente) setCobranca(pendente);
          else if (atual?.pagamentos?.some(p => p.referencia === `point:${sessionStorage.getItem(`vf_fiado_point_${conta.id}`)}`)) finalizar();
          else if (atual) sessionStorage.removeItem(`vf_fiado_point_${conta.id}`);
        } catch { /* Ao reabrir a tela a reserva continua disponível. */ }
      }
    } finally { operando.current = false; setBusy(false); }
  }

  async function cancelarPoint() {
    if (!cobranca || operando.current) return;
    operando.current = true; setBusy(true); setAviso('');
    try {
      const r = await cancelarCobrancaFiado(conta.id, cobranca.id);
      aplicar(r);
      if (r.cobranca.status === 'pendente') setAviso('Cancelamento solicitado. Aguarde a confirmação da Point.');
    } catch (err) { setAviso((err as Error).message); }
    finally { operando.current = false; setBusy(false); }
  }

  async function copiarPix() {
    if (!pix) return;
    try { await navigator.clipboard.writeText(pix.payload); setCopiado(true); }
    catch { setAviso('Selecione o código e copie com Ctrl+C.'); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section role="dialog" aria-modal="true" aria-labelledby="receber-titulo" className="modal-panel w-full max-w-lg space-y-4 overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl max-h-[90vh]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="receber-titulo" className="text-lg font-bold text-white">Receber fiado</h2>
            <p className="text-sm text-slate-400">{conta.cliente_nome || 'Sem cliente'} · Conta #{conta.id}</p>
            <p className="text-sm text-slate-400">Saldo: {moeda(conta.valor_pendente)}</p>
          </div>
          <button aria-label="Fechar recebimento" disabled={busy} onClick={onFechar} className="p-2 text-slate-400 disabled:opacity-50"><X size={20} /></button>
        </div>
        {!pix ? <><label className="block space-y-1 text-sm text-slate-300">Valor a receber
          <input autoFocus aria-label="Valor a receber" inputMode="decimal" className={campo} value={valorTexto} disabled={bloqueado} onChange={e => setValorTexto(e.target.value)} />
        </label>
        <div className="grid grid-cols-2 gap-2" role="group" aria-label="Forma de pagamento">
          {(Object.entries(FORMAS_RECEBIMENTO) as [FormaRecebimento, string][]).map(([f, nome]) => (
            <button key={f} disabled={bloqueado} aria-pressed={forma === f} onClick={() => { setForma(f); setCanal('padrao'); setConferido(false); setAviso(''); }} className={`${botao} flex items-center justify-center gap-2 border ${forma === f ? 'border-brand-500 bg-brand-600/20 text-brand-300' : 'border-slate-700 text-slate-400'}`}>
              {f === 'dinheiro' ? <Banknote size={18} /> : f === 'pix' ? <Smartphone size={18} /> : <CreditCard size={18} />}{nome}
            </button>
          ))}
        </div>
        </> : <p className="text-xl font-semibold text-brand-300">PIX · {moeda(pix.valor)}</p>}
        {forma !== 'dinheiro' && !cobranca && !pix && !manual && (
          <label className="block space-y-1 text-sm text-slate-300">Como receber
            <select aria-label="Como receber" className={campo} value={canal} disabled={busy || !configPronta} onChange={e => { setCanal(e.target.value); setConferido(false); }}>
              <option value="padrao">{forma === 'pix' ? 'QR Code / copia e cola' : pointDisponivel ? 'Enviar para a Point' : 'Cartão passado em outra maquininha'}</option>
              {forma === 'pix' && pointDisponivel && !!config?.pix_integrado && <option value="point">PIX na Point (confirmação automática)</option>}
              {(forma === 'pix' || pointDisponivel) && <option value="manual">{forma === 'pix' ? 'PIX já recebido' : 'Cartão passado em outra maquininha'}</option>}
            </select>
          </label>
        )}
        {cobranca ? (
          <div className="space-y-3 rounded-xl border border-brand-700 bg-brand-900/20 p-4">
            <p className="font-medium text-brand-300">{estado === 'ON_TERMINAL' ? 'Cobrança na maquininha' : estado === 'PROCESSING' ? 'Pagamento em processamento' : 'Aguardando pagamento na Point'}</p>
            <p className="text-sm text-slate-400">A baixa será feita após a aprovação. Você pode fechar esta janela e acompanhar depois em Receber.</p>
            <button className={`${botao} bg-slate-800 text-white`} disabled={busy} onClick={() => { void cancelarPoint(); }}>Cancelar cobrança na Point</button>
          </div>
        ) : (
          <>
            {pix && <div className="space-y-3 text-center">
              <img src={`data:image/png;base64,${pix.qr_base64}`} alt="QR Code PIX do fiado" className="mx-auto h-40 w-40 rounded-lg bg-white p-2" />
              <label className="block text-left text-sm text-slate-300">PIX copia e cola
                <textarea aria-label="PIX copia e cola" readOnly value={pix.payload} onFocus={e => e.target.select()} className={`${campo} mt-1 h-16 resize-none text-xs`} />
              </label>
              <button onClick={() => { void copiarPix(); }} className={`${botao} bg-brand-600 text-white`}>{copiado ? 'Código copiado!' : 'Copiar código PIX'}</button>
              <p className="text-sm text-slate-300">Código salvo. Envie pelo WhatsApp e continue vendendo: a maquininha fica livre.</p>
              <p className="text-xs text-amber-300">Confira o crédito na conta da loja antes de confirmar. Gerar ou copiar o código não quita a dívida.</p>
              {pix.valor > conta.valor_pendente && <p className="text-xs text-amber-300">O saldo mudou após gerar este código. Confira o valor recebido antes de fazer um novo acerto.</p>}
            </div>}
            {!usaPoint && forma !== 'dinheiro' && (!usaQr || pix) && !manual && (
              <label className="flex items-start gap-2 text-sm text-slate-300"><input type="checkbox" checked={conferido} onChange={e => setConferido(e.target.checked)} className="mt-1 accent-brand-500" />{forma === 'pix' ? 'Conferi que o PIX foi recebido na conta da loja.' : 'Conferi que o cartão foi aprovado na maquininha.'}</label>
            )}
            {manual && <p className="text-sm text-amber-300">Reenvie a confirmação para verificar este recebimento sem duplicar a baixa.</p>}
            <button disabled={busy || (!configPronta && forma !== 'dinheiro' && forma !== 'pix') || (!usaPoint && forma !== 'dinheiro' && (!usaQr || !!pix) && !conferido && !manual)} onClick={() => { void receber(); }} className={`${botao} w-full bg-emerald-600 text-white hover:bg-emerald-500`}>
              {busy ? 'Aguarde…' : manual ? 'Verificar recebimento' : usaPoint ? 'Enviar cobrança para a Point' : usaQr && !pix ? 'Gerar PIX' : forma === 'dinheiro' ? 'Confirmar recebimento em dinheiro' : 'Confirmar recebimento'}
            </button>
          </>
        )}
        {aviso && <p role="alert" className="rounded-lg bg-amber-900/30 p-3 text-sm text-amber-200">{aviso}</p>}
        <button disabled={busy} onClick={onFechar} className={`${botao} sticky bottom-0 w-full bg-slate-800 text-slate-300 shadow-lg`}>{pix ? 'Fechar e continuar vendendo' : cobranca ? 'Fechar e acompanhar depois' : 'Voltar'}</button>
      </section>
    </div>
  );
}
