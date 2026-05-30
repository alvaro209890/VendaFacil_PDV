"""Configuração do Painel SaaS embutida no .exe.

EDITE este valor ANTES de gerar o .exe (no Windows) para apontar para o seu
painel na VPS. Assim cada loja já recebe o executável "conectado", sem precisar
mexer em variáveis de ambiente.

Exemplo:
    PAINEL_URL = "https://painel.seudominio.com"

Deixe vazio ("") para distribuir em MODO LOCAL (sem controle central de licença).
A variável de ambiente VENDAFACIL_PAINEL_URL, se definida, tem prioridade sobre
este valor.
"""
PAINEL_URL = ""
