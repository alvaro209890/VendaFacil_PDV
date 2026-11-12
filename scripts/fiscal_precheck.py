"""Inspeção somente leitura do cofre da loja, sem imprimir dados ou segredos.

Não importa o aplicativo nem abre/converte outro certificado existente no PC.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def _cnpj_certificado(cert) -> str | None:
    from cryptography import x509
    from cryptography.x509.oid import ObjectIdentifier, NameOID
    try:
        nomes = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        for nome in nomes.get_values_for_type(x509.OtherName):
            if nome.type_id == ObjectIdentifier('2.16.76.1.3.3'):
                # DER UTF8String/PrintableString com CNPJ de 14 caracteres.
                raw = nome.value
                if len(raw) == 16 and raw[0] in (12, 19, 22) and raw[1] == 14:
                    valor = raw[2:].decode('ascii')
                    if re.fullmatch(r'[0-9]{14}', valor):
                        return valor
    except x509.ExtensionNotFound:
        pass
    for oid in (NameOID.SERIAL_NUMBER, NameOID.COMMON_NAME):
        for atributo in cert.subject.get_attributes_for_oid(oid):
            candidatos = re.findall(r'(?<![0-9])[0-9]{14}(?![0-9])', atributo.value)
            if len(candidatos) == 1:
                return candidatos[0]
    return None


def avaliar_config(cfg: dict, maquina: dict, credenciamento: bool = False) -> dict:
    resultado = {'ambiente': 'homologacao' if cfg.get('ambiente') == 'homologacao' else 'outro_ou_ausente',
                 'certificado_presente': bool(cfg.get('certificado_a1_b64')),
                 'senha_certificado_presente': bool(cfg.get('certificado_senha')),
                 'certificado_valido': False, 'titular_presente': False,
                 'cnpj_certificado_confere': False, 'vencimento': None,
                 'csc_presente': bool(cfg.get('csc')), 'id_csc_presente': bool(cfg.get('csc_id')),
                 'credenciamento_comprovado': bool(credenciamento),
                 'token_mp_presente': bool(maquina.get('access_token')),
                 'adquirente_presente': bool(maquina.get('adquirente_cnpj'))}
    campos = ('razao_social', 'cnpj', 'inscricao_estadual', 'cnae', 'logradouro', 'numero',
              'bairro', 'municipio', 'codigo_municipio', 'uf', 'cep', 'regime_tributario')
    resultado['empresa_campos_ausentes'] = [c for c in campos if not str(cfg.get(c) or '').strip()]
    if resultado['certificado_presente'] and resultado['senha_certificado_presente']:
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            key, cert, _ = pkcs12.load_key_and_certificates(
                base64.b64decode(cfg['certificado_a1_b64'], validate=True), cfg['certificado_senha'].encode())
            if cert and key:
                agora = datetime.now(timezone.utc)
                resultado['titular_presente'] = bool(cert.subject)
                resultado['vencimento'] = cert.not_valid_after_utc.date().isoformat()
                resultado['certificado_valido'] = (cert.not_valid_before_utc <= agora <= cert.not_valid_after_utc
                                                    and cert.issuer != cert.subject)
                cnpj = re.sub(r'[^0-9]', '', str(cfg.get('cnpj') or ''))
                resultado['cnpj_certificado_confere'] = bool(cnpj and _cnpj_certificado(cert) == cnpj)
        except Exception:
            # Nunca imprimir erro da biblioteca, senha, conteúdo ou caminho do A1.
            resultado['certificado_valido'] = False
    bloqueios = []
    if not (resultado['certificado_valido'] and resultado['cnpj_certificado_confere']):
        bloqueios.append('B1')
    if not (resultado['csc_presente'] and resultado['id_csc_presente']):
        bloqueios.append('B2')
    if not credenciamento:
        bloqueios.append('B3')
    if resultado['empresa_campos_ausentes'] or resultado['ambiente'] != 'homologacao':
        bloqueios.append('B4')
    if not (resultado['token_mp_presente'] and resultado['adquirente_presente']):
        bloqueios.append('B5')
    resultado['bloqueios'] = bloqueios
    resultado['apto_homologacao'] = not bloqueios
    return resultado


def avaliar_banco(caminho: Path) -> dict:
    cfg, maquina, credenciado = {}, {}, False
    existe = caminho.is_file()
    legivel = False
    if existe:
        try:
            # mode=ro garante que precheck não cria banco nem executa migrações.
            with closing(sqlite3.connect(caminho.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
                conn.row_factory = sqlite3.Row
                cfg = dict(conn.execute('SELECT * FROM config_fiscal WHERE id=1').fetchone() or {})
                maquina = dict(conn.execute('SELECT * FROM config_maquininha WHERE id=1').fetchone() or {})
                cnpj = re.sub(r'[^0-9]', '', str(cfg.get('cnpj') or ''))
                credenciado = bool(cnpj and conn.execute(
                    "SELECT 1 FROM notas_fiscais WHERE ambiente='homologacao' AND status='autorizada' "
                    "AND protocolo IS NOT NULL AND substr(chave,7,14)=? LIMIT 1", (cnpj,)).fetchone())
                legivel = True
        except sqlite3.Error:
            pass
    return {'banco_presente': existe, 'banco_legivel': legivel,
            **avaliar_config(cfg, maquina, credenciado)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    padrao = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'VendaFacilPDV' / 'dados' / 'vendafacil.db'
    parser.add_argument('--banco', type=Path, default=padrao)
    args = parser.parse_args()
    resultado = avaliar_banco(args.banco)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado['apto_homologacao'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
