"""QA estrutural do vídeo e folha de quadros para revisão humana."""
import json
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[2]
out=root/'output/playwright/tutorial-xml'
video=root/'public/tutoriais/importar-xml.mp4'
meta=json.loads((root/'public/tutoriais/importar-xml.json').read_text(encoding='utf8'))
info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
assert abs(float(info['format']['duration'])-meta['duracao']) < .3
assert any(s['codec_name']=='h264' and s['width']==1600 and s['height']==900 for s in info['streams'])
assert any(s['codec_name']=='aac' for s in info['streams'])
vtt=(root/'public/tutoriais/importar-xml.vtt').read_text(encoding='utf8')
assert vtt.startswith('WEBVTT') and vtt.count('-->')>=28
grid=Image.new('RGB',(1600,960),'#020617'); draw=ImageDraw.Draw(grid)
for i,c in enumerate(meta['capitulos']):
    t=c['inicio']+c['duracao']*.6
    p=out/f"qa-cena-{c['id']}.jpg"
    subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-vf','scale=400:225',str(p)],check=True)
    x=(i%4)*400; y=(i//4)*240
    grid.paste(Image.open(p),(x,y)); draw.text((x+5,y+225),f"Cena {c['id']} - {t:.1f}s",fill='white')
grid.save(out/'qa-contato.jpg')
subprocess.run(['ffmpeg','-v','warning','-i',str(video),'-f','null','-'],check=True,stdout=subprocess.DEVNULL,stderr=(out/'qa-decode.log').open('w'))
print(f"OK: {meta['duracao']}s, H.264 1600x900, voz AAC, 14 cenas e legendas; decodificação integral concluída.")
