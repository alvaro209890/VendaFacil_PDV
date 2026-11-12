"""R07: rotação e sanitização no arquivo de log local."""
import logging
from logging.handlers import RotatingFileHandler

import errors


def test_r07_log_rotativo_na_pasta_de_dados(monkeypatch, tmp_path):
    pasta = tmp_path / 'logs'
    arquivo = pasta / 'vendafacil.log'
    monkeypatch.setattr(errors, 'LOG_DIR', pasta)
    monkeypatch.setattr(errors, 'LOG_FILE', arquivo)
    root = logging.getLogger()
    nivel_anterior = root.level
    errors.configure_error_logging()
    handler = next(h for h in root.handlers if getattr(h, 'baseFilename', None) == str(arquivo))
    try:
        assert isinstance(handler, RotatingFileHandler)
        assert handler.maxBytes == 1_000_000
        assert handler.backupCount == 5
        for i in range(8):
            handler.emit(logging.LogRecord('fixture', logging.INFO, __file__, 0,
                                           'evento %d %s', (i, 'x' * 900_000), None))
        assert len(list(pasta.glob('vendafacil.log*'))) == 6
        assert 'evento 7' in arquivo.read_text(encoding='utf-8')[:120]
    finally:
        root.removeHandler(handler)
        handler.close()
        root.setLevel(nivel_anterior)
