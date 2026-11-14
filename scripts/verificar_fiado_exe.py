"""Aceite do fiado no binário, sem acessar loja, bancos ou terminal reais."""
import argparse
import tempfile
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roteiro_exe import Pdv, ROOT, _produto, _vender


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=ROOT / 'dist_exe' / 'VendaFacilPDV.exe')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='vf-fiado-') as dados:
        pdv = Pdv(args.exe, Path(dados))
        try:
            assert pdv.iniciar()['version'] == '1.0.20'
            pdv.login(novo=True)
            pdv.pedir('PUT', '/api/pix/config', dados={'pix_chave': 'teste@example.com', 'pix_nome': 'LOJA TESTE', 'pix_cidade': 'QUERENCIA'})
            pdv.pedir('POST', '/api/caixa/abrir', dados={'valor_abertura': 10})
            conta = pdv.pedir('POST', '/api/contas-receber', 201, dados={'valor_total': 100, 'observacao': 'Aceite descartável do fiado'})['conta']['id']
            base = f'/api/contas-receber/{conta}'
            pix = pdv.pedir('POST', base + '/pix', dados={'valor': 30})['pix']
            atual = pdv.pedir('GET', base)['conta']
            assert atual['valor_pendente'] == 100 and not atual['cobranca_pendente']
            assert atual['pix_pendentes'][0]['payload'] == pix['payload']
            # Uma venda normal continua possível enquanto o cliente guarda o código.
            _vender(pdv, _produto(pdv))
            antes = pdv.pedir('GET', '/api/caixa/atual')['resumo']['dinheiro_esperado']
            assert antes == 20
            pagamento = {'valor': 30, 'forma': 'pix', 'referencia': pix['id']}
            for _ in range(2):
                atual = pdv.pedir('POST', base + '/pagar', dados=pagamento)['conta']
            assert atual['valor_pendente'] == 70 and len(atual['pagamentos']) == 1
            assert atual['pagamentos'][0]['forma'] == 'pix' and not atual['pix_pendentes']
            assert pdv.pedir('GET', '/api/caixa/atual')['resumo']['dinheiro_esperado'] == antes
            for forma, valor in [('dinheiro', 20), ('debito', 10), ('credito', 5)]:
                pdv.pedir('POST', base + '/pagar', dados={'valor': valor, 'forma': forma, 'referencia': str(uuid4())})
            assert pdv.pedir('GET', '/api/caixa/atual')['resumo']['dinheiro_esperado'] == 40
            outro_pix = pdv.pedir('POST', base + '/pix', dados={'valor': 25})['pix']
            pdv.parar()
            pdv.iniciar()
            pdv.login()
            atual = pdv.pedir('GET', base)['conta']
            assert atual['valor_pendente'] == 35
            assert atual['pix_pendentes'][0]['payload'] == outro_pix['payload']
            assert [p['forma'] for p in atual['pagamentos']] == ['pix', 'dinheiro', 'debito', 'credito']
            assert pdv.erros_5xx == 0
            print(f'OK: {pdv.requisicoes} requisições, 0 erros 5xx; PIX salvo após reinício; venda liberada e caixa correto.')
        finally:
            pdv.parar()


if __name__ == '__main__':
    main()
