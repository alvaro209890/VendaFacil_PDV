"""S14 (P42): nota fiscal só é lida, consultada, cancelada ou baixada pelo dono.

Duas lojas no mesmo banco local. A loja B tenta alcançar a nota da loja A por
id de venda e por id de nota. Precisa ver 404 (não 403: não confirmar que a
nota existe) e a nota da loja A não pode ser transmitida nem cancelada.
"""
import pytest
from fastapi.testclient import TestClient

import database
import fiscal
import fiscal_router
from auth import _agora, _gerar_jwt, _token_user
from main import app


@pytest.fixture
def duas_lojas(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    agora = _agora()
    dono = local.create_user('dono', 'Dono', 'hash_de_fixture', agora)
    outro = local.create_user('outro', 'Outro', 'hash_de_fixture', agora)
    # O roteador e o serviço fiscal usam o banco desta fixture.
    monkeypatch.setattr(fiscal_router, 'db', local)
    monkeypatch.setattr(fiscal, 'db', local)

    produto = local.create_produto(dono['id'], 'Café', 1, 2, 5, 0, '', 'UN', agora)
    venda = local.create_venda(dono['id'], None, 2, 0, 'dinheiro', '', [{
        'produto_id': produto['id'], 'nome_produto': 'Café',
        'quantidade': 1, 'preco_unitario': 2, 'subtotal': 2,
    }], agora)
    assert venda
    notas = {}
    for modelo in ('65', '55'):
        notas[modelo] = local.criar_nota({
            'user_id': dono['id'], 'venda_id': venda['id'],
            'ref': f'teste-owner-{modelo}', 'modelo': modelo,
            'ambiente': 'homologacao', 'status': 'autorizada',
            'chave': '35260112345678000195650010000000011000000017',
            'criado_em': agora, 'atualizado_em': agora,
        })

    def headers(user):
        return {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(user))}

    api = TestClient(app, raise_server_exceptions=False)
    yield api, local, dono, outro, venda, notas, headers
    api.close()
    local.close()


def test_s14_dono_le_a_propria_nota(duas_lojas):
    api, _, dono, _, venda, notas, headers = duas_lojas
    r = api.get(f"/api/fiscal/nfce/venda/{venda['id']}", headers=headers(dono))
    assert r.status_code == 200, r.text
    assert r.json()['nota']['id'] == notas['65']['id']
    r = api.get(f"/api/fiscal/nfe/venda/{venda['id']}", headers=headers(dono))
    assert r.status_code == 200, r.text
    assert r.json()['nota']['id'] == notas['55']['id']


def test_s14_outra_loja_nao_le_nota_por_venda(duas_lojas):
    api, _, _, outro, venda, _, headers = duas_lojas
    for rota in ('nfce', 'nfe'):
        r = api.get(f"/api/fiscal/{rota}/venda/{venda['id']}", headers=headers(outro))
        assert r.status_code == 404, f'{rota}: {r.status_code} {r.text}'


def test_s14_outra_loja_nao_consulta_nota(duas_lojas, monkeypatch):
    api, _, _, outro, _, notas, headers = duas_lojas
    chamadas = []
    monkeypatch.setattr(fiscal, 'consultar_nfce',
                        lambda nota_id: chamadas.append(nota_id) or {})
    for rota, modelo in (('nfce', '65'), ('nfe', '55')):
        r = api.post(f"/api/fiscal/{rota}/{notas[modelo]['id']}/consultar",
                     headers=headers(outro))
        assert r.status_code == 404, f'{rota}: {r.status_code} {r.text}'
    assert chamadas == []


def test_s14_dono_consulta_e_cancela_sem_bloqueio(duas_lojas, monkeypatch):
    api, _, dono, _, _, notas, headers = duas_lojas
    chamadas = []
    monkeypatch.setattr(fiscal, 'consultar_nfce',
                        lambda nota_id: chamadas.append(('consulta', nota_id)) or {})
    monkeypatch.setattr(fiscal, 'cancelar_nfce',
                        lambda nota_id, just: chamadas.append(('cancelamento', nota_id)) or {})
    for rota, modelo in (('nfce', '65'), ('nfe', '55')):
        r = api.post(f"/api/fiscal/{rota}/{notas[modelo]['id']}/consultar",
                     headers=headers(dono))
        assert r.status_code == 200
    r = api.post(f"/api/fiscal/nfce/{notas['65']['id']}/cancelar",
                 headers=headers(dono), json={'justificativa': 'Cancelamento autorizado pelo dono'})
    assert r.status_code == 200
    assert chamadas == [('consulta', notas['65']['id']), ('consulta', notas['55']['id']),
                        ('cancelamento', notas['65']['id'])]


def test_s14_venda_do_dono_sem_nota_retorna_null(duas_lojas):
    api, local, dono, _, venda, _, headers = duas_lojas
    with local._lock, local._conn:
        local._conn.execute('DELETE FROM notas_fiscais WHERE venda_id = ?', (venda['id'],))
    for rota in ('nfce', 'nfe'):
        r = api.get(f"/api/fiscal/{rota}/venda/{venda['id']}", headers=headers(dono))
        assert r.status_code == 200
        assert r.json() == {'nota': None}


def test_s14_outra_loja_nao_cancela_nota(duas_lojas, monkeypatch):
    api, local, _, outro, _, notas, headers = duas_lojas
    chamadas = []
    monkeypatch.setattr(fiscal, 'cancelar_nfce',
                        lambda nota_id, just: chamadas.append(nota_id) or {})
    r = api.post(f"/api/fiscal/nfce/{notas['65']['id']}/cancelar",
                 headers=headers(outro),
                 json={'justificativa': 'Tentativa de cancelar nota de outra loja'})
    assert r.status_code == 404, r.text
    assert chamadas == []
    assert local.get_nota(notas['65']['id'])['status'] == 'autorizada'


def test_s14_outra_loja_nao_baixa_xml(duas_lojas):
    api, local, dono, outro, _, notas, headers = duas_lojas
    local.atualizar_nota(notas['65']['id'],
                         {'xml_autorizado': '<nfeProc/>'}, _agora())
    r = api.get(f"/api/fiscal/nfce/nota/{notas['65']['id']}/xml",
                headers=headers(outro))
    assert r.status_code == 404, r.text
    # O dono continua baixando o próprio XML.
    r = api.get(f"/api/fiscal/nfce/nota/{notas['65']['id']}/xml",
                headers=headers(dono))
    assert r.status_code == 200, r.text
    assert r.content == b'<nfeProc/>'


def test_s14_nota_inexistente_404_para_o_dono(duas_lojas):
    api, _, dono, _, _, _, headers = duas_lojas
    r = api.post('/api/fiscal/nfce/999999/consultar', headers=headers(dono))
    assert r.status_code == 404, r.text
    r = api.post('/api/fiscal/nfce/999999/cancelar', headers=headers(dono),
                 json={'justificativa': 'Nota que não existe em lugar nenhum'})
    assert r.status_code == 404, r.text
