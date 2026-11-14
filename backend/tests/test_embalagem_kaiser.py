"""Caso real da NF-e 446817 (Kaiser lata, 50 CX x 12 = 600 UN) e regras de preço.

A nota de verdade fica fora do git (%TEMP%\\vf-nota.xml). Aqui vai uma cópia
reduzida com os mesmos campos que pesam: uCom/uTrib UN, qCom 600, vUnCom 2,74,
vOutro 12,36, cEAN (pacote) diferente de cEANTrib (lata). O banco dos testes é
um só na sessão: cada caso gera os seus códigos, chave e nome.
"""
import itertools

PACOTE = "7896045500116"  # cEAN da NF-e 446817
LATA = "7896045512317"    # cEANTrib da NF-e 446817 (lata 350 ml)
_seq = itertools.count(1)


def gtin(base12: str) -> str:
    soma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(base12)))
    return base12 + str((-soma) % 10)


class Caso:
    def __init__(self):
        n = next(_seq)
        self.pacote = gtin(f"789604559{n:03d}")
        self.lata = gtin(f"789604558{n:03d}")
        self.nome = f"CX 00050 KAISER LT 350ML #{n}"
        self.chave = f"512611260691050001905502100044681710043{n:05d}"

    def xml(self, ucom="UN", qcom="600.0000", vun="2.74000000", vprod="1644.00",
            extra="<vOutro>12.36</vOutro>", imposto="", ean=None, ean_trib=None):
        ean = self.pacote if ean is None else ean
        ean_trib = self.lata if ean_trib is None else ean_trib
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><NFe>
<infNFe Id="NFe{self.chave}" versao="4.00"><ide><mod>55</mod><nNF>446817</nNF></ide>
<emit><xNome>DISTRIBUIDORA DE BEBIDAS CANARANA LTDA</xNome></emit>
<det nItem="1"><prod><cProd>0001200272</cProd><cEAN>{ean}</cEAN><xProd>{self.nome}</xProd>
<NCM>22030000</NCM><CEST>0302100</CEST><CFOP>5405</CFOP><uCom>{ucom}</uCom><qCom>{qcom}</qCom>
<vUnCom>{vun}</vUnCom><vProd>{vprod}</vProd><cEANTrib>{ean_trib}</cEANTrib><uTrib>UN</uTrib>
<qTrib>600.0000</qTrib><vUnTrib>2.74000000</vUnTrib>{extra}<indTot>1</indTot></prod>
<imposto>{imposto}</imposto></det>
</infNFe></NFe></nfeProc>'''.encode()

    def produto(self, client, auth):
        return next(p for p in client.get("/api/produtos", headers=auth).json()["produtos"] if p["nome"] == self.nome)

    def caixa_e_unidade(self, fator=12, **extra):
        """O que a tela manda ao marcar 'vende caixa e unidade' — inclusive a conta
        antiga dela (quantidade = 600 x fator), que o backend não pode aceitar às cegas."""
        return dict(vende_por_unidade=True, confirmar_abertura=True, unidade_compra="CX",
                    quantidade_por_embalagem=fator, preco_embalagem=40, preco_unidade=3.8,
                    quantidade=600 * fator, preco_custo=round(2.74 / fator, 4),
                    codigo_barras=self.pacote, codigo_barras_unidade=self.lata, **extra)


def previa(client, auth, xml):
    r = client.post("/api/produtos/importar-xml/preview", headers=auth, content=xml)
    assert r.status_code == 200, r.text
    return r.json()


def confirmar(client, auth, nota, it, **extra):
    """Mesmo corpo que a tela de importação manda."""
    data = dict(produto_id=it["produto_id"], nome=it["nome"], codigo_barras=it["codigo_barras"],
                codigo_barras_unidade=it.get("codigo_barras_unidade", ""),
                unidade=it["unidade"], unidade_compra=it["unidade_compra"],
                quantidade_por_embalagem=it["quantidade_por_embalagem"], quantidade_xml=it["quantidade_xml"],
                quantidade=it["quantidade"], preco_custo=it["valor_unitario"],
                preco_venda=round(it["valor_unitario"] * 1.3, 2), unidade_xml=it["unidade_xml"],
                valor_unitario_xml=it["valor_unitario_xml"], ncm=it["ncm"], cfop=it["cfop"])
    data.update(extra)
    return client.post("/api/produtos/importar-xml/confirmar", headers=auth,
                       json={"documento": nota["numero"], "chave": nota["chave"], "itens": [data]})


def test_previa_custo_real_e_codigo_da_lata(client, auth):
    c = Caso()
    it = previa(client, auth, c.xml(ean=PACOTE, ean_trib=LATA))["itens"][0]
    assert it["quantidade"] == 600 and it["fator_entrada"] == 1
    assert it["valor_unitario_nota"] == 2.74
    # (1644,00 + 12,36 de outras despesas) / 600 = 2,7606 por lata.
    assert it["valor_unitario"] == 2.7606 and it["valor_unitario_xml"] == 2.7606
    assert it["codigo_barras"] == PACOTE and it["codigo_barras_unidade"] == LATA
    assert it["perguntar_embalagem"] is True
    assert "600 UN viram 600 UN" in it["mensagem_entrada"] and "despesas" in it["mensagem_entrada"]


def test_nota_em_un_com_caixa_e_unidade_nao_multiplica(client, auth):
    """Bug da 1.0.15: marcar 'é embalagem' na nota em UN virava 7.200 latas a R$ 0,23."""
    c = Caso()
    nota = previa(client, auth, c.xml())
    r = confirmar(client, auth, nota, nota["itens"][0], **c.caixa_e_unidade(nota_em_embalagem=False))
    assert r.status_code == 200, r.text
    p = c.produto(client, auth)
    assert p["estoque"] == 600 and p["preco_custo"] == 2.7606
    assert p["quantidade_por_embalagem"] == 12 and p["unidade_compra"] == "CX"
    assert (p["preco_embalagem"], p["preco_unidade"], p["vende_por_unidade"]) == (40, 3.8, 1)
    assert p["codigo_barras"] == c.pacote and p["codigo_barras_unidade"] == c.lata


def test_nota_em_un_sem_dizer_como_conta_tambem_nao_multiplica(client, auth):
    c = Caso()
    nota = previa(client, auth, c.xml())
    r = confirmar(client, auth, nota, nota["itens"][0], **c.caixa_e_unidade())
    assert r.status_code == 200, r.text
    assert c.produto(client, auth)["estoque"] == 600


def test_nota_em_caixas_multiplica_quando_o_operador_diz(client, auth):
    # 50 CX a R$ 32,88 = 600 latas a R$ 2,74.
    c = Caso()
    nota = previa(client, auth, c.xml(ucom="CX", qcom="50.0000", vun="32.88000000", extra=""))
    it = nota["itens"][0]
    assert it["fator_sugerido"] == 12  # qTrib 600 UN / qCom 50 CX
    r = confirmar(client, auth, nota, it, **c.caixa_e_unidade(nota_em_embalagem=True))
    assert r.status_code == 200, r.text
    p = c.produto(client, auth)
    assert p["estoque"] == 600 and p["preco_custo"] == 2.74


def test_custo_soma_frete_seguro_outras_ipi_st_e_tira_desconto(client, auth):
    imposto = ("<ICMS><ICMS10><orig>0</orig><CST>10</CST><vICMSST>6.00</vICMSST><vFCPST>1.00</vFCPST></ICMS10></ICMS>"
               "<IPI><cEnq>999</cEnq><IPITrib><CST>50</CST><vIPI>4.00</vIPI></IPITrib></IPI>")
    xml = Caso().xml(ean="SEM GTIN", ean_trib="SEM GTIN", qcom="10.0000", vun="10.00000000", vprod="100.00",
                     extra="<vFrete>10.00</vFrete><vSeg>2.00</vSeg><vDesc>5.00</vDesc><vOutro>3.00</vOutro>",
                     imposto=imposto)
    it = previa(client, auth, xml)["itens"][0]
    # 100 + 10 + 2 + 3 + 4 + 6 + 1 − 5 = 121 → 12,10 por unidade.
    assert it["valor_unitario"] == 12.1 and it["valor_unitario_nota"] == 10


def test_casa_produto_ja_cadastrado_pelo_codigo_da_lata(client, auth):
    c = Caso()
    r = client.post("/api/produtos", headers=auth, json={
        "nome": f"Kaiser lata {c.lata}", "codigo_barras": c.lata, "preco_venda": 4, "estoque": 5})
    assert r.status_code == 201, r.text
    pid = r.json()["produto"]["id"]
    nota = previa(client, auth, c.xml())
    it = nota["itens"][0]
    assert it["produto_id"] == pid and it["acao"] == "atualizar"
    r = confirmar(client, auth, nota, it)
    assert r.status_code == 200 and r.json()["criados"] == 0, r.text
    p = client.get(f"/api/produtos/{pid}", headers=auth).json()["produto"]
    assert p["estoque"] == 605 and p["preco_venda"] == 4


def test_produto_novo_guarda_os_dois_codigos(client, auth):
    c = Caso()
    nota = previa(client, auth, c.xml())
    r = confirmar(client, auth, nota, nota["itens"][0])
    assert r.status_code == 200, r.text
    p = c.produto(client, auth)
    assert p["codigo_barras"] == c.pacote and p["codigo_barras_unidade"] == c.lata
    assert p["vende_por_unidade"] == 0 and p["estoque"] == 600


def test_codigo_da_unidade_de_outro_produto_recusa_o_novo(client, auth):
    c, outro = Caso(), Caso()
    r = client.post("/api/produtos", headers=auth, json={
        "nome": outro.nome, "codigo_barras": outro.lata, "preco_venda": 4, "estoque": 1})
    assert r.status_code == 201
    nota = previa(client, auth, c.xml())
    r = confirmar(client, auth, nota, nota["itens"][0], codigo_barras_unidade=outro.lata)
    # Não cria duplicado nem joga estoque num produto que a prévia não mostrou.
    assert r.status_code == 409, r.text
    nomes = [p["nome"] for p in client.get("/api/produtos", headers=auth).json()["produtos"]]
    assert c.nome not in nomes
