"""Vendas / Checkout — VendaFácil PDV"""

import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth import _agora
from database import db, EstoqueConcorrente
from dinheiro import CENTAVO, decimal, moeda, multiplicar, somar
from produtos import _get_user_id
import conta as conta_mod

router = APIRouter()

# ── Models ──

class ItemVenda(BaseModel):
    produto_id: int
    quantidade: float = Field(allow_inf_nan=False)
    modo_venda: Literal["unidade", "embalagem"] | None = None


class PagamentoEletronico(BaseModel):
    """Vínculo do pagamento eletrônico p/ a NFC-e (Portaria 262/2023-MT).

    Preenchido pelo PDV a partir da resposta da maquininha (campo
    ``pagamento_fiscal`` de GET /maquininha/cobranca/{id})."""
    tipo_integracao: str | None = Field(default=None, max_length=1)   # 1 integrado | 2 não
    adquirente_cnpj: str | None = Field(default=None, max_length=18)
    bandeira: str | None = Field(default=None, max_length=20)         # tBand ou id MP
    autorizacao: str | None = Field(default=None, max_length=40)      # cAut
    payment_id: str | None = Field(default=None, max_length=40)
    terminal: str | None = Field(default=None, max_length=60)


class ParcelaVenda(BaseModel):
    forma: str = Field(max_length=30)
    valor: float = Field(allow_inf_nan=False)
    pagamento: PagamentoEletronico | None = None
    pix_mp_id: str | None = Field(default=None, min_length=1, max_length=40)


class CheckoutRequest(BaseModel):
    itens: list[ItemVenda]
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    forma_pagamento: str = Field(default="dinheiro", max_length=30)
    observacao: str = Field(default="", max_length=200)
    cliente_id: int | None = None
    cpf_consumidor: str | None = Field(default=None, max_length=14)
    emitir_nota: bool = False
    pagamento: PagamentoEletronico | None = None
    pagamentos: list[ParcelaVenda] | None = Field(default=None, max_length=100)
    dinheiro_recebido: float | None = Field(default=None, allow_inf_nan=False)
    referencia_checkout: UUID | None = None


# ── Rotas ──

@router.post("/checkout", status_code=201)
async def rota_checkout(data: CheckoutRequest, request: Request):
    resultado = await checkout(data, request)
    if resultado.get("reusada"):
        return JSONResponse(status_code=200, content=resultado)
    return resultado


async def checkout(data: CheckoutRequest, request: Request, *, pix_mp: dict | None = None):
    """Finaliza uma venda: baixa estoque e registra no banco."""
    user_id = _get_user_id(request)
    licenca = conta_mod.status(online=False)
    if licenca.get("bloqueado"):
        raise HTTPException(status_code=403, detail=licenca.get("motivo") or "Licença suspensa.")
    formas_divisiveis = {"dinheiro", "pix", "debito", "credito", "fiado"}
    partes = data.pagamentos
    forma = data.forma_pagamento
    if partes is not None:
        if not partes or any(p.forma not in formas_divisiveis for p in partes):
            raise HTTPException(status_code=400, detail="Use dinheiro, PIX, débito, crédito ou fiado nas parcelas.")
        if data.pagamento:
            raise HTTPException(status_code=400, detail="Informe o pagamento eletrônico na própria parcela.")
        forma = partes[0].forma if len(partes) == 1 else "misto"
    elif forma not in formas_divisiveis | {"fiado", "outros"}:
        raise HTTPException(status_code=400, detail="Forma de pagamento inválida.")

    ids = ([p.pix_mp_id or (p.pagamento and p.pagamento.payment_id) for p in partes]
           if partes is not None else [data.pagamento and data.pagamento.payment_id])
    ids = [pid for pid in ids if pid]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=400, detail="A mesma cobrança não pode pagar duas parcelas.")
    referencia = str(data.referencia_checkout) if data.referencia_checkout else None
    try:
        venda = db.venda_checkout_existente(user_id, ids, referencia)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if venda:
        return {"venda": venda, "itens": venda["itens"], "reusada": True}

    if not data.itens:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um item à venda.")

    if forma == "fiado" or (partes and any(p.forma == "fiado" for p in partes)):
        if not data.cliente_id:
            raise HTTPException(status_code=400, detail="Selecione um cliente para venda fiada.")
        if not db.get_cliente(data.cliente_id, user_id):
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # Validar e calcular
    itens_processados = []
    subtotal_total = somar([])
    desconto = moeda(data.desconto)
    erros = []

    for item in data.itens:
        if item.quantidade <= 0:
            erros.append("Quantidade deve ser maior que zero.")
            continue
        produto = db.get_produto(item.produto_id, user_id)
        if not produto:
            erros.append(f"Produto ID {item.produto_id} não encontrado.")
            continue
        if not produto["ativo"]:
            erros.append(f"Produto '{produto['nome']}' está desativado.")
            continue
        modo = item.modo_venda or "unidade"
        dupla = bool(produto.get("vende_por_unidade"))
        if dupla and not item.quantidade.is_integer():
            erros.append("Embalagem e avulso exigem quantidade inteira.")
            continue
        fator = produto["quantidade_por_embalagem"] if dupla and modo == "embalagem" else 1
        quantidade_estoque = float(decimal(item.quantidade) * decimal(fator))
        if produto["estoque"] < quantidade_estoque:
            pedido = (f"{item.quantidade:g} {produto['unidade_compra']} ({quantidade_estoque:g} {produto['unidade']})"
                      if fator != 1 else f"{item.quantidade:g} {produto['unidade']}")
            erros.append(
                f"Estoque insuficiente de '{produto['nome']}': "
                f"tem {produto['estoque']:g} {produto['unidade']}, pedido {pedido}."
            )
            continue

        # D3 (Álvaro, 12/11/2026): produto sem preço de venda não é vendido
        # (antes caía para o preço de custo, sem aviso).
        preco = produto["preco_embalagem" if modo == "embalagem" else "preco_unidade"] if dupla else produto["preco_venda"]
        if not preco or preco <= 0:
            erros.append(f"Produto '{produto['nome']}' está sem preço de venda. "
                         "Cadastre o preço em Produtos antes de vender.")
            continue
        subtotal = multiplicar(item.quantidade, preco)
        subtotal_total += subtotal

        itens_processados.append({
            "produto_id": produto["id"],
            "nome_produto": f"{produto['nome']} — {produto['unidade_compra'] if modo == 'embalagem' else 'avulso'}" if dupla else produto["nome"],
            "quantidade": item.quantidade,
            "preco_unitario": preco,
            "subtotal": moeda(subtotal),
            "modo_venda": modo if dupla else None,
            "unidade_venda": (produto["unidade_compra"] if modo == "embalagem" else "UN") if dupla else produto["unidade"],
            "quantidade_estoque": quantidade_estoque,
            "custo_unitario_estoque": produto["preco_custo"],
        })

    if erros:
        raise HTTPException(status_code=400, detail={"erros": erros})

    if decimal(desconto) > subtotal_total:
        raise HTTPException(
            status_code=400,
            detail=f"Desconto (R$ {desconto:.2f}) maior que o subtotal da venda "
                   f"(R$ {subtotal_total:.2f}).",
        )

    total = moeda(subtotal_total - decimal(desconto))
    if total < 0:
        total = 0

    try:
        pagamentos, cobrancas = preparar_pagamentos(data, total, pix_mp)
        venda = db.checkout_atomico(
            user_id=user_id,
            cliente_id=data.cliente_id,
            total=total,
            desconto=desconto,
            forma_pagamento=forma,
            observacao=data.observacao,
            itens=itens_processados,
            agora=_agora(),
            pagamento_detalhe=pagamentos[0]["detalhe"] if len(pagamentos) == 1 else None,
            pagamentos=pagamentos,
            cobrancas=cobrancas,
            referencia=referencia,
        )
    except EstoqueConcorrente as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if venda.pop("reusada", False):
        return {"venda": venda, "itens": venda["itens"], "reusada": True}

    # Emissão de nota fiscal se solicitado
    nota = None
    if data.emitir_nota and venda:
        import fiscal
        try:
            # Passar o CPF se fornecido
            nota = fiscal.anexar_qrcode(fiscal.emitir_nfce(venda["id"], user_id, cpf=data.cpf_consumidor))
        except Exception as e:
            # Não falha a venda se a nota der erro, mas avisa
            return {"venda": venda, "itens": itens_processados, "erro_nota": str(e)}

    return {"venda": venda, "itens": itens_processados, "nota": nota}


def preparar_pagamentos(data: CheckoutRequest, total: float, pix_mp: dict | None) -> tuple[list[dict], list[dict]]:
    partes = data.pagamentos
    if partes is None:
        partes = [ParcelaVenda(forma=data.forma_pagamento, valor=total, pagamento=data.pagamento)]
    elif any(decimal(p.valor) <= 0 or moeda(p.valor) != p.valor for p in partes):
        raise ValueError("Cada parcela deve ser maior que zero e ter até duas casas decimais.")
    if abs(somar(p.valor for p in partes) - decimal(total)) > CENTAVO:
        raise ValueError("A soma dos pagamentos deve ser igual ao total da venda.")

    troco = decimal(0)
    if data.dinheiro_recebido is not None:
        dinheiro = somar(p.valor for p in partes if p.forma == "dinheiro")
        recebido = decimal(moeda(data.dinheiro_recebido))
        if not any(p.forma == "dinheiro" for p in partes) or recebido < dinheiro:
            raise ValueError("O dinheiro recebido deve cobrir a parte em dinheiro.")
        troco = recebido - dinheiro

    pagamentos = []
    cobrancas = []
    for parte in partes:
        detalhe = parte.pagamento.model_dump(exclude_none=True) if parte.pagamento else {}
        pix = pix_mp
        if parte.pix_mp_id:
            if parte.forma != "pix" or parte.pagamento:
                raise ValueError("Vincule o PIX do Mercado Pago somente a uma parcela PIX.")
            from pix import verificar_pagamento_mp
            pix, _ = verificar_pagamento_mp(parte.pix_mp_id)
        if pix:
            tolerancia = CENTAVO if data.pagamentos is None else decimal(0)
            if abs(decimal(pix["valor"]) - decimal(parte.valor)) > tolerancia:
                raise HTTPException(status_code=409, detail="O PIX aprovado tem valor diferente da parcela PIX.")
            detalhe = pix["detalhe"]
            cobrancas.append({**pix, "pix_mp": True})
        elif detalhe.get("payment_id"):
            if data.pagamentos is not None and parte.forma not in {"debito", "credito", "pix"}:
                raise ValueError("Vincule a cobrança da Point a uma parcela eletrônica.")
            cobrancas.append({"id": detalhe["payment_id"], "valor": parte.valor, "forma": parte.forma,
                              "obrigatoria": data.pagamentos is not None})
        if parte.forma == "dinheiro" and troco:
            detalhe["troco"] = moeda(troco)
            troco = decimal(0)
        pagamentos.append({"forma": parte.forma, "valor": parte.valor,
                           "detalhe": json.dumps(detalhe, ensure_ascii=False) if detalhe else None})
    return pagamentos, cobrancas


@router.get("")
async def listar(request: Request, limit: int = 50, offset: int = 0):
    user_id = _get_user_id(request)
    vendas = db.list_vendas(user_id, limit=limit, offset=offset)
    return {"vendas": vendas, "resumo_hoje": db.resumo_vendas_hoje(user_id)}


@router.get("/{venda_id}")
async def obter(venda_id: int, request: Request):
    user_id = _get_user_id(request)
    venda = db.get_venda_completa(venda_id, user_id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")
    return {"venda": venda}


class CancelarVendaRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


@router.post("/{venda_id}/cancelar")
async def cancelar_venda(venda_id: int, data: CancelarVendaRequest, request: Request):
    user_id = _get_user_id(request)
    try:
        venda = db.cancelar_venda(venda_id, user_id, data.motivo, _agora())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")
    return {"venda": venda}
