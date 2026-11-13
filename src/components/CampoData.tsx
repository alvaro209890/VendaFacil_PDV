import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import "../../painel/static/calendario.js";
import type { CalendarioData } from "../../painel/static/calendario.js";

type CampoDataProps = {
  rotulo: string;
  valor: string;
  onChange: (valor: string) => void;
  className?: string;
  campoRef?: RefObject<CalendarioData | null>;
};

export default function CampoData({ rotulo, valor, onChange, className, campoRef }: CampoDataProps) {
  const refLocal = useRef<CalendarioData>(null);

  useEffect(() => {
    const campo = refLocal.current;
    if (campoRef) campoRef.current = campo;
    function alterar(evento: Event) {
      onChange((evento as CustomEvent<string>).detail);
    }
    campo?.addEventListener("dataalterada", alterar);
    return () => {
      campo?.removeEventListener("dataalterada", alterar);
      if (campoRef?.current === campo) campoRef.current = null;
    };
  }, [onChange, campoRef]);

  return (
    <vf-calendario ref={refLocal} rotulo={rotulo} valor={valor} className={className} />
  );
}
