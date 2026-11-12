"""Vendas / Checkout — VendaFácil PDV"""

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth import _agora
from database import db, EstoqueConcorrente
from dinheiro import decimal, moeda, multiplicar, somar
from produtos import _get_user_id
import conta as conta_mod

router = APIRouter()

# ── Models ──

class ItemVenda(BaseModel):
    produto_id: int
    quantidade: float = Field(allow_inf_nan=False)


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


class CheckoutRequest(BaseModel):
    itens: list[ItemVenda]
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    forma_pagamento: str = Field(default="dinheiro", max_length=30)
    observacao: str = Field(default="", max_length=200)
    cliente_id: int | None = None
    cpf_consumidor: str | None = Field(default=None, max_length=14)
    emitir_nota: bool = False
    pagamento: PagamentoEletronico | None = None


# ── Rotas ──

@router.post("/checkout", status_code=201)
async def checkout(data: CheckoutRequest, request: Request):
    """Finaliza uma venda: baixa estoque e registra no banco."""
    user_id = _get_user_id(request)
    licenca = conta_mod.status(online=False)
    if licenca.get("bloqueado"):
        raise HTTPException(status_code=403, detail=licenca.get("motivo") or "Licença suspensa.")
    payment_id = data.pagamento.payment_id if data.pagamento and data.pagamento.payment_id else None
    if payment_id:
        venda_id = db.venda_da_cobranca(user_id, payment_id)
        if venda_id:
            venda = db.get_venda_completa(venda_id, user_id)
            return JSONResponse(status_code=200, content={
                "venda": venda, "itens": venda.get("itens") if venda else [], "reusada": True,
            })

    if not data.itens:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um item à venda.")

    if data.forma_pagamento == "fiado":
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
        if produto["estoque"] < item.quantidade:
            erros.append(
                f"Estoque insuficiente de '{produto['nome']}': "
                f"tem {produto['estoque']} {produto['unidade']}, pedido {item.quantidade}."
            )
            continue

        # D3 (Álvaro, 12/11/2026): produto sem preço de venda não é vendido
        # (antes caía para o preço de custo, sem aviso).
        if not produto["preco_venda"] or produto["preco_venda"] <= 0:
            erros.append(f"Produto '{produto['nome']}' está sem preço de venda. "
                         "Cadastre o preço em Produtos antes de vender.")
            continue
        preco = produto["preco_venda"]
        subtotal = multiplicar(item.quantidade, preco)
        subtotal_total += subtotal

        itens_processados.append({
            "produto_id": produto["id"],
            "nome_produto": produto["nome"],
            "quantidade": item.quantidade,
            "preco_unitario": preco,
            "subtotal": moeda(subtotal),
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

    agora = _agora()


    pagamento_detalhe = None
    if data.pagamento is not None:
        pagamento_detalhe = json.dumps(
            data.pagamento.model_dump(exclude_none=True), ensure_ascii=False
        )

    try:
        venda = db.checkout_atomico(
            user_id=user_id,
            cliente_id=data.cliente_id,
            total=total,
            desconto=desconto,
            forma_pagamento=data.forma_pagamento,
            observacao=data.observacao,
            itens=itens_processados,
            agora=agora,
            pagamento_detalhe=pagamento_detalhe,
        )
    except EstoqueConcorrente as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payment_id and venda:
        db.vincular_cobranca_venda(user_id, payment_id, venda["id"])


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
