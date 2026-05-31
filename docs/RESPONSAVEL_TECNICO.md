# Responsável Técnico (infRespTec) na NF-e / NFC-e

Este documento explica o grupo **Responsável Técnico** do XML fiscal, **por que o
VendaFácil o mantém desligado por padrão**, e **como ligá-lo** caso a sua UF passe
a exigir.

> **Resumo de uma linha:** em **Mato Grosso, hoje, não é exigido** — deixe
> **desligado**. O sistema só inclui esse grupo se você ligar explicitamente.

## O que é

A partir da **Nota Técnica 2018.005**, o layout 4.00 da NF-e/NFC-e ganhou o grupo
opcional `infRespTec` (último filho de `infNFe`), que identifica a **empresa de
software** responsável pelo sistema emissor. Campos:

| Tag | Conteúdo |
|-----|----------|
| `CNPJ` | CNPJ da empresa de software (a casa que faz/distribui o PDV) |
| `xContato` | nome do contato de suporte |
| `email` | e-mail de contato |
| `fone` | telefone (só dígitos) |
| `idCSRT` | identificador do CSRT (**só quando a UF exige CSRT**) |
| `hashCSRT` | `Base64( SHA-1( CSRT + chave_de_acesso ) )` (**idem**) |

O **CSRT** (Código de Segurança do Responsável Técnico) é um código que a SEFAZ
entrega à empresa de software. **Sem CSRT** cadastrado, envia-se só o bloco de
contato; **com CSRT**, o sistema calcula o `hashCSRT` automaticamente.

## Por que vem desligado

- **Mato Grosso não exige** o grupo `infRespTec` (posição reafirmada pela SEFAZ-MT
  desde 03/06/2019, sem alteração até hoje).
- Quem **exige** o grupo: AM, MS, PE, PR, SC, TO. **MT não está na lista.**
- A **Rejeição 975** (falta de CSRT) **só ocorre se o grupo for enviado** sem o
  CSRT. Como o VendaFácil **não envia o grupo** por padrão, essa rejeição
  **não acontece** e a nota autoriza normalmente.

Ou seja: o caminho mais seguro em MT é **não enviar** o grupo — que é o padrão.

## Quando ligar

Ligue **apenas** se:

1. A SEFAZ da UF onde a loja emite **passar a exigir** o Responsável Técnico
   (ex.: **Paraná torna o CSRT obrigatório a partir de abril/2026**), **ou**
2. Você, como casa de software, **quiser** se identificar voluntariamente.

Antes de ligar com CSRT, é preciso **obter o CSRT junto à SEFAZ** da UF (cadastro
do responsável técnico no portal estadual).

## Como ligar (tela)

`Configurações Fiscais` → seção **Responsável Técnico (avançado)**:

1. Marque **"Enviar grupo infRespTec no XML"**.
2. Preencha **CNPJ da empresa de software**, contato, e-mail e telefone.
3. **Só se a UF exigir CSRT:** preencha **ID do CSRT** e **CSRT**. Sem isso, o
   sistema envia apenas o contato (válido nas UFs que não exigem CSRT).
4. Salve. O CSRT é tratado como segredo (não retorna preenchido para a tela).

## Como funciona no código

| Onde | O quê |
|------|-------|
| `backend/database.py` | colunas `resp_tec_*` em `config_fiscal` (migração automática) |
| `backend/fiscal_config.py` | campos no `ConfigFiscalInput`; `resp_tec_csrt` é segredo |
| `backend/fiscal_direto.py` | `_anexar_resp_tec()` monta `infRespTec`; `_hash_csrt()` calcula o hash |
| `src/pages/Fiscal.tsx` | seção recolhível "Responsável Técnico (avançado)" |

Regras do `_anexar_resp_tec`:

- Não faz nada se `resp_tec_habilitado` for falso **ou** se faltar o CNPJ.
- Inclui `idCSRT`/`hashCSRT` **somente** quando **CSRT e ID** estão preenchidos.

Testes em `backend/tests/test_fiscal_direto.py`:
`test_resp_tec_desligado_por_padrao_nao_aparece`,
`test_resp_tec_ligado_sem_csrt_inclui_contato`,
`test_resp_tec_com_csrt_inclui_hash`.

## Importante

A obrigatoriedade muda por **Nota Técnica estadual**. Confirme a regra da UF no
**credenciamento** (portal da SEFAZ) antes de mudar de homologação para produção.
Hoje, em **MT**, o correto é **manter desligado**.
