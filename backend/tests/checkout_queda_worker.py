"""Worker V06: pausa dentro do SQL para o teste matar o processo de verdade.

Somente fixtures de backend/tests. Não tem opção equivalente no produto.
"""
import asyncio
import os
from pathlib import Path
import sys

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
if len(sys.argv) > 3 and sys.argv[3]:
    sys.path.insert(0, sys.argv[3])
os.environ['VENDAFACIL_DATA_DIR'] = sys.argv[1]
os.environ['VENDAFACIL_PAINEL_URL'] = ''
os.environ['VENDAFACIL_NO_BROWSER'] = '1'

from database import db
from auth import _gerar_jwt, _token_user
from starlette.requests import Request
from vendas import CheckoutRequest, checkout


def pausar():
    print('PONTO_DE_CORTE_SQL', flush=True)
    sys.stdin.read(1)
    return 0


db._conn.create_function('pausar_teste', 0, pausar)
with db._conn:
    db._conn.execute('CREATE TEMP TRIGGER pausa_venda BEFORE INSERT ON vendas BEGIN SELECT pausar_teste(); END')
user = db.get_user_by_usuario('transacao')
token = _gerar_jwt(_token_user(user))
request = Request({'type': 'http', 'method': 'POST', 'path': '/api/vendas/checkout',
                   'headers': [(b'authorization', ('Bearer ' + token).encode())]})
data = CheckoutRequest(itens=[{'produto_id': int(sys.argv[2]), 'quantidade': 1}])
asyncio.run(checkout(data, request))
