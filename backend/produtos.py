"""Produtos CRUD — VendaFácil PDV"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db, NotaEntradaDuplicada
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


def _norm_unidade(valor: str | None, padrao: str = "UN") -> str:
    return (valor or padrao).strip().upper() or padrao


def _fator(valor: float | None) -> float:
    try:
        v = float(valor or 1)
    except (TypeError, ValueError):
        v = 1
    return v if v > 0 else 1


def _ean(valor: str | None) -> str:
    limpo = (valor or "").strip()
    if limpo.upper().replace(" ", "") in ("SEMGTIN", ""):
        return ""
    return limpo


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
    model_config = {"allow_inf_nan": False}
    vende_por_unidade: bool = False
    preco_embalagem: float = Field(default=0, ge=0)
    preco_unidade: float = Field(default=0, ge=0)
    codigo_barras_unidade: str = Field(default="", max_length=60)
    nome: str = Field(min_length=1, max_length=120)
    categoria_id: int | None = Field(default=None)
    preco_custo: float = Field(default=0, ge=0)
    preco_venda: float = Field(default=0, ge=0)
    estoque: float = Field(default=0, ge=0)
    estoque_minimo: float = Field(default=5, ge=0)
    codigo_barras: str = Field(default="", max_length=60)
    unidade: str = Field(default="UN", max_length=10)
    unidade_compra: str = Field(default="", max_length=10)
    quantidade_por_embalagem: float = Field(default=1, gt=0)


class ProdutoUpdate(FiscalMixin):
    model_config = {"allow_inf_nan": False}
    vende_por_unidade: bool | None = None
    preco_embalagem: float | None = Field(default=None, ge=0)
    preco_unidade: float | None = Field(default=None, ge=0)
    codigo_barras_unidade: str | None = Field(default=None, max_length=60)
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    categoria_id: int | None = Field(default=None)
    preco_custo: float | None = Field(default=None, ge=0)
    preco_venda: float | None = Field(default=None, ge=0)
    estoque: float | None = Field(default=None, ge=0)
    estoque_minimo: float | None = Field(default=None, ge=0)
    codigo_barras: str | None = Field(default=None, max_length=60)
    unidade: str | None = Field(default=None, max_length=10)
    unidade_compra: str | None = Field(default=None, max_length=10)
    quantidade_por_embalagem: float | None = Field(default=None, gt=0)
    ativo: int | None = Field(default=None, ge=0, le=1)


class ItemImportar(BaseModel):
    model_config = {"allow_inf_nan": False}

    produto_id: int | None = None        # None = criar produto novo
    nome: str = Field(min_length=1, max_length=120)
    codigo_barras: str = Field(default="", max_length=60)
    unidade: str = Field(default="UN", max_length=10)
    unidade_compra: str = Field(default="", max_length=10)
    quantidade_por_embalagem: float = Field(default=1, gt=0)
    quantidade: float = Field(gt=0)
    quantidade_xml: float | None = Field(default=None, gt=0)
    preco_custo: float = Field(default=0, ge=0)
    preco_venda: float = Field(default=0, ge=0)   # usado só ao criar novo
    atualizar_custo: bool = True
    ncm: str | None = Field(default=None, max_length=8)
    cfop: str | None = Field(default=None, max_length=4)


class ConfirmarImportacao(BaseModel):
    documento: str = Field(default="", max_length=60)   # nº/chave da NF-e
    chave: str = Field(default="", max_length=44)
    itens: list[ItemImportar] = Field(min_length=1)


class EntradaInput(BaseModel):
    quantidade: float = Field(gt=0)
    custo_unitario: float | None = Field(default=None, ge=0)
    observacao: str = Field(default="", max_length=200)


class AjusteInput(BaseModel):
    """Ajuste manual de estoque: baixa por perda/quebra ou acerto por inventário."""
    tipo: str = Field(pattern="^(perda|quebra|inventario)$")
    # perda/quebra: quantidade a baixar (>0). inventario: contagem real (>=0).
    quantidade: float = Field(ge=0)
    observacao: str = Field(default="", max_length=200)


# ── Rotas ──

def validar_embalagem(p: dict):
    if not p.get("vende_por_unidade"):
        return
    fator = p.get("quantidade_por_embalagem", 1)
    if (_norm_unidade(p.get("unidade")) != "UN" or not (p.get("unidade_compra") or "").strip()
            or _norm_unidade(p.get("unidade_compra")) in {"UN", "KG", "G", "LT", "ML"}
            or fator <= 0 or not float(fator).is_integer()
            or p.get("preco_embalagem", 0) <= 0 or p.get("preco_unidade", 0) <= 0):
        raise HTTPException(status_code=400, detail="Informe embalagem, quantidade inteira e os dois preços maiores que zero; estoque em UN.")
    if p.get("codigo_barras_unidade") and p.get("codigo_barras_unidade") == p.get("codigo_barras"):
        raise HTTPException(status_code=400, detail="Os códigos da embalagem e da unidade devem ser diferentes.")

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
    validar_embalagem(data.model_dump())
    codigo = _ean(data.codigo_barras)
    if codigo and db.get_produto_by_codigo(user_id, codigo):
        raise HTTPException(status_code=409, detail="Já existe produto com este código de barras.")
    p = db.create_produto(
        user_id=user_id,
        nome=data.nome,
        categoria_id=data.categoria_id,
        preco_custo=data.preco_custo,
        preco_venda=data.preco_venda,
        estoque=data.estoque,
        estoque_minimo=data.estoque_minimo,
        codigo_barras=codigo,
        unidade=_norm_unidade(data.unidade),
        unidade_compra=_norm_unidade(data.unidade_compra, data.unidade),
        quantidade_por_embalagem=_fator(data.quantidade_por_embalagem),
        vende_por_unidade=data.vende_por_unidade, preco_embalagem=data.preco_embalagem,
        preco_unidade=data.preco_unidade, codigo_barras_unidade=_ean(data.codigo_barras_unidade),
        agora=agora,
        fiscais={k: v for k, v in data.model_dump(include=set(FiscalMixin.model_fields)).items() if v is not None},
    )
    return {"produto": p}


@router.put("/{produto_id}")
async def atualizar(produto_id: int, data: ProdutoUpdate, request: Request):
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates.get("vende_por_unidade") and not p.get("vende_por_unidade"):
        if not all(k in updates for k in ("preco_embalagem", "preco_unidade")):
            raise HTTPException(status_code=400, detail="Ao ativar, informe os dois preços de venda.")
    validar_embalagem({**p, **updates})
    if "unidade" in updates:
        updates["unidade"] = _norm_unidade(updates["unidade"])
    if "unidade_compra" in updates:
        updates["unidade_compra"] = _norm_unidade(updates["unidade_compra"], updates.get("unidade", p.get("unidade") or "UN"))
    if "quantidade_por_embalagem" in updates:
        updates["quantidade_por_embalagem"] = _fator(updates["quantidade_por_embalagem"])
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
        unidade_xml = _norm_unidade(it["unidade"])
        unidade_estoque = _norm_unidade(match.get("unidade") if match else unidade_xml)
        unidade_compra = _norm_unidade(match.get("unidade_compra") if match else unidade_xml, unidade_xml)
        fator_cadastro = _fator(match.get("quantidade_por_embalagem") if match else 1)
        if not match or unidade_xml == unidade_estoque:
            fator = 1
        elif unidade_xml == unidade_compra and unidade_compra != unidade_estoque:
            fator = fator_cadastro
        elif fator_cadastro > 1 and unidade_compra == unidade_estoque:
            fator = fator_cadastro
        else:
            fator = 1
        quantidade_xml = it["quantidade"]
        quantidade_estoque = round(quantidade_xml * fator, 4)
        custo_unitario = round((it["valor_unitario"] / fator) if fator else it["valor_unitario"], 4)
        itens.append({
            **it,
            "unidade_xml": unidade_xml,
            "unidade": unidade_estoque,
            "unidade_compra": unidade_compra,
            "quantidade_xml": quantidade_xml,
            "quantidade": quantidade_estoque,
            "valor_unitario_xml": it["valor_unitario"],
            "valor_unitario": custo_unitario,
            "quantidade_por_embalagem": fator_cadastro if match else 1,
            "produto_id": match["id"] if match else None,
            "produto_nome": match["nome"] if match else None,
            "estoque_atual": match["estoque"] if match else 0,
            "preco_custo_atual": match["preco_custo"] if match else None,
            "preco_venda_atual": match["preco_venda"] if match else None,
            "acao": "atualizar" if match else "criar",
        })
    return {"emitente": nfe["emitente"], "numero": nfe["numero"],
            "chave": nfe["chave"], "ja_importada": bool(nfe["chave"]) and db.nota_entrada_importada(user_id, nfe["chave"]),
            "itens": itens}


@router.post("/importar-xml/confirmar")
async def importar_xml_confirmar(data: ConfirmarImportacao, request: Request):
    """Aplica a importação: dá entrada no estoque (existentes) e cria os novos."""
    user_id = _get_user_id(request)
    agora = _agora()
    doc = data.documento or ""
    chave = (data.chave or "").strip()
    if chave and (len(chave) != 44 or not chave.isdigit()):
        raise HTTPException(status_code=400, detail="Chave da NF-e inválida.")
    itens = []
    for item in data.itens:
        normalizado = item.model_dump()
        normalizado["codigo_barras"] = _ean(item.codigo_barras)
        normalizado["unidade"] = _norm_unidade(item.unidade)
        normalizado["unidade_compra"] = _norm_unidade(item.unidade_compra, item.unidade)
        normalizado["quantidade_por_embalagem"] = _fator(item.quantidade_por_embalagem)
        itens.append(normalizado)
    try:
        return db.importar_entrada_atomica(user_id, chave, doc, itens, agora)
    except NotaEntradaDuplicada as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post("/{produto_id}/ajuste")
async def ajuste_estoque(produto_id: int, data: AjusteInput, request: Request):
    """Ajusta o estoque manualmente.

    - perda/quebra: baixa `quantidade` do estoque (não pode passar do disponível).
    - inventario: define o estoque para a contagem real informada em `quantidade`,
      registrando a diferença como entrada (sobra) ou saída (falta).
    """
    user_id = _get_user_id(request)
    produto = db.get_produto(produto_id, user_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    agora = _agora()
    estoque_atual = float(produto["estoque"])

    if data.tipo == "inventario":
        diferenca = round(data.quantidade - estoque_atual, 4)
        db.definir_estoque(produto_id, user_id, data.quantidade, agora)
        if diferenca != 0:
            db.registrar_movimentacao(
                user_id, produto_id,
                "entrada" if diferenca > 0 else "saida", abs(diferenca), agora,
                origem="inventario",
                observacao=data.observacao or f"Inventário: contagem {data.quantidade} (antes {estoque_atual})",
            )
    else:  # perda | quebra
        if data.quantidade <= 0:
            raise HTTPException(status_code=400, detail="Informe a quantidade a baixar.")
        if data.quantidade > estoque_atual:
            raise HTTPException(
                status_code=400,
                detail=f"Não há estoque suficiente: tem {estoque_atual} {produto['unidade']}.",
            )
        db.definir_estoque(produto_id, user_id, estoque_atual - data.quantidade, agora)
        db.registrar_movimentacao(
            user_id, produto_id, "saida", data.quantidade, agora,
            origem=data.tipo, observacao=data.observacao or data.tipo.capitalize(),
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
