"""Confere os PDFs de cupom gerados por roteiro_exe.py --chromium --cupons <json>.

Para cada largura (58 e 80 mm) e cada situação (contingência e autorizada):
largura da página, acentuação, chave, protocolo, marcação de homologação,
duas vias e aviso de contingência, e decodifica os QR Codes do próprio PDF,
comparando com o qrcode_url que o PDV gravou na nota.

Requer PyMuPDF (fitz) e OpenCV (cv2). Uso:
    py -3.12 -X utf8 -I scripts/verificar_cupons_pdf.py output/fase6/notas-simuladas.json
"""
import json
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

PT_POR_MM = 72 / 25.4


def _qrs(pagina) -> list[str]:
    """Rasteriza a região de cada imagem do PDF e decodifica o QR dela.

    O detector padrão do OpenCV 5 às vezes não lê um QR legível numa resolução
    específica; por isso tenta 300/400/200 dpi e o detector Aruco. A comparação
    com o qrcode_url da nota continua exata."""
    detectores = (cv2.QRCodeDetector(), cv2.QRCodeDetectorAruco())
    achados = []
    for info in pagina.get_image_info():
        area = fitz.Rect(info["bbox"]) + (-6, -6, 6, 6)  # margem branca em volta
        texto = ""
        for dpi in (300, 400, 200):
            imagem = pagina.get_pixmap(dpi=dpi, clip=area, colorspace=fitz.csGRAY)
            matriz = np.frombuffer(imagem.samples, dtype=np.uint8).reshape(imagem.height, imagem.width)
            texto = next((t for t in (d.detectAndDecode(matriz)[0] for d in detectores) if t), "")
            if texto:
                break
        achados.append(texto)
    return achados


def conferir(nome: str, pdf: Path, nota: dict) -> list[str]:
    falhas = []
    mm = int(nome.rsplit("-", 1)[1].removesuffix("mm"))
    contingencia = nome.startswith("contingencia")
    with fitz.open(pdf) as doc:
        if doc.page_count != 1:
            falhas.append(f"{doc.page_count} páginas")
        pagina = doc[0]
        largura = pagina.rect.width / PT_POR_MM
        texto = " ".join(pagina.get_text().split())
        qrs = _qrs(pagina)
    if abs(largura - mm) > 0.5:
        falhas.append(f"largura {largura:.1f} mm")
    chave = " ".join(nota["chave"][i:i + 4] for i in range(0, 44, 4))
    esperados = ["Açúcar de teste", "Mercearia Açúcar de Teste", "Cuiabá", "DANFE NFC-e",
                 "EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO — SEM VALOR FISCAL", "CONSUMIDOR NÃO IDENTIFICADO",
                 f"NFC-e no {int(nota['numero'])} serie {int(nota['serie'])}", chave]
    if contingencia:
        esperados += ["VIA DO CONSUMIDOR", "VIA DO ESTABELECIMENTO (guardar)", "corte aqui",
                      "Pendente de autorização", "Transmitir assim que a conexão voltar"]
        if texto.count("EMITIDA EM CONTINGÊNCIA") != 4:  # topo e bloco fiscal, nas duas vias
            falhas.append(f"aviso de contingência {texto.count('EMITIDA EM CONTINGÊNCIA')}x")
        if "Protocolo de autorização" in texto:
            falhas.append("protocolo impresso na contingência")
    else:
        esperados.append(f"Protocolo de autorização: {nota['protocolo']}")
        if "CONTINGÊNCIA" in texto or "VIA DO" in texto:
            falhas.append("marcação de contingência no cupom autorizado")
    falhas += [f"texto ausente: {e}" for e in esperados if e not in texto]
    if texto.count(chave) != (2 if contingencia else 1):
        falhas.append(f"chave {texto.count(chave)}x")
    if qrs != [nota["qrcode_url"]] * (2 if contingencia else 1):
        falhas.append(f"QR decodificado {len(qrs)}x, igual à nota: {[q == nota['qrcode_url'] for q in qrs]}")
    print(f"{nome}: {largura:.1f} mm, {len(qrs)} QR decodificado(s) "
          f"{'= qrcode_url da nota' if qrs and set(qrs) == {nota['qrcode_url']} else 'DIVERGENTE'}, "
          f"{'OK' if not falhas else 'FALHOU: ' + '; '.join(falhas)}")
    if qrs:
        print(f"  QR: {qrs[0][:60]}...")
    return falhas


def main() -> int:
    notas_json = Path(sys.argv[1] if len(sys.argv) > 1 else "output/fase6/notas-simuladas.json")
    notas = json.loads(notas_json.read_text(encoding="utf-8"))
    pasta = notas_json.parent / "cupons"
    falhas = 0
    for nome in ("contingencia-58mm", "contingencia-80mm", "autorizada-58mm", "autorizada-80mm"):
        pdf = pasta / f"{nome}.pdf"
        if nome not in notas or not pdf.exists():
            print(f"{nome}: ausente")
            falhas += 1
            continue
        falhas += bool(conferir(nome, pdf, notas[nome]))
    print(f"Cupons em PDF: {4 - falhas}/4 conferidos.")
    return int(falhas > 0)


if __name__ == "__main__":
    sys.exit(main())
