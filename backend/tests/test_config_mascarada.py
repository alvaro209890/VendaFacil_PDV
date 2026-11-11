"""Testes para preservação de configurações mascaradas (F3.17).

Garante que salvar configs fiscais e de maquininha:
- Não apague segredos quando enviados vazios, omitidos ou com whitespace;
- Preserve valores originais no fluxo GET mascarado -> PUT salvar;
- Atualize para novo valor se fornecido texto não-vazio (mantendo mascarado no retorno);
- Permita remoção apenas via campo explícito validado ('limpar_segredos');
- Recuse (400 ou 422) tentativa de limpar colunas fora da whitelist;
- Recuse (400 ou 422) ambiguidade entre fornecer novo valor e pedir limpeza do mesmo campo;
- Mantenha funcionamento das demais configurações normais (device_id, flags, etc.).
"""
import pytest
from fastapi.testclient import TestClient

import database
import fiscal_config
import mercadopago
from auth import _gerar_jwt
from main import app


@pytest.fixture
def isolado(tmp_path, monkeypatch):
    """Isola banco SQLite em pasta temporária para cada teste."""
    monkeypatch.setattr(database, "DB_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "vendafacil.db")
    local = database.Database()
    monkeypatch.setattr(fiscal_config, "db", local)
    monkeypatch.setattr(mercadopago, "db", local)
    api = TestClient(app, raise_server_exceptions=False)
    try:
        yield local, api
    finally:
        api.close()
        local.close()


def _auth_headers() -> dict[str, str]:
    token = _gerar_jwt({
        "sub": "1",
        "usuario": "admin",
        "email": "admin@loja.com",
        "nome": "Administrador",
        "iat": 1,
        "exp": 9_999_999_999,
    })
    return {"Authorization": "Bearer " + token}


def test_fiscal_get_mascarado_put_preserva_5_segredos(isolado):
    """GET mascarado seguido de PUT reenviando o payload não apaga os 5 segredos fiscais."""
    db_local, api = isolado
    headers = _auth_headers()

    # 1. Configura inicialmente os 5 segredos fiscais
    payload_inicial = {
        "razao_social": "Empresa Teste",
        "gateway_token": "TOK-FISC-1",
        "csc": "CSC-VAL-1",
        "certificado_a1_b64": "CERT-B64-1",
        "certificado_senha": "PASS-CERT-1",
        "resp_tec_csrt": "CSRT-VAL-1",
    }
    r_ini = api.put("/api/fiscal/config", headers=headers, json=payload_inicial)
    assert r_ini.status_code == 200

    # 2. GET mascarado
    r_get = api.get("/api/fiscal/config", headers=headers)
    assert r_get.status_code == 200
    cfg_get = r_get.json()["config"]

    # Verifica que na resposta os segredos vieram mascarados
    for k in ("gateway_token", "csc", "certificado_a1_b64", "certificado_senha", "resp_tec_csrt"):
        assert cfg_get[k] == ""
        assert cfg_get[k + "_preenchido"] is True

    # 3. PUT reenviando dados mascarados com alteração de razão social
    payload_reenvio = dict(cfg_get)
    payload_reenvio["razao_social"] = "Empresa Atualizada"
    # Também simula espaços em branco em um dos campos mascarados
    payload_reenvio["csc"] = "   "

    r_put = api.put("/api/fiscal/config", headers=headers, json=payload_reenvio)
    assert r_put.status_code == 200

    # 4. Verifica no banco se os 5 segredos continuam intactos
    no_banco = db_local.get_config_fiscal()
    assert no_banco.get("razao_social") == "Empresa Atualizada"
    gw_ok = (no_banco.get("gateway_token") == "TOK-FISC-1")
    assert gw_ok is True, "gateway_token foi apagado"
    csc_ok = (no_banco.get("csc") == "CSC-VAL-1")
    assert csc_ok is True, "csc foi apagado"
    a1_ok = (no_banco.get("certificado_a1_b64") == "CERT-B64-1")
    assert a1_ok is True, "certificado_a1_b64 foi apagado"
    pwd_ok = (no_banco.get("certificado_senha") == "PASS-CERT-1")
    assert pwd_ok is True, "certificado_senha foi apagado"
    csrt_ok = (no_banco.get("resp_tec_csrt") == "CSRT-VAL-1")
    assert csrt_ok is True, "resp_tec_csrt foi apagado"


def test_maquininha_get_mascarado_put_preserva_access_token(isolado):
    """GET mascarado seguido de PUT não apaga o access_token da maquininha."""
    db_local, api = isolado
    headers = _auth_headers()

    # 1. Configura access_token inicial
    r_ini = api.put("/api/maquininha/config", headers=headers, json={
        "access_token": "MP-TOKEN-INICIAL",
        "device_id": "POINT1",
    })
    assert r_ini.status_code == 200

    # 2. GET mascarado
    r_get = api.get("/api/maquininha/config", headers=headers)
    assert r_get.status_code == 200
    cfg_get = r_get.json()["config"]
    assert cfg_get["access_token"] == ""
    assert cfg_get["access_token_preenchido"] is True

    # 3. PUT reenviando com access_token vazio e novo device_id
    r_put = api.put("/api/maquininha/config", headers=headers, json={
        "access_token": "",
        "device_id": "POINT2",
    })
    assert r_put.status_code == 200

    # 4. Verifica persistência no banco
    no_banco = db_local.get_config_maquininha()
    assert no_banco.get("device_id") == "POINT2"
    tok_ok = (no_banco.get("access_token") == "MP-TOKEN-INICIAL")
    assert tok_ok is True, "access_token foi apagado"


def test_novo_valor_troca_segredo_e_permanece_mascarado(isolado):
    """Envio de novo valor substitui o segredo anterior e retorna mascarado."""
    db_local, api = isolado
    headers = _auth_headers()

    # Configuração inicial
    api.put("/api/fiscal/config", headers=headers, json={"csc": "CSC-ANTIGO"})
    api.put("/api/maquininha/config", headers=headers, json={"access_token": "TOKEN-ANTIGO"})

    # Atualiza com novos valores não vazios
    r_fisc = api.put("/api/fiscal/config", headers=headers, json={"csc": "  CSC-NOVO  "})
    assert r_fisc.status_code == 200
    resp_fisc = r_fisc.json()["config"]
    assert resp_fisc["csc"] == ""
    assert resp_fisc["csc_preenchido"] is True

    r_maq = api.put("/api/maquininha/config", headers=headers, json={"access_token": "TOKEN-NOVO"})
    assert r_maq.status_code == 200
    resp_maq = r_maq.json()["config"]
    assert resp_maq["access_token"] == ""
    assert resp_maq["access_token_preenchido"] is True

    # Verifica no banco
    csc_novo_ok = (db_local.get_config_fiscal().get("csc") == "  CSC-NOVO  ")
    assert csc_novo_ok is True, "csc não foi atualizado para novo valor"
    tok_novo_ok = (db_local.get_config_maquininha().get("access_token") == "TOKEN-NOVO")
    assert tok_novo_ok is True, "access_token não foi atualizado para novo valor"


def test_limpar_segredos_explicito_valido(isolado):
    """Campo explícito limpar_segredos remove apenas os segredos solicitados."""
    db_local, api = isolado
    headers = _auth_headers()

    # Configura 2 segredos fiscais
    api.put("/api/fiscal/config", headers=headers, json={
        "csc": "CSC-MANTER",
        "gateway_token": "TOKEN-REMOVER",
    })

    # Pede limpeza explícita de gateway_token
    r_limpar = api.put("/api/fiscal/config", headers=headers, json={
        "limpar_segredos": ["gateway_token"],
    })
    assert r_limpar.status_code == 200

    no_banco = db_local.get_config_fiscal()
    manter_ok = (no_banco.get("csc") == "CSC-MANTER")
    assert manter_ok is True, "csc original não foi mantido"
    remover_ok = not bool(no_banco.get("gateway_token"))
    assert remover_ok is True, "gateway_token não foi limpo"

    # Maquininha: limpa access_token
    api.put("/api/maquininha/config", headers=headers, json={"access_token": "TOKEN-MP-REMOVER"})
    r_limpar_maq = api.put("/api/maquininha/config", headers=headers, json={
        "limpar_segredos": ["access_token"],
    })
    assert r_limpar_maq.status_code == 200
    no_banco_maq = db_local.get_config_maquininha()
    maq_removido_ok = not bool(no_banco_maq.get("access_token"))
    assert maq_removido_ok is True, "access_token não foi limpo"


def test_limpar_segredos_recusa_coluna_fora_da_whitelist(isolado):
    """limpar_segredos recusa (400 ou 422) colunas que não são segredos."""
    _, api = isolado
    headers = _auth_headers()

    # Tentativa de limpar coluna normal do fiscal
    r1 = api.put("/api/fiscal/config", headers=headers, json={
        "limpar_segredos": ["razao_social"],
    })
    assert r1.status_code in (400, 422)

    # Tentativa de limpar coluna normal da maquininha
    r2 = api.put("/api/maquininha/config", headers=headers, json={
        "limpar_segredos": ["device_id"],
    })
    assert r2.status_code in (400, 422)


def test_ambiguidade_novo_valor_e_limpeza_recusa(isolado):
    """Envio de novo valor E inclusão em limpar_segredos para o mesmo campo é recusado (400 ou 422)."""
    _, api = isolado
    headers = _auth_headers()

    # Fiscal
    r1 = api.put("/api/fiscal/config", headers=headers, json={
        "csc": "NOVO_VALOR",
        "limpar_segredos": ["csc"],
    })
    assert r1.status_code in (400, 422)

    # Maquininha
    r2 = api.put("/api/maquininha/config", headers=headers, json={
        "access_token": "NOVO_VALOR",
        "limpar_segredos": ["access_token"],
    })
    assert r2.status_code in (400, 422)


def test_demais_configs_continuam_funcionando(isolado):
    """Demais campos normais e flags continuam funcionando sem regressão."""
    db_local, api = isolado
    headers = _auth_headers()

    rf = api.put("/api/fiscal/config", headers=headers, json={
        "habilitado": True,
        "serie_nfce": 2,
        "ambiente": "homologacao",
    })
    assert rf.status_code == 200
    banco_f = db_local.get_config_fiscal()
    assert banco_f.get("habilitado") == 1
    assert banco_f.get("serie_nfce") == 2
    assert banco_f.get("ambiente") == "homologacao"

    rm = api.put("/api/maquininha/config", headers=headers, json={
        "habilitado": True,
        "imprimir_comprovante": False,
        "device_id": "DEVICE_XYZ",
    })
    assert rm.status_code == 200
    banco_m = db_local.get_config_maquininha()
    assert banco_m.get("habilitado") == 1
    assert banco_m.get("imprimir_comprovante") == 0
    assert banco_m.get("device_id") == "DEVICE_XYZ"


_CAMPOS = [
    ("/api/fiscal/config", nome, "get_config_fiscal")
    for nome in ("gateway_token", "csc", "certificado_a1_b64", "certificado_senha", "resp_tec_csrt")
] + [("/api/maquininha/config", "access_token", "get_config_maquininha")]


@pytest.mark.parametrize("rota,campo,leitura", _CAMPOS, ids=[c[1] for c in _CAMPOS])
def test_novo_segredo_preserva_valor_literal_inclusive_espacos(isolado, rota, campo, leitura):
    """Valores são fixtures opacas, não credenciais reais: não normalizar senha/token."""
    db_local, api = isolado
    original = "  fixture-opaca-com-espacos  "
    resposta = api.put(rota, headers=_auth_headers(), json={campo: original})
    assert resposta.status_code == 200
    intacto = getattr(db_local, leitura)().get(campo) == original
    assert intacto is True, "Novo segredo foi normalizado indevidamente"
    mascarado = resposta.json()["config"].get(campo) == ""
    assert mascarado is True, "Retorno deve continuar mascarado"


@pytest.mark.parametrize("rota,campo,leitura", _CAMPOS, ids=[c[1] for c in _CAMPOS])
@pytest.mark.parametrize("branco", ["", " \t ", None], ids=["vazio", "whitespace", "null"])
def test_reenvio_vazio_preserva_cada_segredo(isolado, rota, campo, leitura, branco):
    """Amplia a cobertura de omissão/nulos sem imprimir valores ou JWT."""
    db_local, api = isolado
    original = "fixture-opaca-anterior"
    headers = _auth_headers()
    assert api.put(rota, headers=headers, json={campo: original}).status_code == 200
    assert api.put(rota, headers=headers, json={campo: branco}).status_code == 200
    intacto = getattr(db_local, leitura)().get(campo) == original
    assert intacto is True, "Reenvio vazio apagou o segredo"