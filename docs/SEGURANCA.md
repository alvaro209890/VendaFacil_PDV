# Segurança do PDV

O que o caixa da mercearia protege, o que fica de fora de propósito e o que fazer se o computador sair da loja. Escolhas de 2026-11-10.

## O que protege

- Rota `/api/*` sem token válido responde 401. Abertas de propósito: login, registro do primeiro usuário, ativação da licença e o heartbeat do executável.
- Depois do primeiro usuário, outro registro só entra com quem já está autenticado.
- Cinco senhas erradas no login local esperam 30 s, e a espera cresce até 15 min. Não trava para sempre.
- CORS só aceita `127.0.0.1` e `localhost` na porta do PDV e na 5173 do Vite.
- O executável não publica `/docs` nem `/openapi.json`.
- Leitura da configuração fiscal e da maquininha não devolve CSC, senha do certificado, arquivo A1 nem token. O log troca esses campos por `***`.

## Erros de validação e corpos recebidos

O log de validação registra identificador, método, rota e descritores dos campos,
mas **não grava o corpo recebido**, mesmo em JSON malformado. Binários são tratados
como opacos pelo formatter. Se a sanitização falhar, o fallback não usa `repr`
do objeto original. Detalhes estruturados continuam mascarando os campos
sensíveis e preservando o motivo útil; os testes usam canários não secretos.

## Senha

- Mínimo de 8 caracteres no registro.
- Recusadas, além da senha igual ao usuário: `senha`, `1234`, `12345`, `123456`, `12345678`, `123456789`, `password`, `qwerty`, `admin`, `admin123`, `vendafacil`, `00000000`.
- Quem já entrou com senha antiga continua entrando. A regra vale para senha nova.

## Cofre fiscal

CSC, senha do certificado, arquivo A1 e tokens ficam no SQLite da loja, em claro. A leitura da API devolve o campo vazio e a marca de preenchido. O log troca esses valores por `***`. Criptografar o arquivo do banco não foi feito: quem tem o PC da loja já tem o caixa. Se o computador for trocado ou roubado, restaurar o backup só na máquina nova e trocar CSC e certificado no painel da SEFAZ.

## Salvar configuração mascarada

O PUT fiscal e o da maquininha preservam segredos omitidos, nulos, vazios ou
compostos apenas por espaços. Reenviar o GET mascarado não apaga credenciais.
Um novo valor não vazio é armazenado **exatamente como recebido**, inclusive
espaços nas extremidades: senha e token são valores opacos, não texto a normalizar.

A remoção exige `limpar_segredos`, lista explícita limitada aos campos sensíveis
daquela configuração. Um nome fora da lista permitida é recusado; enviar um
novo valor e pedir limpeza do mesmo campo também é recusado, antes de gravar.
Campos comuns e flags continuam atualizáveis. A resposta permanece mascarada.
Esse contrato de armazenamento não valida certificado nem prova homologação.

## Impressão de recibos

Forma de pagamento, identificador da venda, número e série da nota são texto
escapado no HTML da impressão. O atributo da imagem só recebe Base64 com
caracteres permitidos, tamanho compatível e prefixo de PNG; dados inválidos não
viram atributos ou eventos. Isso não valida conteúdo de QR fiscal nem autorização.

Os testes usam Chromium isolado, sem rede nem impressora, e canários benignos
para conferir o DOM em 58/80 mm. Não substituem teste físico ou homologação SEFAZ.

## Token de 30 dias

O token local dura 720 horas. A loja abre e fecha no mesmo PC, muitas vezes sem internet. Um token curto trancaria o caixa no meio do expediente se o painel não respondesse. Trinta dias cobrem o mês sem pedir senha todo dia, e o bloqueio da licença continua valendo na revalidação. Não é sessão de banco: é o caixa da loja.

## O que um PDV offline aceita

O caixa precisa vender com a luz e a internet caindo. Por isso o banco fica na máquina da loja, não num servidor. Quem está na frente do PC já opera o caixa. A proteção é contra a rede e contra a tela, não contra quem leva o computador.

## Onde ficam os segredos

No executável, a pasta é `%LOCALAPPDATA%\VendaFacilPDV\dados`. Em desenvolvimento, `dados/` na raiz do projeto.

| Arquivo | O que guarda |
|---|---|
| `vendafacil.db` | vendas, e em claro: CSC, senha e arquivo do certificado, token do gateway e token da maquininha |
| `conta.json` | token e validade da licença |
| `jwt_secret.key` | segredo que assina o token local |
| `logs/vendafacil.log` | erros, com segredo mascarado |

## Dependências e auditoria npm

Em 2026-11-11, a auditoria real passou de 21 avisos para zero após atualização
conservadora do lock e override de `minimatch` para `^11.0.8`. O override deve
ser reavaliado quando os consumidores atualizarem seus próprios intervalos;
não é autorização para forçar versões futuras nem ocultar advisories.

`npm audit`, `npm ls`, build e ESLint foram executados novamente pelo orquestrador,
assim como os 13 testes Chromium existentes; a revisão independente do patch
fica registrada no plano. Zero aqui significa zero avisos conhecidos no relatório
consultado, não ausência garantida de vulnerabilidades. As credenciais de registro
npm nunca entram em relatório ou commit.

## PC trocado ou roubado

1. No computador novo, restaurar o backup só se a loja ainda tem o controle da máquina antiga. Se foi roubo, não restaurar o certificado velho.
2. Trocar a senha do caixa.
3. Pedir CSC novo e revogar o certificado A1 na SEFAZ. Instalar o novo só na máquina nova.
4. Trocar o token da maquininha no Mercado Pago e gravar de novo na configuração.
5. Apagar, se ainda der, a pasta `dados` da máquina antiga.
