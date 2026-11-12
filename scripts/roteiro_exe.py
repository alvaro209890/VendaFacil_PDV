"""Valida a distribuição do PDV na porta 3021, com dados descartáveis."""
import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:3021"
HTTP = build_opener(ProxyHandler({}))
LOGIN = {"usuario": "roteiro-exe", "senha": "Fixture-exe@2026"}


class Pdv:
    def __init__(self, exe: Path, dados: Path, *, sefaz=None):
        self.exe, self.dados, self.sefaz = exe.resolve(strict=True), dados, sefaz
        self.processo = None
        self.token = ""
        self.requisicoes = self.erros_5xx = 0

    def iniciar(self) -> dict:
        with socket.socket() as teste:
            if teste.connect_ex(("127.0.0.1", 3021)) == 0:
                raise RuntimeError("Porta de teste 3021 ocupada.")
        ignoradas = {"pythonpath", "vendafacil_jwt_secret", "http_proxy", "https_proxy",
                     "all_proxy", "no_proxy", "requests_ca_bundle", "curl_ca_bundle"}
        ambiente = {k: v for k, v in os.environ.items() if k.lower() not in ignoradas}
        ambiente.update(VENDAFACIL_DATA_DIR=str(self.dados), VENDAFACIL_PAINEL_URL="",
                        VENDAFACIL_PORT="3021", VENDAFACIL_HOST="127.0.0.1", VENDAFACIL_NO_BROWSER="1")
        if self.sefaz:
            ambiente.update(HTTP_PROXY=self.sefaz.proxy, HTTPS_PROXY=self.sefaz.proxy,
                            NO_PROXY="127.0.0.1,localhost", REQUESTS_CA_BUNDLE=str(self.sefaz.ca))
        self.processo = subprocess.Popen([str(self.exe)], cwd=self.exe.parent, env=ambiente,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
        limite = time.monotonic() + 45
        while time.monotonic() < limite and self.processo.poll() is None:
            try:
                with HTTP.open(URL + "/health", timeout=1) as resposta:
                    saude = json.load(resposta)
                if saude.get("app") == "vendafacil-pdv":
                    print(f"Executável respondeu /health (versão {saude.get('version')}).", flush=True)
                    return saude
            except (URLError, TimeoutError, ValueError):
                time.sleep(0.2)
        raise RuntimeError("Executável não respondeu ao /health em 45 s.")

    def parar(self) -> None:
        if self.processo is not None and self.processo.poll() is None:
            subprocess.run(["taskkill", "/PID", str(self.processo.pid), "/T", "/F"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            self.processo.wait(timeout=12)
        self.processo = None

    def pedir(self, metodo: str, rota: str, status=200, *, dados=None, corpo=None, json_out=True):
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if dados is not None:
            corpo = json.dumps(dados, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        req = Request(URL + rota, data=corpo, headers=headers, method=metodo)
        try:
            resposta = HTTP.open(req, timeout=38)
        except HTTPError as exc:
            resposta = exc
        with resposta:
            codigo, payload = resposta.code, resposta.read()
        self.requisicoes += 1
        self.erros_5xx += int(codigo >= 500)
        print(f"{metodo} {rota} {codigo}", flush=True)
        if codigo != status:
            raise RuntimeError(f"{metodo} {rota}: esperado HTTP {status}, recebido {codigo}.")
        return json.loads(payload) if json_out else payload

    def login(self, novo=False):
        if novo:
            self.pedir("POST", "/api/auth/registro", dados={**LOGIN, "nome": "Operador de teste"})
        self.token = self.pedir("POST", "/api/auth/login", dados=LOGIN)["token"]


def _produto(pdv: Pdv) -> int:
    dados = {"nome": "Açúcar de teste", "preco_venda": 10, "preco_custo": 6, "estoque": 30,
             "codigo_barras": "12345670", "ncm": "22021000", "cfop": "5102", "cst_csosn": "102"}
    return pdv.pedir("POST", "/api/produtos", 201, dados=dados)["produto"]["id"]


def _vender(pdv: Pdv, pid: int, forma="dinheiro", **outros) -> dict:
    return pdv.pedir("POST", "/api/vendas/checkout", 201, dados={
        "itens": [{"produto_id": pid, "quantidade": 1}], "forma_pagamento": forma, **outros,
    })["venda"]


def _smoke(pdv: Pdv) -> None:
    pdv.pedir("GET", "/", json_out=False)
    assert pdv.pedir("GET", "/health")["version"] == "1.0.13"
    pdv.pedir("GET", "/api/produtos", 401)


def _roteiro(pdv: Pdv, xml: bytes) -> tuple[int, int]:
    pdv.login(novo=True)
    pdv.pedir("POST", "/api/caixa/abrir", dados={"valor_abertura": 100})
    pid = _produto(pdv)
    pdv.pedir("POST", f"/api/produtos/{pid}/entrada", dados={"quantidade": 1})
    cliente = pdv.pedir("POST", "/api/clientes", 201, dados={"nome": "Cliente de teste"})["cliente"]["id"]
    previa = pdv.pedir("POST", "/api/produtos/importar-xml/preview", corpo=xml)
    item = previa["itens"][0]
    entrada = pdv.pedir("POST", "/api/produtos/importar-xml/confirmar", dados={
        "chave": previa["chave"], "documento": "Roteiro executável",
        "itens": [{"produto_id": None, "nome": item["nome"], "codigo_barras": item["codigo_barras"],
                   "unidade": item["unidade"], "quantidade": item["quantidade"],
                   "preco_custo": item["valor_unitario"], "preco_venda": 2}],
    })
    assert entrada["criados"] == 1
    pdv.pedir("PUT", "/api/pix/config", dados={"pix_chave": "roteiro@example.invalid",
                                              "pix_nome": "Loja de teste", "pix_cidade": "Cuiabá"})
    assert pdv.pedir("POST", "/api/pix/qrcode", dados={"valor": 10})["qr_base64"]
    for forma in ("dinheiro", "credito", "debito", "pix"):
        _vender(pdv, pid, forma)
    _vender(pdv, pid, "fiado", cliente_id=cliente)
    conta = pdv.pedir("GET", "/api/contas-receber")["contas"][0]
    for valor in (3, 7):
        pdv.pedir("POST", f"/api/contas-receber/{conta['id']}/pagar", dados={"valor": valor, "forma": "dinheiro"})
    assert pdv.pedir("GET", "/api/contas-receber")["contas"][0]["status"] == "pago"
    estorno = _vender(pdv, pid)
    pdv.pedir("POST", f"/api/vendas/{estorno['id']}/cancelar", dados={"motivo": "Estorno de teste isolado"})
    for tipo, valor in (("suprimento", 5), ("sangria", 2)):
        pdv.pedir("POST", "/api/caixa/movimento", dados={"tipo": tipo, "valor": valor})
    esperado = pdv.pedir("GET", "/api/caixa/atual")["resumo"]["dinheiro_esperado"]
    assert esperado == 123
    pdv.pedir("POST", "/api/caixa/fechar", dados={"valor_fechamento": esperado})
    assert pdv.pedir("GET", "/api/relatorios/vendas")["qtd_vendas"] == 5
    pdv.pedir("GET", "/api/relatorios/fiscal")
    copia = pdv.pedir("GET", "/api/backup/exportar", json_out=False)
    assert copia.startswith(b"SQLite format 3\0")
    pdv.pedir("PUT", f"/api/produtos/{pid}", dados={"preco_venda": 99})
    pdv.pedir("POST", "/api/backup/restaurar", corpo=copia)
    assert pdv.pedir("GET", f"/api/produtos/{pid}")["produto"]["preco_venda"] == 10
    return pid, pdv.requisicoes


def _nota(pdv: Pdv, venda: int) -> dict:
    return pdv.pedir("GET", f"/api/fiscal/nfce/venda/{venda}")["nota"]


def _chromium(pdv: Pdv, etapa: str, cupons: Path | None = None) -> list[int]:
    pasta = pdv.dados.parent
    resposta = pasta / "venda-ui.json"
    destino = cupons.parent / "cupons" if cupons is not None else pasta / "cupons"
    dados = {"token": pdv.token, "estado": str(pasta / "chromium.json"), "resultado": str(resposta),
             "cupons": str(destino.resolve())}
    subprocess.run(["node", str(ROOT / "scripts" / "roteiro_exe_chromium.mjs"), etapa],
                   input=json.dumps(dados), text=True, encoding="utf-8", cwd=ROOT, check=True, timeout=120)
    return [] if etapa == "retomar" else json.loads(resposta.read_text(encoding="utf-8"))["vendas"]


_CAMPOS_CUPOM = ("status", "tipo_emissao", "chave", "protocolo", "ambiente", "qrcode_base64",
                 "qrcode_url", "xml_assinado", "xml_autorizado", "serie", "numero")


def _resumo(nota: dict) -> dict:
    return {c: nota.get(c) for c in _CAMPOS_CUPOM}


def _offline(pdv: Pdv, pid: int, config: dict, cupons: Path | None, chromium: bool) -> None:
    pdv.pedir("PUT", "/api/fiscal/config", dados=config)
    pdv.pedir("POST", "/api/caixa/abrir", dados={"valor_abertura": 50})
    vendas = _chromium(pdv, "vender", cupons) if chromium else [_vender(pdv, pid, emitir_nota=True)["id"]]
    contingencias = [_nota(pdv, v) for v in vendas]
    for nota in contingencias:
        assert nota["status"] == "contingencia", nota.get("status")
        assert nota["tipo_emissao"] == "9" and nota["qrcode_base64"]
    estorno = _vender(pdv, pid)
    pdv.pedir("POST", f"/api/vendas/{estorno['id']}/cancelar", dados={"motivo": "Cancelamento de teste offline"})
    esperado = pdv.pedir("GET", "/api/caixa/atual")["resumo"]["dinheiro_esperado"]
    assert esperado == 50 + 10 * len(vendas), esperado
    pdv.pedir("POST", "/api/caixa/fechar", dados={"valor_fechamento": esperado})
    assert [_nota(pdv, v)["qrcode_base64"] for v in vendas] == [n["qrcode_base64"] for n in contingencias]
    pdv.parar()
    pdv.sefaz.ligar()
    pdv.iniciar()
    pdv.login()
    if chromium:
        _chromium(pdv, "retomar", cupons)
    limite = time.monotonic() + 55
    while time.monotonic() < limite:
        autorizadas = [_nota(pdv, v) for v in vendas]
        if all(n["status"] == "autorizada" for n in autorizadas):
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Conciliação não concluída: {[n.get('status') for n in autorizadas]}")
    for antes, depois in zip(contingencias, autorizadas):
        for campo in ("id", "chave", "numero", "xml_assinado"):
            assert depois[campo] == antes[campo], campo
        assert depois["protocolo"] and depois["xml_autorizado"]
    print(f"Contingência conciliada após reinício com o mesmo número, XML e chave ({len(vendas)} notas).")
    if cupons is not None:
        normais = _chromium(pdv, "autorizada", cupons) if chromium else [_vender(pdv, pid, emitir_nota=True)["id"]]
        notas_normais = [_nota(pdv, v) for v in normais]
        for nota in notas_normais:
            assert nota["status"] == "autorizada" and nota["tipo_emissao"] == "1"
        larguras = ("58mm", "80mm") if chromium else ("api",)
        dados = {f"contingencia-{mm}": _resumo(n) for mm, n in zip(larguras, contingencias)}
        dados.update({f"autorizada-{mm}": _resumo(n) for mm, n in zip(larguras, notas_normais)})
        cupons.parent.mkdir(parents=True, exist_ok=True)
        cupons.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        print(f"Notas dos cupons gravadas em {cupons}: {', '.join(dados)}.")


def contagens(banco: Path) -> dict:
    with closing(sqlite3.connect(f"{banco.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("users", "clientes", "produtos", "vendas", "itens_venda", "notas_fiscais")}


def _migracao(anterior: Path, atual: Path, dados: Path) -> None:
    velho = Pdv(anterior, dados)
    try:
        velho.iniciar()
        velho.login(novo=True)
        pid = _produto(velho)
        _vender(velho, pid)
    finally:
        velho.parar()
    banco = dados / "vendafacil.db"
    antes = contagens(banco)
    novo = Pdv(atual, dados)
    try:
        novo.iniciar()
        novo.login()
        assert novo.pedir("GET", f"/api/produtos/{pid}")["produto"]["estoque"] == 29
        depois = contagens(banco)
        assert antes == depois
        print(f"Contagens antes: {antes}\nContagens após migração: {depois}")
    finally:
        novo.parar()


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--exe", type=Path, default=ROOT / "dist_exe" / "VendaFacilPDV.exe")
    args.add_argument("--migracao", type=Path, metavar="EXE_ANTERIOR")
    args.add_argument("--cupons", type=Path, metavar="JSON")
    args.add_argument("--somente-smoke", action="store_true")
    args.add_argument("--chromium", action="store_true", help="também imprime e retoma o carrinho pela UI empacotada")
    op = args.parse_args()
    with tempfile.TemporaryDirectory(prefix="vf-roteiro-exe-") as temp:
        pasta = Path(temp)
        dados = pasta / "pdv"
        if op.migracao:
            _migracao(op.migracao, op.exe, dados)
            return 0
        os.environ["VENDAFACIL_DATA_DIR"] = str(pasta / "fixtures")
        os.environ["VENDAFACIL_PAINEL_URL"] = ""
        sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend" / "tests")]
        from sefaz_executavel import SefazExecutavel, emissor_teste
        from test_importacao_parser import xml_nota
        from database import db as db_fixture

        db_fixture.close()

        sefaz = SefazExecutavel(pasta)
        pdv = Pdv(op.exe, dados, sefaz=sefaz)
        try:
            pdv.iniciar()
            _smoke(pdv)
            if not op.somente_smoke:
                pid, comerciais = _roteiro(pdv, xml_nota())
                print(f"Roteiro comercial: {comerciais} requisições HTTP, {pdv.erros_5xx} respostas 5xx.")
                _offline(pdv, pid, emissor_teste(), op.cupons, op.chromium)
            print(f"Roteiro completo: {pdv.requisicoes} requisições HTTP, {pdv.erros_5xx} respostas 5xx.")
        finally:
            pdv.parar()
            sefaz.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
