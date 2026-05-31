"""Emissão de NFC-e (modelo 65) via gateway fiscal.

NÃO falamos direto com a SEFAZ. Usamos um gateway (Focus NFe ou PlugNotas) que
cuida de assinatura, transmissão, contingência e devolve a nota autorizada +
DANFE + QR Code. O certificado digital A1 e o CSC ficam cadastrados NO PAINEL DO
GATEWAY — o .exe só guarda o token de API.

Fluxo:
  1. monta o payload a partir da venda + dados fiscais dos produtos + emitente;
  2. envia ao gateway (assíncrono → status "processando");
  3. consulta o status (loop em background reprocessa as pendentes);
  4. guarda chave/protocolo/links de XML e DANFE em notas_fiscais.
"""
import base64
import json
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from database import db

INTERVALO_SEG = 45
_TIMEOUT = 25

# Mapa forma de pagamento interna → código NFC-e (tag tPag)
_FORMA_PAGTO = {
    "dinheiro": "01", "credito": "03", "debito": "04",
    "pix": "17", "fiado": "99", "outros": "99",
}


class FiscalError(Exception):
    pass


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _data_emissao() -> str:
    # ISO com offset de Brasília (-03:00), exigido pela NFC-e.
    return datetime.now(timezone(timedelta(hours=-3))).replace(microsecond=0).isoformat()


# ─────────────────────────── Gateways ───────────────────────────
class FocusNFe:
    """Gateway Focus NFe (https://focusnfe.com.br) — NFC-e."""

    def __init__(self, token: str, ambiente: str):
        self.token = token
        self.base = (
            "https://api.focusnfe.com.br" if ambiente == "producao"
            else "https://homologacao.focusnfe.com.br"
        )

    def _req(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        url = f"{self.base}{path}"
        auth = base64.b64encode(f"{self.token}:".encode()).decode()
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode() or "{}")
            except Exception:
                return e.code, {"mensagem": str(e)}

    def emitir(self, ref: str, payload: dict) -> tuple[int, dict]:
        return self._req("POST", f"/v2/nfce?ref={ref}", payload)

    def consultar(self, ref: str) -> tuple[int, dict]:
        return self._req("GET", f"/v2/nfce/{ref}?completa=1")

    def cancelar(self, ref: str, justificativa: str) -> tuple[int, dict]:
        return self._req("DELETE", f"/v2/nfce/{ref}", {"justificativa": justificativa})

    @staticmethod
    def normalizar_status(resp: dict) -> dict:
        s = (resp.get("status") or "").lower()
        mapa = {
            "autorizado": "autorizada",
            "processando_autorizacao": "processando",
            "erro_autorizacao": "rejeitada",
            "denegado": "rejeitada",
            "cancelado": "cancelada",
        }
        return {
            "status": mapa.get(s, "processando" if s else "pendente"),
            "chave": resp.get("chave_nfe"),
            "numero": resp.get("numero"),
            "serie": resp.get("serie"),
            "protocolo": resp.get("protocolo") or resp.get("numero_protocolo"),
            "mensagem": resp.get("mensagem_sefaz") or resp.get("mensagem") or resp.get("erros"),
            "xml_url": _abs_focus(resp.get("caminho_xml_nota_fiscal")),
            "danfe_url": _abs_focus(resp.get("caminho_danfe")),
            "qrcode_url": resp.get("qrcode_url") or resp.get("url_consulta_nf"),
        }


def _abs_focus(caminho: str | None) -> str | None:
    if not caminho:
        return None
    if caminho.startswith("http"):
        return caminho
    return f"https://app.focusnfe.com.br{caminho}"


def _qr_base64(texto: str) -> str:
    """Gera o QR Code (PNG base64) do conteúdo de consulta da NFC-e."""
    import io
    import qrcode
    img = qrcode.make(texto, box_size=4, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def anexar_qrcode(nota: dict | None) -> dict | None:
    """Acrescenta `qrcode_base64` à nota autorizada (para imprimir o cupom
    fiscal na térmica). Não persiste — é só para a resposta."""
    if not nota or nota.get("status") != "autorizada" or not nota.get("qrcode_url"):
        return nota
    try:
        nota = dict(nota)
        nota["qrcode_base64"] = _qr_base64(nota["qrcode_url"])
    except Exception:
        pass
    return nota


class PlugNotas:
    """Gateway PlugNotas (esqueleto). A API difere do Focus; preencher conforme
    a documentação (https://docs.plugnotas.com.br). Estrutura pronta para implementar."""

    def __init__(self, token: str, ambiente: str):
        self.token = token
        self.base = "https://api.plugnotas.com.br"  # sandbox: api.sandbox.plugnotas.com.br

    def emitir(self, ref: str, payload: dict) -> tuple[int, dict]:
        raise FiscalError("Gateway PlugNotas ainda não implementado — use 'focusnfe'.")

    def consultar(self, ref: str) -> tuple[int, dict]:
        raise FiscalError("Gateway PlugNotas ainda não implementado.")

    def cancelar(self, ref: str, justificativa: str) -> tuple[int, dict]:
        raise FiscalError("Gateway PlugNotas ainda não implementado.")

    @staticmethod
    def normalizar_status(resp: dict) -> dict:
        return {"status": "processando"}


def _gateway(config: dict):
    nome = (config.get("gateway") or "focusnfe").lower()
    token = config.get("gateway_token") or ""
    ambiente = config.get("ambiente") or "homologacao"
    if not token:
        raise FiscalError("Token do gateway não configurado (Configurações Fiscais).")
    if nome == "plugnotas":
        return PlugNotas(token, ambiente)
    return FocusNFe(token, ambiente)


# ─────────────────────────── Payload NFC-e (formato Focus) ───────────────────────────
def montar_payload(venda: dict, config: dict, cpf: str | None = None) -> dict:
    itens = []
    for i, it in enumerate(venda.get("itens", []), start=1):
        prod = db.get_produto(it["produto_id"]) or {}
        unidade = (prod.get("unidade") or "UN").upper()
        und_trib = (prod.get("unidade_tributavel") or unidade).upper()
        itens.append({
            "numero_item": i,
            "codigo_produto": str(it["produto_id"]),
            "descricao": it["nome_produto"],
            "codigo_ncm": prod.get("ncm") or "00000000",
            "cest": prod.get("cest") or None,
            "cfop": prod.get("cfop") or "5102",
            "unidade_comercial": unidade,
            "quantidade_comercial": it["quantidade"],
            "valor_unitario_comercial": round(it["preco_unitario"], 4),
            "valor_bruto": round(it["subtotal"], 2),
            "unidade_tributavel": und_trib,
            "quantidade_tributavel": it["quantidade"],
            "valor_unitario_tributavel": round(it["preco_unitario"], 4),
            "icms_origem": prod.get("origem") or "0",
            "icms_situacao_tributaria": prod.get("cst_csosn") or "102",
            "icms_aliquota": prod.get("aliquota_icms") or 0,
            "pis_situacao_tributaria": prod.get("cst_pis") or "07",
            "cofins_situacao_tributaria": prod.get("cst_cofins") or "07",
        })

    forma = _FORMA_PAGTO.get(venda.get("forma_pagamento", "dinheiro"), "99")
    total = round(venda.get("total", 0), 2)

    payload = {
        "cnpj_emitente": _so_digitos(config.get("cnpj", "")),
        "data_emissao": _data_emissao(),
        "presenca_comprador": 1,             # operação presencial
        "modalidade_frete": 9,               # sem frete
        "local_destino": 1,                  # operação interna
        "natureza_operacao": "VENDA AO CONSUMIDOR",
        "tipo_documento": 1,                 # saída
        "finalidade_emissao": 1,             # normal
        "consumidor_final": 1,
        "items": itens,
        "formas_pagamento": [
            {"forma_pagamento": forma, "valor_pagamento": total},
        ],
        "valor_desconto": round(venda.get("desconto", 0), 2) or None,
        "informacoes_adicionais_contribuinte": "Lei 12.741/2012: Valor aproximado dos tributos conforme tabela IBPT.",
    }
    if cpf:
        cpf_limpo = _so_digitos(cpf)
        if len(cpf_limpo) == 11:
            payload["cpf_destinatario"] = cpf_limpo
        elif len(cpf_limpo) == 14:
            payload["cnpj_destinatario"] = cpf_limpo

    return payload


def _so_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


# ─────────────────────────── Serviço ───────────────────────────
def _validar_config(config: dict) -> None:
    if not config.get("habilitado"):
        raise FiscalError("Emissão fiscal desativada (ative em Configurações Fiscais).")
    faltando = [c for c in ("cnpj", "gateway_token") if not config.get(c)]
    if faltando:
        raise FiscalError(f"Configuração fiscal incompleta: {', '.join(faltando)}.")


def emitir_nfce(venda_id: int, user_id: int, cpf: str | None = None) -> dict:
    venda = db.get_venda_completa(venda_id, user_id)
    if not venda:
        raise FiscalError("Venda não encontrada.")
    existente = db.get_nota_por_venda(venda_id)
    if existente and existente["status"] in ("autorizada", "processando", "pendente"):
        return existente

    config = db.get_config_fiscal()
    _validar_config(config)
    gw = _gateway(config)

    serie, numero = db.consumir_numero_nfce()
    ref = f"v{venda_id}-{numero}"
    payload = montar_payload(venda, config, cpf=cpf)
    payload["serie"] = serie
    payload["numero"] = numero

    nota = db.criar_nota({
        "venda_id": venda_id, "user_id": user_id, "ref": ref, "modelo": "65",
        "numero": numero, "serie": serie, "ambiente": config.get("ambiente"),
        "status": "pendente", "payload": json.dumps(payload, ensure_ascii=False),
        "criado_em": _agora(), "atualizado_em": _agora(),
    })

    try:
        code, resp = gw.emitir(ref, payload)
    except (urllib.error.URLError, OSError):
        # Offline → fica pendente; o loop de contingência reenvia depois.
        return db.atualizar_nota(nota["id"], {"status": "pendente",
                "mensagem": "Sem conexão — será transmitida automaticamente."}, _agora())

    dados = gw.normalizar_status(resp)
    if code >= 400 and dados["status"] == "pendente":
        dados["status"] = "rejeitada"
    return db.atualizar_nota(nota["id"], dados, _agora())


def consultar_nfce(nota_id: int) -> dict:
    nota = db.get_nota(nota_id)
    if not nota:
        raise FiscalError("Nota não encontrada.")
    config = db.get_config_fiscal()
    gw = _gateway(config)
    code, resp = gw.consultar(nota["ref"])
    dados = gw.normalizar_status(resp)
    return db.atualizar_nota(nota_id, dados, _agora())


def cancelar_nfce(nota_id: int, justificativa: str) -> dict:
    if len(justificativa) < 15:
        raise FiscalError("A justificativa de cancelamento deve ter ao menos 15 caracteres.")
    nota = db.get_nota(nota_id)
    if not nota:
        raise FiscalError("Nota não encontrada.")
    if nota["status"] != "autorizada":
        raise FiscalError("Só é possível cancelar uma nota autorizada.")
    config = db.get_config_fiscal()
    gw = _gateway(config)
    gw.cancelar(nota["ref"], justificativa)
    return db.atualizar_nota(nota_id, {"status": "cancelada", "mensagem": justificativa}, _agora())


def processar_pendentes() -> int:
    """Reenvia/consulta notas pendentes (contingência)."""
    config = db.get_config_fiscal()
    if not config.get("habilitado") or not config.get("gateway_token"):
        return 0
    feitas = 0
    for nota in db.notas_pendentes():
        try:
            payload = json.loads(nota.get("payload") or "{}")
            gw = _gateway(config)
            # Tenta emitir de novo (idempotente pela ref); se já existir, consulta.
            code, resp = gw.emitir(nota["ref"], payload)
            if code == 422 or (isinstance(resp, dict) and resp.get("status")):
                code, resp = gw.consultar(nota["ref"])
            db.atualizar_nota(nota["id"], gw.normalizar_status(resp), _agora())
            feitas += 1
        except Exception:
            continue
    return feitas


def _loop() -> None:
    while True:
        try:
            processar_pendentes()
        except Exception:
            pass
        time.sleep(INTERVALO_SEG)


def iniciar_em_background() -> None:
    t = threading.Thread(target=_loop, daemon=True, name="vf-fiscal")
    t.start()
