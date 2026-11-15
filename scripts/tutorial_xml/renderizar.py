"""Monta a captura real, voz SAPI pt-BR e legendas num MP4 local ao PDV."""
import json
import math
import subprocess
import textwrap
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/playwright/tutorial-xml'
PUBLIC=ROOT/'public/tutoriais'
PUBLIC.mkdir(parents=True,exist_ok=True)
roteiro=json.loads((Path(__file__).parent/'roteiro.json').read_text(encoding='utf8'))
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',31)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
def executar(args):
    with (OUT/'render.log').open('a',encoding='utf8') as log:
        subprocess.run(args,cwd=OUT,stdout=log,stderr=log,check=True)
def stamp(s):
    ms=round(s*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
def assstamp(s):
    cs=round(s*100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'

vtt=['WEBVTT','']; chapters=['WEBVTT','']; meta=[]; inicio=0
for idx,cena in enumerate(roteiro):
    n=cena['id']
    if not (OUT/f'{n}.webm').is_file(): raise FileNotFoundError(n)
    img=Image.new('RGB',(1600,900),'#020617'); draw=ImageDraw.Draw(img)
    draw.text((80,16),'VENDAFÁCIL  /  GUIA DO OPERADOR',font=small,fill='#60a5fa')
    draw.text((80,45),cena['titulo'],font=font,fill='#f8fafc')
    draw.text((1220,18),f'DEMONSTRAÇÃO  •  {idx+1:02} / 14',font=small,fill='#94a3b8')
    draw.rounded_rectangle((1220,52,1520,59),radius=3,fill='#1e293b')
    draw.rounded_rectangle((1220,52,1220+300*(idx+1)/14,59),radius=3,fill='#3b82f6')
    img.save(OUT/f'{n}-moldura.png')
    partes=[]; cues=[]; tempo=0.3
    for j,texto in enumerate(cena['fala']):
        with wave.open(str(OUT/f'{n}-{j}.wav'),'rb') as wav:
            params=wav.getparams(); data=wav.readframes(wav.getnframes())
            dur=wav.getnframes()/wav.getframerate()
        partes.append(data)
        blocos=textwrap.wrap(texto,width=174,break_long_words=False,break_on_hyphens=False)
        total=sum(len(b) for b in blocos)
        off=tempo
        for bloco in blocos:
            d=dur*len(bloco)/total
            cues.append((off,off+d,bloco)); off+=d
        tempo+=dur+0.16
    silence=lambda secs: b'\0'*(round(params.framerate*secs)*params.nchannels*params.sampwidth)
    with wave.open(str(OUT/f'{n}-audio.wav'),'wb') as wav:
        wav.setparams(params); wav.writeframes(silence(.3))
        for data in partes: wav.writeframes(data+silence(.16))
    duracao=math.ceil((tempo+.45)*20)/20
    ass=['[Script Info]','ScriptType: v4.00+','PlayResX: 1600','PlayResY: 900','WrapStyle: 2','',
         '[V4+ Styles]','Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding',
         'Style: Default,Arial,26,&H00FFFFFF,&H00FFFFFF,&H00020617,&H00020617,0,0,0,0,100,100,0,0,1,1,0,2,100,100,15,1','',
         '[Events]','Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text']
    for a,b,texto in cues:
        linhas=textwrap.wrap(texto,width=102,break_long_words=False,break_on_hyphens=False)
        legendado=r'\N'.join(linhas)
        ass.append(f'Dialogue: 0,{assstamp(a)},{assstamp(b)},Default,,0,0,0,,{legendado}')
        vtt.extend([f'{stamp(inicio+a)} --> {stamp(inicio+b)}',texto,''])
    (OUT/f'{n}.ass').write_text('\n'.join(ass),encoding='utf8')
    executar(['ffmpeg','-y','-hide_banner','-filter_complex_threads','2','-i',f'{n}.webm','-i',f'{n}-audio.wav','-loop','1','-i',f'{n}-moldura.png',
              '-filter_complex',f'[0:v]fps=20,scale=1440:720,tpad=stop_mode=clone:stop_duration=600[screen];[2:v][screen]overlay=80:95:shortest=1,ass={n}.ass,format=yuv420p[v];[1:a]apad[a]',
              '-map','[v]','-map','[a]','-t',str(duracao),'-c:v','libx264','-preset','veryfast','-crf','23','-threads','2','-c:a','aac','-b:a','96k','-ar','48000','-ac','1',f'{n}-final.mp4'])
    chapters.extend([f'{stamp(inicio)} --> {stamp(inicio+duracao)}',cena['titulo'],''])
    meta.append({'id':n,'titulo':cena['titulo'],'inicio':round(inicio,3),'duracao':duracao})
    inicio+=duracao
    print(f'Cena {n}: {duracao:.2f}s',flush=True)
(OUT/'concat.txt').write_text('\n'.join(f"file '{c['id']}-final.mp4'" for c in roteiro),encoding='utf8')
destino=PUBLIC/'importar-xml.mp4'
executar(['ffmpeg','-y','-hide_banner','-f','concat','-safe','0','-i','concat.txt','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000','-c:a','aac','-b:a','96k','-movflags','+faststart',str(destino)])
(PUBLIC/'importar-xml.vtt').write_text('\n'.join(vtt),encoding='utf8')
(PUBLIC/'importar-xml-capitulos.vtt').write_text('\n'.join(chapters),encoding='utf8')
(PUBLIC/'importar-xml.json').write_text(json.dumps({'duracao':round(inicio,3),'capitulos':meta},ensure_ascii=False,indent=2),encoding='utf8')
rotulos={'01':'Começar','03':'Produto cadastrado','05':'Caixa ou unidade','08':'Dois preços','10':'Confirmar entrada','13':'Alterar preço'}
atalhos=[{'id':c['id'],'rotulo':rotulos[c['id']],'inicio':c['inicio']} for c in meta if c['id'] in rotulos]
(ROOT/'src/lib/tutorialXml.ts').write_text('export const duracaoTutorialXml = '+str(round(inicio,3))+';\nexport const capitulosTutorialXml = '+json.dumps(atalhos,ensure_ascii=False,indent=2)+' as const;\n',encoding='utf8')
executar(['ffmpeg','-y','-hide_banner','-ss','2','-i',str(destino),'-frames:v','1','-q:v','2',str(PUBLIC/'importar-xml.jpg')])
print(f'Pronto: {destino} ({inicio:.2f}s)',flush=True)
