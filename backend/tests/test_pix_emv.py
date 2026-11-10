"""L06: nome e cidade do PIX não levam acento para o QR."""
from pix import gerar_payload, _crc16


def test_l06_nome_acentuado_fica_ascii_e_crc_bate():
    payload = gerar_payload('loja@imap.com', 10.5, 'José Álvares', 'Querência')
    assert 'JOSE ALVARES' in payload
    assert 'QUERENCIA' in payload
    assert 'É' not in payload and 'Ã' not in payload
    assert payload[-4:] == _crc16(payload[:-4] + '0000')
