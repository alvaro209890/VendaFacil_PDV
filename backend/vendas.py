"""Vendas / Checkout — VendaFácil PDV"""

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db
from produtos import _get_user_id

router = APIRouter()

# ── Models ──

class ItemVenda(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)


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
    desconto: float = Field(default=0, ge=0)
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

    if not data.itens:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um item à venda.")

    if data.forma_pagamento == "fiado":
        if not data.cliente_id:
            raise HTTPException(status_code=400, detail="Selecione um cliente para venda fiada.")
        if not db.get_cliente(data.cliente_id, user_id):
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # Validar e calcular
    itens_processados = []
    subtotal_total = 0.0
    erros = []

    for item in data.itens:
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

        preco = produto["preco_venda"] if produto["preco_venda"] > 0 else produto["preco_custo"]
        subtotal = round(item.quantidade * preco, 2)
        subtotal_total += subtotal

        itens_processados.append({
            "produto_id": produto["id"],
            "nome_produto": produto["nome"],
            "quantidade": item.quantidade,
            "preco_unitario": preco,
            "subtotal": subtotal,
        })

    if erros:
        raise HTTPException(status_code=400, detail={"erros": erros})

    total = round(subtotal_total - data.desconto, 2)
    if total < 0:
        total = 0

    agora = _agora()

    # Baixar estoque e criar venda em transação implícita do DB singleton
    for item in itens_processados:
        ok = db.baixar_estoque(item["produto_id"], item["quantidade"])
        if not ok:
            raise HTTPException(
                status_code=409,
                detail=f"Erro ao baixar estoque de '{item['nome_produto']}'.",
            )

    pagamento_detalhe = None
    if data.pagamento is not None:
        pagamento_detalhe = json.dumps(
            data.pagamento.model_dump(exclude_none=True), ensure_ascii=False
        )

    venda = db.create_venda(
        user_id=user_id,
        cliente_id=data.cliente_id,
        total=total,
        desconto=data.desconto,
        forma_pagamento=data.forma_pagamento,
        observacao=data.observacao,
        itens=itens_processados,
        agora=agora,
        pagamento_detalhe=pagamento_detalhe,
    )

    # Registra a saída de estoque de cada item (histórico de movimentações).
    if venda:
        for item in itens_processados:
            db.registrar_movimentacao(
                user_id, item["produto_id"], "saida", item["quantidade"], agora,
                custo_unitario=None, origem="venda", documento=str(venda["id"]),
                observacao=item["nome_produto"],
            )

    # Se for venda fiada, cria conta a receber automaticamente
    if data.forma_pagamento == "fiado" and venda:
        db.create_conta_receber(
            user_id=user_id,
            cliente_id=data.cliente_id,
            venda_id=venda["id"],
            valor_total=total,
            data_vencimento=None,
            observacao=f"Venda #{venda['id']} — {len(itens_processados)} item(ns)",
            agora=agora,
        )

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
    return {"vendas": vendas}


@router.get("/{venda_id}")
async def obter(venda_id: int, request: Request):
    user_id = _get_user_id(request)
    venda = db.get_venda_completa(venda_id, user_id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")
    return {"venda": venda}
