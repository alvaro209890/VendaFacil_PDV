"""Cadastro fiscal da NFC-e: CFOP derivado do CSOSN e pendências do catálogo.

A SEFAZ-MT valida o par CSOSN × CFOP **item a item** e rejeita a nota inteira
quando um item está fora da tabela da NT 2023.003 (rejeição 725, "NFC-e com CFOP
inválido"). Um catálogo importado com CFOP de NF-e (5401/5403) ou com CFOP de
substituição tributária em produto sem ST (5405 + CSOSN 102) derrubava vendas
que tinham itens perfeitamente válidos.

Regra adotada: **o CFOP da NFC-e é derivado do CSOSN na hora de emitir**.

- CSOSN 500 (ICMS já recolhido por ST) → 5405, e o CEST passa a ser obrigatório;
- demais CSOSN do Simples (101/102/103/104/300/400/900) → 5102, preservando
  5101/5103/5104/5115 quando o cadastro já usa um deles.

O cadastro continua mandando no CSOSN — é ele que define a tributação. O CFOP
deixa de ser uma fonte de erro: se o cadastro estiver com um CFOP de NF-e, a
NFC-e sai com o CFOP que a SEFAZ aceita, sem perder o item nem a venda.

O que **não** se deriva é o NCM: sem ele a SEFAZ rejeita (778) e não existe
substituto legal. Por isso o módulo também lista as pendências do catálogo e
sugere o NCM de um produto irmão já válido — sugestão, nunca aplicação
automática; quem confirma é o lojista/contador.
"""
from __future__ import annotations

import re
import unicodedata

CFOP_ST = "5405"
CFOP_SEM_ST = frozenset({"5101", "5102", "5103", "5104", "5115"})
CSOSN_ST = "500"
CFOP_POR_CSOSN = {c: "5102" for c in ("101", "102", "103", "104", "300", "400", "900")}
CSOSN_SUPORTADOS = frozenset(CFOP_POR_CSOSN) | {CSOSN_ST}

# Palavras que aparecem em produtos de NCM diferente e não servem para achar
# "irmão" no catálogo (papel higiênico x papel alumínio, suco x suco em pó...).
_TOKENS_GENERICOS = frozenset({
    "papel", "suco", "doce", "bolacha", "biscoito", "batata", "carvao", "pacoca",
    "amendoin", "amendoim", "gelo", "agua", "leite", "oleo", "molho", "queijo",
    "mussarela", "sabonete", "detergente", "toalha", "body", "creme", "bala",
    "salgadinho", "pipoca", "ovo", "acucar", "farinha", "arroz", "feijao",
})


def so_digitos(valor: object) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def cfop_nfce(prod: dict) -> str:
    """CFOP que a SEFAZ aceita na NFC-e para o CSOSN do produto."""
    csosn = str(prod.get("cst_csosn") or "102").strip()
    cfop = str(prod.get("cfop") or "").strip()
    if csosn == CSOSN_ST:
        return CFOP_ST
    if cfop in CFOP_SEM_ST:
        return cfop
    return CFOP_POR_CSOSN.get(csosn, "5102")


def pendencias_produto(prod: dict) -> list[str]:
    """Campos que impedem a emissão da NFC-e para este produto."""
    faltas: list[str] = []
    if len(so_digitos(prod.get("ncm"))) != 8:
        faltas.append("ncm")
    csosn = str(prod.get("cst_csosn") or "").strip()
    if csosn not in CSOSN_SUPORTADOS:
        faltas.append("cst_csosn")
    if csosn == CSOSN_ST and len(so_digitos(prod.get("cest"))) != 7:
        faltas.append("cest")
    return faltas


def _tokens(nome: str) -> list[str]:
    limpo = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return [t for t in re.sub(r"[^a-zA-Z0-9 ]", " ", limpo).lower().split() if len(t) >= 3]


def sugestao_ncm(prod: dict, catalogo: list[dict]) -> str:
    """NCM de um produto irmão do catálogo — só quando não há ambiguidade.

    Irmão = mesmo token "forte" do nome (fora a lista de palavras genéricas) e
    NCM válido. Se os irmãos apontam para NCMs diferentes, não sugere nada:
    melhor faltar do que chutar.
    """
    if len(so_digitos(prod.get("ncm"))) == 8:
        return ""
    tokens = [t for t in _tokens(prod.get("nome", "")) if t not in _TOKENS_GENERICOS]
    if not tokens:
        return ""
    alvo = tokens[0]
    ncms = {
        so_digitos(p.get("ncm"))
        for p in catalogo
        if p.get("id") != prod.get("id") and alvo in _tokens(p.get("nome", ""))
        and len(so_digitos(p.get("ncm"))) == 8
    }
    return ncms.pop() if len(ncms) == 1 else ""


def analisar(produtos: list[dict], vendas_por_produto: dict[int, int] | None = None) -> list[dict]:
    """Pendências do catálogo, com sugestão de NCM e peso de venda."""
    vendas = vendas_por_produto or {}
    itens = []
    for p in produtos:
        faltas = pendencias_produto(p)
        if not faltas:
            continue
        itens.append({
            "id": p.get("id"),
            "nome": p.get("nome") or "",
            "ncm": p.get("ncm") or "",
            "cest": p.get("cest") or "",
            "cfop": p.get("cfop") or "",
            "cst_csosn": p.get("cst_csosn") or "",
            "cfop_nfce": cfop_nfce(p),
            "faltando": faltas,
            "sugestao_ncm": sugestao_ncm(p, produtos),
            "vendas_30d": int(vendas.get(p.get("id"), 0)),
        })
    itens.sort(key=lambda x: (-x["vendas_30d"], x["nome"].lower()))
    return itens
