import { motion } from "framer-motion";
import {
  AlertTriangle,
  Banknote,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  Database,
  FileCheck2,
  FileText,
  HelpCircle,
  Landmark,
  Package,
  ReceiptText,
  Search,
  ShieldCheck,
  ShoppingCart,
  Smartphone,
  Users,
  Wallet,
} from "lucide-react";

type FieldRow = {
  campo: string;
  onde: string;
  cuidado: string;
};

type HelpSection = {
  id: string;
  titulo: string;
  texto: string;
  itens: string[];
};

const fiscalRows: FieldRow[] = [
  {
    campo: "CNPJ, razão social e nome fantasia",
    onde: "Cartão CNPJ, contrato social, contador ou cadastro da empresa na Receita Federal.",
    cuidado: "Use os dados do estabelecimento que vai vender. Filial e matriz podem ter CNPJ e IE diferentes.",
  },
  {
    campo: "Inscrição Estadual",
    onde: "Cadastro de contribuinte da SEFAZ-MT, Sintegra/consulta cadastral ou contador.",
    cuidado: "A IE precisa estar ativa e vinculada ao CNPJ emitente.",
  },
  {
    campo: "Regime tributário",
    onde: "Contador. Normalmente Simples Nacional, Simples com excesso de sublimite ou Regime Normal.",
    cuidado: "Não escolha por tentativa. O CRT errado pode rejeitar nota ou gerar imposto incorreto.",
  },
  {
    campo: "Endereço do emitente",
    onde: "Cartão CNPJ, alvará, cadastro estadual ou contador.",
    cuidado: "O endereço deve ser o da loja emitente da nota, com CEP e município corretos.",
  },
  {
    campo: "Código IBGE do município",
    onde: "Tabela de municípios do IBGE, contador ou cadastro fiscal da empresa.",
    cuidado: "Para Cuiabá, por exemplo, o código é 5103403. Não use CEP no lugar do código IBGE.",
  },
  {
    campo: "Certificado A1",
    onde: "Arquivo .pfx ou .p12 emitido por autoridade certificadora ICP-Brasil para o CNPJ/e-PJ da empresa.",
    cuidado: "Guarde senha e arquivo em local seguro. Certificado vencido, senha errada ou CNPJ divergente impede emissão.",
  },
  {
    campo: "CSC e ID CSC",
    onde: "Portal de NFC-e/serviços da SEFAZ-MT, após credenciamento do contribuinte. O contador costuma ajudar nessa liberação.",
    cuidado: "O CSC é usado no QR Code da NFC-e. Ambiente de homologação e produção podem ter códigos diferentes.",
  },
  {
    campo: "Série e próximo número",
    onde: "Contador, histórico de notas já emitidas ou controle anterior da loja.",
    cuidado: "NFC-e modelo 65 e NF-e modelo 55 têm numeração separada. Não reutilize número já autorizado.",
  },
  {
    campo: "NCM",
    onde: "XML/nota de compra do fornecedor, contador ou tabela fiscal de classificação de mercadorias.",
    cuidado: "Não copie de produto parecido sem conferência. NCM incorreto é uma das fontes clássicas de rejeição.",
  },
  {
    campo: "CFOP",
    onde: "Contador, conforme tipo da venda e UF do cliente. Venda interna de mercadoria comum costuma usar CFOP de venda dentro do estado.",
    cuidado: "O CFOP muda conforme operação. Não transforme exemplo em regra fixa.",
  },
  {
    campo: "CSOSN/CST, origem, PIS e COFINS",
    onde: "Contador, regime tributário e cadastro fiscal do produto.",
    cuidado: "Esses campos definem tratamento tributário. Em dúvida, deixe a venda sem nota até o contador revisar.",
  },
  {
    campo: "CEST e GTIN/código de barras",
    onde: "XML do fornecedor, cadastro do fabricante, contador ou conferência fiscal do produto.",
    cuidado: "CEST só entra quando aplicável. GTIN ausente deve ficar como SEM GTIN no fluxo fiscal.",
  },
];

const sections: HelpSection[] = [
  {
    id: "inicio",
    titulo: "Primeira Configuração",
    texto: "Faça esta sequência antes de usar o caixa no dia a dia.",
    itens: [
      "Entre com o usuário administrador e cadastre os dados básicos da loja.",
      "Cadastre categorias simples: bebidas, mercearia, limpeza, frios, padaria e outros grupos que façam sentido para a loja.",
      "Cadastre produtos com preço de venda, estoque inicial, unidade de venda e código de barras quando existir.",
      "Configure PIX, maquininha e fiscal somente depois que os produtos principais já estiverem revisados.",
      "Faça um backup assim que terminar a configuração inicial.",
    ],
  },
  {
    id: "pdv",
    titulo: "PDV e Venda",
    texto: "A tela PDV é o caixa da mercearia.",
    itens: [
      "Use a busca para localizar produto por nome ou código de barras.",
      "Revise quantidade, preço e desconto antes de finalizar.",
      "Em dinheiro, informe quanto o cliente entregou para o sistema calcular o troco.",
      "Para PIX, confira a chave configurada e só finalize após confirmar pagamento.",
      "Para cartão, use a opção de maquininha quando estiver configurada; se a maquininha for manual, registre a forma correta para o caixa bater.",
      "Venda fiado deve ser vinculada a cliente, para aparecer em Contas a Receber.",
      "Marque emitir NFC-e apenas quando os dados fiscais estiverem prontos e o ambiente correto estiver selecionado.",
    ],
  },
  {
    id: "produtos",
    titulo: "Produtos e Estoque",
    texto: "O estoque correto depende de cadastro e rotina.",
    itens: [
      "Use unidade UN para item vendido por unidade, KG para peso e CX quando controlar por caixa.",
      "Quando comprar caixa e vender unidade, preencha quantidade por embalagem para converter corretamente.",
      "Ao importar XML de fornecedor, confira descrição, código de barras, custo, unidade e quantidade antes de confirmar.",
      "Atualize preço de custo quando a compra chegar mais cara ou mais barata.",
      "Cadastre estoque mínimo para receber alerta de reposição.",
      "Produtos inativos saem da venda, mas continuam no histórico.",
    ],
  },
  {
    id: "clientes",
    titulo: "Clientes",
    texto: "Cliente simples serve para fiado; cliente fiscal completo serve para NF-e modelo 55.",
    itens: [
      "Para venda fiado, cadastre nome e telefone no mínimo.",
      "Para NF-e, cadastre CPF/CNPJ, endereço completo, município, código IBGE, UF, CEP e indicador de IE.",
      "Use indicador IE 1 para contribuinte de ICMS, 2 para isento quando aplicável e 9 para não contribuinte.",
      "Empresa que pede nota completa deve ter CNPJ e dados fiscais conferidos antes de emitir.",
    ],
  },
  {
    id: "vendas",
    titulo: "Vendas e Notas",
    texto: "O histórico permite conferir venda, nota e ações fiscais.",
    itens: [
      "Abra uma venda para ver itens, forma de pagamento, total e observações.",
      "NFC-e modelo 65 é o cupom fiscal normal do balcão para consumidor final.",
      "NF-e modelo 55 é nota completa, usada quando uma empresa ou operação exige destinatário identificado.",
      "Se uma nota for rejeitada, leia a mensagem e corrija cadastro, produto ou configuração antes de tentar novamente.",
      "Cancelamento deve ser feito dentro do prazo fiscal e com justificativa clara.",
    ],
  },
  {
    id: "caixa",
    titulo: "Caixa e Recebimentos",
    texto: "Use o caixa para conferir se o dinheiro físico e as formas de pagamento batem com o sistema.",
    itens: [
      "Confira vendas por forma de pagamento no fechamento do turno.",
      "Separe dinheiro, PIX, cartão de débito, crédito e fiado.",
      "Em Contas a Receber, registre pagamento parcial ou total do cliente fiado.",
      "Evite apagar ou refazer venda para corrigir caixa; prefira registrar a correção de forma rastreável.",
    ],
  },
  {
    id: "backup",
    titulo: "Backup",
    texto: "Backup é o seguro da loja contra perda de dados.",
    itens: [
      "Baixe backup manual pelo menos uma vez por semana.",
      "Guarde uma cópia fora do computador: pen drive, HD externo ou nuvem.",
      "Antes de atualizar o sistema ou trocar de máquina, faça backup.",
      "Restauração substitui os dados atuais; só restaure quando tiver certeza do arquivo.",
    ],
  },
];

const rotina = [
  "Abrir o sistema e conferir se data/hora do Windows estão corretas.",
  "Verificar se impressora, internet, PIX e maquininha estão funcionando.",
  "Fazer vendas pelo PDV e conferir troco antes de finalizar.",
  "Registrar entrada de mercadoria assim que receber compra.",
  "No fim do expediente, conferir caixa, contas fiado e fazer backup se houve movimento importante.",
];

const problemas = [
  {
    titulo: "Nota rejeitada",
    detalhe: "Leia a mensagem da SEFAZ, corrija produto, cliente ou configuração fiscal e tente novamente. Não ignore rejeição.",
  },
  {
    titulo: "Certificado não assina",
    detalhe: "Confira se o arquivo é A1 .pfx/.p12, se a senha está correta, se não venceu e se pertence ao CNPJ da loja.",
  },
  {
    titulo: "QR Code da NFC-e inválido",
    detalhe: "Revise CSC, ID CSC, ambiente e credenciamento NFC-e. Homologação e produção podem usar credenciais diferentes.",
  },
  {
    titulo: "Estoque ficou errado",
    detalhe: "Confira unidade de compra, unidade de venda, quantidade por embalagem e lançamentos de entrada.",
  },
  {
    titulo: "Caixa não bate",
    detalhe: "Compare forma de pagamento das vendas, troco informado em dinheiro, recebimentos de fiado e comprovantes de cartão/PIX.",
  },
];

function SectionBlock({ section }: { section: HelpSection }) {
  return (
    <section id={section.id} className="bg-slate-900 border border-slate-800 rounded-lg p-4 scroll-mt-24">
      <h2 className="text-white font-black text-lg mb-1">{section.titulo}</h2>
      <p className="text-slate-400 text-sm mb-3">{section.texto}</p>
      <ul className="space-y-2">
        {section.itens.map((item) => (
          <li key={item} className="flex gap-2 text-sm text-slate-300 leading-relaxed">
            <CheckCircle2 size={16} className="text-emerald-400 mt-0.5 shrink-0" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function QuickLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <a href={href} className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm font-bold text-slate-300 hover:border-brand-500 hover:text-white transition-colors">
      <span className="text-brand-400">{icon}</span>
      <span>{label}</span>
    </a>
  );
}

export default function ManualPage() {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-brand-600/20 grid place-items-center text-brand-400">
          <BookOpen size={20} />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-white">Manual do VendaFácil PDV</h1>
          <p className="text-slate-500 text-xs sm:text-sm">Guia de operação da mercearia, cadastro fiscal e rotina segura de caixa.</p>
        </div>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex gap-3">
        <AlertTriangle className="text-amber-300 shrink-0 mt-0.5" size={20} />
        <div className="text-sm text-amber-100 leading-relaxed">
          <b>Antes de emitir nota em produção:</b> confirme os dados com o contador e faça testes em homologação.
          Nota fiscal autorizada em produção tem validade fiscal; nota rejeitada precisa ser corrigida antes de entregar ao cliente.
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">
        <QuickLink href="#fiscal" icon={<Landmark size={16} />} label="Dados fiscais" />
        <QuickLink href="#pdv" icon={<ShoppingCart size={16} />} label="Vender no PDV" />
        <QuickLink href="#produtos" icon={<Package size={16} />} label="Produtos e estoque" />
        <QuickLink href="#problemas" icon={<HelpCircle size={16} />} label="Resolver problemas" />
      </div>

      <section id="fiscal" className="bg-slate-900 border border-slate-800 rounded-lg p-4 scroll-mt-24">
        <div className="flex items-center gap-2 mb-2">
          <FileText size={18} className="text-brand-400" />
          <h2 className="text-white font-black text-lg">Aba Fiscal: Onde Pegar Cada Dado</h2>
        </div>
        <p className="text-slate-400 text-sm leading-relaxed mb-4">
          No fluxo sem Focus, o sistema transmite direto para a SEFAZ-MT. Por isso, o cadastro fiscal precisa estar completo:
          certificado A1 da loja, CSC/idCSC da NFC-e, credenciamento, dados do emitente e dados fiscais dos produtos.
        </p>

        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="bg-slate-950 text-slate-300">
              <tr>
                <th className="text-left p-3 font-bold">Campo</th>
                <th className="text-left p-3 font-bold">Onde pegar</th>
                <th className="text-left p-3 font-bold">Cuidado</th>
              </tr>
            </thead>
            <tbody>
              {fiscalRows.map((row) => (
                <tr key={row.campo} className="border-t border-slate-800 align-top">
                  <td className="p-3 text-white font-bold">{row.campo}</td>
                  <td className="p-3 text-slate-300 leading-relaxed">{row.onde}</td>
                  <td className="p-3 text-slate-400 leading-relaxed">{row.cuidado}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid md:grid-cols-2 gap-3 mt-4">
          <div className="border border-slate-800 rounded-lg p-3">
            <h3 className="text-slate-200 font-bold text-sm flex items-center gap-2 mb-2"><ShieldCheck size={16} className="text-emerald-400" /> Checklist antes de homologar</h3>
            <ul className="space-y-2 text-sm text-slate-300">
              <li>Empresa credenciada/habilitada na SEFAZ-MT.</li>
              <li>Certificado A1 válido e senha testada.</li>
              <li>CSC/idCSC gerado para NFC-e.</li>
              <li>Produtos principais com NCM, CFOP, CSOSN/CST e unidade.</li>
              <li>Série e próximo número combinados com o contador.</li>
            </ul>
          </div>
          <div className="border border-slate-800 rounded-lg p-3">
            <h3 className="text-slate-200 font-bold text-sm flex items-center gap-2 mb-2"><FileCheck2 size={16} className="text-emerald-400" /> Homologação para produção</h3>
            <ul className="space-y-2 text-sm text-slate-300">
              <li>Configure ambiente como homologação e emita notas de teste.</li>
              <li>Consulte se a nota ficou autorizada, rejeitada ou cancelada.</li>
              <li>Corrija rejeições antes de mudar para produção.</li>
              <li>Produção só deve ser usada após liberação e validação com o contador.</li>
            </ul>
          </div>
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-4">
        {sections.map((section) => (
          <SectionBlock key={section.id} section={section} />
        ))}
      </div>

      <section className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <ClipboardList size={18} className="text-brand-400" />
          <h2 className="text-white font-black text-lg">Rotina Recomendada do Dia</h2>
        </div>
        <ol className="space-y-2">
          {rotina.map((item, idx) => (
            <li key={item} className="flex gap-3 text-sm text-slate-300">
              <span className="w-6 h-6 rounded-lg bg-brand-600/20 text-brand-300 grid place-items-center font-black text-xs shrink-0">{idx + 1}</span>
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
          <ShoppingCart size={18} className="text-brand-400 mb-2" />
          <h3 className="text-white font-bold text-sm mb-1">NFC-e no balcão</h3>
          <p className="text-slate-400 text-xs leading-relaxed">Use para venda normal ao consumidor final, principalmente no caixa da mercearia.</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
          <ReceiptText size={18} className="text-brand-400 mb-2" />
          <h3 className="text-white font-bold text-sm mb-1">NF-e para empresa</h3>
          <p className="text-slate-400 text-xs leading-relaxed">Use modelo 55 quando o cliente exige nota completa com destinatário identificado.</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
          <Wallet size={18} className="text-brand-400 mb-2" />
          <h3 className="text-white font-bold text-sm mb-1">Fiado controlado</h3>
          <p className="text-slate-400 text-xs leading-relaxed">Vincule cliente e acompanhe pagamentos em Contas a Receber.</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
          <Database size={18} className="text-brand-400 mb-2" />
          <h3 className="text-white font-bold text-sm mb-1">Backup frequente</h3>
          <p className="text-slate-400 text-xs leading-relaxed">Baixe cópias e guarde fora do computador da loja.</p>
        </div>
      </section>

      <section id="problemas" className="bg-slate-900 border border-slate-800 rounded-lg p-4 scroll-mt-24">
        <div className="flex items-center gap-2 mb-3">
          <Search size={18} className="text-brand-400" />
          <h2 className="text-white font-black text-lg">Problemas Comuns</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {problemas.map((item) => (
            <div key={item.titulo} className="border border-slate-800 rounded-lg p-3">
              <h3 className="text-slate-200 font-bold text-sm mb-1">{item.titulo}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{item.detalhe}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <h2 className="text-white font-black text-lg mb-3">Atalhos por Área</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
          <div className="text-slate-300 flex items-center gap-2"><Package size={16} className="text-brand-400" /> Produtos: cadastro, preço, fiscal e estoque.</div>
          <div className="text-slate-300 flex items-center gap-2"><Users size={16} className="text-brand-400" /> Clientes: fiado e NF-e completa.</div>
          <div className="text-slate-300 flex items-center gap-2"><Banknote size={16} className="text-brand-400" /> Caixa: conferência por forma de pagamento.</div>
          <div className="text-slate-300 flex items-center gap-2"><CreditCard size={16} className="text-brand-400" /> Maquininha: cartão integrado ou conferido.</div>
          <div className="text-slate-300 flex items-center gap-2"><Smartphone size={16} className="text-brand-400" /> PIX: QR Code e chave de recebimento.</div>
          <div className="text-slate-300 flex items-center gap-2"><FileText size={16} className="text-brand-400" /> Fiscal: A1, CSC, séries e ambiente.</div>
          <div className="text-slate-300 flex items-center gap-2"><ReceiptText size={16} className="text-brand-400" /> Vendas: histórico, notas e recibos.</div>
          <div className="text-slate-300 flex items-center gap-2"><Database size={16} className="text-brand-400" /> Backup: salvar e restaurar dados.</div>
        </div>
      </section>

      <section className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs text-slate-500 leading-relaxed">
        <b className="text-slate-300">Referências fiscais para conferência:</b> Portal NFC-e SEFAZ-MT, Portal NF-e SEFAZ-MT,
        Manual de Credenciamento NF-e da SEFAZ-MT, documentação nacional NF-e/NFC-e e orientações do contador responsável.
        Este manual ajuda no uso do sistema, mas não substitui a conferência contábil da operação da loja.
      </section>
    </motion.div>
  );
}
