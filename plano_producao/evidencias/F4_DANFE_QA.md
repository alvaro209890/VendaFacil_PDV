# DANFE — conferência visual e funcional local

12/11/2026. Fonte: [Manual DANFE NFC-e/QR Code v6.0, março2025](https://www.nfe.fazenda.gov.br/PORTAl/exibirArquivo.aspx?AspxAutoDetectCookieSupport=1&conteudo=k%2FIuuaW4YiY%3D),
divisões I–VI. Fonte de dados da fixture: `backend/tests/fixtures/cupom_nfce.xml`.

`node --test frontend-tests/recibo-fiscal.test.mjs frontend-tests/recibo-xss.test.mjs`:
11 testes aprovados (F4_DANFE_GREEN.txt); antes, 3 regressões falhavam (F4_DANFE_RED.txt).
Build e lint com código0 (F4_DANFE_BUILD/LINT.txt).

Imagens `output/playwright/danfe-58.png` e `danfe-80.png` abertas e inspecionadas:
emitente da emissão, CNPJ/IE/endereço, código/descrição/quantidade/unidade/preços,
totais/pagamento, ambiente de homologação, consumidor, protocolo/horário/chave,
URL de consulta e tributos são legíveis e ficam dentro da largura do papel.
Texto vindo do XML é escapado; teste de injeção incluído. Sem valor de tributos
no XML, o cupom não afirma ter usado tabela IBPT.

QR mantém o caminho já validado de PNG/Base64 e medidas40/50mm; sua leitura a
partir do PDF e a impressão física têm portões próprios na Fase6/B7. Estas duas
imagens exercitam os novos campos textuais, sem alegar leitura de QR ou papel real.
