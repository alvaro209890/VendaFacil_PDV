import { useState } from "react";
import type { FormEvent } from "react";
import { PackagePlus, X } from "lucide-react";
import { criarProduto, atualizarProduto, entradaEstoque } from "../lib/api";
import type { Produto } from "../lib/api";
import { lerNumeroPtBr } from "../lib/numeros";

/** Janela do caixa para não travar a venda:
 * - "cadastrar": o código/nome bipado não existe → cadastro rápido e já vende;
 * - "completar": o produto existe mas está sem estoque ou sem preço → entrada
 *   rápida (fica no histórico como "Entrada rápida no caixa") e/ou preço. */
export type JanelaProduto =
  | { tipo: "cadastrar"; codigo: string; nome: string }
  | { tipo: "completar"; produto: Produto; modo: "embalagem" | "unidade"; semPreco: boolean; semEstoque: boolean };

const UNIDADES = ["UN", "KG", "G", "LT", "ML", "CX", "FD", "PCT"];
const fmt = (n: number) => Number(n || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
const CAMPO = "mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-brand-500 focus:outline-none";

export default function JanelaProdutoModal({ janela, onFechar, onPronto }: {
  janela: JanelaProduto;
  onFechar: () => void;
  onPronto: (produto: Produto, modo: "embalagem" | "unidade", criado: boolean) => void;
}) {
  const cadastrar = janela.tipo === "cadastrar";
  const p = janela.tipo === "completar" ? janela.produto : null;
  const modo = janela.tipo === "completar" ? janela.modo : "unidade";
  const embalagem = !!p?.vende_por_unidade && modo === "embalagem";
  const pedePreco = cadastrar || (janela.tipo === "completar" && janela.semPreco);
  const pedeQtd = cadastrar || (janela.tipo === "completar" && janela.semEstoque);
  const qtdInteira = !!p?.vende_por_unidade;
  const unEntrada = embalagem ? p!.unidade_compra : (p?.unidade || "UN");

  const [nome, setNome] = useState(cadastrar ? janela.nome : "");
  const [codigo, setCodigo] = useState(cadastrar ? janela.codigo : "");
  const [preco, setPreco] = useState("");
  const [qtd, setQtd] = useState("");
  const [custo, setCusto] = useState("");
  const [unidade, setUnidade] = useState("UN");
  const [ncm, setNcm] = useState("");
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (salvando) return;
    const vPreco = pedePreco ? lerNumeroPtBr(preco) : null;
    const vQtd = pedeQtd ? lerNumeroPtBr(qtd) : null;
    const vCusto = custo.trim() ? lerNumeroPtBr(custo) : 0;
    if (cadastrar && !nome.trim()) { setErro("Informe o nome do produto."); return; }
    if (pedePreco && !(vPreco && vPreco > 0)) { setErro("Informe o preço de venda (maior que zero)."); return; }
    if (pedeQtd && !(vQtd && vQtd > 0)) { setErro(`Informe quantas ${unEntrada} chegaram (maior que zero).`); return; }
    if (pedeQtd && qtdInteira && !Number.isInteger(vQtd)) { setErro("Use quantidade inteira para este produto."); return; }
    if (vCusto === null || vCusto < 0) { setErro("Custo inválido."); return; }
    if (cadastrar && ncm.trim() && !/^\d{8}$/.test(ncm.trim())) { setErro("NCM tem 8 dígitos (ou deixe em branco)."); return; }
    setErro("");
    setSalvando(true);
    try {
      let produto: Produto;
      if (cadastrar) {
        produto = (await criarProduto({
          nome: nome.trim(), codigo_barras: codigo.trim(), preco_venda: vPreco!, preco_custo: vCusto,
          estoque: vQtd!, unidade, unidade_compra: unidade, quantidade_por_embalagem: 1,
          ncm: ncm.trim(), cest: "", cfop: "5102", origem: "0", unidade_tributavel: "",
          cst_csosn: "102", cst_pis: "07", cst_cofins: "07",
        })).produto;
      } else {
        produto = p!;
        if (pedePreco) produto = (await atualizarProduto(produto.id, { preco_venda: vPreco! })).produto;
        if (pedeQtd) {
          produto = (await entradaEstoque(produto.id, vQtd!, vCusto ? vCusto : undefined,
            "Entrada rápida no caixa", embalagem ? "embalagem" : "unidade")).produto;
        }
      }
      onPronto(produto, modo, cadastrar);
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  const titulo = cadastrar ? "Produto não cadastrado" : (janela.tipo === "completar" && janela.semEstoque ? "Sem estoque" : "Sem preço de venda");
  const botao = cadastrar ? "Cadastrar e vender" : pedeQtd ? "Dar entrada e vender" : "Salvar preço e vender";

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[#020617]/90 backdrop-blur-sm" onClick={onFechar} />
      <form role="dialog" aria-modal="true" aria-labelledby="janela-produto-titulo" onSubmit={salvar}
        className="relative w-full max-w-md space-y-3 rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600/10 text-brand-400"><PackagePlus size={20} /></div>
          <h2 id="janela-produto-titulo" className="flex-1 text-lg font-black text-white">{titulo}</h2>
          <button type="button" aria-label="Fechar" onClick={onFechar} className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-800"><X size={18} /></button>
        </div>

        {cadastrar ? (
          <p className="text-sm text-slate-400">{janela.codigo ? <>O código <b className="text-white">{janela.codigo}</b> não está cadastrado.</> : <>Nada encontrado para <b className="text-white">{janela.nome}</b>.</>} Cadastre agora e ele já entra na venda.</p>
        ) : (
          <div className="space-y-1 text-sm text-slate-300">
            {janela.semEstoque && <p>Estoque insuficiente de <b className="text-white">“{p!.nome}”</b>: tem {fmt(p!.estoque)} {p!.unidade}{embalagem ? `; 1 ${p!.unidade_compra} precisa de ${fmt(p!.quantidade_por_embalagem)}` : ""}.</p>}
            {janela.semPreco && <p><b className="text-white">“{p!.nome}”</b> está sem preço de venda.</p>}
          </div>
        )}

        {cadastrar && <>
          <label className="block text-xs text-slate-300">Nome *<input aria-label="Nome do produto" autoFocus={!nome} value={nome} onChange={e => setNome(e.target.value)} className={CAMPO} placeholder="Ex: Refrigerante 2L" /></label>
          <label className="block text-xs text-slate-300">Código de barras<input aria-label="Código de barras" value={codigo} onChange={e => setCodigo(e.target.value)} className={CAMPO} placeholder="opcional" /></label>
        </>}
        <div className="grid grid-cols-2 gap-3">
          {pedePreco && <label className="block text-xs text-slate-300">Preço de venda (R$) *<input aria-label="Preço de venda" autoFocus={!cadastrar ? !pedeQtd : !!nome} inputMode="decimal" value={preco} onChange={e => setPreco(e.target.value)} className={CAMPO} placeholder="0,00" /></label>}
          {pedeQtd && <label className="block text-xs text-slate-300">{cadastrar ? "Quantidade em estoque *" : `Quantas ${unEntrada} chegaram? *`}<input aria-label="Quantidade em estoque" autoFocus={!cadastrar} inputMode="decimal" value={qtd} onChange={e => setQtd(e.target.value)} className={CAMPO} placeholder="0" /></label>}
          {cadastrar && <label className="block text-xs text-slate-300">Unidade<select aria-label="Unidade" value={unidade} onChange={e => setUnidade(e.target.value)} className={CAMPO}>{UNIDADES.map(u => <option key={u}>{u}</option>)}</select></label>}
          {pedeQtd && <label className="block text-xs text-slate-300">Custo {embalagem ? `por ${unEntrada}` : "por unidade"} (R$)<input aria-label="Custo" inputMode="decimal" value={custo} onChange={e => setCusto(e.target.value)} className={CAMPO} placeholder="opcional" /></label>}
          {cadastrar && <label className="block text-xs text-slate-300">NCM (para NFC-e)<input aria-label="NCM" inputMode="numeric" value={ncm} onChange={e => setNcm(e.target.value.replace(/\D/g, "").slice(0, 8))} className={CAMPO} placeholder="opcional" /></label>}
        </div>
        {cadastrar && <p className="text-2xs text-slate-500">Categoria, estoque mínimo, dados fiscais e caixa + unidade: complete depois em Produtos.</p>}

        {erro && <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-2 text-sm text-red-300">{erro}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onFechar} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-slate-300 hover:bg-slate-700">Cancelar (Esc)</button>
          <button type="submit" disabled={salvando} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white enabled:hover:bg-emerald-500 disabled:opacity-60">{salvando ? "Salvando..." : botao}</button>
        </div>
      </form>
    </div>
  );
}
