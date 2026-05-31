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


def test_ajuste_perda_baixa_estoque(client, auth):
    p = _criar_produto(client, auth, nome="Perda", estoque=10)
    r = client.post(f"/api/produtos/{p['id']}/ajuste", json={
        "tipo": "perda", "quantidade": 3, "observacao": "Vencido",
    }, headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["produto"]["estoque"] == 7
    movs = client.get(f"/api/produtos/{p['id']}/movimentacoes", headers=auth).json()["movimentacoes"]
    assert movs[0]["tipo"] == "saida" and movs[0]["origem"] == "perda"


def test_ajuste_perda_acima_do_estoque_falha(client, auth):
    p = _criar_produto(client, auth, nome="PerdaDemais", estoque=2)
    r = client.post(f"/api/produtos/{p['id']}/ajuste", json={
        "tipo": "quebra", "quantidade": 5,
    }, headers=auth)
    assert r.status_code == 400


def test_ajuste_inventario_acerta_para_cima_e_para_baixo(client, auth):
    p = _criar_produto(client, auth, nome="Inventario", estoque=10)
    # contagem real maior → vira entrada da diferença
    r = client.post(f"/api/produtos/{p['id']}/ajuste", json={
        "tipo": "inventario", "quantidade": 13,
    }, headers=auth)
    assert r.status_code == 200 and r.json()["produto"]["estoque"] == 13
    movs = client.get(f"/api/produtos/{p['id']}/movimentacoes", headers=auth).json()["movimentacoes"]
    assert movs[0]["tipo"] == "entrada" and movs[0]["quantidade"] == 3
    # contagem real menor → vira saída da diferença
    r2 = client.post(f"/api/produtos/{p['id']}/ajuste", json={
        "tipo": "inventario", "quantidade": 8,
    }, headers=auth)
    assert r2.status_code == 200 and r2.json()["produto"]["estoque"] == 8
    movs2 = client.get(f"/api/produtos/{p['id']}/movimentacoes", headers=auth).json()["movimentacoes"]
    assert movs2[0]["tipo"] == "saida" and movs2[0]["quantidade"] == 5


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


def test_pix_config_e_qrcode(client, auth):
    # sem chave → não dá pra gerar
    client.put("/api/pix/config", headers=auth, json={"pix_chave": "", "pix_nome": "", "pix_cidade": ""})
    assert client.get("/api/pix/chave", headers=auth).json()["configurada"] is False
    assert client.post("/api/pix/qrcode", headers=auth, json={"valor": 10}).status_code == 503
    # configura e gera o QR
    client.put("/api/pix/config", headers=auth, json={
        "pix_chave": "teste@pix.com", "pix_nome": "Minha Loja", "pix_cidade": "Cidade",
    })
    assert client.get("/api/pix/chave", headers=auth).json()["configurada"] is True
    r = client.post("/api/pix/qrcode", headers=auth, json={"valor": 12.5})
    assert r.status_code == 200 and r.json()["payload"] and r.json()["qr_base64"]
