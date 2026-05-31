# Instalar o VendaFacil PDV em um PC Windows

Este guia e para instalar o sistema no computador do caixa usando o instalador
`VendaFacilPDV-Setup-1.0.0.exe`.

## Requisitos do computador

- Windows 10 ou Windows 11, 64 bits.
- Permissao de administrador para instalar.
- Navegador instalado, como Microsoft Edge, Chrome ou Firefox.
- Internet somente para ativacao/sincronizacao, quando o painel estiver configurado. O PDV continua vendendo offline.

## Arquivo que deve ser entregue

Entregue ao cliente o instalador:

```text
dist_installer\VendaFacilPDV-Setup-1.0.0.exe
```

O executavel direto tambem existe em:

```text
dist_exe\VendaFacilPDV.exe
```

Para cliente final, prefira sempre o instalador, pois ele cria atalhos, registra
o desinstalador e usa o icone oficial do VendaFacil PDV.

## Passo a passo de instalacao

1. Copie ou baixe `VendaFacilPDV-Setup-1.0.0.exe` no PC do caixa.
2. Clique com o botao direito no instalador e escolha `Executar como administrador`.
3. Se o Windows SmartScreen aparecer, clique em `Mais informacoes` e depois `Executar assim mesmo`.
4. Avance no instalador e deixe marcada a opcao de criar atalho na Area de Trabalho.
5. Ao finalizar, marque `Abrir o VendaFacil PDV agora` ou abra pelo atalho `VendaFacil PDV`.
6. O sistema abre no navegador em `http://127.0.0.1:3020/`.

## Primeiro uso

- Em modo local, crie o usuario inicial na tela de registro/login.
- Se o painel SaaS estiver configurado no build, entre com o login e senha cadastrados no painel.
- Cadastre produtos, configure PIX/maquininha/fiscal se necessario, e faca uma venda de teste.

## Onde ficam os dados

Os dados do lojista ficam fora da pasta do programa:

```text
%LOCALAPPDATA%\VendaFacilPDV\dados
```

Essa pasta guarda o banco SQLite, segredos locais e backups. Reinstalar ou
atualizar o sistema por cima nao apaga as vendas.

## Atualizar versao

1. Feche o VendaFacil PDV no PC do caixa.
2. Rode o novo `VendaFacilPDV-Setup-x.y.z.exe` como administrador.
3. Instale por cima da versao anterior.
4. Abra o atalho e confira uma venda/produto existente.

## Desinstalar

Use `Configurações > Aplicativos > VendaFacil PDV > Desinstalar`, ou o atalho
`Desinstalar VendaFacil PDV` no Menu Iniciar.

Por seguranca, a desinstalacao nao remove automaticamente:

```text
%LOCALAPPDATA%\VendaFacilPDV
```

Apague essa pasta manualmente apenas se tiver certeza de que nao precisa mais
dos dados da loja.

## Solucao rapida de problemas

- O app nao abriu: abra pelo atalho `VendaFacil PDV` e acesse `http://127.0.0.1:3020/`.
- Porta ocupada: feche outros VendaFacil abertos pelo Gerenciador de Tarefas e tente novamente.
- SmartScreen: para builds sem assinatura digital, o aviso e esperado na primeira instalacao.
- Antivirus bloqueou: permita o app somente se o arquivo veio do seu repositorio/Release oficial.
