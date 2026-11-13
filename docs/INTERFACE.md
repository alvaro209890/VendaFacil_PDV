# Interface do caixa

Mudanças de tela de 13/11/2026. Não alteram a API nem o deploy do painel na VPS.

## Datas

Relatórios, Contas a receber e a validade da licença no painel usam o mesmo
campo de data (`dd/mm/aaaa`), no lugar do seletor nativo do navegador. O
componente é `painel/static/calendario.js`. No PDV ele entra pelo
`src/components/CampoData.tsx`. No painel, `painel/main.py` serve o arquivo em
`/calendario.js`.

Uma data inválida não é gravada. Vazio continua permitido onde a data é
opcional (vencimento do fiado e licença).

## Produtos

- **Importar XML** abre um diálogo com a prévia: dá para marcar ou desmarcar
  todos os itens, e o rodapé mostra quantos serão criados ou repostos.
- **Dados fiscais (NFC-e)** abrem numa janela no centro da tela. O formulário
  do produto não estica mais para baixo da barra do celular. NCM, CFOP, CEST,
  origem, CSOSN e alíquota de ICMS ficam nessa janela. Ao concluir, o botão do
  formulário mostra o resumo (NCM, CFOP e CSOSN).
