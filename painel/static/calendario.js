const diasDaSemana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const nomeMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });
const nomeData = new Intl.DateTimeFormat("pt-BR", { dateStyle: "full", timeZone: "UTC" });

function dataUTC(ano, mes, dia = 1) {
  const data = new Date(0);
  data.setUTCFullYear(ano, mes, dia);
  return data;
}

function iso(ano, mes, dia) {
  return [String(ano).padStart(4, "0"), String(mes).padStart(2, "0"), String(dia).padStart(2, "0")].join("-");
}

export function dataLocal(data = new Date()) {
  return iso(data.getFullYear(), data.getMonth() + 1, data.getDate());
}

function dataISO(data) {
  return iso(data.getUTCFullYear(), data.getUTCMonth() + 1, data.getUTCDate());
}

function lerISO(valor) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor)) return null;
  const [ano, mes, dia] = valor.split("-").map(Number);
  const data = dataUTC(ano, mes - 1, dia);
  return ano > 0 && dataISO(data) === valor ? data : null;
}

function lerDigitacao(texto) {
  const partes = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(texto)
    || /^(\d{2})(\d{2})(\d{4})$/.exec(texto);
  return partes ? lerISO(iso(Number(partes[3]), Number(partes[2]), Number(partes[1]))) : null;
}

const estilo = `
  :host { display: block; min-width: 0; color-scheme: dark; font: inherit; }
  *, *::before, *::after { box-sizing: border-box; }
  [hidden] { display: none !important; }
  label { display: block; margin-bottom: 4px; color: #a8b5ca; font-size: 12px; }
  input, select, button { font: inherit; color: inherit; }
  button { cursor: pointer; }
  button:disabled { cursor: not-allowed; opacity: .4; }
  button:focus-visible, select:focus-visible, input:focus-visible {
    outline: 2px solid #93c5fd;
    outline-offset: 2px;
  }
  .campo {
    display: flex; align-items: center; background: #1e293b;
    border: 1px solid #334155; border-radius: 8px; color: #f1f5f9;
    font-size: 14px; min-height: 40px;
  }
  .campo:focus-within { border-color: #60a5fa; box-shadow: 0 0 0 2px #3b82f633; }
  .campo.invalido { border-color: #fb7185; }
  .campo input {
    min-width: 0; width: 100%; height: 38px; padding: 0 0 0 12px;
    background: transparent; border: 0; outline: 0; font-variant-numeric: tabular-nums;
  }
  .campo input::placeholder { color: #94a3b8; }
  .abrir, .seta {
    display: grid; place-items: center; flex: none;
    width: 36px; height: 34px; border: 0; border-radius: 7px;
    background: transparent; color: #93c5fd;
  }
  .abrir { margin: 2px; }
  .abrir:hover, .abrir[aria-expanded="true"], .seta:hover:not(:disabled) { background: #253d60; color: #dbeafe; }
  .erro { color: #fda4af; font-size: 12px; margin: 6px 0 0; }
  .calendario {
    position: fixed; inset: auto; margin: 0; width: min(320px, calc(100vw - 16px));
    max-height: calc(100dvh - 16px); overflow: auto; overscroll-behavior: contain;
    padding: 12px; border: 1px solid #334155; border-radius: 14px;
    background: #111c30; color: #f1f5f9; box-shadow: 0 16px 44px #0009;
    font-size: 14px;
  }
  .cabecalho { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
  .cabecalho select, .cabecalho input {
    min-width: 0; height: 34px; border-radius: 7px; padding: 0 6px;
    border: 1px solid #334155; background: #1e293b;
  }
  .cabecalho select { flex: 1; }
  .cabecalho input { width: 66px; appearance: textfield; }
  .cabecalho input::-webkit-inner-spin-button { appearance: none; }
  .semana, .dias { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 3px; }
  .semana { text-align: center; font-size: 11px; color: #a8b5ca; margin-bottom: 5px; }
  .dia {
    height: 35px; padding: 0; border: 1px solid transparent; border-radius: 7px;
    background: transparent; color: #e2e8f0; font-variant-numeric: tabular-nums;
  }
  .dia:hover:not(:disabled) { background: #253d60; }
  .dia.fora { color: #94a3b8; }
  .dia[aria-current="date"] { border-color: #60a5fa; }
  .dia[aria-pressed="true"] { background: #2563eb; color: white; font-weight: 700; }
  .dia[aria-pressed="true"]:hover { background: #1d4ed8; }
  .rodape { display: flex; justify-content: space-between; gap: 8px; border-top: 1px solid #334155; margin-top: 9px; padding-top: 9px; }
  .rodape button { background: transparent; color: #bfdbfe; border: 0; border-radius: 7px; padding: 7px 10px; font-weight: 600; }
  .rodape button:hover:not(:disabled) { background: #253d60; }
  @media (max-width: 768px) {
    .campo input { font-size: 16px; }
    .dia { height: 38px; }
  }
`;

const modelo = document.createElement("template");
modelo.innerHTML = `
  <style>${estilo}</style>
  <label for="data"></label>
  <div class="campo">
    <input id="data" type="text" placeholder="dd/mm/aaaa" maxlength="10" autocomplete="off" spellcheck="false">
    <button class="abrir" type="button" popovertarget="calendario" aria-haspopup="dialog" aria-expanded="false">
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18M8 15h2m4 0h2"/>
      </svg>
    </button>
  </div>
  <p class="erro" id="erro" role="alert" hidden>Digite uma data válida no formato dd/mm/aaaa.</p>
  <div id="calendario" class="calendario" popover role="dialog">
    <div class="cabecalho">
      <button type="button" class="seta anterior" aria-label="Mês anterior">❮</button>
      <select aria-label="Mês">${Array.from({ length: 12 }, (_, mes) => `<option value="${mes}">${nomeMes.format(dataUTC(2000, mes))}</option>`).join("")}</select>
      <input class="ano" type="number" min="1" max="9999" aria-label="Ano">
      <button type="button" class="seta seguinte" aria-label="Próximo mês">❯</button>
    </div>
    <div class="semana" aria-hidden="true">${diasDaSemana.map((dia) => `<span>${dia}</span>`).join("")}</div>
    <div class="dias" role="group" aria-label="Dias do mês"></div>
    <div class="rodape"><button type="button" class="limpar">Limpar</button><button type="button" class="hoje">Hoje</button></div>
  </div>
`;

class CalendarioData extends HTMLElement {
  static formAssociated = true;
  static observedAttributes = ["rotulo", "valor"];

  #form = this.attachInternals();
  #raiz = this.attachShadow({ mode: "open" });
  #valor = "";
  #dia = lerISO(dataLocal());

  constructor() {
    super();
    this.#raiz.append(modelo.content.cloneNode(true));
    this.campo = this.#raiz.querySelector("#data");
    this.abrir = this.#raiz.querySelector(".abrir");
    this.calendario = this.#raiz.querySelector("#calendario");
    this.mes = this.#raiz.querySelector("select");
    this.ano = this.#raiz.querySelector(".ano");
    this.dias = this.#raiz.querySelector(".dias");
    this.anterior = this.#raiz.querySelector(".anterior");
    this.seguinte = this.#raiz.querySelector(".seguinte");
    this.limpar = this.#raiz.querySelector(".limpar");
    this.erro = this.#raiz.querySelector(".erro");

    this.campo.addEventListener("input", () => this.#validar(false));
    this.campo.addEventListener("blur", () => this.#confirmarDigitacao());
    this.campo.addEventListener("keydown", (evento) => {
      if (evento.key !== "Enter") return;
      evento.preventDefault();
      this.#confirmarDigitacao();
    });

    this.calendario.addEventListener("beforetoggle", (evento) => {
      if (evento.newState !== "open") return;
      this.#dia = lerISO(this.#valor || dataLocal());
      this.#desenharDias();
    });
    this.calendario.addEventListener("toggle", (evento) => {
      const aberto = evento.newState === "open";
      this.abrir.setAttribute("aria-expanded", String(aberto));
      if (aberto) {
        this.#posicionar();
        this.#focarDia();
      }
    });
    this.anterior.onclick = () => this.#mudarMes(this.#dia.getUTCMonth() - 1);
    this.seguinte.onclick = () => this.#mudarMes(this.#dia.getUTCMonth() + 1);
    this.mes.onchange = () => this.#mudarMes(Number(this.mes.value));
    this.ano.onchange = () => this.#mudarMes(this.#dia.getUTCMonth(), Number(this.ano.value));
    this.limpar.onclick = () => this.#selecionar("");
    this.#raiz.querySelector(".hoje").onclick = () => this.#selecionar(dataLocal());
    this.dias.addEventListener("keydown", (evento) => this.#navegarDias(evento));
  }

  connectedCallback() {
    window.addEventListener("resize", this.#posicionar);
    window.addEventListener("scroll", this.#posicionar, true);
  }

  disconnectedCallback() {
    window.removeEventListener("resize", this.#posicionar);
    window.removeEventListener("scroll", this.#posicionar, true);
  }

  attributeChangedCallback(atributo, _anterior, valor) {
    if (atributo === "rotulo") {
      this.#raiz.querySelector("label").textContent = valor;
      this.abrir.setAttribute("aria-label", `Abrir calendário: ${valor}`);
      this.calendario.setAttribute("aria-label", `Calendário: ${valor}`);
    } else {
      this.#aplicarValor(valor || "");
    }
  }

  formResetCallback() {
    this.#aplicarValor(this.getAttribute("valor") || "");
  }

  confirmar() {
    const valor = this.#confirmarDigitacao();
    if (valor === null) this.campo.focus();
    return valor;
  }

  #validar(mostrar) {
    const texto = this.campo.value.trim();
    const data = lerDigitacao(texto);
    const invalido = texto !== "" && !data;
    this.#form.setFormValue(invalido ? "" : data ? dataISO(data) : "");
    this.#form.setValidity(invalido ? { badInput: true } : {}, invalido ? this.erro.textContent : "", this.campo);
    this.erro.hidden = !invalido || (!mostrar && this.erro.hidden);
    this.campo.closest(".campo").classList.toggle("invalido", !this.erro.hidden);
    this.campo.setAttribute("aria-invalid", String(!this.erro.hidden));
    if (this.erro.hidden) this.campo.removeAttribute("aria-describedby");
    else this.campo.setAttribute("aria-describedby", "erro");
    return invalido ? null : data ? dataISO(data) : "";
  }

  #aplicarValor(valor) {
    const anterior = this.#valor;
    this.#valor = lerISO(valor) ? valor : "";
    this.campo.value = this.#valor.split("-").reverse().join("/");
    this.#validar(false);
    return anterior !== this.#valor;
  }

  #confirmarDigitacao() {
    const valor = this.#validar(true);
    if (valor !== null) this.#atualizar(valor);
    return valor;
  }

  #atualizar(valor) {
    if (this.#aplicarValor(valor)) {
      this.dispatchEvent(new CustomEvent("dataalterada", { detail: this.#valor }));
    }
  }

  #selecionar(valor) {
    this.#atualizar(valor);
    this.calendario.hidePopover();
    this.abrir.focus();
  }

  #posicionar = () => {
    if (!this.calendario.matches(":popover-open")) return;
    const ancora = this.campo.closest(".campo").getBoundingClientRect();
    const { width, height } = this.calendario.getBoundingClientRect();
    const larguraTela = document.documentElement.clientWidth;
    const alturaTela = document.documentElement.clientHeight;
    const margem = 8;
    const embaixo = ancora.bottom + margem;
    const emCima = ancora.top - height - margem;
    const topo = embaixo + height <= alturaTela - margem || emCima < margem ? embaixo : emCima;
    this.calendario.style.left = `${Math.max(margem, Math.min(ancora.left, larguraTela - width - margem))}px`;
    this.calendario.style.top = `${Math.max(margem, Math.min(topo, alturaTela - height - margem))}px`;
  };

  #mudarMes(mes, ano = this.#dia.getUTCFullYear()) {
    const primeiroDia = dataUTC(ano, mes);
    const anoDestino = primeiroDia.getUTCFullYear();
    if (!Number.isInteger(anoDestino) || anoDestino < 1 || anoDestino > 9999) {
      this.ano.value = String(this.#dia.getUTCFullYear());
      return;
    }
    const mesDestino = primeiroDia.getUTCMonth();
    const ultimoDia = dataUTC(anoDestino, mesDestino + 1, 0).getUTCDate();
    this.#dia = dataUTC(anoDestino, mesDestino, Math.min(this.#dia.getUTCDate(), ultimoDia));
    this.#desenharDias();
  }

  #desenharDias() {
    const ano = this.#dia.getUTCFullYear();
    const mes = this.#dia.getUTCMonth();
    const inicio = 1 - dataUTC(ano, mes).getUTCDay();
    const hoje = dataLocal();
    const diaAtivo = dataISO(this.#dia);
    this.ano.value = String(ano);
    this.mes.value = String(mes);
    this.anterior.disabled = ano === 1 && mes === 0;
    this.seguinte.disabled = ano === 9999 && mes === 11;
    this.limpar.disabled = !this.#valor && !this.campo.value;
    this.dias.replaceChildren(...Array.from({ length: 42 }, (_, indice) => {
      const data = dataUTC(ano, mes, inicio + indice);
      const valor = dataISO(data);
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = data.getUTCMonth() === mes ? "dia" : "dia fora";
      botao.textContent = String(data.getUTCDate());
      botao.setAttribute("aria-label", nomeData.format(data));
      botao.setAttribute("aria-pressed", String(valor === this.#valor));
      if (valor === hoje) botao.setAttribute("aria-current", "date");
      botao.tabIndex = valor === diaAtivo ? 0 : -1;
      botao.disabled = data.getUTCFullYear() < 1 || data.getUTCFullYear() > 9999;
      botao.onclick = () => this.#selecionar(valor);
      return botao;
    }));
  }

  #focarDia() {
    this.dias.querySelector('[tabindex="0"]')?.focus({ preventScroll: true });
  }

  #navegarDias(evento) {
    const deslocamentos = {
      ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7,
      Home: -this.#dia.getUTCDay(), End: 6 - this.#dia.getUTCDay(),
    };
    if (Object.hasOwn(deslocamentos, evento.key)) {
      evento.preventDefault();
      const data = dataUTC(this.#dia.getUTCFullYear(), this.#dia.getUTCMonth(), this.#dia.getUTCDate() + deslocamentos[evento.key]);
      if (data.getUTCFullYear() < 1 || data.getUTCFullYear() > 9999) return;
      this.#dia = data;
      this.#desenharDias();
    } else if (evento.key === "PageUp" || evento.key === "PageDown") {
      evento.preventDefault();
      this.#mudarMes(this.#dia.getUTCMonth() + (evento.key === "PageUp" ? -1 : 1));
    } else {
      return;
    }
    this.#focarDia();
  }
}

if (!customElements.get("vf-calendario")) customElements.define("vf-calendario", CalendarioData);
if (import.meta.hot) import.meta.hot.accept(() => location.reload());
