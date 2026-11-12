"""X18/P49: Portaria MT 177/2021, arts.3 §4 II e 8 II a."""
import pytest
from test_fiscal_direto import _cfg, _venda
import fiscal_direto


@pytest.mark.parametrize("valor,cpf,erro", [
    (999.99, None, None), (1000, None, "1.000"), (1000.01, None, "1.000"),
    (1000, "12345678909", None), (199999.99, "12345678909", None),
    (200000, "12345678909", "200.000"), (200000.01, "12345678909", "200.000"),
])
def test_x18_limites_inclusivos_mt(client, auth, valor, cpf, erro):
    p = client.post("/api/produtos", headers=auth, json={
        "nome": "Limite fiscal sintético", "preco_venda": valor, "estoque": 10,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    venda = _venda(p)
    venda.update(total=valor)
    venda["itens"][0].update(preco_unitario=valor, subtotal=valor)
    if erro:
        with pytest.raises(fiscal_direto.FiscalDiretoError, match=erro):
            fiscal_direto.montar_documento(venda, _cfg(), cpf_consumidor=cpf, serie=1, numero=1)
    else:
        assert fiscal_direto.montar_documento(venda, _cfg(), cpf_consumidor=cpf, serie=1, numero=1).chave
