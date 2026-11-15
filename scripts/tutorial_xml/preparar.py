"""Dados sintéticos, somente na API descartável 3121 usada para gravar o tutorial."""
import json
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'output/playwright/tutorial-xml'
OUT.mkdir(parents=True, exist_ok=True)
def pedir(path, data, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request('http://127.0.0.1:3121'+path, data=json.dumps(data).encode(), headers=headers)
    return json.load(urllib.request.urlopen(req))

user={'usuario':'tutorial-xml','nome':'Loja de demonstração','senha':'Tutorial-xml-25'}
r=pedir('/api/auth/registro',user)
def gtin(n):
    base=f'789000000{n:03d}'
    return base+str((10-sum(int(c)*(3 if i%2 else 1) for i,c in enumerate(base))%10)%10)
codigos=[gtin(n) for n in (251,252,253,254)]
pedir('/api/produtos',{'nome':'Bebida láctea 200 ml','codigo_barras':codigos[0],'estoque':54,'unidade':'UN','preco_custo':1.59,'preco_venda':2.07},r['token'])
xml=f'''<NFe><infNFe><ide><mod>55</mod><nNF>125</nNF></ide><emit><xNome>Fornecedor de demonstração</xNome></emit>
<det nItem="1"><prod><cEAN>{codigos[0]}</cEAN><xProd>Bebida láctea 200 ml</xProd><uCom>UN</uCom><qCom>54</qCom><vUnCom>1.59</vUnCom><vProd>85.86</vProd></prod></det>
<det nItem="2"><prod><cEAN>{codigos[1]}</cEAN><xProd>CARTEIRA Palheiro tradicional</xProd><uCom>UN</uCom><qCom>2</qCom><vUnCom>10</vUnCom><vProd>20</vProd></prod></det>
<det nItem="3"><prod><cEAN>{codigos[2]}</cEAN><xProd>CX Cerveja lata 350 ml</xProd><uCom>CX</uCom><qCom>2</qCom><vUnCom>24</vUnCom><vProd>48</vProd><uTrib>UN</uTrib><qTrib>24</qTrib><cEANTrib>{codigos[3]}</cEANTrib></prod></det>
</infNFe></NFe>'''
(OUT/'nota-demonstracao.xml').write_text(xml,encoding='utf8')
print('Banco descartável preparado; XML com três produtos de demonstração.')
