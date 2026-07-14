import sys
from pathlib import Path
import base64
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
import fiscal_direto


def _cfg():
    return {
        "cnpj": "12345678000195",
        "inscricao_estadual": "00130000019",
        "regime_tributario": "1",
        "logradouro": "Rua Teste",
        "numero": "100",
        "bairro": "Centro",
        "municipio": "Cuiaba",
        "codigo_municipio": "5103403",
        "uf": "MT",
        "cep": "78000000",
        "ambiente": "homologacao",
        "csc": "CSCDEHOMOLOGACAO",
        "csc_id": "000001",
        "serie_nfce": 1,
        "proximo_numero_nfce": 1,
        "serie_nfe": 1,
        "proximo_numero_nfe": 1,
    }


def _venda(produto):
    return {
        "id": 1,
        "total": 10,
        "desconto": 0,
        "forma_pagamento": "dinheiro",
        "itens": [{
            "produto_id": produto["id"],
            "nome_produto": produto["nome"],
            "quantidade": 1,
            "preco_unitario": 10,
            "subtotal": 10,
        }],
    }


def test_monta_xml_nfce_65(client, auth):
    r = client.post("/api/produtos", headers=auth, json={
        "nome": "Refri Fiscal", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    })
    produto = r.json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", cpf_consumidor="12345678909", serie=1, numero=1)
    assert "<mod>65</mod>" in doc.xml
    assert doc.chave.startswith("51")
    # QR Code 2.00 (pipe-delimitado), não o formato 1.00 antigo.
    assert doc.qrcode_url and f"?p={doc.chave}|2|" in doc.qrcode_url


def _venda_cartao(produto, pagamento):
    v = _venda(produto)
    v["forma_pagamento"] = "credito"
    v["pagamento_detalhe"] = pagamento
    return v


def test_pag_dinheiro_nao_tem_grupo_card(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Pao Frances", "preco_venda": 10, "estoque": 5,
        "ncm": "19059090", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)
    assert "<tPag>01</tPag>" in doc.xml
    assert "<card>" not in doc.xml


def test_pag_cartao_integrado_emite_card_tpintegra1(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Leite Card", "preco_venda": 10, "estoque": 5,
        "ncm": "04012010", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    import json as _json
    pagamento = _json.dumps({
        "tipo_integracao": "1", "adquirente_cnpj": "10573521000191",
        "bandeira": "master", "autorizacao": "123456",
    })
    doc = fiscal_direto.montar_documento(_venda_cartao(produto, pagamento), _cfg(), "65", serie=1, numero=1)
    assert "<tPag>03</tPag>" in doc.xml
    assert "<card><tpIntegra>1</tpIntegra>" in doc.xml
    assert "<CNPJ>10573521000191</CNPJ>" in doc.xml
    assert "<tBand>02</tBand>" in doc.xml          # master → 02
    assert "<cAut>123456</cAut>" in doc.xml


def test_pag_cartao_sem_dados_cai_para_nao_integrado(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Cafe Manual", "preco_venda": 10, "estoque": 5,
        "ncm": "09011110", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    # cartão manual: sem CNPJ/cAut → tpIntegra=2 (evita rejeição 392)
    doc = fiscal_direto.montar_documento(_venda_cartao(produto, None), _cfg(), "65", serie=1, numero=1)
    assert "<card><tpIntegra>2</tpIntegra></card>" in doc.xml
    assert "<cAut>" not in doc.xml


def test_pag_pix_integrado_usa_card_sem_tband(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Suco Pix", "preco_venda": 10, "estoque": 5,
        "ncm": "20098990", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    import json as _json
    v = _venda(produto)
    v["forma_pagamento"] = "pix"
    v["pagamento_detalhe"] = _json.dumps({
        "tipo_integracao": "1", "adquirente_cnpj": "10573521000191",
        "autorizacao": "E10573521202406011200abc",  # endToEndId
    })
    doc = fiscal_direto.montar_documento(v, _cfg(), "65", serie=1, numero=1)
    assert "<tPag>17</tPag>" in doc.xml
    assert "<card><tpIntegra>1</tpIntegra>" in doc.xml
    assert "<cAut>E10573521202406011200abc</cAut>" in doc.xml
    assert "<tBand>" not in doc.xml          # PIX não tem bandeira de cartão


def test_pag_cartao_integrado_incompleto_nao_usa_tpintegra1(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Acucar Sem CNPJ", "preco_venda": 10, "estoque": 5,
        "ncm": "17019900", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    import json as _json
    # tem autorização mas falta o CNPJ da credenciadora → não pode tpIntegra=1
    pagamento = _json.dumps({"tipo_integracao": "1", "autorizacao": "999", "bandeira": "visa"})
    doc = fiscal_direto.montar_documento(_venda_cartao(produto, pagamento), _cfg(), "65", serie=1, numero=1)
    assert "<tpIntegra>2</tpIntegra>" in doc.xml
    assert "<cAut>" not in doc.xml


def test_monta_xml_nfce_produto_st_e_monofasico_no_grupo_correto(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Cerveja Fiscal", "preco_venda": 10, "estoque": 5,
        "ncm": "22030000", "cfop": "5405", "cst_csosn": "500", "unidade": "UN",
        "cst_pis": "04", "cst_cofins": "06", "cest": "0300700",
    }).json()["produto"]

    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)

    assert "<ICMSSN500>" in doc.xml
    assert "<ICMSSN102>" not in doc.xml
    assert "<CSOSN>500</CSOSN>" in doc.xml
    assert "<PISNT><CST>04</CST></PISNT>" in doc.xml
    assert "<COFINSNT><CST>06</CST></COFINSNT>" in doc.xml
    assert "<vPIS>0.00</vPIS>" in doc.xml
    assert "<vCOFINS>0.00</vCOFINS>" in doc.xml


def test_monta_xml_nfce_rejeita_csosn_de_substituto_para_revenda(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Produto ST Errado", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5405", "cst_csosn": "201", "unidade": "UN",
        "cest": "0300700",
    }).json()["produto"]

    import pytest
    with pytest.raises(fiscal_direto.FiscalDiretoError, match="use CSOSN 500"):
        fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)


def test_monta_xml_nfe_55_para_empresa(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Arroz Fiscal", "preco_venda": 10, "estoque": 5,
        "ncm": "10063021", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    dest = {
        "nome": "Empresa Teste LTDA", "documento": "11222333000181",
        "logradouro": "Av Cliente", "numero": "10", "bairro": "Centro",
        "municipio": "Cuiaba", "codigo_municipio": "5103403", "uf": "MT",
        "cep": "78000000", "indicador_ie": "9", "inscricao_estadual": "",
    }
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "55", destinatario=dest, serie=1, numero=1)
    assert "<mod>55</mod>" in doc.xml
    assert "<CNPJ>11222333000181</CNPJ>" in doc.xml


def test_resp_tec_desligado_por_padrao_nao_aparece(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Sem RespTec", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)
    assert "infRespTec" not in doc.xml


def test_resp_tec_ligado_sem_csrt_inclui_contato(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Com RespTec", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    cfg = {**_cfg(), "resp_tec_habilitado": 1, "resp_tec_cnpj": "11222333000181",
           "resp_tec_contato": "Suporte VendaFacil", "resp_tec_email": "suporte@vf.com",
           "resp_tec_fone": "6535551234"}
    doc = fiscal_direto.montar_documento(_venda(produto), cfg, "65", serie=1, numero=1)
    assert "<infRespTec>" in doc.xml
    assert "<CNPJ>11222333000181</CNPJ>" in doc.xml
    assert "idCSRT" not in doc.xml  # sem CSRT cadastrado, não envia hash


def test_resp_tec_com_csrt_inclui_hash(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "RespTec CSRT", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    cfg = {**_cfg(), "resp_tec_habilitado": 1, "resp_tec_cnpj": "11222333000181",
           "resp_tec_csrt": "G8L88UN1234567890ABCDEF", "resp_tec_id_csrt": "01"}
    doc = fiscal_direto.montar_documento(_venda(produto), cfg, "65", serie=1, numero=1)
    assert "<idCSRT>01</idCSRT>" in doc.xml
    # hashCSRT confere com Base64(SHA1(CSRT+chave))
    esperado = fiscal_direto._hash_csrt("G8L88UN1234567890ABCDEF", doc.chave)
    assert f"<hashCSRT>{esperado}</hashCSRT>" in doc.xml


def test_export_xml_por_nota_e_zip(client, auth):
    import io as _io, zipfile as _zip
    # cria uma nota autorizada com XML diretamente no banco
    db.criar_nota({
        "venda_id": 99001, "user_id": 1, "ref": "exp-65-1", "modelo": "65",
        "numero": 1, "serie": 1, "ambiente": "homologacao", "status": "autorizada",
        "chave": "51000112345678000195650010000000011000000015",
        "xml_autorizado": "<nfeProc>EXPORT-OK</nfeProc>",
        "criado_em": "2030-01-10T10:00:00", "atualizado_em": "2030-01-10T10:00:00",
    })
    nota = db.get_nota_por_venda(99001, "65")

    # download por nota
    r = client.get(f"/api/fiscal/nfce/nota/{nota['id']}/xml", headers=auth)
    assert r.status_code == 200
    assert "EXPORT-OK" in r.text
    assert "attachment" in r.headers.get("content-disposition", "")

    # export ZIP do período
    z = client.get("/api/fiscal/nfce/export/xml?inicio=2030-01-01&fim=2030-01-31", headers=auth)
    assert z.status_code == 200
    zf = _zip.ZipFile(_io.BytesIO(z.content))
    assert any("EXPORT-OK" in zf.read(n).decode() for n in zf.namelist())

    # período sem notas → 404
    vazio = client.get("/api/fiscal/nfce/export/xml?inicio=2031-01-01&fim=2031-01-31", headers=auth)
    assert vazio.status_code == 404


def test_numeracao_separada_nfce_nfe():
    db.salvar_config_fiscal({"serie_nfce": 7, "proximo_numero_nfce": 11, "serie_nfe": 3, "proximo_numero_nfe": 21}, "agora")
    assert db.consumir_numero_fiscal("65") == (7, 11)
    assert db.consumir_numero_fiscal("55") == (3, 21)


def test_assina_xml_com_a1_pkcs12_sintetico():
    import pytest
    # Dependências de assinatura só são instaladas no build Windows
    # (requirements-build.txt). Sem elas, o teste é irrelevante neste ambiente.
    pytest.importorskip("cryptography")
    pytest.importorskip("signxml")
    pytest.importorskip("lxml")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE A1")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(
        b"teste",
        key,
        cert,
        None,
        serialization.BestAvailableEncryption(b"1234"),
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        '<infNFe Id="NFe51000112345678000195650010000000011000000015" versao="4.00">'
        "<ide><cUF>51</cUF></ide>"
        "</infNFe></NFe>"
    )

    assinado = fiscal_direto.assinar_xml(xml, {
        "certificado_a1_b64": base64.b64encode(pfx).decode(),
        "certificado_senha": "1234",
    })

    assert "<ds:Signature" in assinado or "<Signature" in assinado
    assert "rsa-sha1" in assinado
    # NF-e exige C14N não-exclusiva (REC-xml-c14n-20010315); o default do signxml
    # (xml-exc-c14n#) seria rejeitado pela SEFAZ.
    assert "REC-xml-c14n-20010315" in assinado
    assert "xml-exc-c14n" not in assinado


def test_normaliza_retorno_sefaz_autorizado_com_xml_proc():
    xml_assinado = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe51000112345678000195650010000000011000000015" versao="4.00" /></NFe>'
    )
    retorno = (
        '<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        "<cStat>104</cStat><xMotivo>Lote processado</xMotivo>"
        '<protNFe versao="4.00"><infProt>'
        "<chNFe>51000112345678000195650010000000011000000015</chNFe>"
        "<nProt>151000000000001</nProt><cStat>100</cStat>"
        "<xMotivo>Autorizado o uso da NF-e</xMotivo>"
        "</infProt></protNFe></retEnviNFe>"
    )

    dados = fiscal_direto.normalizar_retorno_sefaz(retorno, xml_assinado, 200)

    assert dados["status"] == "autorizada"
    assert dados["protocolo"] == "151000000000001"
    assert "nfeProc" in dados["xml_autorizado"]
    assert "protNFe" in dados["xml_autorizado"]


def test_normaliza_retorno_sefaz_rejeitado():
    retorno = (
        '<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        "<cStat>104</cStat><xMotivo>Lote processado</xMotivo>"
        '<protNFe versao="4.00"><infProt>'
        "<cStat>539</cStat><xMotivo>Duplicidade de NF-e</xMotivo>"
        "</infProt></protNFe></retEnviNFe>"
    )

    dados = fiscal_direto.normalizar_retorno_sefaz(retorno, None, 200)

    assert dados["status"] == "rejeitada"
    assert dados["motivo_rejeicao"] == "Duplicidade de NF-e"


def test_monta_xml_evento_cancelamento():
    nota = {"chave": "51000112345678000195650010000000011000000015", "protocolo": "151000000000001"}
    xml = fiscal_direto.montar_cancelamento_xml(nota, _cfg(), "Erro de emissao da venda teste")

    assert "<tpEvento>110111</tpEvento>" in xml
    assert "<nProt>151000000000001</nProt>" in xml
    assert "ID1101115100011234567800019565001000000001100000001501" in xml


def test_normaliza_retorno_evento_cancelado():
    retorno = (
        '<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
        '<retEvento versao="1.00"><infEvento>'
        "<cStat>135</cStat><xMotivo>Evento registrado e vinculado a NF-e</xMotivo>"
        "<nProt>151000000000009</nProt>"
        "</infEvento></retEvento></retEnvEvento>"
    )

    dados = fiscal_direto.normalizar_retorno_evento(retorno, 200)

    assert dados["status"] == "cancelada"
    assert dados["protocolo"] == "151000000000009"


def test_desconto_rateado_fecha_total(client, auth):
    p1 = client.post("/api/produtos", headers=auth, json={
        "nome": "Item A", "preco_venda": 10, "estoque": 9,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    p2 = client.post("/api/produtos", headers=auth, json={
        "nome": "Item B", "preco_venda": 5, "estoque": 9,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    venda = {
        "id": 1, "total": 12.0, "desconto": 3.0, "forma_pagamento": "dinheiro",
        "itens": [
            {"produto_id": p1["id"], "nome_produto": "Item A", "quantidade": 1, "preco_unitario": 10, "subtotal": 10},
            {"produto_id": p2["id"], "nome_produto": "Item B", "quantidade": 1, "preco_unitario": 5, "subtotal": 5},
        ],
    }
    doc = fiscal_direto.montar_documento(venda, _cfg(), "65", serie=1, numero=1)
    # Totais fecham: vProd 15,00 − vDesc 3,00 = vNF 12,00 (senão a SEFAZ rejeita).
    assert "<vProd>15.00</vProd>" in doc.xml
    assert "<vDesc>3.00</vDesc>" in doc.xml          # total (ICMSTot)
    assert "<vNF>12.00</vNF>" in doc.xml
    assert "<vPag>12.00</vPag>" in doc.xml
    # Rateio por item: 2,00 no item de R$10 e 1,00 no de R$5 (soma = desconto).
    assert "<vDesc>2.00</vDesc>" in doc.xml
    assert "<vDesc>1.00</vDesc>" in doc.xml


def test_qrcode_online_padrao_2(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "QR Online", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    url = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1).qrcode_url
    assert "?p=" in url
    assert "&" not in url                 # QR Code 2.00 usa "|", nunca "&"
    assert "nVersao=100" not in url and "cDest=" not in url and "digVal=" not in url
    # URL de consulta OFICIAL de MT: http (sem TLS) e sem "www" na homologação.
    assert url.startswith("http://homologacao.sefaz.mt.gov.br/nfce/consultanfce?p=")
    campos = url.split("?p=", 1)[1].split("|")
    assert campos[1] == "2"               # versão do QR Code
    assert campos[2] == "2"               # tpAmb = homologação
    assert campos[3] == "1"               # idCSC SEM zeros à esquerda (manual QR Code)
    assert len(campos[4]) == 40 and campos[4].isalnum()   # SHA-1 hex


def test_cnf_aleatorio_diferente_do_nnf(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "cNF aleatorio", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)
    cnf = doc.chave[35:43]
    assert cnf != "00000001"              # nNF=1 → cNF não pode ser igual (MOC)
    assert len(cnf) == 8 and cnf.isdigit()


def test_contingencia_offline_tpemis9_sem_supl(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Contingencia", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1,
                                         tp_emis="9", dh_cont="2026-06-05T12:00:00-04:00")
    assert "<tpEmis>9</tpEmis>" in doc.xml
    assert "<dhCont>" in doc.xml and "<xJust>" in doc.xml
    assert "infNFeSupl" not in doc.xml    # o QR offline é inserido após a assinatura
    assert doc.chave[34] == "9"           # posição do tpEmis dentro da chave de acesso


def test_inserir_qrcode_offline_insere_supl_e_qr_offline():
    import pytest
    pytest.importorskip("lxml")
    chave = "51000112345678000195650010000000011000000015"
    xml_assinado = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        f'<infNFe Id="NFe{chave}" versao="4.00"><ide><cUF>51</cUF></ide></infNFe>'
        '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo>'
        '<Reference><DigestValue>YWJjZGVm</DigestValue></Reference>'
        '</SignedInfo></Signature></NFe>'
    )
    xml_final, qr = fiscal_direto.inserir_qrcode_offline(
        xml_assinado, _cfg(), chave, "2026-06-05T12:00:00-04:00", 10.0, "homologacao")
    # Grupo suplementar entra na ordem correta: infNFe, infNFeSupl, Signature.
    from xml.etree import ElementTree as ET
    filhos = [el.tag.split("}")[-1] for el in ET.fromstring(xml_final.encode("utf-8"))]
    assert filhos == ["infNFe", "infNFeSupl", "Signature"]
    # QR 2.0 offline (manual do DANFE/QR Code): chave|2|tpAmb|DIA|vNF|digValHex|idCSC|hash
    # — só o DIA da emissão (2 dígitos), sem vICMS, e o DigestValue é o TEXTO
    # Base64 convertido a hexadecimal (não os bytes decodificados).
    p = qr.split("?p=", 1)[1].split("|")
    assert len(p) == 8
    assert p[0] == chave and p[1] == "2" and p[2] == "2"
    assert p[3] == "05"                                  # dia de 2026-06-05
    assert p[4] == "10.00"
    assert p[5] == "YWJjZGVm".encode("utf-8").hex()      # hex do texto Base64
    assert p[6] == "1" and len(p[7]) == 40               # idCSC sem zeros + SHA-1


def test_contingencia_assina_e_insere_qr_offline(client, auth):
    import pytest
    pytest.importorskip("cryptography")
    pytest.importorskip("signxml")
    pytest.importorskip("lxml")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE A1")])
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(b"t", key, cert, None, BestAvailableEncryption(b"1234"))
    cfg = {**_cfg(), "certificado_a1_b64": base64.b64encode(pfx).decode(), "certificado_senha": "1234"}

    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Conting Full", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), cfg, "65", serie=1, numero=1,
                                         tp_emis="9", dh_cont="2026-06-05T12:00:00-04:00")
    assinado = fiscal_direto.assinar_xml(doc.xml, cfg)
    xml_final, qr = fiscal_direto.inserir_qrcode_offline(
        assinado, cfg, doc.chave, doc.dh_emi, doc.v_nf, "homologacao")

    from xml.etree import ElementTree as ET
    filhos = [el.tag.split("}")[-1] for el in ET.fromstring(xml_final.encode("utf-8"))]
    assert filhos == ["infNFe", "infNFeSupl", "Signature"]   # ordem exigida pelo XSD
    campos = qr.split("?p=", 1)[1].split("|")
    assert len(campos) == 8 and campos[1] == "2"             # QR offline 2.00: 8 campos
    assert campos[5]                                          # digVal(hex) veio da assinatura real


# ───────────────────────── Correções legislação MT (2026-07) ─────────────────────────

def _pfx_sintetico(senha=b"1234"):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE A1")])
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(b"t", key, cert, None,
                                                BestAvailableEncryption(senha))
    return base64.b64encode(pfx).decode(), key


def _produto_simples(client, auth, nome="Produto MT"):
    return client.post("/api/produtos", headers=auth, json={
        "nome": nome, "preco_venda": 10, "estoque": 50,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]


def test_ws_mt_usa_nomes_oficiais_dos_servicos():
    # Caminho é case-sensitive: "NfeAutorizacao4" (não NFe...), consulta é
    # "NfeConsulta4" e evento é "RecepcaoEvento4" — tanto na NFC-e quanto na NF-e.
    ws = fiscal_direto.WS
    assert ws[("65", "producao", "autorizacao")].endswith("/nfcews/services/NfeAutorizacao4")
    assert ws[("65", "producao", "consulta")].endswith("/nfcews/services/NfeConsulta4")
    assert ws[("65", "producao", "evento")].endswith("/nfcews/services/RecepcaoEvento4")
    assert ws[("55", "producao", "autorizacao")].endswith("/nfews/v2/services/NfeAutorizacao4")
    assert ws[("55", "homologacao", "consulta")].endswith("/nfews/v2/services/NfeConsulta4")
    assert "NFeConsultaProtocolo4" not in str(ws)
    assert "NFeRecepcaoEvento4" not in str(ws)
    # QR de consulta oficial de MT é http:// e produção tem "www".
    assert fiscal_direto.URL_QR_NFCE["producao"] == "http://www.sefaz.mt.gov.br/nfce/consultanfce"
    assert fiscal_direto.URL_QR_NFCE["homologacao"] == "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce"


def test_soap_envelope_usa_namespace_do_wsdl_e_action():
    body, headers = fiscal_direto.montar_soap("autorizacao", "<enviNFe>x</enviNFe>")
    texto = body.decode("utf-8")
    assert '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4">' in texto
    assert 'action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"' \
        in headers["Content-Type"]

    body, headers = fiscal_direto.montar_soap("consulta", "<consSitNFe>x</consSitNFe>")
    assert 'wsdl/NFeConsultaProtocolo4"' in body.decode()
    assert "/nfeConsultaNF" in headers["Content-Type"]

    body, headers = fiscal_direto.montar_soap("evento", "<envEvento>x</envEvento>")
    assert 'wsdl/NFeRecepcaoEvento4"' in body.decode()
    assert "/nfeRecepcaoEvento" in headers["Content-Type"]


def test_conteudo_interno_do_soap_leva_namespace_da_nfe():
    xml = '<?xml version="1.0"?><NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe/></NFe>'
    import unittest.mock as mock
    with mock.patch.object(fiscal_direto, "_post_soap", return_value={"status_code": 200, "texto": ""}) as m:
        fiscal_direto.transmitir_autorizacao("65", xml, _cfg())
    conteudo = m.call_args[0][2]
    assert conteudo.startswith('<enviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">')
    assert "<indSinc>1</indSinc>" in conteudo


def test_pag_fiado_usa_99_com_xpag_e_indpag_prazo(client, auth):
    produto = _produto_simples(client, auth, "Fiado MT")
    v = _venda(produto)
    v["forma_pagamento"] = "fiado"
    doc = fiscal_direto.montar_documento(v, _cfg(), "65", serie=1, numero=1)
    assert "<indPag>1</indPag>" in doc.xml            # a prazo
    assert "<tPag>99</tPag>" in doc.xml
    assert "<xPag>Crediario da loja (fiado)</xPag>" in doc.xml   # xPag obrigatório c/ tPag 99


def test_pag_pix_estatico_usa_tpag_20(client, auth):
    # PIX manual (QR fixo da chave da loja) é PIX ESTÁTICO → tPag 20 (IT 2024.002).
    produto = _produto_simples(client, auth, "Pix Estatico")
    v = _venda(produto)
    v["forma_pagamento"] = "pix"
    doc = fiscal_direto.montar_documento(v, _cfg(), "65", serie=1, numero=1)
    assert "<tPag>20</tPag>" in doc.xml
    assert "<card>" not in doc.xml
    assert "<indPag>0</indPag>" in doc.xml


def test_crt_2_e_3_sao_recusados_com_mensagem_clara(client, auth):
    import pytest
    produto = _produto_simples(client, auth, "CRT errado")
    for crt in ("2", "3"):
        with pytest.raises(fiscal_direto.FiscalDiretoError, match="CRT"):
            fiscal_direto.montar_documento(_venda(produto), {**_cfg(), "regime_tributario": crt},
                                           "65", serie=1, numero=1)


def test_cpf_consumidor_invalido_e_recusado_antes_da_sefaz(client, auth):
    import pytest
    produto = _produto_simples(client, auth, "CPF invalido")
    with pytest.raises(fiscal_direto.FiscalDiretoError, match="CPF"):
        fiscal_direto.montar_documento(_venda(produto), _cfg(), "65",
                                       cpf_consumidor="12345678900", serie=1, numero=1)


def test_cnpj_emitente_invalido_e_recusado(client, auth):
    import pytest
    produto = _produto_simples(client, auth, "CNPJ emit invalido")
    with pytest.raises(fiscal_direto.FiscalDiretoError, match="CNPJ do emitente"):
        fiscal_direto.montar_documento(_venda(produto), {**_cfg(), "cnpj": "12345678000190"},
                                       "65", serie=1, numero=1)


def test_nfce_acima_de_10k_exige_consumidor_identificado(client, auth):
    import pytest
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Caro", "preco_venda": 10001, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    v = {
        "id": 1, "total": 10001, "desconto": 0, "forma_pagamento": "dinheiro",
        "itens": [{"produto_id": produto["id"], "nome_produto": "Caro",
                   "quantidade": 1, "preco_unitario": 10001, "subtotal": 10001}],
    }
    with pytest.raises(fiscal_direto.FiscalDiretoError, match="10.000"):
        fiscal_direto.montar_documento(v, _cfg(), "65", serie=1, numero=1)
    # identificando o consumidor, passa
    doc = fiscal_direto.montar_documento(v, _cfg(), "65", cpf_consumidor="12345678909",
                                         serie=1, numero=1)
    assert "<CPF>12345678909</CPF>" in doc.xml


def test_produto_st_sem_cest_e_recusado(client, auth):
    import pytest
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Cerveja sem CEST", "preco_venda": 10, "estoque": 5,
        "ncm": "22030000", "cfop": "5405", "cst_csosn": "500", "unidade": "UN",
    }).json()["produto"]
    with pytest.raises(fiscal_direto.FiscalDiretoError, match="CEST"):
        fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)


def test_nfe_55_ie_do_destinatario_coerente_com_indiedest(client, auth):
    produto = _produto_simples(client, auth, "IE coerente")
    dest = {
        "nome": "Empresa IE LTDA", "documento": "11222333000181",
        "logradouro": "Av X", "numero": "1", "bairro": "Centro",
        "municipio": "Cuiaba", "codigo_municipio": "5103403", "uf": "MT",
        "cep": "78000000", "indicador_ie": "", "inscricao_estadual": "0013000001-9",
    }
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "55",
                                         destinatario=dest, serie=1, numero=1)
    # IE preenchida sem indicador → assume contribuinte (1) e emite a IE
    assert "<indIEDest>1</indIEDest>" in doc.xml
    assert "<IE>00130000019</IE>" in doc.xml

    dest2 = {**dest, "indicador_ie": "9"}
    doc2 = fiscal_direto.montar_documento(_venda(produto), _cfg(), "55",
                                          destinatario=dest2, serie=1, numero=1)
    # não-contribuinte (9) NUNCA leva a tag IE (rejeição na SEFAZ)
    assert "<indIEDest>9</indIEDest>" in doc2.xml
    assert doc2.xml.count("<IE>") == 1        # só a IE do emitente


def test_nfe_55_interestadual_exige_cfop_6xxx(client, auth):
    import pytest
    produto = _produto_simples(client, auth, "Interestadual")
    dest = {
        "nome": "Cliente SP", "documento": "11222333000181",
        "logradouro": "Av SP", "numero": "1", "bairro": "Centro",
        "municipio": "Sao Paulo", "codigo_municipio": "3550308", "uf": "SP",
        "cep": "01000000", "indicador_ie": "9", "inscricao_estadual": "",
    }
    with pytest.raises(fiscal_direto.FiscalDiretoError, match="6xxx"):
        fiscal_direto.montar_documento(_venda(produto), _cfg(), "55",
                                       destinatario=dest, serie=1, numero=1)


def test_chave_de_acesso_usa_mesmo_mes_do_dhemi(client, auth):
    produto = _produto_simples(client, auth, "AAMM chave")
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)
    # AAMM (posições 2-6 da chave) tem que casar com o dhEmi (Rejeição 615)
    assert doc.chave[2:6] == doc.dh_emi[2:4] + doc.dh_emi[5:7]


def test_xprod_longo_e_truncado_em_120(client, auth):
    produto = _produto_simples(client, auth, "Nome Sanitizado")
    v = _venda(produto)
    # nome com espaços nas pontas/duplicados (Rejeição 588) e acima de 120 chars
    v["itens"][0]["nome_produto"] = "  Cafe   Especial  " + "X" * 150
    doc = fiscal_direto.montar_documento(v, _cfg(), "65", serie=1, numero=1)
    esperado = ("Cafe Especial " + "X" * 150)[:120]
    assert f"<xProd>{esperado}</xProd>" in doc.xml
    assert "X" * 121 not in doc.xml


def test_lei_12741_vtottrib_com_percentual_ibpt(client, auth):
    produto = _produto_simples(client, auth, "IBPT")
    cfg = {**_cfg(), "ibpt_percentual": 20.5}
    doc = fiscal_direto.montar_documento(_venda(produto), cfg, "65", serie=1, numero=1)
    # 20,5% de R$ 10,00 = R$ 2,05 no item e no total + texto da Lei 12.741
    assert "<vTotTrib>2.05</vTotTrib>" in doc.xml
    assert "Trib aprox R$ 2.05 (20.50%)" in doc.xml
    # sem percentual configurado, não inventa valor
    doc2 = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", serie=1, numero=1)
    assert "<vTotTrib>" not in doc2.xml


def test_qrcode_3_online_dispensa_csc(client, auth):
    produto = _produto_simples(client, auth, "QR3 online")
    cfg = {**_cfg(), "qrcode_versao": "3", "csc": "", "csc_id": ""}
    doc = fiscal_direto.montar_documento(_venda(produto), cfg, "65", serie=1, numero=1)
    assert doc.qrcode_url.endswith(f"?p={doc.chave}|3|2")


def test_qrcode_3_offline_assina_com_a1():
    import pytest
    pytest.importorskip("cryptography")
    pytest.importorskip("lxml")
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    b64, key = _pfx_sintetico()
    cfg = {**_cfg(), "qrcode_versao": "3",
           "certificado_a1_b64": b64, "certificado_senha": "1234"}
    chave = "51000112345678000195650010000000019000000015"
    xml_assinado = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        f'<infNFe Id="NFe{chave}" versao="4.00">'
        '<dest><CPF>12345678909</CPF></dest></infNFe>'
        '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#"><SignedInfo>'
        '<Reference><DigestValue>YWJjZGVm</DigestValue></Reference>'
        '</SignedInfo></Signature></NFe>'
    )
    _, qr = fiscal_direto.inserir_qrcode_offline(
        xml_assinado, cfg, chave, "2026-06-05T12:00:00-04:00", 10.0, "homologacao")
    p = qr.split("?p=", 1)[1].split("|")
    # chave|3|tpAmb|dia|vNF|tpIdDest|cDest|assinatura
    assert p[:7] == [chave, "3", "2", "05", "10.00", "2", "12345678909"]
    assinatura = base64.b64decode(p[7])
    key.public_key().verify(assinatura, "|".join(p[:7]).encode("utf-8"),
                            padding.PKCS1v15(), hashes.SHA1())  # não levanta = válida
