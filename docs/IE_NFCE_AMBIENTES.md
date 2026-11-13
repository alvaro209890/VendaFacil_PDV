# IE e NFC-e: homologação x produção (por que deu cStat 230)

> Documento de apoio para a instalação na loja e para a conversa com o contador.
> Escrito em 13/11/2026, depois do primeiro envio real da NFC-e da mercearia.

## Resumo em três linhas

1. A IE da loja está **ativa** no cadastro estadual (CCE) — isso a habilita ao ICMS, não à NFC-e.
2. O autorizador de NFC-e tem um cadastro de contribuintes **por ambiente**; em **homologação** a IE respondeu **cStat 230 — "IE do emitente não cadastrada"**.
3. Isso bloqueia o **teste**. **Produção nunca foi testada** e pode funcionar: só um envio real, com a loja em produção, responde.

## O caso concreto (mercearia do James)

| Campo | Valor |
|---|---|
| Razão social | JAMES LOIOLA FERREIRA |
| CNPJ | 42.115.849/0001-50 |
| IE | 13.876.189-2 (ativa no CCE, emitido em 12/11/2026) |
| CNAE | 4729-6/99 |
| Regime | Simples Nacional (CRT 1) |
| Município | Querência/MT (cMun 5107065) |
| Certificado | A1 da própria loja, válido até 01/04/2027 |
| CSC | cadastrado no cofre (homologação) |
| Ambiente no PDV | `homologacao` |

Prova do envio de 12/11/2026 19:46 (nota nº 5, série 1):

```
retEnviNFe: cStat 104 — Lote processado
protNFe:    cStat 230 — Rejeicao: IE do emitente nao cadastrada
```

Ou seja: TLS, assinatura, XML e QR passaram; o que parou foi o **cadastro**.

## Por que a IE ativa não basta

A SEFAZ-MT mantém **duas bases de contribuintes** para a NFC-e:

| Ambiente | Para quê | Estado da IE |
|---|---|---|
| **Homologação** | treino. Nota sem valor fiscal | ❌ não cadastrada (cStat 230 em 12/11) |
| **Produção** | nota real da venda | ❓ nunca testada |

É comum a loja estar habilitada em produção e não em homologação (as bases são
atualizadas em momentos diferentes). O contrário também acontece. Não há como
saber sem transmitir — e transmitir em homologação é inofensivo, enquanto em
produção gera documento fiscal de verdade.

## O que fazer no dia da instalação

1. Instalar o PDV no PC da loja (`INSTALACAO_WINDOWS.md`) e cadastrar na aba
   **Fiscal**: certificado A1 + senha, CSC + ID, dados da empresa (CNPJ igual ao
   do certificado, IE, CNAE, endereço, CRT), ambiente **homologação**.
2. `scripts\fiscal_precheck.py` — deve acusar só **B3** (credenciamento) e
   **B5** (Mercado Pago). Qualquer outro item é configuração local.
3. **Teste em homologação** (uma venda de teste): se vier `cStat 100`, o cadastro
   está OK naquela base; se vier `230`, confirma o bloqueio cadastral.
4. **Teste em produção** (a decisão D1 é só até a primeira nota autorizada):
   - trocar o ambiente para **produção** na tela Fiscal;
   - cadastrar o **CSC de produção** (o de homologação não serve);
   - emitir a venda real;
   - `cStat 100` → a loja está emitindo NFC-e válida;
   - `cStat 230` → a loja não consegue emitir; abrir chamado na SEFAZ-MT com o
     XML e o retorno (guardados no SQLite local e exportáveis em Vendas).
5. Registrar o resultado em `plano_producao/04_BLOQUEIOS.md` (B3) e no diário.

## Mensagem pronta para a contadora

> Bom dia! Preciso de uma verificação no cadastro fiscal do James Loiola Ferreira.
>
> Dados: CNPJ 42.115.849/0001-50 · IE 13.876.189-2 · CNAE 4729-6/99 · Simples
> Nacional · Querência/MT.
>
> Estamos implantando o PDV dele e o software já transmite NFC-e (modelo 65,
> layout 4.00, certificado A1 da própria loja válido até 01/04/2027, CSC
> cadastrado). O envio chega à SEFAZ-MT, mas o autorizador responde
> **"Rejeição 230 – IE do emitente não cadastrada"** no ambiente de
> **homologação**.
>
> A IE está ativa no CCE, então entendo que seja só a habilitação da IE no
> autorizador de NFC-e daquele ambiente. Pode confirmar:
> 1. Se a loja está credenciada para emitir NFC-e em **produção**;
> 2. Se dá para solicitar à SEFAZ-MT a inclusão da IE no cadastro do autorizador
>    de **homologação**;
> 3. Se há alguma pendência cadastral que justifique essa rejeição.
>
> Se em produção já estiver habilitada, podemos fazer o teste real por lá.

## Não confundir

- **Rejeição não é nota.** cStat 230 (ou qualquer 2xx/5xx de rejeição) significa
  que a nota **não existe** fiscalmente. Nada a cancelar; o número é tratado
  pelo controle de numeração do próprio PDV.
- **Contingência não resolve rejeição cadastral.** Contingência offline
  (`tpEmis=9`) existe para SEFAZ indisponível, não para recusa de cadastro.
- **Homologação não vale como nota fiscal**, mesmo autorizada (`cStat 100`).
  Serve para provar o fluxo.
- **O 230 não é problema de certificado nem de assinatura**: ambos já foram
  aceitos no mesmo envio (o lote voltou 104 e só o protocolo rejeitou).

## Onde isso aparece no sistema

- Tela **Fiscal**: ambiente, certificado, CSC, dados da empresa e o retorno da
  última transmissão.
- **Vendas → abrir a venda**: XML assinado, retorno da SEFAZ e "Baixar XML".
- `scripts\fiscal_precheck.py`: inspeção somente leitura do cofre, sem imprimir
  segredos; sai com código 2 quando há bloqueio.
