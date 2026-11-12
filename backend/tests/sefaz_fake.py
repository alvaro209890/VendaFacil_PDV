"""Servidor SOAP local para testes da integração fiscal direta.

Não configura URLs de teste no produto: o fixture troca WS em memória e o
servidor só escuta loopback. As respostas usam os envelopes e leiautes SEFAZ.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from typing import Any


NS = "http://www.portalfiscal.inf.br/nfe"
SOAP = "http://www.w3.org/2003/05/soap-envelope"


def _nfe(fragment: str) -> str:
    return f'<soap:Envelope xmlns:soap="{SOAP}"><soap:Body>{fragment}</soap:Body></soap:Envelope>'


def retorno_autorizacao(cstat: str = "100", motivo: str = "Autorizado o uso da NF-e",
                       protocolo: str = "151260000000001", chave: str | None = None,
                       recebido_em: str | None = None) -> str:
    recebido_em = recebido_em or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if cstat in {"103", "105", "106"}:
        recibo = "151260000000000" if cstat in {"103", "105"} else ""
        return _nfe(
            f'<retEnviNFe xmlns="{NS}" versao="4.00"><tpAmb>2</tpAmb><cStat>{cstat}</cStat>'
            f'<xMotivo>{motivo}</xMotivo><nRec>{recibo}</nRec></retEnviNFe>'
        )
    chave_xml = f"<chNFe>{chave}</chNFe>" if chave else ""
    return _nfe(
        f'<retEnviNFe xmlns="{NS}" versao="4.00"><tpAmb>2</tpAmb><cStat>104</cStat>'
        '<xMotivo>Lote processado</xMotivo><protNFe versao="4.00"><infProt>'
        f'{chave_xml}<dhRecbto>{recebido_em}</dhRecbto><nProt>{protocolo}</nProt>'
        f'<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>'
        '</infProt></protNFe></retEnviNFe>'
    )


def retorno_consulta(cstat: str = "100", motivo: str = "Autorizado o uso da NF-e",
                     protocolo: str = "151260000000001", chave: str | None = None,
                     recebido_em: str | None = None) -> str:
    recebido_em = recebido_em or datetime.now(timezone.utc).isoformat(timespec="seconds")
    chave_xml = f"<chNFe>{chave}</chNFe>" if chave else ""
    if cstat == "217":
        return _nfe(
            f'<retConsSitNFe xmlns="{NS}" versao="4.00"><tpAmb>2</tpAmb>'
            f'<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>{chave_xml}</retConsSitNFe>'
        )
    return _nfe(
        f'<retConsSitNFe xmlns="{NS}" versao="4.00"><tpAmb>2</tpAmb><cStat>{cstat}</cStat>'
        f'<xMotivo>{motivo}</xMotivo>{chave_xml}<protNFe versao="4.00"><infProt>'
        f'{chave_xml}<dhRecbto>{recebido_em}</dhRecbto><nProt>{protocolo}</nProt>'
        f'<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>'
        '</infProt></protNFe></retConsSitNFe>'
    )


def retorno_evento(cstat: str = "135", motivo: str = "Evento registrado e vinculado a NF-e",
                   protocolo: str = "151260000000009") -> str:
    return _nfe(
        f'<retEnvEvento xmlns="{NS}" versao="1.00"><idLote>1</idLote><tpAmb>2</tpAmb>'
        '<verAplic>SVRS2026</verAplic><cOrgao>51</cOrgao><cStat>128</cStat>'
        '<xMotivo>Lote de Evento Processado</xMotivo><retEvento versao="1.00"><infEvento>'
        f'<cOrgao>51</cOrgao><tpAmb>2</tpAmb><cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>'
        f'<nProt>{protocolo}</nProt></infEvento></retEvento></retEnvEvento>'
    )


def retorno_inutilizacao(cstat: str = "102", motivo: str = "Inutilização de número homologado",
                         protocolo: str = "151260000000010") -> str:
    return _nfe(
        f'<retInutNFe xmlns="{NS}" versao="4.00"><infInut><tpAmb>2</tpAmb><verAplic>SVRS2026</verAplic>'
        f'<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo><ano>26</ano><CNPJ>12345678000195</CNPJ>'
        f'<mod>65</mod><serie>1</serie><nNFIni>4</nNFIni><nNFFin>4</nNFFin><dhRecbto>2026-11-12T10:00:00-04:00</dhRecbto>'
        f'<nProt>{protocolo}</nProt></infInut></retInutNFe>'
    )


def retorno_status(cstat: str = "107", motivo: str = "Serviço em Operação") -> str:
    return _nfe(
        f'<retConsStatServ xmlns="{NS}" versao="4.00"><tpAmb>2</tpAmb><verAplic>SVRS2026</verAplic>'
        f'<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo><cUF>51</cUF><dhRecbto>2026-11-12T10:00:00-04:00</dhRecbto>'
        '<tMed>1</tMed><dhRetorno></dhRetorno><xObs></xObs></retConsStatServ>'
    )


@dataclass
class Reply:
    body: str
    status: int = 200
    delay: float = 0


class SefazFake:
    """Fila independente por serviço; registra cada requisição SOAP recebida."""

    def __init__(self) -> None:
        self.queues: dict[str, deque[Reply]] = defaultdict(deque)
        self.calls: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8", errors="replace")
                service = owner.service_from_path(self.path)
                with owner.lock:
                    owner.calls.append({"service": service, "path": self.path,
                                        "headers": dict(self.headers), "body": body})
                    reply = owner.queues[service].popleft() if owner.queues[service] else owner.default(service)
                if reply.delay:
                    time.sleep(reply.delay)
                raw = reply.body.encode("utf-8")
                self.send_response(reply.status)
                self.send_header("Content-Type", "application/soap+xml; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    @staticmethod
    def service_from_path(path: str) -> str:
        tail = path.rstrip("/").rsplit("/", 1)[-1].lower()
        if "autorizacao" in tail:
            return "autorizacao"
        if "consulta" in tail:
            return "consulta"
        if "evento" in tail:
            return "evento"
        if "inutil" in tail:
            return "inutilizacao"
        if "status" in tail:
            return "status"
        return tail

    @staticmethod
    def default(service: str) -> Reply:
        body = {"autorizacao": retorno_autorizacao,
                "consulta": retorno_consulta,
                "evento": retorno_evento,
                "inutilizacao": retorno_inutilizacao,
                "status": retorno_status}.get(service, retorno_autorizacao)()
        return Reply(body)

    def push(self, service: str, body: str, status: int = 200, delay: float = 0) -> None:
        with self.lock:
            self.queues[service].append(Reply(body, status, delay))

    def endpoint(self, service: str, modelo: str = "65", ambiente: str = "homologacao") -> str:
        # Paridade no nome do endpoint evita que a rotina de inferência do
        # serviço dependa de qualquer configuração do produto.
        names = {"autorizacao": "NfeAutorizacao4", "consulta": "NfeConsulta4",
                 "evento": "RecepcaoEvento4", "inutilizacao": "NfeInutilizacao4",
                 "status": "NfeStatusServico4"}
        prefix = "nfcews/services" if modelo == "65" else "nfews/v2/services"
        return f"{self.base_url}/{prefix}/{names[service]}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def unused_endpoint(self, service: str, modelo: str = "65") -> str:
        # Reserve then close an ephemeral loopback port for deterministic
        # connection refusal without contacting any external host.
        import socket
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        names = {"autorizacao": "NfeAutorizacao4", "consulta": "NfeConsulta4",
                 "evento": "RecepcaoEvento4"}
        return f"http://127.0.0.1:{port}/{names[service]}"
