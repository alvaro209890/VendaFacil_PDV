"""M01-M12: fluxos fiscais contra HTTP SOAP local e assinatura A1 real.

O teste não altera configuração de produto para apontar a SEFAZ falsa: só troca
o mapa fiscal_direto.WS em memória. O certificado é efêmero e exclusivo dos
testes; nenhuma senha ou material do ambiente da loja é usado.
"""
import base64
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
import fiscal
import fiscal_direto
from sefaz_fake import (SefazFake, retorno_autorizacao, retorno_consulta,
                        retorno_evento, retorno_inutilizacao, retorno_status)


_CERTIFICADO_TESTE = None


def _certificado_teste():
    global _CERTIFICADO_TESTE
    if _CERTIFICADO_TESTE:
        return _CERTIFICADO_TESTE
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CERTIFICADO TESTE LOCAL")])
    agora = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome)
            .public_key(chave.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(agora - timedelta(minutes=1))
            .not_valid_after(agora + timedelta(days=2)).sign(chave, hashes.SHA256()))
    pfx = pkcs12.serialize_key_and_certificates(
        b"teste", chave, cert, None, serialization.BestAvailableEncryption(b"somente-teste"))
    _CERTIFICADO_TESTE = base64.b64encode(pfx).decode("ascii")
    return _CERTIFICADO_TESTE


@pytest.fixture
def fiscal_store(tmp_path, monkeypatch):
    import database
    import auth
    import conta
    import fiscal_router
    import fiscal_config
    import fiscal_servicos_router
    import vendas
    import main
    import produtos

    monkeypatch.setattr(database, "DB_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "sefaz_simulador.db")
    store = database.Database()
    for module in (database, auth, conta, fiscal, fiscal_direto, fiscal_router,
                   fiscal_config, fiscal_servicos_router, vendas, main, produtos):
        if hasattr(module, "db"):
            monkeypatch.setattr(module, "db", store)
    monkeypatch.setattr(sys.modules[__name__], "db", store)
    user = store.create_user("sefaz-teste", "Usuário SEFAZ de teste",
                             auth._hash_senha("Senha-Fiscal-Teste-2026"), auth._agora())
    assert user
    token = auth._gerar_jwt(auth._token_user(user))
    yield {"db": store, "user": user, "token": token}
    store.close()


@pytest.fixture
def client(fiscal_store):
    from main import app
    # Sem gerenciar lifespan: main.startup dispara loops permanentes que não
    # fazem parte do cenário HTTP e poderiam atravessar o fixture.
    return TestClient(app)


@pytest.fixture
def auth(fiscal_store):
    return {"Authorization": "Bearer " + fiscal_store["token"]}


@pytest.fixture
def simulador(monkeypatch):
    fake = SefazFake()
    originais = dict(fiscal_direto.WS)
    try:
        for (modelo, ambiente, servico) in originais:
            fiscal_direto.WS[(modelo, ambiente, servico)] = fake.endpoint(servico, modelo, ambiente)
        # O método opcional de status e a implementação nova de inutilização
        # usam estas chaves, sem acrescentar URL de simulador à configuração.
        for modelo in ("65", "55"):
            for ambiente in ("homologacao", "producao"):
                fiscal_direto.WS[(modelo, ambiente, "status")] = fake.endpoint("status", modelo, ambiente)
                fiscal_direto.WS[(modelo, ambiente, "inutilizacao")] = fake.endpoint("inutilizacao", modelo, ambiente)
        yield fake
    finally:
        fiscal_direto.WS.clear()
        fiscal_direto.WS.update(originais)
        fake.stop()


@pytest.fixture
def emissor(simulador, fiscal_store):
    config = {
        "habilitado": 1, "provedor_fiscal": "sefaz_mt_direto", "ambiente": "homologacao",
        "cnpj": "12345678000195", "inscricao_estadual": "00130000019",
        "regime_tributario": "1", "logradouro": "Rua Teste", "numero": "100",
        "bairro": "Centro", "municipio": "Cuiaba", "codigo_municipio": "5103403",
        "uf": "MT", "cep": "78000000", "csc": "CSC-DE-TESTE", "csc_id": "1",
        "serie_nfce": 1, "proximo_numero_nfce": 1, "serie_nfe": 1, "proximo_numero_nfe": 1,
        "certificado_a1_b64": _certificado_teste(), "certificado_senha": "somente-teste",
    }
    fiscal_store["db"].salvar_config_fiscal(config, "fixture-sefaz-simulador")
    produto = {
        "nome": "Item de teste fiscal", "preco_venda": 10, "estoque": 200,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }
    return {"user_id": fiscal_store["user"]["id"], "config": config, "produto": produto}


@pytest.fixture
def loja(client, auth, emissor):
    p = client.post("/api/produtos", headers=auth, json=emissor["produto"])
    assert p.status_code == 201, p.text
    return {**emissor, "produto_id": p.json()["produto"]["id"], "client": client, "auth": auth}


def _vender(loja, qtd=1):
    r = loja["client"].post("/api/vendas/checkout", headers=loja["auth"], json={
        "itens": [{"produto_id": loja["produto_id"], "quantidade": qtd}],
        "forma_pagamento": "dinheiro",
    })
    assert r.status_code == 201, r.text
    return r.json()["venda"]


def _emitir(loja, venda):
    return loja["client"].post(f"/api/fiscal/nfce/venda/{venda['id']}/emitir",
                                headers=loja["auth"], json={})


def _api_consultar(loja, nota_id):
    return loja["client"].post(f"/api/fiscal/nfce/{nota_id}/consultar", headers=loja["auth"])


def _chamada_chave(call):
    import re
    m = re.search(r"<chNFe>(\d{44})</chNFe>", call["body"])
    return m.group(1) if m else None


def test_m01_autorizacao_cstat_100_pela_api_guarda_protocolo_e_xml(loja, simulador):
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao(protocolo="151260000000101"))
    r = _emitir(loja, venda)
    assert r.status_code == 200, r.text
    nota = r.json()["nota"]
    assert nota["status"] == "autorizada"
    assert nota["protocolo"] == "151260000000101"
    assert "<nfeProc" in nota["xml_autorizado"]
    assert len(simulador.calls) == 1 and simulador.calls[0]["service"] == "autorizacao"
    assert "<Signature" in simulador.calls[0]["body"] or "<ds:Signature" in simulador.calls[0]["body"]


def test_m02_rejeicao_preserva_venda_e_nota_e_permite_reemissao(loja, simulador):
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao("225", "Falha no schema XML", ""))
    r = _emitir(loja, venda)
    assert r.status_code == 200, r.text
    assert r.json()["nota"]["status"] == "rejeitada"
    assert "schema" in r.json()["nota"]["motivo_rejeicao"]
    assert db.get_venda(venda["id"], loja["user_id"])["status"] == "concluida"
    # Uma nova tentativa após rejeição permanece vinculada à mesma venda sem
    # apagar o registro anterior nem mudar o estoque do checkout.
    simulador.push("autorizacao", retorno_autorizacao(protocolo="151260000000102"))
    r2 = _emitir(loja, venda)
    assert r2.status_code == 200, r2.text
    assert r2.json()["nota"]["status"] == "autorizada"
    assert db.get_nota_por_venda(venda["id"], "65")["status"] == "autorizada"


def test_m03_duplicidade_em_contingencia_consulta_chave_sem_criar_segunda_nota(loja, simulador):
    venda = _vender(loja)
    key = ("65", "homologacao", "autorizacao")
    endpoint = fiscal_direto.WS[key]
    fiscal_direto.WS[key] = simulador.unused_endpoint("autorizacao")
    try:
        nota_offline = _emitir(loja, venda).json()["nota"]
    finally:
        fiscal_direto.WS[key] = endpoint
    assert nota_offline["status"] == "contingencia"
    simulador.push("autorizacao", retorno_autorizacao("539", "Duplicidade de NF-e"))
    simulador.push("consulta", retorno_consulta("100", "Autorizado o uso da NF-e", "151260000000103"))
    assert fiscal._processar_pendentes_direto(loja["config"]) == 1
    nota_final = db.get_nota(nota_offline["id"])
    assert nota_final["status"] == "autorizada"
    assert nota_final["protocolo"] == "151260000000103"
    assert len([n for n in db.notas_pendentes() if n.get("venda_id") == venda["id"]]) == 0
    assert [c["service"] for c in simulador.calls] == ["autorizacao", "consulta"]


def test_m04_timeout_leitura_consulta_sem_retransmitir_nota(loja, simulador, monkeypatch):
    import requests
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao(), delay=0.35)
    original = requests.Session.post

    def timeout_curto(session, *args, **kwargs):
        kwargs["timeout"] = 0.08
        return original(session, *args, **kwargs)

    monkeypatch.setattr(requests.Session, "post", timeout_curto)
    r = _emitir(loja, venda)
    assert r.status_code == 200, r.text
    pendente = r.json()["nota"]
    assert pendente["status"] in ("processando", "pendente")
    assert db.get_nota_por_venda(venda["id"], "65")["id"] == pendente["id"]
    simulador.push("consulta", retorno_consulta("100", "Autorizado o uso da NF-e", "151260000000104"))
    assert fiscal._processar_pendentes_direto(loja["config"]) == 1
    assert [c["service"] for c in simulador.calls] == ["autorizacao", "consulta"]
    assert db.get_nota(pendente["id"])["status"] == "autorizada"


def test_m05_http_503_preserva_reserva_e_retorna_a_consultar(loja, simulador):
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao("0", "Serviço temporariamente indisponível"), status=503)
    r = _emitir(loja, venda)
    assert r.status_code == 200, r.text
    nota = r.json()["nota"]
    assert nota["status"] in ("processando", "pendente", "contingencia")
    simulador.push("consulta", retorno_consulta("100", "Autorizado o uso da NF-e", "151260000000105"))
    fiscal._processar_pendentes_direto(loja["config"])
    assert db.get_nota(nota["id"])["status"] == "autorizada"
    assert db.get_nota_por_venda(venda["id"], "65")["id"] == nota["id"]
    assert [c["service"] for c in simulador.calls] == ["autorizacao", "consulta"]


def test_m06_processando_105_reconsulta_e_autoriza(loja, simulador):
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao("105", "Lote em processamento", ""))
    r = _emitir(loja, venda)
    nota = r.json()["nota"]
    assert nota["status"] == "processando"
    simulador.push("consulta", retorno_consulta("100", "Autorizado o uso da NF-e", "151260000000106"))
    assert fiscal._processar_pendentes_direto(loja["config"]) == 1
    assert db.get_nota(nota["id"])["status"] == "autorizada"
    assert [c["service"] for c in simulador.calls] == ["autorizacao", "consulta"]


def test_m07_cstat_150_e_autorizacao_valida(loja, simulador):
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao("150", "Autorizado uso fora de prazo", "151260000000107"))
    r = _emitir(loja, venda)
    assert r.status_code == 200, r.text
    assert r.json()["nota"]["status"] == "autorizada"
    assert r.json()["nota"]["protocolo"] == "151260000000107"


def test_m08_evento_135_cancela_e_rejeicao_preserva_autorizacao(loja, simulador):
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao(protocolo="151260000000108"))
    nota = _emitir(loja, venda).json()["nota"]
    simulador.push("evento", retorno_evento("135", "Evento registrado e vinculado a NF-e"))
    ok = loja["client"].post(f"/api/fiscal/nfce/{nota['id']}/cancelar", headers=loja["auth"],
                              json={"justificativa": "Cancelamento de teste fiscal"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["nota"]["status"] == "cancelada"

    # Outra nota autorizada recebe rejeição de evento; mantém autorização.
    venda2 = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao(protocolo="151260000000109"))
    nota2 = _emitir(loja, venda2).json()["nota"]
    simulador.push("evento", retorno_evento("573", "Duplicidade de evento"))
    rejeitado = loja["client"].post(f"/api/fiscal/nfce/{nota2['id']}/cancelar", headers=loja["auth"],
                                    json={"justificativa": "Tentativa de cancelamento teste"})
    assert rejeitado.status_code == 200, rejeitado.text
    assert rejeitado.json()["nota"]["status"] == "autorizada"


def test_m09_contrato_inutilizacao_homologada(simulador, emissor):
    simulador.push("inutilizacao", retorno_inutilizacao())
    resultado = fiscal_direto.inutilizar_numeracao(
        emissor["config"], "65", 2026, 1, 4, 4,
        "Inutilizacao de numero nao utilizado no teste")
    assert resultado["cstat"] == "102"
    assert resultado["status"] == "inutilizada"
    assert resultado["protocolo"] == "151260000000010"
    assert "<inutNFe" in resultado["xml_pedido"]
    assert simulador.calls[-1]["service"] == "inutilizacao"


@pytest.mark.parametrize(("cstat", "operacao"), [("107", True), ("108", False)])
def test_m10_status_servico_operando_e_fora_de_operacao(client, auth, simulador,
                                                         emissor, cstat, operacao):
    simulador.push("status", retorno_status(cstat, "Serviço em Operação" if operacao else "Serviço Paralisado"))
    r = client.get("/api/fiscal/servicos/status?modelo=65", headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["cstat"] == cstat
    assert r.json()["em_operacao"] is operacao
    assert r.json()["mensagem"]
    assert simulador.calls[-1]["service"] == "status"


def test_m11_nota_processando_sobrevive_reentrada_do_loop_sem_reenvio(loja, simulador):
    import os
    import subprocess
    import database
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao("105", "Lote em processamento", ""))
    nota = _emitir(loja, venda).json()["nota"]
    nota_apos_reinicio = db.get_nota(nota["id"])
    assert nota_apos_reinicio["status"] == "processando"
    simulador.push("consulta", retorno_consulta("100", "Autorizado o uso da NF-e", "151260000000111"))
    # Processo novo, conexão nova e nenhum estado Python herdado. O único
    # transporte permitido no filho é o simulador de loopback.
    codigo = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import database, fiscal, fiscal_direto
database.DB_PATH = Path(sys.argv[2])
local = database.Database()
fiscal.db = fiscal_direto.db = local
for chave in fiscal_direto.WS:
    fiscal_direto.WS[chave] = sys.argv[3] + '/' + {'autorizacao':'NfeAutorizacao4',
        'consulta':'NfeConsulta4','evento':'RecepcaoEvento4','status':'NfeStatusServico4',
        'inutilizacao':'NfeInutilizacao4'}[chave[2]]
try:
    assert fiscal._processar_pendentes_direto(local.get_config_fiscal()) == 1
    assert local.get_nota(int(sys.argv[4]))['status'] == 'autorizada'
    print('M11: processo novo retomou nota sem retransmitir')
finally:
    local.close()
"""
    env = {**os.environ, "PYTHONPATH": "", "VENDAFACIL_DATA_DIR": str(database.DB_PATH.parent)}
    reinicio = subprocess.run([sys.executable, "-X", "utf8", "-I", "-c", codigo,
                               str(Path(__file__).resolve().parent.parent), str(database.DB_PATH),
                               simulador.base_url, str(nota["id"])], env=env, capture_output=True,
                              text=True, encoding="utf-8", timeout=30)
    assert reinicio.returncode == 0, reinicio.stderr
    assert [c["service"] for c in simulador.calls] == ["autorizacao", "consulta"]
    assert db.get_nota(nota["id"])["status"] == "autorizada"


def test_m12_tres_vendas_offline_depois_autorizadas_sem_duplica(loja, simulador):
    vendas = [_vender(loja) for _ in range(3)]
    key = ("65", "homologacao", "autorizacao")
    endpoint = fiscal_direto.WS[key]
    fiscal_direto.WS[key] = simulador.unused_endpoint("autorizacao")
    try:
        notas = [_emitir(loja, venda).json()["nota"] for venda in vendas]
    finally:
        fiscal_direto.WS[key] = endpoint
    assert [n["status"] for n in notas] == ["contingencia"] * 3
    assert len({n["id"] for n in notas}) == 3
    for i in range(3):
        simulador.push("autorizacao", retorno_autorizacao(protocolo=f"15126000000012{i}"))
    assert fiscal._processar_pendentes_direto(loja["config"]) == 3
    assert all(db.get_nota(n["id"])["status"] == "autorizada" for n in notas)
    assert [c["service"] for c in simulador.calls] == ["autorizacao"] * 3


def test_x14_cancelar_apos_contingencia_autorizada_sem_duplica(loja, simulador):
    venda = _vender(loja)
    key = ("65", "homologacao", "autorizacao")
    endpoint = fiscal_direto.WS[key]
    fiscal_direto.WS[key] = simulador.unused_endpoint("autorizacao")
    try:
        offline = _emitir(loja, venda).json()["nota"]
    finally:
        fiscal_direto.WS[key] = endpoint
    assert offline["status"] == "contingencia"
    # A criação é antiga: quem define o prazo é a autorização posterior.
    with db._lock, db._conn:
        db._conn.execute("UPDATE notas_fiscais SET criado_em=? WHERE id=?",
                         ((datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(), offline["id"]))
    simulador.push("autorizacao", retorno_autorizacao())
    assert fiscal._processar_pendentes_direto(loja["config"]) == 1
    simulador.push("evento", retorno_evento())
    resposta = loja["client"].post(f"/api/fiscal/nfce/{offline['id']}/cancelar",
                                  headers=loja["auth"], json={"justificativa": "Cancelamento apos contingencia de teste"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["nota"]["status"] == "cancelada"
    assert resposta.json()["nota"]["id"] == offline["id"]
    assert [c["service"] for c in simulador.calls] == ["autorizacao", "evento"]
    with db._lock:
        assert db._conn.execute("SELECT count(*) FROM notas_fiscais WHERE venda_id=?", (venda["id"],)).fetchone()[0] == 1


@pytest.mark.parametrize("modelo", ["65", "55"])
def test_x13_direto_nao_cai_em_gateway_emissao_consulta_loop_cancelamento(loja, simulador, monkeypatch, modelo):
    def legado_proibido(*args, **kwargs):
        pytest.fail("Emissor direto tentou usar gateway legado")
    monkeypatch.setattr(fiscal, "_gateway", legado_proibido)
    monkeypatch.setattr(fiscal.FocusNFe, "__init__", legado_proibido)
    monkeypatch.setattr(fiscal.PlugNotas, "__init__", legado_proibido)
    venda = _vender(loja)
    simulador.push("autorizacao", retorno_autorizacao("105", "Lote em processamento", ""))
    if modelo == "65":
        nota = _emitir(loja, venda).json()["nota"]
    else:
        cliente = db.create_cliente(loja["user_id"], "Consumidor de teste", "", "", "", "",
                                    datetime.now(timezone.utc).isoformat(), documento="12345678909",
                                    logradouro="Rua Teste", numero="1", bairro="Centro", municipio="Cuiaba",
                                    codigo_municipio="5103403", uf="MT", cep="78000000")
        nota = fiscal.emitir_nfe(venda["id"], loja["user_id"], cliente["id"])
    assert nota["status"] == "processando"
    assert _api_consultar(loja, nota["id"]).json()["nota"]["status"] == "autorizada"
    cancelamento = loja["client"].post(f"/api/fiscal/nfce/{nota['id']}/cancelar",
                                       headers=loja["auth"], json={"justificativa": "Cancelamento para testar provedor direto"})
    assert cancelamento.status_code == 200, cancelamento.text
    assert cancelamento.json()["nota"]["status"] == "cancelada"
    assert fiscal.processar_pendentes() == 0
