"""P35/X14: reservas fiscais não queimam numeração por falhas locais."""
from datetime import datetime, timezone
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database
import fiscal
import fiscal_direto


@pytest.fixture
def fiscal_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "fiscal-reserva.db")
    local = database.Database()
    monkeypatch.setattr(fiscal, "db", local)
    monkeypatch.setattr(fiscal_direto, "db", local)

    agora = datetime.now(timezone.utc).isoformat()
    user = local.create_user("reserva-teste", "Reserva teste", "hash_fixture", agora)
    produto = local.create_produto(
        user["id"], "Produto fiscal de teste", 5, 10, 20, 0, "", "UN", agora,
    )

    def venda(produto_atual=produto):
        return local.create_venda(
            user["id"], None, 10, 0, "dinheiro", "",
            [{"produto_id": produto_atual["id"], "nome_produto": produto_atual["nome"],
              "quantidade": 1, "preco_unitario": 10, "subtotal": 10}],
            agora,
        )

    yield local, user, produto, venda
    local.close()


def _config_habilitada(db, **extra):
    return db.salvar_config_fiscal({
        "habilitado": 1,
        "provedor_fiscal": "sefaz_mt_direto",
        "ambiente": "homologacao",
        **extra,
    }, "2026-11-12T12:00:00+00:00")


def _qtd_notas(db):
    with db._lock:
        return db._conn.execute("SELECT COUNT(*) FROM notas_fiscais").fetchone()[0]


def test_p35_reserva_sem_linha_de_configuracao_nao_grava_nota(fiscal_tmp):
    db, user, _, criar_venda = fiscal_tmp
    venda = criar_venda()

    with pytest.raises(ValueError, match="[Cc]onfigura[çc][ãa]o fiscal"):
        db.reservar_nota_fiscal(venda["id"], user["id"], "65", "homologacao",
                                "2026-11-12T12:00:00+00:00")

    assert _qtd_notas(db) == 0
    with db._lock:
        assert db._conn.execute("SELECT 1 FROM config_fiscal WHERE id = 1").fetchone() is None


@pytest.mark.parametrize("falha", ["certificado", "itens"])
def test_p35_falha_local_preflight_nao_consume_numero_nem_deixa_orfa(
        fiscal_tmp, monkeypatch, falha):
    db, user, _, criar_venda = fiscal_tmp
    venda = criar_venda()
    config = {"certificado_a1_b64": "", "certificado_senha": ""}
    if falha == "itens":
        # Dados inteiramente sintéticos de teste; o certificado não é carregado,
        # pois a validação dos itens deve falhar antes de assinar/transmitir.
        config.update({"certificado_a1_b64": "Zml4dHVyZQ==", "certificado_senha": "fixture",
                       "csc": "CSC_FIXTURE", "csc_id": "1"})
        monkeypatch.setattr(fiscal_direto, "_validar_certificado", lambda *_: None)

    _config_habilitada(db, **config)
    monkeypatch.setattr(fiscal, "_validar_config", lambda *_: None)
    monkeypatch.setattr(fiscal_direto, "_validar_emitente", lambda *_: None)
    envios = []
    monkeypatch.setattr(fiscal_direto, "transmitir_autorizacao",
                        lambda *args, **kwargs: envios.append((args, kwargs)))

    mensagem = "certificado" if falha == "certificado" else "incompletos"
    with pytest.raises(fiscal.FiscalError, match=mensagem):
        fiscal.emitir_nfce(venda["id"], user["id"])

    assert _qtd_notas(db) == 0
    assert db.get_config_fiscal()["proximo_numero_nfce"] == 1
    assert envios == []


def test_p35_falha_de_assinatura_retorna_a_mesma_reserva_sem_consumir_outro_numero(
        fiscal_tmp, monkeypatch):
    db, user, _, criar_venda = fiscal_tmp
    venda = criar_venda()
    _config_habilitada(db)
    monkeypatch.setattr(fiscal, "_validar_config", lambda *_: None)
    # O preflight em si é coberto pelos dois casos anteriores; aqui o cenário é
    # a reserva sobreviver a uma falha local na montagem/assinatura.
    monkeypatch.setattr(fiscal, "_preflight_direto", lambda *_: None)

    chamadas = []

    def preparar(_venda, _config, _modelo, *, serie, numero, **kwargs):
        chamadas.append((serie, numero))
        if len(chamadas) == 1:
            # Falha local antes de qualquer chamada a transmitir_autorizacao.
            raise fiscal_direto.FiscalDiretoError("Falha sintética ao assinar XML.")
        return {
            "serie": serie,
            "numero": numero,
            "chave": "51261112345678000195650010000000011000000010",
            "xml_assinado": "<NFe>FIXTURE</NFe>",
            "payload": "{}",
            "retorno": {"texto": "", "status_code": 200},
        }

    monkeypatch.setattr(fiscal_direto, "preparar_e_tentar_transmitir", preparar)
    with pytest.raises(fiscal.FiscalError, match="assinar XML"):
        fiscal.emitir_nfce(venda["id"], user["id"])

    primeira = db.get_nota_por_venda(venda["id"], "65")
    assert primeira is not None
    primeiro_id, primeiro_numero = primeira["id"], primeira["numero"]

    retomada = fiscal.emitir_nfce(venda["id"], user["id"])
    assert retomada["id"] == primeiro_id
    assert retomada["numero"] == primeiro_numero
    assert retomada["status"] == "processando"
    assert chamadas == [(primeira["serie"], primeiro_numero)] * 2
    assert db.get_config_fiscal()["proximo_numero_nfce"] == primeiro_numero + 1

    # Uma reserva possivelmente transmitida mantém seu número; a venda seguinte
    # recebe o próximo e nunca reaproveita a numeração da primeira.
    outra_venda = criar_venda()
    outra, criada = db.reservar_nota_fiscal(
        outra_venda["id"], user["id"], "65", "homologacao", "2026-11-12T12:01:00+00:00")
    assert criada is True
    assert outra["numero"] == primeiro_numero + 1


@pytest.mark.parametrize("mesma_venda", [True, False])
def test_x12_x14_reservas_concorrentes_duas_conexoes_sem_buraco(fiscal_tmp, mesma_venda):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    db, user, _, criar_venda = fiscal_tmp
    _config_habilitada(db)
    vendas = [criar_venda() for _ in range(12)]
    outra = database.Database()
    barreira = Barrier(2)

    def reservar(args):
        conn, indices = args
        barreira.wait(timeout=10)
        return [conn.reservar_nota_fiscal(
            vendas[0 if mesma_venda else i]["id"], user["id"], "65", "homologacao",
            "2026-11-12T12:00:00+00:00") for i in indices]

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            grupos = list(pool.map(reservar, [(db, range(0, 12, 2)), (outra, range(1, 12, 2))]))
        resultados = [r for grupo in grupos for r in grupo]
        if mesma_venda:
            assert len({r[0]["id"] for r in resultados}) == 1
            assert sum(criada for _, criada in resultados) == 1
            assert db.get_config_fiscal()["proximo_numero_nfce"] == 2
        else:
            assert sorted(r[0]["numero"] for r in resultados) == list(range(1, 13))
            assert all(criada for _, criada in resultados)
            assert db.get_config_fiscal()["proximo_numero_nfce"] == 13
    finally:
        outra.close()
