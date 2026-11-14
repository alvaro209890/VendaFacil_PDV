from xml.etree import ElementTree as ET
import fiscal_direto
import fiscal
from test_fiscal_direto import _cfg
from test_embalagem import criar
from test_embalagem_vendas import vender


def test_t10_linha_comercial_e_tributavel_sem_transmitir(client,auth):
    p=criar(client,auth,ncm='24031900',cfop='5102')
    r=vender(client,auth,p,[{'quantidade':1,'modo_venda':'embalagem'},{'quantidade':1}])
    assert r.status_code==201,r.text
    venda=client.get(f"/api/vendas/{r.json()['venda']['id']}",headers=auth).json()['venda']
    # Alterar produto depois não muda a unidade comercial histórica.
    client.put(f"/api/produtos/{p['id']}",headers=auth,json={'unidade_compra':'FARDO','quantidade_por_embalagem':30})
    doc=fiscal_direto.montar_documento(venda,_cfg(),'65',serie=1,numero=1)
    raiz=ET.fromstring(doc.xml); ns={'n':'http://www.portalfiscal.inf.br/nfe'}
    produtos=raiz.findall('.//n:det/n:prod',ns)
    def campo(i,k): return produtos[i].findtext('n:'+k,namespaces=ns)
    assert campo(0,'qCom')=='1.0000' and campo(0,'uCom')=='CART' and campo(0,'vUnCom')=='20.0000'
    assert campo(1,'qCom')=='1.0000' and campo(1,'uCom')=='UN' and campo(1,'vUnCom')=='2.0000'
    assert campo(0,'qTrib')=='20.0000' and campo(0,'uTrib')=='UN' and campo(0,'vUnTrib')=='1.0000'
    assert raiz.findtext('.//n:tpAmb',namespaces=ns)=='2'
    payload=fiscal.montar_payload(venda,_cfg())
    assert payload['items'][0]['unidade_comercial']=='CART'
