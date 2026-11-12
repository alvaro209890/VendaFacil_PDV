"""B4: o CNAE pedido no precheck deve poder ser salvo pela loja."""
def test_config_fiscal_persiste_cnae_normalizado(client, auth):
    r = client.put('/api/fiscal/config', headers=auth, json={'cnae': '4712-1/00'})
    assert r.status_code == 200, r.text
    assert r.json()['config']['cnae'] == '4712100'
    assert client.get('/api/fiscal/config', headers=auth).json()['config']['cnae'] == '4712100'
