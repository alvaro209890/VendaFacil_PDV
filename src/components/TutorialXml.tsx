import { useRef } from "react";
import { PlayCircle, Download } from "lucide-react";
import { capitulosTutorialXml, duracaoTutorialXml } from "../lib/tutorialXml";

const tempo = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function TutorialXml() {
  const videoRef = useRef<HTMLVideoElement>(null);
  function assistir(inicio: number) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = inicio;
    video.scrollIntoView({ behavior: "smooth", block: "start" });
    void video.play().catch(() => video.focus());
  }
  return (
    <section id="tutorial-xml" aria-labelledby="titulo-tutorial-xml" className="scroll-mt-20 rounded-xl border border-brand-500/40 bg-slate-900 p-3 sm:p-5">
      <div className="mb-3 flex items-start gap-3">
        <PlayCircle className="mt-0.5 shrink-0 text-brand-400" size={25} />
        <div>
          <h2 id="titulo-tutorial-xml" className="text-lg font-bold text-white">Vídeo: importar XML e conferir o estoque</h2>
          <p className="mt-1 text-sm text-slate-400">Passo a passo na tela do PDV, com narração e legendas em português. {tempo(duracaoTutorialXml)} · disponível sem internet.</p>
        </div>
      </div>
      <video ref={videoRef} controls playsInline preload="none" poster="/tutoriais/importar-xml.jpg" aria-label="Tutorial de importação de XML" className="block aspect-video w-full scroll-mt-20 rounded-lg bg-black">
        <source src="/tutoriais/importar-xml.mp4" type="video/mp4" />
        <track kind="captions" src="/tutoriais/importar-xml.vtt" srcLang="pt-BR" label="Português" />
        Seu navegador não reproduziu o vídeo. Use o link abaixo para baixar.
      </video>
      <p className="mb-2 mt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Ir direto para uma explicação</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {capitulosTutorialXml.map(c => <button key={c.id} type="button" onClick={() => assistir(c.inicio)} className="rounded-lg border border-slate-700 px-3 py-2 text-left text-sm text-slate-200 hover:border-brand-400 hover:bg-brand-500/10 focus-visible:outline-2 focus-visible:outline-brand-400">
          <span className="mr-2 text-xs text-brand-300">{tempo(c.inicio)}</span>{c.rotulo}
        </button>)}
      </div>
      <a href="/tutoriais/importar-xml.mp4" download="VendaFacil-como-importar-XML.mp4" className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-brand-300 hover:underline"><Download size={15} />Baixar vídeo para guardar</a>
    </section>
  );
}
