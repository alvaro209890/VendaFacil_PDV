"""Fluxos fiscais e de venda: contingência, prazo de cancelamento (MT),
integridade do estoque no checkout e export de XML."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
import fiscal


def _user_id():
    return db.get_user_by_usuario("teste")["id"]


def _criar_venda(client, auth, qtd=1):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Fluxo Fiscal", "preco_venda": 10, "estoque": 100,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    r = client.post("/api/vendas/checkout", headers=auth, json={
        "itens": [{"produto_id": produto["id"], "quantidade": qtd}],
        "forma_pagamento": "dinheiro",
    })
    assert r.status_code == 201, r.text
    return produto, r.json()["venda"]


def _nota_base(venda_id, status, modelo="65", criado_em=None, **extra):
    agora = criado_em or datetime.now(timezone.utc).isoformat()
    return db.criar_nota({
        "venda_id": venda_id, "user_id": _user_id(),
        "ref": f"fx-{modelo}-{venda_id}-{status}", "modelo": modelo,
        "numero": 1, "serie": 1, "ambiente": "homologacao", "status": status,
        "criado_em": agora, "atualizado_em": agora, **extra,
    })


def test_emitir_nfce_nao_duplica_nota_em_contingencia(client, auth):
    _, venda = _criar_venda(client, auth)
    nota = _nota_base(venda["id"], "contingencia",
                      chave="51260712345678000195650010000000019000000010")
    # Reemitir a mesma venda NÃO pode abrir novo número: a nota offline ainda
    # será transmitida pelo loop automático.
    assert fiscal.emitir_nfce(venda["id"], _user_id())["id"] == nota["id"]


def test_anexar_qrcode_tambem_na_contingencia():
    nota = {"status": "contingencia", "qrcode_url": "http://exemplo/?p=x|2|2|1|A"}
    out = fiscal.anexar_qrcode(dict(nota))
    assert out.get("qrcode_base64")           # DANFE offline imprime o QR
    ok = {"status": "autorizada", "qrcode_url": nota["qrcode_url"]}
    assert fiscal.anexar_qrcode(dict(ok)).get("qrcode_base64")
    rejeitada = {"status": "rejeitada", "qrcode_url": nota["qrcode_url"]}
    assert not fiscal.anexar_qrcode(dict(rejeitada)).get("qrcode_base64")


def test_cancelamento_fora_do_prazo_mt_e_bloqueado_com_orientacao(client, auth):
    _, venda = _criar_venda(client, auth)
    antiga = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    nota = _nota_base(venda["id"], "autorizada", criado_em=antiga,
                      chave="51260712345678000195650010000000029000000011",
                      protocolo="151000000000001")
    with pytest.raises(fiscal.FiscalError, match="30 minutos"):
        fiscal.cancelar_nfce(nota["id"], "Cancelamento de teste fora do prazo")


def test_cancelamento_recente_passa_da_checagem_de_prazo(client, auth):
    _, venda = _criar_venda(client, auth)
    nota = _nota_base(venda["id"], "autorizada",
                      chave="51260712345678000195650010000000039000000012",
                      protocolo="151000000000002")
    db.salvar_config_fiscal({"habilitado": 1, "provedor_fiscal": "sefaz_mt_direto",
                             "certificado_a1_b64": "", "certificado_senha": ""}, "t")
    # Dentro dos 30 min a checagem de prazo não barra; o erro seguinte é o
    # certificado A1 ausente/inválido (a transmissão nem começa).
    with pytest.raises(fiscal.FiscalError, match="[Cc]ertificado"):
        fiscal.cancelar_nfce(nota["id"], "Cancelamento de teste dentro do prazo")


def test_checkout_recusa_desconto_maior_que_subtotal(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Desconto Louco", "preco_venda": 10, "estoque": 10,
    }).json()["produto"]
    r = client.post("/api/vendas/checkout", headers=auth, json={
        "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        "desconto": 99, "forma_pagamento": "dinheiro",
    })
    assert r.status_code == 400
    assert "Desconto" in r.text


def test_checkout_devolve_estoque_se_baixa_falhar_no_meio(client, auth, monkeypatch):
    p1 = client.post("/api/produtos", headers=auth, json={
        "nome": "Estorno A", "preco_venda": 5, "estoque": 10}).json()["produto"]
    p2 = client.post("/api/produtos", headers=auth, json={
        "nome": "Estorno B", "preco_venda": 5, "estoque": 10}).json()["produto"]

    original = db.baixar_estoque

    def falha_no_segundo(produto_id, quantidade):
        if produto_id == p2["id"]:
            return False          # simula corrida: outro caixa levou o estoque
        return original(produto_id, quantidade)

    monkeypatch.setattr(db, "baixar_estoque", falha_no_segundo)
    r = client.post("/api/vendas/checkout", headers=auth, json={
        "itens": [{"produto_id": p1["id"], "quantidade": 3},
                  {"produto_id": p2["id"], "quantidade": 3}],
        "forma_pagamento": "dinheiro",
    })
    assert r.status_code == 409
    # o que já tinha sido baixado do produto A voltou
    assert db.get_produto(p1["id"])["estoque"] == 10


def test_export_xml_somente_com_fim(client, auth):
    _, venda = _criar_venda(client, auth)
    _nota_base(venda["id"], "autorizada",
               chave="51260712345678000195650010000000049000000013",
               criado_em="2029-05-10T10:00:00",
               xml_autorizado="<nfeProc>SO-FIM</nfeProc>")
    r = client.get("/api/fiscal/nfce/export/xml?fim=2029-12-31", headers=auth)
    assert r.status_code == 200
    r2 = client.get("/api/fiscal/nfce/export/xml?fim=2029-01-31", headers=auth)
    assert r2.status_code == 404
