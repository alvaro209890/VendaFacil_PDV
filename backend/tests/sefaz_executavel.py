"""Servidor local da fixture do .exe. Aceita apenas SOAP sintético em homologação."""
import re
import socketserver
import ssl
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from sefaz_fake import retorno_autorizacao, retorno_consulta
from test_sefaz_simulador import _certificado_teste

HOST = "homologacao.sefaz.mt.gov.br"


def emissor_teste() -> dict:
    return {
        "habilitado": True, "provedor_fiscal": "sefaz_mt_direto", "ambiente": "homologacao",
        "cnpj": "12345678000195", "razao_social": "Mercearia Açúcar de Teste", "cnae": "4712100",
        "inscricao_estadual": "00130000019", "regime_tributario": "1",
        "logradouro": "Rua Teste", "numero": "100", "bairro": "Centro",
        "municipio": "Cuiabá", "codigo_municipio": "5103403", "uf": "MT", "cep": "78000000",
        "csc": "CSC-DE-TESTE", "csc_id": "1", "serie_nfce": 1, "proximo_numero_nfce": 1,
        "certificado_a1_b64": _certificado_teste(), "certificado_senha": "somente-teste",
    }


def _certificado_servidor(pasta: Path) -> tuple[ssl.SSLContext, Path]:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOST)])
    agora = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome).public_key(chave.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(agora - timedelta(minutes=5))
            .not_valid_after(agora + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(HOST)]), critical=False)
            .sign(chave, hashes.SHA256()))
    pem, priv = pasta / "sefaz-teste.pem", pasta / "sefaz-teste-key.pem"
    pem.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    priv.write_bytes(chave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(pem, priv)
    return ctx, pem


def _ler_cabecalhos(stream) -> tuple[bytes, dict]:
    primeira = stream.readline(8192).strip()
    campos = {}
    for _ in range(40):
        linha = stream.readline(8192).strip()
        if not linha:
            return primeira, campos
        nome, _, valor = linha.partition(b":")
        campos[nome.lower()] = valor.strip()
    raise ValueError("Cabeçalho inesperado na fixture")


class _SoapFixture(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        try:
            with self.request.makefile("rb", buffering=0) as stream:
                linha, _ = _ler_cabecalhos(stream)
            if linha.split()[:2] != [b"CONNECT", f"{HOST}:443".encode()]:
                self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                return
            self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            with self.server.ctx.wrap_socket(self.request, server_side=True) as tls:
                with tls.makefile("rb") as stream:
                    linha, cabecalhos = _ler_cabecalhos(stream)
                    tamanho = int(cabecalhos.get(b"content-length", b"0"))
                    if not 0 < tamanho <= 2_000_000:
                        return
                    dados = stream.read(tamanho)
                if linha.startswith(b"POST /nfcews/services/NfeAutorizacao4 "):
                    chave = re.search(rb'Id="NFe(\d{44})"', dados).group(1).decode()
                    self.server.autorizadas.add(chave)
                    corpo = retorno_autorizacao(chave=chave)
                elif linha.startswith(b"POST /nfcews/services/NfeConsulta4 "):
                    chave = re.search(rb"<chNFe>(\d{44})</chNFe>", dados).group(1).decode()
                    corpo = (retorno_consulta(chave=chave) if chave in self.server.autorizadas
                             else retorno_consulta("217", "Chave ainda não registrada na fixture", chave=chave))
                else:
                    return
                resposta = corpo.encode()
                tls.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/soap+xml\r\nConnection: close\r\n"
                            + f"Content-Length: {len(resposta)}\r\n\r\n".encode() + resposta)
        except (OSError, ValueError, AttributeError):
            return


class SefazExecutavel:
    def __init__(self, pasta: Path):
        ctx, self.ca = _certificado_servidor(pasta)
        self.servidor = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _SoapFixture, bind_and_activate=False)
        self.servidor.daemon_threads = True
        self.servidor.ctx = ctx
        self.servidor.autorizadas = set()
        self.servidor.server_bind()
        self.proxy = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        self.thread = None

    def ligar(self) -> None:
        self.servidor.server_activate()
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()

    def fechar(self) -> None:
        if self.thread is not None:
            self.servidor.shutdown()
            self.thread.join(timeout=3)
        self.servidor.server_close()
