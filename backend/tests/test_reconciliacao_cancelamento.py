"""Consulta explícita resolve evento aceito cuja resposta se perdeu."""
import pytest
import fiscal
import fiscal_direto


def _resposta(cstat):
    return ('<retConsSitNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
            f'<cStat>{cstat}</cStat><xMotivo>Cancelamento homologado</xMotivo>'
            '<protNFe><infProt><cStat>100</cStat><nProt>151260000000001</nProt>'
            '<dhRecbto>2026-11-12T10:00:00-04:00</dhRecbto>'
            '</infProt></protNFe></retConsSitNFe>')


@pytest.mark.parametrize('cstat', ['101', '151'])
def test_consulta_cancelada_prevalece_sobre_protocolo_original(cstat):
    r = fiscal_direto.normalizar_retorno_sefaz(_resposta(cstat), http_status=200)
    assert r['status'] == 'cancelada'
    assert r['cstat'] == cstat


def test_consulta_explicita_reconcilia_nota_local_autorizada(monkeypatch):
    nota = {'id': 1, 'status': 'autorizada', 'modelo': '65', 'chave': '5' * 44,
            'protocolo': '151260000000001'}
    class Store:
        def get_nota(self, _): return dict(nota)
        def get_config_fiscal(self): return {'provedor_fiscal': 'sefaz_mt_direto'}
        def atualizar_nota(self, _, dados, agora):
            nota.update(dados)
            return dict(nota)
    consultas = []
    def consultar(*args):
        consultas.append(args)
        return {'status_code': 200, 'texto': _resposta('101')}
    monkeypatch.setattr(fiscal, 'db', Store())
    monkeypatch.setattr(fiscal_direto, 'consultar_chave', consultar)
    r = fiscal.consultar_nfce(1)
    assert len(consultas) == 1
    assert r['status'] == 'cancelada'
