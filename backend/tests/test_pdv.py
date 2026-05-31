"""Testes de ponta a ponta do PDV (venda, estoque, XML, caixa, relatório)."""

XML_NFE = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><NFe>
<infNFe Id="NFe35200114200166000187650010000000071123456789" versao="4.00">
<ide><nNF>71</nNF></ide>
<emit><xNome>Distribuidora Teste</xNome></emit>
<det nItem="1"><prod><cEAN>7891000555555</cEAN><xProd>BISCOITO</xProd>
<uCom>UN</uCom><qCom>12.0000</qCom><vUnCom>2.5000</vUnCom></prod></det>
</infNFe></NFe></nfeProc>"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def _criar_produto(client, auth, **kw):
    base = {"nome": "Produto", "preco_venda": 10.0, "preco_custo": 6.0, "estoque": 10}
    base.update(kw)
    r = client.post("/api/produtos", json=base, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()["produto"]


def test_checkout_baixa_estoque(client, auth):
    p = _criar_produto(client, auth, nome="Refri", estoque=10)
    r = client.post("/api/vendas/checkout", json={
        "itens": [{"produto_id": p["id"], "quantidade": 3}], "forma_pagamento": "dinheiro",
    }, headers=auth)
    assert r.status_code == 201, r.text
    atual = client.get(f"/api/produtos/{p['id']}", headers=auth).json()["produto"]
    assert atual["estoque"] == 7


def test_checkout_estoque_insuficiente(client, auth):
    p = _criar_produto(client, auth, nome="Pouco", estoque=2)
    r = client.post("/api/vendas/checkout", json={
        "itens": [{"produto_id": p["id"], "quantidade": 5}], "forma_pagamento": "dinheiro",
    }, headers=auth)
    assert r.status_code == 400


def test_entrada_manual_estoque(client, auth):
    p = _criar_produto(client, auth, nome="Entrada", estoque=0)
    r = client.post(f"/api/produtos/{p['id']}/entrada", json={"quantidade": 8}, headers=auth)
    assert r.status_code == 200
    assert r.json()["produto"]["estoque"] == 8


def test_importar_xml(client, auth):
    prev = client.post("/api/produtos/importar-xml/preview", content=XML_NFE, headers=auth)
    assert prev.status_code == 200, prev.text
    item = prev.json()["itens"][0]
    assert item["nome"] == "BISCOITO" and item["acao"] == "criar"
    conf = client.post("/api/produtos/importar-xml/confirmar", json={
        "documento": "71",
        "itens": [{
            "produto_id": None, "nome": "BISCOITO", "codigo_barras": "7891000555555",
            "unidade": "UN", "quantidade": 12, "preco_custo": 2.5, "preco_venda": 4.0,
            "atualizar_custo": True,
        }],
    }, headers=auth)
    assert conf.status_code == 200 and conf.json()["criados"] == 1
    # reimportar com o mesmo EAN deve casar (repor), não criar de novo
    prev2 = client.post("/api/produtos/importar-xml/preview", content=XML_NFE, headers=auth)
    assert prev2.json()["itens"][0]["acao"] == "atualizar"


def test_caixa_fluxo(client, auth):
    assert client.get("/api/caixa/atual", headers=auth).json()["aberto"] in (True, False)
    # fecha um eventual caixa aberto de teste anterior
    if client.get("/api/caixa/atual", headers=auth).json()["aberto"]:
        client.post("/api/caixa/fechar", json={"valor_fechamento": 0}, headers=auth)
    ab = client.post("/api/caixa/abrir", json={"valor_abertura": 100}, headers=auth)
    assert ab.status_code == 200 and ab.json()["resumo"]["dinheiro_esperado"] == 100
    p = _criar_produto(client, auth, nome="CaixaItem", preco_venda=10, estoque=5)
    client.post("/api/vendas/checkout", json={"itens": [{"produto_id": p["id"], "quantidade": 2}], "forma_pagamento": "dinheiro"}, headers=auth)
    client.post("/api/caixa/movimento", json={"tipo": "sangria", "valor": 30}, headers=auth)
    atual = client.get("/api/caixa/atual", headers=auth).json()["resumo"]
    assert atual["dinheiro_esperado"] == 90  # 100 + 20 - 30
    fech = client.post("/api/caixa/fechar", json={"valor_fechamento": 88}, headers=auth)
    assert fech.json()["sessao"]["diferenca"] == -2.0


def test_relatorio_vendas(client, auth):
    r = client.get("/api/relatorios/vendas", headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["faturamento"] > 0 and d["qtd_vendas"] > 0


def test_backup_exportar(client, auth):
    r = client.get("/api/backup/exportar", headers=auth)
    assert r.status_code == 200
    assert r.content[:15] == b"SQLite format 3"
