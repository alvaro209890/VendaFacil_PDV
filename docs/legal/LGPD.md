# Guia prático de adequação à LGPD — VendaFácil PDV

> ⚠️ Material de apoio, não aconselhamento jurídico. Valide com um advogado.

A LGPD (Lei 13.709/2018) se aplica porque o sistema trata **dados pessoais**:
das Lojas (clientes do SaaS) e, indiretamente, dos **clientes finais** das lojas
(nome, telefone, CPF em nota).

## Papéis

- **[NOME DA EMPRESA] = controladora** dos dados do relacionamento com as Lojas.
- **[NOME DA EMPRESA] = operadora** dos dados que a Loja cadastra de seus
  clientes (a Loja é a controladora desses).
- Recomendado um **Contrato/Adendo de Tratamento de Dados (DPA)** entre você e a
  Loja deixando esses papéis claros.

## Checklist de adequação

- [ ] Publicar **Política de Privacidade** e **Termos de Uso** (modelos nesta pasta).
- [ ] Registrar o **aceite** (data/hora) de cada Loja aos Termos/Política.
- [ ] Nomear um **Encarregado (DPO)** e divulgar o contato.
- [ ] Mapear os dados tratados e as **bases legais** (já descritas na Política).
- [ ] Manter **contratos com operadores** (Render, Supabase, gateway fiscal,
      Mercado Pago) e verificar onde os dados ficam armazenados.
- [ ] Definir **prazo de retenção** e rotina de **exclusão** ao fim do contrato.
- [ ] Ter um **canal** para pedidos dos titulares (acesso, correção, exclusão).
- [ ] Plano de resposta a **incidentes** de segurança (notificar ANPD/titulares
      quando houver risco).
- [ ] Minimizar dados: só colete o necessário (ex.: CPF na nota só quando o
      cliente pedir).

## Pontos específicos deste sistema

- **CPF na nota**: só é coletado quando o consumidor solicita. Trate como dado
  pessoal e não exponha desnecessariamente.
- **Dados de cartão**: não são coletados nem armazenados — o pagamento em cartão
  é processado pelo Mercado Pago. Isso reduz bastante o risco.
- **Banco local do PDV**: fica na máquina da Loja; oriente a Loja a proteger o
  computador (essa responsabilidade é da Loja como controladora).
- **Backup e acesso**: restrinja quem tem acesso ao painel admin e ao banco
  (Supabase).

## Transferência internacional

Se os provedores (ex.: Render/Supabase) armazenarem dados **fora do Brasil**,
informe isso na Política e verifique as salvaguardas exigidas pela LGPD.
