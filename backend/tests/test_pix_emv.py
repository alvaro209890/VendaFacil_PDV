"""L06: nome e cidade do PIX não levam acento para o QR."""
from pix import gerar_payload, _crc16
from binascii import crc_hqx


def test_l06_nome_acentuado_fica_ascii_e_crc_bate():
    payload = gerar_payload('loja@imap.com', 10.5, 'José Álvares', 'Querência')
    assert 'JOSE ALVARES' in payload
    assert 'QUERENCIA' in payload
    assert 'É' not in payload and 'Ã' not in payload
    assert payload[-4:] == f'{crc_hqx(payload[:-4].encode(), 0xFFFF):04X}'


def test_crc_confere_com_vetor_publicado_pelo_banco_central():
    # Manual de Padrões para Iniciação do Pix, exemplo estático com chave EVP.
    payload = ('00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000'
               '5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***6304')
    assert _crc16(payload) == '1D3D'
