import type { DetailedHTMLProps, HTMLAttributes } from "react";
import type { CalendarioData } from "../painel/static/calendario.js";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "vf-calendario": DetailedHTMLProps<
        HTMLAttributes<CalendarioData> & { rotulo?: string; valor?: string },
        CalendarioData
      >;
    }
  }
}
