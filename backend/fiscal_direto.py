"""Emissor fiscal direto SEFAZ-MT (base local, sem gateway).

Este módulo monta XML NF-e/NFC-e 4.00, assina com A1 quando configurado e
prepara/transmite SOAP para homologação/produção da SEFAZ-MT. A emissão real
depende de certificado A1 da loja, CSC/idCSC e credenciamento estadual.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from database import db

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
ET.register_namespace("", NFE_NS)

C_UF_MT = "51"
VERSAO = "4.00"
# URLs OFICIAIS de consulta do QR Code da NFC-e em MT (cadastro nacional de
# endereços por UF). A SEFAZ valida o conteúdo do qrCode/urlChave contra esse
# cadastro (Rejeição 591): produção é http com "www", homologação sem "www".
URL_QR_NFCE = {
    "homologacao": "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce",
    "producao": "http://www.sefaz.mt.gov.br/nfce/consultanfce",
}
# Webservices SEFAZ-MT 4.00 (autorizador próprio). Os nomes dos serviços são os
# publicados pela SEFAZ-MT: "NfeAutorizacao4" (não "NFe..."), consulta é
# "NfeConsulta4" e evento é "RecepcaoEvento4" — o caminho é case-sensitive.
WS = {
    ("65", "homologacao", "autorizacao"): "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4",
    ("65", "producao", "autorizacao"): "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4",
    ("65", "homologacao", "consulta"): "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeConsulta4",
    ("65", "producao", "consulta"): "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeConsulta4",
    ("65", "homologacao", "evento"): "https://homologacao.sefaz.mt.gov.br/nfcews/services/RecepcaoEvento4",
    ("65", "producao", "evento"): "https://nfce.sefaz.mt.gov.br/nfcews/services/RecepcaoEvento4",
    ("55", "homologacao", "autorizacao"): "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
    ("55", "producao", "autorizacao"): "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
    ("55", "homologacao", "consulta"): "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4",
    ("55", "producao", "consulta"): "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4",
    ("55", "homologacao", "evento"): "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4",
    ("55", "producao", "evento"): "https://nfe.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4",
}
# Operação/método SOAP por serviço. O elemento <nfeDadosMsg> fica no namespace
# do WSDL da operação (portalfiscal/nfe/wsdl/<Operação>) e o Content-Type SOAP
# 1.2 leva action="<namespace>/<método>" — sem isso o servidor não roteia a
# mensagem. Só o conteúdo interno (enviNFe/consSitNFe/envEvento) usa o
# namespace do leiaute da NF-e.
_SOAP_OP = {
    "autorizacao": ("NFeAutorizacao4", "nfeAutorizacaoLote"),
    "consulta": ("NFeConsultaProtocolo4", "nfeConsultaNF"),
    "evento": ("NFeRecepcaoEvento4", "nfeRecepcaoEvento"),
}


class FiscalDiretoError(Exception):
    pass


@dataclass
class DocumentoMontado:
    chave: str
    xml: str
    payload: dict
    qrcode_url: str | None = None
    dh_emi: str | None = None
    v_nf: float | None = None


def so_digitos(s: str | None) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


TZ_MT = timezone(timedelta(hours=-4))     # Mato Grosso (Cuiabá), sem horário de verão


def agora_mt() -> str:
    return datetime.now(TZ_MT).replace(microsecond=0).isoformat()


def _texto_xml(s, maximo: int) -> str:
    """Normaliza texto para o XML fiscal: colapsa espaços internos, remove
    espaços nas pontas (Rejeição 588) e corta no tamanho máximo do campo
    (Rejeição 215 — falha de schema por excesso de caracteres)."""
    limpo = " ".join(str(s or "").split())
    return limpo[:maximo]


def _dv_mod11(numeros: str, pesos: list[int]) -> int:
    soma = sum(int(d) * p for d, p in zip(numeros, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def validar_cpf(cpf: str) -> bool:
    """Valida CPF (11 dígitos + dígitos verificadores). Evita a Rejeição 237."""
    c = so_digitos(cpf)
    if len(c) != 11 or c == c[0] * 11:
        return False
    d1 = _dv_mod11(c[:9], list(range(10, 1, -1)))
    d2 = _dv_mod11(c[:10], list(range(11, 1, -1)))
    return c[9] == str(d1) and c[10] == str(d2)


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ (14 dígitos + dígitos verificadores). Evita as Rejeições 207/504."""
    c = so_digitos(cnpj)
    if len(c) != 14 or c == c[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    d1 = _dv_mod11(c[:12], pesos1)
    d2 = _dv_mod11(c[:13], pesos2)
    return c[12] == str(d1) and c[13] == str(d2)


def dv_chave(chave43: str) -> str:
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = sum(int(n) * pesos[i % len(pesos)] for i, n in enumerate(reversed(chave43)))
    resto = soma % 11
    dv = 11 - resto
    return "0" if dv >= 10 else str(dv)


def gerar_cnf(numero: int) -> str:
    """Código numérico (cNF) aleatório de 8 dígitos, diferente do nNF.

    O MOC da NF-e exige cNF aleatório e proíbe que ele seja igual ao número da
    nota (nNF) — usar o próprio número é rejeitado pela SEFAZ e enfraquece o
    controle anti-fraude embutido na chave de acesso."""
    proibido = f"{numero % 100000000:08d}"
    while True:
        cod = f"{secrets.randbelow(100000000):08d}"
        if cod != proibido:
            return cod


def chave_acesso(config: dict, modelo: str, serie: int, numero: int,
                 tp_emis: str = "1", cnf: str | None = None,
                 dt: datetime | None = None) -> str:
    # ``dt`` deve ser o MESMO instante usado no dhEmi: AAMM da chave divergente
    # do mês de emissão é rejeitado pela SEFAZ (Rejeição 615) — sem isso a
    # emissão na virada de mês/ano poderia usar dois relógios diferentes.
    dt = dt or datetime.now(TZ_MT)
    cnpj = so_digitos(config.get("cnpj")).zfill(14)
    ano_mes = dt.strftime("%y%m")
    cod = cnf or gerar_cnf(numero)
    base = f"{C_UF_MT}{ano_mes}{cnpj}{modelo}{serie:03d}{numero:09d}{tp_emis}{cod}"
    return base + dv_chave(base)


def _tag(parent, name: str, text=None):
    el = ET.SubElement(parent, f"{{{NFE_NS}}}{name}")
    if text is not None:
        el.text = str(text)
    return el


# ── Pagamento (grupo <pag>/<detPag>/<card>) ───────────────────────────────────
# Mapa tPag (forma interna → código NFC-e/NF-e, Tabela de Meios de Pagamento
# atualizada pelo IT 2024.002, em produção desde 01/07/2024). PIX é tratado à
# parte: 17 = PIX dinâmico (Point integrada, com cAut) e 20 = PIX estático
# (QR fixo da loja, fluxo do pix.py). Fiado/outros caem em 99 + xPag, que é
# obrigatório quando tPag=99.
_TPAG = {"dinheiro": "01", "credito": "03", "debito": "04"}

# Bandeira → tBand (tabela YA06). Aceita o id de bandeira do Mercado Pago
# (master, visa, elo...) ou o próprio código numérico já pronto.
_TBAND = {
    "visa": "01", "master": "02", "mastercard": "02", "amex": "03",
    "american express": "03", "sorocred": "04", "diners": "05",
    "diners club": "05", "elo": "06", "hipercard": "07", "hiper": "07",
    "aura": "08", "cabal": "09",
}
_TBAND_CODIGOS = {"01", "02", "03", "04", "05", "06", "07", "08", "09",
                  "10", "11", "12", "13", "99"}


def _tband(bandeira) -> str | None:
    """Normaliza a bandeira para o código tBand. Desconhecida vira 99 (Outros)."""
    if not bandeira:
        return None
    b = str(bandeira).strip().lower()
    if b in _TBAND_CODIGOS:
        return b
    return _TBAND.get(b, "99")


def _pagamento_detalhe(venda: dict) -> dict:
    """Lê os dados do pagamento eletrônico gravados na venda (JSON ou dict)."""
    raw = venda.get("pagamento_detalhe")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    return {}


def _grupo_pagamento(inf, venda: dict, valor: float) -> None:
    """Monta <pag>/<detPag> e, p/ cartão/PIX integrado, o grupo <card>.

    Vínculo do pagamento eletrônico — obrigatório em MT (Decreto 599/2023 e
    Portaria SEFAZ 262/2023) para CNAEs de varejo (inclui mercearia 4712-1).
    Com a transação integrada (tpIntegra=1) o layout exige CNPJ da credenciadora
    e cAut (código de autorização) — sem eles a SEFAZ rejeita (392). Quando os
    dados não vêm completos, declara-se não integrado (tpIntegra=2).
    """
    pag = _tag(inf, "pag")
    detp = _tag(pag, "detPag")
    forma = (venda.get("forma_pagamento") or "").lower()
    pd = _pagamento_detalhe(venda)
    if forma == "pix":
        # IT 2024.002: 17 = PIX dinâmico (QR por transação, com cAut/endToEndId);
        # 20 = PIX estático (QR fixo da chave da loja, sem transação integrada).
        tpag = "17" if pd.get("tipo_integracao") else "20"
    else:
        tpag = _TPAG.get(forma, "99")
    # indPag: 0 = à vista, 1 = a prazo (fiado/crediário da mercearia).
    _tag(detp, "indPag", "1" if forma == "fiado" else "0")
    _tag(detp, "tPag", tpag)
    if tpag == "99":
        # xPag é obrigatório quando tPag=99 (rejeição por regra YA02); descreve
        # o meio de pagamento real.
        _tag(detp, "xPag", "Crediario da loja (fiado)" if forma == "fiado" else "Outros")
    _tag(detp, "vPag", f"{valor:.2f}")

    eletronico = forma in {"credito", "debito"} or (
        forma == "pix" and pd.get("tipo_integracao")
    )
    if not eletronico:
        return

    cnpj = so_digitos(pd.get("adquirente_cnpj"))
    cAut = str(pd.get("autorizacao") or "").strip()
    card = _tag(detp, "card")
    if pd.get("tipo_integracao") == "1" and cnpj and cAut:
        _tag(card, "tpIntegra", "1")
        _tag(card, "CNPJ", cnpj)
        tband = _tband(pd.get("bandeira"))
        if tband:
            _tag(card, "tBand", tband)
        _tag(card, "cAut", cAut)
    else:
        _tag(card, "tpIntegra", "2")


def _validar_emitente(config: dict) -> None:
    obrig = ("cnpj", "inscricao_estadual", "regime_tributario", "codigo_municipio",
             "municipio", "uf", "logradouro", "numero", "bairro", "cep")
    faltando = [c for c in obrig if not str(config.get(c) or "").strip()]
    if faltando:
        raise FiscalDiretoError(f"Configuração fiscal incompleta: {', '.join(faltando)}.")
    if (config.get("uf") or "").upper() != "MT":
        raise FiscalDiretoError("Emissão direta configurada para Mato Grosso: UF do emitente deve ser MT.")
    if not validar_cnpj(config.get("cnpj")):
        raise FiscalDiretoError("CNPJ do emitente inválido (confira os 14 dígitos em Configurações Fiscais).")
    cmun = so_digitos(config.get("codigo_municipio"))
    if len(cmun) != 7 or not cmun.startswith("51"):
        raise FiscalDiretoError(
            "Código IBGE do município inválido: use os 7 dígitos do município de MT "
            "(começa com 51 — ex.: Cuiabá 5103403).")
    if len(so_digitos(config.get("cep"))) != 8:
        raise FiscalDiretoError("CEP do emitente inválido (8 dígitos).")
    # O emissor monta os grupos ICMS do Simples Nacional (CSOSN). CRT 2 (excesso
    # de sublimite) usa CST comum e CRT 3 (regime normal) passa a exigir os
    # grupos IBS/CBS da Reforma Tributária a partir de 03/08/2026 (NT 2025.002,
    # regra UB12-10) — nenhum dos dois é suportado. Simples Nacional (CRT 1) e
    # MEI (CRT 4) só precisam de IBS/CBS a partir de 01/04/2027.
    crt = str(config.get("regime_tributario") or "1").strip()
    if crt not in {"1", "4"}:
        raise FiscalDiretoError(
            f"Regime tributário (CRT) {crt} não suportado: o emissor atende Simples "
            "Nacional (CRT 1) e MEI (CRT 4). CRT 2 exige grupos CST e CRT 3 (regime "
            "normal) exige IBS/CBS a partir de 03/08/2026 (NT 2025.002).")


def _validar_certificado(config: dict, modelo: str) -> None:
    if not config.get("certificado_a1_b64") or not config.get("certificado_senha"):
        raise FiscalDiretoError("Informe o certificado A1 da loja e a senha em Configurações Fiscais.")
    # No QR Code 3.0 (NT 2025.001) o CSC deixa de existir — a validação passa a
    # ser por assinatura digital. O CSC/idCSC só é exigido no QR Code 2.0.
    if modelo == "65" and str(config.get("qrcode_versao") or "2") != "3" and (
            not config.get("csc") or not config.get("csc_id")):
        raise FiscalDiretoError("Informe CSC e ID do CSC para emitir NFC-e (QR Code 2.0).")


def validar_itens(venda: dict) -> None:
    faltas = []
    erros = []
    for item in venda.get("itens", []):
        prod = db.get_produto(item["produto_id"]) or {}
        for campo in ("ncm", "cfop", "cst_csosn", "unidade"):
            if not prod.get(campo):
                faltas.append(f"{item['nome_produto']}: {campo}")
        ncm = so_digitos(prod.get("ncm"))
        if prod.get("ncm") and len(ncm) != 8:
            erros.append(f"{item['nome_produto']}: NCM deve ter 8 dígitos (Rejeição 778)")
        csosn = str(prod.get("cst_csosn") or "").strip()
        cfop = str(prod.get("cfop") or "").strip()
        cest = so_digitos(prod.get("cest"))
        # Produto com ICMS-ST (CSOSN 500 / CFOP 5405) exige CEST — Convênio
        # ICMS 92/15; sem ele a SEFAZ rejeita (806). Vale para bebidas frias,
        # cigarros etc. da mercearia.
        if (csosn == "500" or cfop == "5405") and not cest:
            erros.append(f"{item['nome_produto']}: produto com ICMS-ST (CSOSN 500/CFOP 5405) "
                         "exige o código CEST (Rejeição 806)")
        if cest and len(cest) != 7:
            erros.append(f"{item['nome_produto']}: CEST deve ter 7 dígitos")
    if faltas:
        raise FiscalDiretoError("Produtos com dados fiscais incompletos: " + "; ".join(faltas[:8]))
    if erros:
        raise FiscalDiretoError("Dados fiscais inválidos — corrija no cadastro do produto: "
                                + "; ".join(erros[:8]))


# ── Seleção de grupos de imposto (NFC-e/NF-e Simples Nacional) ────────────────
# O grupo do XML muda conforme o CST/CSOSN. Emitir tudo como ICMSSN102/PISNT é
# o erro clássico que rejeita ST na SEFAZ e atrapalha a apuração. Aqui cada
# código vai para o grupo certo do leiaute 4.00.

# CSOSN -> grupo ICMS do Simples Nacional
_ICMS_SN_GRUPO = {
    "101": "ICMSSN101",
    "102": "ICMSSN102", "103": "ICMSSN102", "300": "ICMSSN102", "400": "ICMSSN102",
    "500": "ICMSSN500",
    "900": "ICMSSN900",
}


def _grupo_icms_sn(imposto, prod: dict) -> None:
    """Monta <ICMS> com o grupo SN correto a partir do CSOSN do produto.

    Cobre os códigos que uma mercearia no Simples realmente usa:
    102/103/300/400 (tributação normal/isento/imune/não trib.), 500 (ICMS já
    recolhido por substituição tributária — bebidas frias, cigarro), 101 (com
    crédito) e 900 (outros). Os códigos de *substituto* 201/202/203 exigem base
    e MVA da ST e não se aplicam ao revendedor — orientamos usar 500.
    """
    csosn = (str(prod.get("cst_csosn") or "102")).strip()
    orig = str(prod.get("origem") or "0")
    grupo = _ICMS_SN_GRUPO.get(csosn)
    if grupo is None:
        if csosn in {"201", "202", "203"}:
            raise FiscalDiretoError(
                f"CSOSN {csosn} é de contribuinte substituto (exige base/MVA da ST). "
                "Para revenda de produto com ICMS já recolhido use CSOSN 500."
            )
        raise FiscalDiretoError(f"CSOSN {csosn} não suportado na emissão direta.")
    icms = _tag(imposto, "ICMS")
    sn = _tag(icms, grupo)
    _tag(sn, "orig", orig)
    _tag(sn, "CSOSN", csosn)
    if grupo == "ICMSSN101":
        # Permite crédito de ICMS no Simples: alíquota de crédito do produto.
        p_cred = float(prod.get("aliquota_icms") or 0)
        _tag(sn, "pCredSN", f"{p_cred:.4f}")
        _tag(sn, "vCredICMSSN", "0.00")


def _grupo_pis(imposto, prod: dict, base: float) -> float:
    """Monta <PIS> conforme o CST e devolve o valor de PIS lançado (para o total).

    CST 01/02 → PISAliq (tributado por alíquota). 04..09 → PISNT (não tributado:
    monofásico=04, ST=05, alíquota zero=06, isenta=07, sem incidência=08,
    suspensão=09). Demais (49..99) → PISOutr.
    """
    cst = (str(prod.get("cst_pis") or "07")).strip().zfill(2)
    pis = _tag(imposto, "PIS")
    if cst in {"01", "02"}:
        aliq = float(prod.get("aliquota_pis") or 0)
        valor = round(base * aliq / 100, 2)
        g = _tag(pis, "PISAliq")
        _tag(g, "CST", cst)
        _tag(g, "vBC", f"{base:.2f}")
        _tag(g, "pPIS", f"{aliq:.4f}")
        _tag(g, "vPIS", f"{valor:.2f}")
        return valor
    if cst in {"04", "05", "06", "07", "08", "09"}:
        g = _tag(pis, "PISNT")
        _tag(g, "CST", cst)
        return 0.0
    aliq = float(prod.get("aliquota_pis") or 0)
    valor = round(base * aliq / 100, 2)
    g = _tag(pis, "PISOutr")
    _tag(g, "CST", cst)
    _tag(g, "vBC", f"{base:.2f}")
    _tag(g, "pPIS", f"{aliq:.4f}")
    _tag(g, "vPIS", f"{valor:.2f}")
    return valor


def _grupo_cofins(imposto, prod: dict, base: float) -> float:
    """Igual a _grupo_pis, para a COFINS (CST/alíquota próprios do produto)."""
    cst = (str(prod.get("cst_cofins") or "07")).strip().zfill(2)
    cof = _tag(imposto, "COFINS")
    if cst in {"01", "02"}:
        aliq = float(prod.get("aliquota_cofins") or 0)
        valor = round(base * aliq / 100, 2)
        g = _tag(cof, "COFINSAliq")
        _tag(g, "CST", cst)
        _tag(g, "vBC", f"{base:.2f}")
        _tag(g, "pCOFINS", f"{aliq:.4f}")
        _tag(g, "vCOFINS", f"{valor:.2f}")
        return valor
    if cst in {"04", "05", "06", "07", "08", "09"}:
        g = _tag(cof, "COFINSNT")
        _tag(g, "CST", cst)
        return 0.0
    aliq = float(prod.get("aliquota_cofins") or 0)
    valor = round(base * aliq / 100, 2)
    g = _tag(cof, "COFINSOutr")
    _tag(g, "CST", cst)
    _tag(g, "vBC", f"{base:.2f}")
    _tag(g, "pCOFINS", f"{aliq:.4f}")
    _tag(g, "vCOFINS", f"{valor:.2f}")
    return valor


def _ratear(total: float, valores: list[float]) -> list[float]:
    """Rateia ``total`` proporcionalmente a ``valores`` (2 casas). A última
    parcela absorve a sobra de arredondamento para a soma fechar exatamente —
    é o que faz o desconto do cabeçalho bater com o somatório dos itens (senão
    a SEFAZ rejeita o total)."""
    soma = round(sum(valores), 2)
    if total <= 0 or soma <= 0:
        return [0.0 for _ in valores]
    partes: list[float] = []
    acumulado = 0.0
    for i, v in enumerate(valores):
        if i == len(valores) - 1:
            partes.append(round(total - acumulado, 2))
        else:
            parte = round(total * v / soma, 2)
            acumulado = round(acumulado + parte, 2)
            partes.append(parte)
    return partes


def montar_documento(venda: dict, config: dict, modelo: str = "65",
                     cpf_consumidor: str | None = None,
                     destinatario: dict | None = None,
                     serie: int | None = None, numero: int | None = None,
                     tp_emis: str = "1", dh_cont: str | None = None,
                     just_cont: str | None = None) -> DocumentoMontado:
    modelo = str(modelo)
    tp_emis = str(tp_emis)
    _validar_emitente(config)
    validar_itens(venda)
    if modelo == "55" and not destinatario:
        raise FiscalDiretoError("NF-e modelo 55 exige destinatário.")

    serie = int(serie or (config.get("serie_nfe") if modelo == "55" else config.get("serie_nfce")) or 1)
    numero = int(numero or (config.get("proximo_numero_nfe") if modelo == "55" else config.get("proximo_numero_nfce")) or 1)
    ambiente = config.get("ambiente") or "homologacao"
    tp_amb = "1" if ambiente == "producao" else "2"
    dt_emissao = datetime.now(TZ_MT).replace(microsecond=0)
    dh_emi = dt_emissao.isoformat()
    chave = chave_acesso(config, modelo, serie, numero, tp_emis, dt=dt_emissao)
    inf_id = "NFe" + chave

    nfe = ET.Element(f"{{{NFE_NS}}}NFe")
    inf = _tag(nfe, "infNFe")
    inf.set("Id", inf_id)
    inf.set("versao", VERSAO)
    ide = _tag(inf, "ide")
    _tag(ide, "cUF", C_UF_MT)
    _tag(ide, "cNF", chave[35:43])
    _tag(ide, "natOp", "VENDA AO CONSUMIDOR" if modelo == "65" else "VENDA DE MERCADORIA")
    _tag(ide, "mod", modelo)
    _tag(ide, "serie", serie)
    _tag(ide, "nNF", numero)
    _tag(ide, "dhEmi", dh_emi)
    _tag(ide, "tpNF", "1")
    # idDest: NFC-e é sempre operação interna; NF-e segue a UF do destinatário
    # (idDest=1 com destinatário de outra UF é a Rejeição 694).
    uf_dest = ((destinatario or {}).get("uf") or "MT").strip().upper()
    id_dest = "1" if (modelo == "65" or uf_dest == "MT") else "2"
    if modelo == "55":
        cfops = {str(db.get_produto(i["produto_id"]).get("cfop") or "").strip()
                 for i in venda.get("itens", []) if db.get_produto(i["produto_id"])}
        if id_dest == "2" and any(c.startswith("5") for c in cfops):
            raise FiscalDiretoError(
                f"NF-e para destinatário de {uf_dest} é operação interestadual: "
                "os produtos precisam de CFOP 6xxx (hoje estão com 5xxx).")
        if id_dest == "1" and any(c.startswith("6") for c in cfops):
            raise FiscalDiretoError(
                "Destinatário de MT com produto de CFOP 6xxx (interestadual): "
                "use CFOP 5xxx para operação interna.")
    _tag(ide, "idDest", id_dest)
    _tag(ide, "cMunFG", so_digitos(config.get("codigo_municipio")))
    _tag(ide, "tpImp", "4" if modelo == "65" else "1")
    _tag(ide, "tpEmis", tp_emis)
    _tag(ide, "cDV", chave[-1])
    _tag(ide, "tpAmb", tp_amb)
    _tag(ide, "finNFe", "1")
    _tag(ide, "indFinal", "1" if modelo == "65" else "0")
    _tag(ide, "indPres", "1")
    _tag(ide, "procEmi", "0")
    _tag(ide, "verProc", "VendaFacilPDV")
    if tp_emis == "9":
        # Contingência offline: data/hora de entrada em contingência + justificativa
        # (15 a 256 caracteres). Vêm depois de verProc no leiaute 4.00.
        _tag(ide, "dhCont", dh_cont or dh_emi)
        just = (just_cont or "").strip()
        if len(just) < 15:
            just = "Sem comunicacao com a SEFAZ no momento da venda"
        _tag(ide, "xJust", just[:256])

    emit = _tag(inf, "emit")
    _tag(emit, "CNPJ", so_digitos(config.get("cnpj")))
    _tag(emit, "xNome", _texto_xml(config.get("razao_social") or config.get("nome_fantasia"), 60))
    _tag(emit, "xFant", _texto_xml(config.get("nome_fantasia") or config.get("razao_social"), 60))
    end = _tag(emit, "enderEmit")
    _tag(end, "xLgr", _texto_xml(config.get("logradouro"), 60))
    _tag(end, "nro", _texto_xml(config.get("numero"), 60))
    _tag(end, "xBairro", _texto_xml(config.get("bairro"), 60))
    _tag(end, "cMun", so_digitos(config.get("codigo_municipio")))
    _tag(end, "xMun", _texto_xml(config.get("municipio"), 60))
    _tag(end, "UF", (config.get("uf") or "MT").upper())
    _tag(end, "CEP", so_digitos(config.get("cep")))
    _tag(end, "cPais", "1058")
    _tag(end, "xPais", "BRASIL")
    _tag(emit, "IE", so_digitos(config.get("inscricao_estadual")))
    _tag(emit, "CRT", config.get("regime_tributario") or "1")

    dest_doc = so_digitos(cpf_consumidor)
    if modelo == "55":
        dest_doc = so_digitos(destinatario.get("documento"))
    if dest_doc and len(dest_doc) == 11 and not validar_cpf(dest_doc):
        raise FiscalDiretoError("CPF do consumidor inválido — confira os dígitos (Rejeição 237).")
    if dest_doc and len(dest_doc) == 14 and not validar_cnpj(dest_doc):
        raise FiscalDiretoError("CNPJ do destinatário inválido — confira os dígitos (Rejeição 207).")
    if dest_doc and len(dest_doc) not in (11, 14):
        raise FiscalDiretoError("Documento do consumidor deve ter 11 dígitos (CPF) ou 14 (CNPJ).")
    if modelo == "55" or dest_doc:
        dest = _tag(inf, "dest")
        _tag(dest, "CNPJ" if len(dest_doc) == 14 else "CPF", dest_doc)
        # Em homologação a SEFAZ exige este nome no destinatário (Rejeição 706).
        nome_dest = _texto_xml((destinatario or {}).get("nome") or "CONSUMIDOR", 60)
        if tp_amb == "2":
            nome_dest = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
        _tag(dest, "xNome", nome_dest)
        if modelo == "55":
            de = _tag(dest, "enderDest")
            _tag(de, "xLgr", _texto_xml(destinatario.get("logradouro"), 60))
            _tag(de, "nro", _texto_xml(destinatario.get("numero"), 60))
            _tag(de, "xBairro", _texto_xml(destinatario.get("bairro"), 60))
            _tag(de, "cMun", so_digitos(destinatario.get("codigo_municipio")))
            _tag(de, "xMun", _texto_xml(destinatario.get("municipio"), 60))
            _tag(de, "UF", uf_dest)
            _tag(de, "CEP", so_digitos(destinatario.get("cep")))
            _tag(de, "cPais", "1058")
            _tag(de, "xPais", "BRASIL")
        # indIEDest e IE precisam ser coerentes: IE só pode ir no XML quando o
        # destinatário é contribuinte (indIEDest=1) — IE com indIEDest=9 é
        # rejeitado. NFC-e é sempre não-contribuinte (9).
        ie_dest = so_digitos((destinatario or {}).get("inscricao_estadual"))
        indicador = str((destinatario or {}).get("indicador_ie") or "").strip()
        if modelo != "55":
            indicador = "9"
        elif not indicador:
            indicador = "1" if ie_dest else "9"
        _tag(dest, "indIEDest", indicador)
        if modelo == "55" and indicador == "1":
            if not ie_dest:
                raise FiscalDiretoError(
                    "Destinatário marcado como contribuinte (indIEDest=1) sem inscrição "
                    "estadual — informe a IE no cadastro do cliente.")
            _tag(dest, "IE", ie_dest)

    itens = venda.get("itens", [])
    brutos = [round(float(it["quantidade"]) * float(it["preco_unitario"]), 2) for it in itens]
    total_prod = round(sum(brutos), 2)
    desconto = round(float(venda.get("desconto") or 0), 2)
    if desconto > total_prod:           # nunca descontar mais do que o valor dos produtos
        desconto = total_prod
    descontos = _ratear(desconto, brutos)

    # Lei 12.741/2012: percentual aproximado dos tributos (tabela IBPT) definido
    # em Configurações Fiscais. Com ele preenchido o documento informa o VALOR
    # aproximado (vTotTrib por item e no total + texto no infCpl), como a lei
    # exige; com 0 a informação fica só referenciada ao IBPT.
    p_ibpt = float(config.get("ibpt_percentual") or 0)
    v_trib_total = 0.0

    v_pis_total = 0.0
    v_cofins_total = 0.0
    for idx, (item, bruto, vdesc) in enumerate(zip(itens, brutos, descontos), 1):
        prod = db.get_produto(item["produto_id"]) or {}
        qtd = float(item["quantidade"])
        val = float(item["preco_unitario"])
        det = _tag(inf, "det")
        det.set("nItem", str(idx))
        p = _tag(det, "prod")
        _tag(p, "cProd", item["produto_id"])
        _tag(p, "cEAN", prod.get("codigo_barras") or "SEM GTIN")
        _tag(p, "xProd", _texto_xml(item["nome_produto"], 120))
        _tag(p, "NCM", so_digitos(prod.get("ncm")))
        if prod.get("cest"):
            _tag(p, "CEST", so_digitos(prod.get("cest")))
        _tag(p, "CFOP", prod.get("cfop"))
        _tag(p, "uCom", (prod.get("unidade") or "UN").upper())
        _tag(p, "qCom", f"{qtd:.4f}")
        _tag(p, "vUnCom", f"{val:.4f}")
        _tag(p, "vProd", f"{bruto:.2f}")
        _tag(p, "cEANTrib", prod.get("codigo_barras") or "SEM GTIN")
        _tag(p, "uTrib", (prod.get("unidade_tributavel") or prod.get("unidade") or "UN").upper())
        _tag(p, "qTrib", f"{qtd:.4f}")
        _tag(p, "vUnTrib", f"{val:.4f}")
        if vdesc > 0:
            _tag(p, "vDesc", f"{vdesc:.2f}")
        _tag(p, "indTot", "1")
        # Base de PIS/COFINS líquida do desconto rateado (relevante p/ CST tributado).
        base_trib = round(bruto - vdesc, 2)
        imp = _tag(det, "imposto")
        if p_ibpt > 0:
            v_trib_item = round(base_trib * p_ibpt / 100, 2)
            v_trib_total = round(v_trib_total + v_trib_item, 2)
            _tag(imp, "vTotTrib", f"{v_trib_item:.2f}")
        _grupo_icms_sn(imp, prod)
        v_pis_total += _grupo_pis(imp, prod, base_trib)
        v_cofins_total += _grupo_cofins(imp, prod, base_trib)

    total = _tag(inf, "total")
    icmst = _tag(total, "ICMSTot")
    # Simples Nacional (CRT 1/4): ICMS próprio não compõe os totais (vICMS=0).
    # ST e monofásico (CSOSN 500 / CST PIS-COFINS 04..06) também não geram
    # imposto a recolher na nota — é justamente o que evita a bitributação.
    for tag in ("vBC", "vICMS", "vICMSDeson", "vFCPUFDest", "vICMSUFDest",
                "vICMSUFRemet", "vFCP", "vBCST", "vST", "vFCPST", "vFCPSTRet"):
        _tag(icmst, tag, "0.00")
    v_nf = round(total_prod - desconto, 2)
    if modelo == "65":
        # Limites nacionais da NFC-e: acima de R$ 200.000,00 a emissão é vedada
        # (use NF-e mod. 55) e acima de R$ 10.000,00 o consumidor precisa estar
        # identificado por CPF/CNPJ (Rejeição 785).
        if v_nf > 200000:
            raise FiscalDiretoError(
                "NFC-e não pode ultrapassar R$ 200.000,00 — emita NF-e (modelo 55) "
                "para esta venda.")
        if v_nf > 10000 and not dest_doc:
            raise FiscalDiretoError(
                "Venda acima de R$ 10.000,00 exige identificar o consumidor: "
                "informe CPF ou CNPJ na emissão da NFC-e.")
    _tag(icmst, "vProd", f"{total_prod:.2f}")
    _tag(icmst, "vFrete", "0.00")
    _tag(icmst, "vSeg", "0.00")
    _tag(icmst, "vDesc", f"{desconto:.2f}")
    for tag in ("vII", "vIPI", "vIPIDevol"):
        _tag(icmst, tag, "0.00")
    _tag(icmst, "vPIS", f"{v_pis_total:.2f}")
    _tag(icmst, "vCOFINS", f"{v_cofins_total:.2f}")
    _tag(icmst, "vOutro", "0.00")
    _tag(icmst, "vNF", f"{v_nf:.2f}")
    if p_ibpt > 0:
        _tag(icmst, "vTotTrib", f"{v_trib_total:.2f}")
    transp = _tag(inf, "transp")
    _tag(transp, "modFrete", "9")
    _grupo_pagamento(inf, venda, v_nf)

    # Lei 12.741/2012 — informação dos tributos no documento ao consumidor.
    if p_ibpt > 0:
        texto_trib = (f"Trib aprox R$ {v_trib_total:.2f} ({p_ibpt:.2f}%) Fonte: IBPT "
                      "- Lei 12.741/2012. ")
    else:
        texto_trib = "Lei 12.741/2012 - Valor aproximado dos tributos conforme tabela IBPT. "
    infad = _tag(inf, "infAdic")
    _tag(infad, "infCpl", texto_trib + "Documento emitido por optante pelo Simples Nacional.")

    _anexar_resp_tec(inf, config, chave)

    qrcode_url = None
    if modelo == "65" and tp_emis != "9":
        # Online: QR Code 2.00 (não usa DigestValue). Em contingência (tpEmis=9) o
        # QR é gerado após a assinatura, em inserir_qrcode_offline().
        infsupl = _tag(nfe, "infNFeSupl")
        qrcode_url = gerar_qrcode_url(chave, config, ambiente)
        _tag(infsupl, "qrCode", qrcode_url)
        _tag(infsupl, "urlChave", URL_QR_NFCE[ambiente])

    xml = ET.tostring(nfe, encoding="utf-8", xml_declaration=True).decode("utf-8")
    payload = {"modelo": modelo, "chave": chave, "ambiente": ambiente,
               "serie": serie, "numero": numero, "tp_emis": tp_emis}
    return DocumentoMontado(chave=chave, xml=xml, payload=payload,
                            qrcode_url=qrcode_url, dh_emi=dh_emi, v_nf=v_nf)


def _hash_csrt(csrt: str, chave: str) -> str:
    """hashCSRT = Base64( SHA-1( CSRT + chave_de_acesso ) ), conforme NT 2018.005."""
    digest = hashlib.sha1((csrt + chave).encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _anexar_resp_tec(inf, config: dict, chave: str) -> None:
    """Anexa o grupo infRespTec (Responsável Técnico) ao infNFe, quando habilitado.

    Desligado por padrão. MT não exige hoje (ver docs/RESPONSAVEL_TECNICO.md); este
    grupo existe como blindagem para UFs que passem a exigir. Quando ligado sem CSRT,
    envia só os dados de contato; com CSRT cadastrado na SEFAZ, inclui idCSRT/hashCSRT
    (necessário em UFs que exigem o CSRT, p. ex. PR a partir de 2026)."""
    if not config.get("resp_tec_habilitado"):
        return
    cnpj = so_digitos(config.get("resp_tec_cnpj"))
    if not cnpj:
        return
    rt = _tag(inf, "infRespTec")
    _tag(rt, "CNPJ", cnpj)
    _tag(rt, "xContato", (config.get("resp_tec_contato") or "")[:60] or "SUPORTE")
    _tag(rt, "email", (config.get("resp_tec_email") or "")[:60])
    _tag(rt, "fone", so_digitos(config.get("resp_tec_fone")))
    csrt = (config.get("resp_tec_csrt") or "").strip()
    id_csrt = (config.get("resp_tec_id_csrt") or "").strip()
    if csrt and id_csrt:
        _tag(rt, "idCSRT", id_csrt)
        _tag(rt, "hashCSRT", _hash_csrt(csrt, chave))


def _assinar_conteudo_qr3(conteudo: str, config: dict) -> str:
    """Assinatura do QR Code 3.0 offline: RSA-SHA1 do conteúdo (mesma chave do
    A1 usado na NF-e), em Base64 — NT 2025.001 / Manual DANFE-NFC-e 6.00."""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import pkcs12
    except Exception as e:
        raise FiscalDiretoError(f"Dependências de assinatura fiscal não instaladas: {e}")
    pfx = base64.b64decode(config.get("certificado_a1_b64") or "")
    senha = (config.get("certificado_senha") or "").encode()
    try:
        key, _cert, _cas = pkcs12.load_key_and_certificates(pfx, senha or None)
    except ValueError as e:
        raise FiscalDiretoError(f"Certificado A1 inválido ou senha incorreta ({e}).")
    if not key:
        raise FiscalDiretoError("Certificado A1 inválido ou senha incorreta.")
    assinatura = key.sign(conteudo.encode("utf-8"), padding.PKCS1v15(), hashes.SHA1())
    return base64.b64encode(assinatura).decode("ascii")


def gerar_qrcode_url(chave: str, config: dict, ambiente: str, *,
                     tp_emis: str = "1", dh_emi: str | None = None,
                     v_nf: float | None = None, dig_val: str | None = None,
                     dest_doc: str | None = None) -> str:
    """URL do QR Code da NFC-e — QR Code **2.00** (padrão) ou **3.0** (NT
    2025.001), conforme ``config['qrcode_versao']``.

    QR 2.00 (Manual DANFE-NFC-e/QR Code 5.1, campos separados por ``|``):
    - Online:       ``p=chave|2|tpAmb|idCSC|hash``
    - Contingência: ``p=chave|2|tpAmb|DD|vNF|digValHex|idCSC|hash`` — DD é só o
      DIA da emissão (2 dígitos) e digValHex é o TEXTO Base64 do DigestValue
      convertido a hexadecimal (não os bytes decodificados).
    ``hash = SHA-1(conteúdo + CSC)`` em hexadecimal maiúsculo; o idCSC entra
    sem zeros à esquerda.

    QR 3.0 (sem CSC; validação por assinatura digital):
    - Online:       ``p=chave|3|tpAmb``
    - Contingência: ``p=chave|3|tpAmb|DD|vNF|tpIdDest|cDest|assinatura``
    """
    tp_amb = "1" if ambiente == "producao" else "2"
    versao_qr = str(config.get("qrcode_versao") or "2").strip()
    dia = (dh_emi or "")[8:10]
    if versao_qr == "3":
        if str(tp_emis) != "9":
            return f"{URL_QR_NFCE[ambiente]}?p={chave}|3|{tp_amb}"
        doc = so_digitos(dest_doc)
        tp_id = "1" if len(doc) == 14 else ("2" if len(doc) == 11 else "")
        conteudo = f"{chave}|3|{tp_amb}|{dia}|{float(v_nf or 0):.2f}|{tp_id}|{doc}"
        return f"{URL_QR_NFCE[ambiente]}?p={conteudo}|{_assinar_conteudo_qr3(conteudo, config)}"
    id_csc = str(int(so_digitos(config.get("csc_id")) or "0"))
    csc = str(config.get("csc") or "").strip()
    if str(tp_emis) == "9":
        dig_hex = (dig_val or "").encode("utf-8").hex()
        conteudo = f"{chave}|2|{tp_amb}|{dia}|{float(v_nf or 0):.2f}|{dig_hex}|{id_csc}"
    else:
        conteudo = f"{chave}|2|{tp_amb}|{id_csc}"
    h = hashlib.sha1((conteudo + csc).encode("utf-8")).hexdigest().upper()
    return f"{URL_QR_NFCE[ambiente]}?p={conteudo}|{h}"


def inserir_qrcode_offline(xml_assinado: str, config: dict, chave: str,
                           dh_emi: str, v_nf: float, ambiente: str) -> tuple[str, str]:
    """Para a NFC-e em contingência: lê o DigestValue da assinatura (e o
    documento do consumidor, usado no QR 3.0), monta o QR offline e insere
    ``<infNFeSupl>`` logo após ``<infNFe>`` (antes da Signature). A assinatura
    cobre apenas ``infNFe``, então acrescentar o grupo suplementar como irmão
    não a invalida."""
    from lxml import etree
    root = etree.fromstring(xml_assinado.encode("utf-8"))
    dig_el = root.find(".//{http://www.w3.org/2000/09/xmldsig#}DigestValue")
    dig_val = dig_el.text if dig_el is not None else None
    dest_doc = root.findtext(f".//{{{NFE_NS}}}dest/{{{NFE_NS}}}CNPJ") or \
        root.findtext(f".//{{{NFE_NS}}}dest/{{{NFE_NS}}}CPF")
    qr = gerar_qrcode_url(chave, config, ambiente, tp_emis="9", dh_emi=dh_emi,
                          v_nf=v_nf, dig_val=dig_val, dest_doc=dest_doc)
    infnfe = root.find(f"{{{NFE_NS}}}infNFe")
    infsupl = etree.Element(f"{{{NFE_NS}}}infNFeSupl")
    etree.SubElement(infsupl, f"{{{NFE_NS}}}qrCode").text = qr
    etree.SubElement(infsupl, f"{{{NFE_NS}}}urlChave").text = URL_QR_NFCE[ambiente]
    infnfe.addnext(infsupl)
    return etree.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8"), qr


def assinar_xml(xml: str, config: dict) -> str:
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12
        from lxml import etree
        from signxml import XMLSigner, methods
    except Exception as e:
        raise FiscalDiretoError(f"Dependências de assinatura fiscal não instaladas: {e}")
    pfx = base64.b64decode(config.get("certificado_a1_b64") or "")
    senha = (config.get("certificado_senha") or "").encode()
    try:
        key, cert, _cas = pkcs12.load_key_and_certificates(pfx, senha or None)
    except ValueError as e:
        raise FiscalDiretoError(f"Certificado A1 inválido ou senha incorreta ({e}).")
    if not key or not cert:
        raise FiscalDiretoError("Certificado A1 inválido ou senha incorreta.")
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    root = etree.fromstring(xml.encode("utf-8"))
    inf = root.find(f".//{{{NFE_NS}}}infNFe")
    if inf is None:
        inf = root.find(f".//{{{NFE_NS}}}infEvento")
    if inf is None or not inf.get("Id"):
        raise FiscalDiretoError("XML fiscal sem identificador para assinatura.")
    ref = "#" + inf.get("Id")
    class NFeXMLSigner(XMLSigner):
        def check_deprecated_methods(self):
            return

    # A NF-e/NFC-e exige C14N **não-exclusiva** (REC-xml-c14n-20010315) tanto no
    # CanonicalizationMethod quanto no Transform da Reference. O padrão do signxml
    # é a C14N exclusiva (xml-exc-c14n#), que a SEFAZ rejeita (Rejeição 297).
    c14n_nfe = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    signed = NFeXMLSigner(
        method=methods.enveloped, digest_algorithm="sha1",
        signature_algorithm="rsa-sha1", c14n_algorithm=c14n_nfe,
    ).sign(root, key=key_pem, cert=cert_pem, reference_uri=ref)
    return etree.tostring(signed, encoding="utf-8", xml_declaration=True).decode("utf-8")


def montar_soap(servico: str, conteudo_xml: str) -> tuple[bytes, dict]:
    """Monta o envelope SOAP 1.2 e os headers do serviço.

    O ``<nfeDadosMsg>`` precisa estar no namespace do WSDL da operação
    (``.../nfe/wsdl/<Operação>``) e o Content-Type precisa do parâmetro
    ``action="<namespace>/<método>"`` — com o namespace do leiaute (portalfiscal
    /nfe) no lugar errado o servidor da SEFAZ não reconhece a operação e a
    transmissão falha sempre."""
    operacao, metodo = _SOAP_OP[servico]
    ns = f"http://www.portalfiscal.inf.br/nfe/wsdl/{operacao}"
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
        f'<soap12:Body><nfeDadosMsg xmlns="{ns}">{conteudo_xml}</nfeDadosMsg></soap12:Body>'
        '</soap12:Envelope>'
    )
    headers = {"Content-Type": f'application/soap+xml; charset=utf-8; action="{ns}/{metodo}"'}
    return body.encode("utf-8"), headers


def _post_soap(modelo: str, servico: str, conteudo_xml: str, config: dict) -> dict:
    """Envia a mensagem ao webservice SEFAZ-MT com o certificado A1 (mTLS)."""
    try:
        import requests
        from requests_pkcs12 import Pkcs12Adapter
    except Exception as e:
        raise FiscalDiretoError(f"Dependências de transmissão fiscal não instaladas: {e}")
    ambiente = config.get("ambiente") or "homologacao"
    url = WS.get((str(modelo), ambiente, servico))
    if not url:
        raise FiscalDiretoError(
            f"Webservice SEFAZ-MT não configurado para modelo {modelo}/{ambiente}/{servico}.")
    if not config.get("certificado_a1_b64") or not config.get("certificado_senha"):
        raise FiscalDiretoError("Informe o certificado A1 da loja e a senha em Configurações Fiscais.")
    pfx = base64.b64decode(config.get("certificado_a1_b64") or "")
    senha = config.get("certificado_senha") or ""
    body, headers = montar_soap(servico, conteudo_xml)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pfx") as fp:
        fp.write(pfx)
        pfx_path = fp.name
    try:
        sess = requests.Session()
        sess.mount("https://", Pkcs12Adapter(pkcs12_filename=pfx_path, pkcs12_password=senha))
        resp = sess.post(url, data=body, headers=headers, timeout=30)
        return {"status_code": resp.status_code, "texto": resp.text}
    finally:
        try:
            Path(pfx_path).unlink(missing_ok=True)
        except Exception:
            pass


def transmitir_autorizacao(modelo: str, xml_assinado: str, config: dict) -> dict:
    xml_inner = _sem_declaracao_xml(xml_assinado)
    envi = (f'<enviNFe xmlns="{NFE_NS}" versao="{VERSAO}">'
            f'<idLote>1</idLote><indSinc>1</indSinc>{xml_inner}</enviNFe>')
    return _post_soap(modelo, "autorizacao", envi, config)


def _texto(el, nome: str) -> str | None:
    if el is None:
        return None
    achado = el.find(f".//{{*}}{nome}")
    if achado is None:
        achado = el.find(nome)
    if achado is None or achado.text is None:
        return None
    return achado.text.strip()


def _sem_declaracao_xml(xml: str | None) -> str:
    return (xml or "").split("?>", 1)[-1].strip()


def _xml_autorizado(xml_assinado: str | None, prot_el) -> str | None:
    if not xml_assinado or prot_el is None:
        return None
    prot_xml = ET.tostring(prot_el, encoding="utf-8").decode("utf-8")
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<nfeProc xmlns="{NFE_NS}" versao="{VERSAO}">'
        f'{_sem_declaracao_xml(xml_assinado)}{prot_xml}'
        f'</nfeProc>'
    )


def normalizar_retorno_sefaz(texto: str | None, xml_assinado: str | None = None,
                             http_status: int | None = None) -> dict:
    """Interpreta retorno SOAP/XML da SEFAZ e devolve campos de notas_fiscais."""
    if not texto:
        return {
            "status": "rejeitada" if http_status and http_status >= 400 else "processando",
            "mensagem": "SEFAZ não retornou corpo de resposta.",
        }
    try:
        root = ET.fromstring(texto.encode("utf-8"))
    except ET.ParseError:
        return {
            "status": "rejeitada" if http_status and http_status >= 400 else "processando",
            "mensagem": texto[:500],
        }

    inf_prot = root.find(".//{*}infProt")
    prot = root.find(".//{*}protNFe")
    if inf_prot is not None:
        cstat = _texto(inf_prot, "cStat")
        motivo = _texto(inf_prot, "xMotivo") or "Retorno SEFAZ sem motivo."
        protocolo = _texto(inf_prot, "nProt")
        if cstat in {"100", "150"}:
            return {
                "status": "autorizada",
                "protocolo": protocolo,
                "mensagem": motivo,
                "xml_autorizado": _xml_autorizado(xml_assinado, prot),
                "motivo_rejeicao": None,
                "cstat": cstat,
            }
        if cstat in {"101", "135", "155"}:
            return {"status": "cancelada", "protocolo": protocolo, "mensagem": motivo, "cstat": cstat}
        return {
            "status": "rejeitada",
            "protocolo": protocolo,
            "mensagem": motivo,
            "motivo_rejeicao": motivo,
            "cstat": cstat,
        }

    cstat = _texto(root, "cStat")
    motivo = _texto(root, "xMotivo") or "Retorno SEFAZ recebido."
    recibo = _texto(root, "nRec")
    if cstat in {"103", "105", "106"}:
        return {"status": "processando", "mensagem": motivo, "recibo": recibo, "cstat": cstat}
    if cstat in {"100", "150"}:
        return {"status": "autorizada", "mensagem": motivo, "recibo": recibo, "cstat": cstat}
    if http_status and http_status >= 400:
        return {"status": "rejeitada", "mensagem": motivo, "motivo_rejeicao": motivo,
                "recibo": recibo, "cstat": cstat}
    return {"status": "processando", "mensagem": motivo, "recibo": recibo, "cstat": cstat}


def normalizar_retorno_evento(texto: str | None, http_status: int | None = None) -> dict:
    if not texto:
        return {
            "status": "rejeitada" if http_status and http_status >= 400 else "processando",
            "mensagem": "SEFAZ não retornou corpo de resposta do evento.",
        }
    try:
        root = ET.fromstring(texto.encode("utf-8"))
    except ET.ParseError:
        return {
            "status": "rejeitada" if http_status and http_status >= 400 else "processando",
            "mensagem": texto[:500],
        }
    inf_evento = root.find(".//{*}retEvento/{*}infEvento")
    if inf_evento is None:
        inf_evento = root.find(".//{*}infEvento")
    alvo = inf_evento if inf_evento is not None else root
    cstat = _texto(alvo, "cStat")
    motivo = _texto(alvo, "xMotivo") or "Retorno de evento recebido."
    protocolo = _texto(alvo, "nProt")
    if cstat in {"135", "155"}:
        return {"status": "cancelada", "protocolo": protocolo, "mensagem": motivo}
    if http_status and http_status >= 400:
        return {"status": "rejeitada", "mensagem": motivo, "motivo_rejeicao": motivo}
    return {"status": "processando", "mensagem": motivo, "motivo_rejeicao": motivo if cstat else None}


def consultar_chave(modelo: str, chave: str, config: dict) -> dict:
    ambiente = config.get("ambiente") or "homologacao"
    tp_amb = "1" if ambiente == "producao" else "2"
    cons = (f'<consSitNFe xmlns="{NFE_NS}" versao="{VERSAO}"><tpAmb>{tp_amb}</tpAmb>'
            f'<xServ>CONSULTAR</xServ><chNFe>{so_digitos(chave)}</chNFe></consSitNFe>')
    return _post_soap(modelo, "consulta", cons, config)


def montar_cancelamento_xml(nota: dict, config: dict, justificativa: str) -> str:
    chave = so_digitos(nota.get("chave"))
    protocolo = str(nota.get("protocolo") or "").strip()
    if not chave:
        raise FiscalDiretoError("Nota sem chave de acesso para cancelamento.")
    if not protocolo:
        raise FiscalDiretoError("Nota sem protocolo de autorização para cancelamento.")
    justificativa = _texto_xml(justificativa, 255)
    if len(justificativa) < 15:
        raise FiscalDiretoError("A justificativa de cancelamento deve ter de 15 a 255 caracteres.")
    ambiente = config.get("ambiente") or "homologacao"
    tp_amb = "1" if ambiente == "producao" else "2"
    evento = ET.Element(f"{{{NFE_NS}}}evento")
    evento.set("versao", "1.00")
    inf = _tag(evento, "infEvento")
    inf.set("Id", f"ID110111{chave}01")
    _tag(inf, "cOrgao", C_UF_MT)
    _tag(inf, "tpAmb", tp_amb)
    _tag(inf, "CNPJ", so_digitos(config.get("cnpj")))
    _tag(inf, "chNFe", chave)
    _tag(inf, "dhEvento", agora_mt())
    _tag(inf, "tpEvento", "110111")
    _tag(inf, "nSeqEvento", "1")
    _tag(inf, "verEvento", "1.00")
    det = _tag(inf, "detEvento")
    det.set("versao", "1.00")
    _tag(det, "descEvento", "Cancelamento")
    _tag(det, "nProt", protocolo)
    _tag(det, "xJust", justificativa.strip())
    return ET.tostring(evento, encoding="utf-8", xml_declaration=True).decode("utf-8")


def transmitir_evento(modelo: str, xml_evento_assinado: str, config: dict) -> dict:
    xml_inner = _sem_declaracao_xml(xml_evento_assinado)
    env = (f'<envEvento xmlns="{NFE_NS}" versao="1.00"><idLote>1</idLote>'
           f'{xml_inner}</envEvento>')
    return _post_soap(modelo, "evento", env, config)


def cancelar_documento(nota: dict, config: dict, justificativa: str) -> dict:
    xml_evento = montar_cancelamento_xml(nota, config, justificativa)
    xml_evento_assinado = assinar_xml(xml_evento, config)
    retorno = transmitir_evento(nota.get("modelo") or "65", xml_evento_assinado, config)
    return {"xml_evento": xml_evento_assinado, "retorno": retorno}


def preparar_e_tentar_transmitir(venda: dict, config: dict, modelo: str = "65",
                                 cpf_consumidor: str | None = None,
                                 destinatario: dict | None = None) -> dict:
    """Monta, assina e tenta transmitir. Trata a queda de internet sem perder o
    número fiscal nem deixar a venda sem nota:

    - **Sem conexão** (NFC-e): emite em **contingência offline** (tpEmis=9), com
      QR Code offline, para imprimir o DANFE na hora e transmitir depois
      (``contingencia=True``).
    - **Sem resposta** após enviar (ex.: timeout de leitura): grava como
      ``pendente=True`` para o loop **consultar** pela chave (não retransmite, p/
      não duplicar — pode ter sido autorizada).
    """
    # Valida tudo ANTES de reservar a numeração: config/produto errado não pode
    # queimar número fiscal (buraco de numeração exige inutilização na SEFAZ).
    _validar_certificado(config, modelo)
    _validar_emitente(config)
    validar_itens(venda)
    try:
        import requests
        sem_conexao = (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout)
    except Exception:
        sem_conexao = (OSError,)

    serie, numero = db.consumir_numero_fiscal(modelo)
    doc = montar_documento(venda, config, modelo, cpf_consumidor, destinatario, serie, numero)
    xml_assinado = assinar_xml(doc.xml, config)
    base = {
        "serie": serie, "numero": numero, "chave": doc.chave, "xml_assinado": xml_assinado,
        "payload": json.dumps(doc.payload, ensure_ascii=False), "qrcode_url": doc.qrcode_url,
    }
    try:
        base["retorno"] = transmitir_autorizacao(modelo, xml_assinado, config)
        return base
    except FiscalDiretoError:
        raise
    except sem_conexao:
        if modelo == "65":
            dh_cont = agora_mt()
            doc9 = montar_documento(venda, config, modelo, cpf_consumidor, destinatario,
                                    serie, numero, tp_emis="9", dh_cont=dh_cont)
            xml9 = assinar_xml(doc9.xml, config)
            ambiente = config.get("ambiente") or "homologacao"
            xml9, qr9 = inserir_qrcode_offline(xml9, config, doc9.chave, doc9.dh_emi, doc9.v_nf, ambiente)
            return {
                "serie": serie, "numero": numero, "chave": doc9.chave, "xml_assinado": xml9,
                "payload": json.dumps(doc9.payload, ensure_ascii=False), "qrcode_url": qr9,
                "contingencia": True,
            }
        base["pendente"] = True       # NF-e (55) não usa contingência offline: deixa pendente
        return base
    except Exception:
        base["pendente"] = True       # enviou mas não obteve resposta → consultar depois
        return base
