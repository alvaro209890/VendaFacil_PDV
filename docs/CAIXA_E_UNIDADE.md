# Caixa e unidade com preços diferentes (1.0.16)

Guia completo do produto vendido **fechado** (caixa, fardo, pacote, display,
carteira) **e solto**, com dois preços que não dependem um do outro. Cobre a
entrada pela NF-e do fornecedor, o cadastro, o caixa, o estoque, o lucro e a
NFC-e. Vale desde a versão **1.0.16** (14/11/2026).

## 1. A regra em uma tabela

Exemplo do lojista: caixa de cerveja com **15** latas a **R$ 60**, lata solta a **R$ 5**.

| Ação | Cobra | Estoque (em latas) |
|---|---|---|
| Compra 2 caixas | custo da caixa ÷ 15 = custo de cada lata | +30 |
| Vende 1 caixa | R$ 60,00 (sai R$ 4,00 cada) | −15 |
| Vende 1 lata | R$ 5,00 | −1 |
| Vende 1 caixa + 3 latas | R$ 75,00 | −18 |
| Vende 15 latas soltas | R$ 75,00 (não R$ 60) | −15 |
| Estoque 14, tenta 1 caixa | recusa: "tem 14 UN, pedido 1 CX (15 UN)" | continua 14; latas seguem |

- **Um produto só**, estoque sempre na menor unidade (a lata).
- O **preço da unidade é digitado**, não é a caixa dividida. A tela só mostra a conta.
- Não existe "abrir a caixa": vender a caixa baixa as 15 latas de uma vez.
- Mudar "unidades dentro" depois não reconta o estoque já lançado (a tela avisa).
- Produto com a opção desligada continua igual ao de sempre (inclusive KG, LT, ML).

## 2. Cadastro (Produtos → + Novo ou Editar)

1. Ligue **Também vende por unidade**.
2. **Nome da embalagem**: CX, FD, PCT, DISPLAY, CARTEIRA…
3. **Qtd por compra** = quantas unidades vêm dentro (inteiro).
4. **Preço da embalagem fechada** e **Preço da unidade** (os dois > 0).
5. **Preço Custo** = custo de **uma unidade**.
6. **Código principal** = o da caixa; **Código da unidade** = o da lata.

Abaixo dos preços a tela mostra a **comparação** (atualiza enquanto digita):

```
CX com 15: R$ 60,00 = R$ 4,00 cada; lucro R$ 7,50 (12,5%).
Unidade avulsa: R$ 5,00; lucro R$ 1,50 (30%).
Quem leva a CX economiza R$ 15,00 frente a 15 soltas.
```

Avisos em amarelo: a caixa saiu **igual ou mais cara** que as unidades soltas,
ou algum preço ficou **abaixo do custo**. Lucro % é sobre o preço de venda.

Produto sem a opção também pode ter um **segundo código de barras** (campo
sempre visível): os dois códigos acham o mesmo produto no caixa.

## 3. Entrada pela NF-e do fornecedor (Produtos → Importar XML)

### 3.1 Custo de aquisição

O custo de cada unidade é o que a loja **paga de verdade**, rateado na quantidade:

```
(valor dos produtos + frete + seguro + outras despesas + IPI + ICMS-ST + FCP-ST − desconto) ÷ quantidade
```

O ICMS retido antes (CST 60, `vICMSSTRet`) não entra: já está no preço.
A prévia mostra o custo da nota e a parcela de despesas. Venda sugerida de
produto novo = custo + 30%.

### 3.2 Como a nota conta — a pergunta que decide o estoque

Produto **novo**: marque **"Vende a embalagem fechada e também a unidade, com
preços diferentes?"**, preencha embalagem, unidades dentro e os dois preços, e
responda **"Como esta nota conta a quantidade?"**:

| Resposta | Quando | Exemplo | Entra |
|---|---|---|---|
| **Em unidades soltas** (padrão quando a nota vem em UN) | o preço da nota é de uma lata | 600 UN a R$ 2,74 | **600 latas** a R$ 2,74 |
| **Em CX fechada** (padrão quando a nota vem em CX, FD…) | o preço da nota é de uma caixa | 50 CX a R$ 32,88, 12 por caixa | **600 latas** a R$ 2,74 |

Confira pelo preço: a prévia mostra "R$ x por UN na nota é preço de uma
unidade ou de uma CX?" e a frase verde "600 UN viram 600 UN" muda na hora.
**O número no nome do item nunca vira estoque** (o "00050" de
`CX 00050 KAISER LT 350ML` é código do fornecedor).

Quando a nota em caixa informa a unidade tributável (ex.: 50 CX e 600 UN), o
PDV já sugere **12 por caixa**, estoque em UN e custo por lata.

Produto **já cadastrado** com caixa + unidade: a nota na unidade da embalagem
multiplica (2 CX → 24 latas); a nota em UN entra 1 para 1. Os dois preços de
venda são mantidos.

### 3.3 Dois códigos de barras na nota

Distribuidoras de bebida costumam mandar o código do **pacote** em `cEAN` e o da
**lata** em `cEANTrib`. O PDV guarda os dois:

- produto novo: código da caixa = `cEAN`, código da unidade = `cEANTrib`
  (editáveis na prévia; bipe uma lata para conferir);
- a próxima nota **casa pelo código da lata** também, mesmo que a loja tenha
  cadastrado só a lata — repõe o estoque em vez de criar duplicado;
- se o código da unidade já é de outro produto, a importação recusa (409) em
  vez de jogar estoque num produto que não estava na prévia.

Com um código só: nota em unidades soltas → é o da unidade; nota em caixas → é
o da caixa.

## 4. Caixa (PDV)

- Dois botões por produto: **CX com 12 — R$ 40,00 (R$ 3,33 cada)** e
  **Unidade — R$ 3,80**. O selo mostra caixas fechadas e latas: `50 CX (600 UN)`.
- Código da caixa lança a caixa inteira; código da unidade, botão Unidade e a
  busca pelo nome lançam 1 avulsa. As duas linhas convivem no carrinho.
- O carrinho limita cada linha pelo estoque que sobra da outra.
- Venda sem modo informado (API antiga) vende **unidade**.

## 5. Histórico, lucro, estorno

- Cada item vendido guarda: modo (caixa/avulso), unidade vendida, latas baixadas
  e o custo da lata no momento da venda.
- Lucro do relatório = preço cobrado − custo da lata × latas baixadas
  (com o custo da venda, não o de hoje).
- Cancelar a venda devolve as latas originais, mesmo se o fator mudar depois.
- Top produtos separa "— CX" e "— avulso".

## 6. NFC-e (homologação)

A linha é o que o cliente levou; o grupo tributável fica em unidades:

| Venda | cEAN | uCom / qCom / vUnCom | cEANTrib | uTrib / qTrib |
|---|---|---|---|---|
| 1 caixa de 12 a R$ 40 | código da caixa | CX / 1 / 40,00 | código da lata | UN / 12 |
| 3 latas a R$ 3,80 | código da lata | UN / 3 / 3,80 | código da lata | UN / 3 |

- Só vai GTIN de verdade (8/12/13/14 dígitos, dígito certo, sem prefixo 2 de
  uso interno). Código próprio ("AVULSO-PALHEIRO", "001", etiqueta de balança)
  sai como **SEM GTIN** nos dois campos — antes ia cru e a SEFAZ recusaria.
- Lata avulsa nunca sai com o GTIN da caixa.
- CARTEIRA vira CART, DISPLAY vira DISP, PACOTE vira PCT (limite de 6 letras).

## 7. Caso real conferido — NF-e 446817 (14/11/2026)

Distribuidora de Bebidas Canarana → Mercearia Loiola. Item
`CX 00050 KAISER LT 350ML`, NCM 2203.00.00, `uCom=UN`, `qCom=600`,
`vUnCom=2,74`, `vOutro=12,36`, `cEAN=7896045500116` (pacote),
`cEANTrib=7896045512317` (lata 350 ml). Volumes: 50 CX → 12 latas por caixa.
Arquivo local fora do git: `%TEMP%\vf-nota.xml`, SHA-256
`ea3051184f0bd3802b2cf716f2c295cff42ab97d017183e33188c10208fe4dfb`.

| Verificação | 1.0.15 | 1.0.16 |
|---|---|---|
| Marcar "é embalagem" (CX 12) na prévia | **7.200 latas a R$ 0,2283** ❌ | 600 latas a R$ 2,7606 ✅ |
| Custo da lata | R$ 2,74 (sem os R$ 12,36) | R$ 2,7606 ✅ |
| Venda sugerida | R$ 3,56 | R$ 3,59 |
| Código da lata guardado | não (bipar a lata não achava) | sim ✅ |
| Nota em CX nova marcada caixa+unidade | recusada "estoque em UN" ❌ | 600 latas ✅ |
| 1 CX (R$ 40) + 3 latas (R$ 3,80) | R$ 51,40, −15 | igual ✅ |
| 12 latas soltas | R$ 45,60 | igual ✅ |
| 11 latas, pede CX | recusa | recusa, "pedido 1 CX (12 UN)" ✅ |
| Estorno, reimportação (409), 2ª nota casa e mantém preços | ok | ok ✅ |
| Caixa de 15 a R$ 60 / unidade a R$ 5 | ok | ok ✅ |

Roteiro: `cenario_kaiser.py` (API, banco temporário, porta 3031) **33/36 →
36/36**; Playwright com a nota real: importar como CX 12 + lata, bipar
`7896045500116` (caixa) e `7896045512317` (lata), cobrar R$ 51,40, estoque 585.

Suítes no HEAD da 1.0.16: backend **513** (+9 de homologação real
desmarcados), painel 23, Node 42, navegador 96, build e lint limpos. Binário
gerado neste PC e testado: `scripts/roteiro_exe.py --chromium` 49 requisições,
0 respostas 5xx; cupons 58/80 mm 4/4 com QR igual ao da nota; Playwright contra
o `.exe` com a nota real 5/5. Setup `VendaFacilPDV-Setup-1.0.16.exe`
40.002.691 bytes, SHA-256
`6D86133E51F514E4AF0B6C110913B9404DC004944FFF11AE09D10A92BB484AB2`.
Nada foi transmitido à SEFAZ; banco real da loja e certificados intocados.

**1.0.17 (mesmo dia):** só tira a obrigação/aviso de caixa aberto no PDV. Mesmas
suítes verdes (backend 513, navegador 96), `.exe` revalidado (49 requisições /
0 5xx, cupons 4/4, Playwright 5/5) e ativado contra o painel real com a conta da
loja. Setup `VendaFacilPDV-Setup-1.0.17.exe` 40.002.839 bytes, SHA-256
`E892829B0D836644D7CC3B68A134F141EFECC3ADB43ED1614117352A2B8FBC68`.

## 8. Contrato da API (para quem integra)

- `POST /api/produtos/importar-xml/preview` devolve por item, além do de antes:
  `valor_unitario_nota` (vUnCom puro), `valor_unitario_xml` (custo de aquisição
  por unidade da nota), `despesas_unitarias`, `codigo_barras_unidade`
  (cEANTrib), `fator_sugerido` (qTrib ÷ qCom quando as unidades diferem).
- `POST /api/produtos/importar-xml/confirmar` aceita por item
  `nota_em_embalagem` (true = cada unidade da nota é uma embalagem; false =
  unidades soltas; ausente = deduz pela unidade da nota: UN → soltas) e
  `codigo_barras_unidade`.
- Checkout: `modo_venda` = `embalagem` | `unidade` (sem modo = unidade).
