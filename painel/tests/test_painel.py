"""Testes do Painel SaaS (admin, contas, financeiro, segurança)."""


def test_setup_e_login(client, admin):
    assert client.get("/api/admin/precisa-setup").json()["precisa_setup"] is False
    assert client.get("/api/admin/contas", headers=admin).status_code == 200


def test_login_errado(client, admin):
    r = client.post("/api/admin/login", json={"email": "admin@teste.com", "senha": "errada"})
    assert r.status_code == 401


def test_conta_crud(client, admin):
    cr = client.post("/api/admin/contas", headers=admin, json={
        "nome_loja": "Loja Teste", "login": "lojateste", "senha": "1234", "plano": "mensal",
    })
    assert cr.status_code == 200, cr.text
    cid = cr.json()["conta"]["id"]
    # login duplicado -> 409
    dup = client.post("/api/admin/contas", headers=admin, json={
        "nome_loja": "X", "login": "lojateste", "senha": "1234",
    })
    assert dup.status_code == 409
    # consta na lista
    contas = client.get("/api/admin/contas", headers=admin).json()["contas"]
    assert any(c["id"] == cid for c in contas)
    # exclui
    assert client.delete(f"/api/admin/contas/{cid}", headers=admin).status_code == 200


def test_validar_conta_pdv(client, admin):
    client.post("/api/admin/contas", headers=admin, json={
        "nome_loja": "Mercado Z", "login": "mercadoz", "senha": "senha123", "plano": "mensal",
    })
    ok = client.post("/api/conta/validar", json={"login": "mercadoz", "senha": "senha123"})
    assert ok.status_code == 200 and ok.json()["ok"] is True and "token" in ok.json()
    bad = client.post("/api/conta/validar", json={"login": "mercadoz", "senha": "x"})
    assert bad.status_code == 401


def test_financeiro_math(client, admin):
    client.put("/api/admin/financeiro", headers=admin, json={"preco_por_loja": 200})
    r = client.get("/api/admin/financeiro", headers=admin).json()
    lojas = r["lojas_ativas"]
    assert r["receita_mensal"] == round(lojas * 200, 2)
    esperado_custo = round(r["custo_fixo_mensal"] + r["custo_por_loja"] * lojas, 2)
    assert r["custo_total_mensal"] == esperado_custo
    assert r["lucro_mensal"] == round(r["receita_mensal"] - r["custo_total_mensal"], 2)


def test_trocar_senha(client, admin):
    # token do fixture continua válido; troca a senha e valida login novo/antigo
    r = client.put("/api/admin/senha", headers=admin, json={"senha_atual": "admin123", "nova_senha": "novaSenha1"})
    assert r.status_code == 200
    assert client.post("/api/admin/login", json={"email": "admin@teste.com", "senha": "novaSenha1"}).status_code == 200
    assert client.post("/api/admin/login", json={"email": "admin@teste.com", "senha": "admin123"}).status_code == 401
    # volta ao original para não afetar outros testes
    client.put("/api/admin/senha", headers=admin, json={"senha_atual": "novaSenha1", "nova_senha": "admin123"})


def test_rate_limit(client):
    # e-mail dedicado para não bloquear o admin dos outros testes
    alvo = {"email": "bruteforce@teste.com", "senha": "x"}
    codigos = [client.post("/api/admin/login", json=alvo).status_code for _ in range(7)]
    assert 429 in codigos  # após várias falhas, passa a bloquear
