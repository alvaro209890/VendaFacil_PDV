# Schemas oficiais NF-e/NFC-e

Baixado em **2026-11-12** do Portal Nacional da NF-e. Os ZIPs não são mantidos
neste repositório; foram extraídos somente arquivos `.xsd`, preservando as
referências relativas entre esquemas.

| Pacote | Conteúdo | Fonte oficial | SHA-256 do ZIP baixado |
|---|---|---|---|
| PL_010g v1.03, publicado em 26/10/2026 | `NFe/` e esquemas de eventos 110001/110300 em `Evento/` | [Portal Nacional — esquemas](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=BMPFMBoln3w%3D), [download do pacote](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=EQhOQMgipXY%3D) | `b329ecbe7e4c05a41bfbc1527f105defb7047328acfeada7c77e1666da485eaf` |
| Evento Cancelamento v1.01, atualizado em 21/12/2018 | Schema de `envEvento`/`evento` cancelamento em `Cancelamento/` | [Portal Nacional — esquemas](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=BMPFMBoln3w%3D), [download oficial do evento](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=0Yynu2Ck%20bM%3D) | `71ccd5fcc48f9604a2a8965146df45e3b73e96e87942ab3391be0d55cc0df718` |

Os caminhos incluídos pelos XSDs permanecem dentro de cada diretório de
pacote. `fiscal_xsd_utils.py` compila `NFe/nfe_v4.00.xsd` e
`Cancelamento/envEventoCancNFe_v1.00.xsd` com acesso à rede desativado.

Os testes de assinatura seguem o **MOC NF-e 7.0, seção 4.2.4**: XMLDSig com
RSA-SHA1, SHA-1 e C14N não exclusiva (`REC-xml-c14n-20010315`). O certificado
autoassinado, a chave e os dados fiscais usados nos testes são sintéticos e
existem somente sob `backend/tests/`.
