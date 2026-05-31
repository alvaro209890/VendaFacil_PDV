"""Produtos CRUD — VendaFácil PDV"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db
import importacao_xml

router = APIRouter()


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


# ── Models ──

class FiscalMixin(BaseModel):
    """Campos fiscais para NFC-e (todos opcionais; usados na emissão)."""
    ncm: str | None = Field(default=None, max_length=8)
    cest: str | None = Field(default=None, max_length=9)
    cfop: str | None = Field(default=None, max_length=4)
    origem: str | None = Field(default=None, max_length=1)
    unidade_tributavel: str | None = Field(default=None, max_length=6)
    cst_csosn: str | None = Field(default=None, max_length=4)
    aliquota_icms: float | None = Field(default=None, ge=0, le=100)
    cst_pis: str | None = Field(default=None, max_length=2)
    aliquota_pis: float | None = Field(default=None, ge=0, le=100)
    cst_cofins: str | None = Field(default=None, max_length=2)
    aliquota_cofins: float | None = Field(default=None, ge=0, le=100)


class ProdutoCreate(FiscalMixin):
    nome: str = Field(min_length=1, max_length=120)
    categoria_id: int | None = Field(default=None)
    preco_custo: float = Field(default=0, ge=0)
    preco_venda: float = Field(default=0, ge=0)
    estoque: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=5, ge=0)
    codigo_barras: str = Field(default="", max_length=60)
    unidade: str = Field(default="UN", max_length=10)


class ProdutoUpdate(FiscalMixin):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    categoria_id: int | None = Field(default=None)
    preco_custo: float | None = Field(default=None, ge=0)
    preco_venda: float | None = Field(default=None, ge=0)
    estoque: int | None = Field(default=None, ge=0)
    estoque_minimo: int | None = Field(default=None, ge=0)
    codigo_barras: str | None = Field(default=None, max_length=60)
    unidade: str | None = Field(default=None, max_length=10)
    ativo: int | None = Field(default=None, ge=0, le=1)


class ItemImportar(BaseModel):
    produto_id: int | None = None        # None = criar produto novo
    nome: str = Field(min_length=1, max_length=120)
    codigo_barras: str = Field(default="", max_length=60)
    unidade: str = Field(default="UN", max_length=10)
    quantidade: float = Field(gt=0)
    preco_custo: float = Field(default=0, ge=0)
    preco_venda: float = Field(default=0, ge=0)   # usado só ao criar novo
    atualizar_custo: bool = True
    ncm: str | None = Field(default=None, max_length=8)
    cfop: str | None = Field(default=None, max_length=4)


class ConfirmarImportacao(BaseModel):
    documento: str = Field(default="", max_length=60)   # nº/chave da NF-e
    itens: list[ItemImportar]


class EntradaInput(BaseModel):
    quantidade: float = Field(gt=0)
    custo_unitario: float | None = Field(default=None, ge=0)
    observacao: str = Field(default="", max_length=200)


# ── Rotas ──

@router.get("")
async def listar(request: Request, ativos: bool = True):
    user_id = _get_user_id(request)
    return {"produtos": db.list_produtos(user_id, ativos_only=ativos)}


@router.get("/{produto_id}")
async def obter(produto_id: int, request: Request):
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return {"produto": p}


@router.post("", status_code=201)
async def criar(data: ProdutoCreate, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    p = db.create_produto(
        user_id=user_id,
        nome=data.nome,
        categoria_id=data.categoria_id,
        preco_custo=data.preco_custo,
        preco_venda=data.preco_venda,
        estoque=data.estoque,
        estoque_minimo=data.estoque_minimo,
        codigo_barras=data.codigo_barras,
        unidade=data.unidade,
        agora=agora,
    )
    # Persiste os campos fiscais informados (create_produto só grava os básicos).
    fiscais = data.model_dump(include=set(FiscalMixin.model_fields))
    fiscais = {k: v for k, v in fiscais.items() if v is not None}
    if fiscais and p:
        p = db.update_produto(p["id"], user_id, atualizado_em=agora, **fiscais)
    return {"produto": p}


@router.put("/{produto_id}")
async def atualizar(produto_id: int, data: ProdutoUpdate, request: Request):
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["atualizado_em"] = _agora()
    p = db.update_produto(produto_id, user_id, **updates)
    return {"produto": p}


# ── Importação de XML (NF-e de entrada) ──

@router.post("/importar-xml/preview")
async def importar_xml_preview(request: Request):
    """Lê o XML da NF-e e devolve os itens já casados com o estoque atual."""
    user_id = _get_user_id(request)
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Envie o conteúdo do arquivo XML.")
    try:
        nfe = importacao_xml.parse_nfe(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    itens = []
    for it in nfe["itens"]:
        match = db.get_produto_by_codigo(user_id, it["codigo_barras"]) if it["codigo_barras"] else None
        itens.append({
            **it,
            "produto_id": match["id"] if match else None,
            "produto_nome": match["nome"] if match else None,
            "estoque_atual": match["estoque"] if match else 0,
            "preco_custo_atual": match["preco_custo"] if match else None,
            "preco_venda_atual": match["preco_venda"] if match else None,
            "acao": "atualizar" if match else "criar",
        })
    return {"emitente": nfe["emitente"], "numero": nfe["numero"],
            "chave": nfe["chave"], "itens": itens}


@router.post("/importar-xml/confirmar")
async def importar_xml_confirmar(data: ConfirmarImportacao, request: Request):
    """Aplica a importação: dá entrada no estoque (existentes) e cria os novos."""
    user_id = _get_user_id(request)
    agora = _agora()
    doc = data.documento or ""
    criados = atualizados = 0
    for it in data.itens:
        if it.produto_id:
            if not db.get_produto(it.produto_id, user_id):
                continue
            novo_custo = it.preco_custo if (it.atualizar_custo and it.preco_custo > 0) else None
            db.entrada_estoque(it.produto_id, user_id, it.quantidade, agora, novo_custo)
            db.registrar_movimentacao(
                user_id, it.produto_id, "entrada", it.quantidade, agora,
                custo_unitario=it.preco_custo, origem="xml", documento=doc,
                observacao=it.nome,
            )
            atualizados += 1
        else:
            novo = db.create_produto(
                user_id=user_id, nome=it.nome, categoria_id=None,
                preco_custo=it.preco_custo, preco_venda=it.preco_venda,
                estoque=it.quantidade, estoque_minimo=5,
                codigo_barras=it.codigo_barras, unidade=it.unidade, agora=agora,
            )
            if novo:
                fiscais = {k: v for k, v in {"ncm": it.ncm, "cfop": it.cfop}.items() if v}
                if fiscais:
                    db.update_produto(novo["id"], user_id, atualizado_em=agora, **fiscais)
                db.registrar_movimentacao(
                    user_id, novo["id"], "entrada", it.quantidade, agora,
                    custo_unitario=it.preco_custo, origem="xml", documento=doc,
                    observacao=it.nome,
                )
                criados += 1
    return {"criados": criados, "atualizados": atualizados,
            "total": criados + atualizados}


# ── Entrada manual de estoque + histórico ──

@router.post("/{produto_id}/entrada")
async def entrada_manual(produto_id: int, data: EntradaInput, request: Request):
    user_id = _get_user_id(request)
    if not db.get_produto(produto_id, user_id):
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    agora = _agora()
    db.entrada_estoque(produto_id, user_id, data.quantidade, agora,
                       novo_custo=data.custo_unitario or None)
    db.registrar_movimentacao(
        user_id, produto_id, "entrada", data.quantidade, agora,
        custo_unitario=data.custo_unitario, origem="manual", observacao=data.observacao,
    )
    return {"produto": db.get_produto(produto_id, user_id)}


@router.get("/{produto_id}/movimentacoes")
async def movimentacoes(produto_id: int, request: Request):
    user_id = _get_user_id(request)
    return {"movimentacoes": db.list_movimentacoes(user_id, produto_id)}


@router.delete("/{produto_id}")
async def desativar(produto_id: int, request: Request):
    """Desativa um produto (soft delete)."""
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    db.update_produto(produto_id, user_id, ativo=0, atualizado_em=_agora())
    return {"ok": True}
