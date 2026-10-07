import React from "react";

import logoSempreHub from "../assets/logo-semprehub.svg";
import { NOME_FASE, corFase, reais } from "../formatos";
import type { Dre, FaseAtual, Usuario } from "../tipos";

export function Cabecalho({
  usuario,
  aoSair,
  aoInicio,
  children,
}: {
  usuario: Usuario;
  aoSair: () => void;
  aoInicio: () => void;
  children?: React.ReactNode;
}) {
  return (
    <header className="bg-marinho text-white shadow-lg">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <button onClick={aoInicio} className="flex items-center gap-4 text-left" aria-label="SempreHub — ir para o início">
          {/* O logo vai sobre um fundo branco, como foi desenhado, para manter cores e legibilidade */}
          <span className="flex shrink-0 items-center rounded-xl bg-white px-3 py-1.5 shadow-sm ring-1 ring-ouro/40">
            <img src={logoSempreHub} alt="SempreHub" className="h-10 w-auto sm:h-12" />
          </span>
          <span className="hidden text-[11px] uppercase leading-snug tracking-[0.2em] text-ouro md:block">
            Ecossistema de
            <br />
            Aceleração de Negócios
          </span>
        </button>
        <div className="flex items-center gap-4 text-sm">
          <div className="text-right">
            <p className="font-medium">{usuario.nome}</p>
            <p className="text-xs text-white/60">{usuario.papel === "PROFESSOR" ? "Professor(a)" : "Aluno(a)"}</p>
          </div>
          <button
            onClick={aoSair}
            className="rounded-lg border border-white/20 px-3 py-1.5 text-xs font-medium text-white/80 hover:bg-white/10"
          >
            Sair
          </button>
        </div>
      </div>
      {children && <div className="mx-auto max-w-7xl px-4 pb-5 sm:px-6">{children}</div>}
    </header>
  );
}

export function Cartao({
  titulo,
  acao,
  children,
  className = "",
}: {
  titulo?: React.ReactNode;
  acao?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl bg-white p-5 shadow-[0_8px_30px_-18px_rgba(11,37,69,0.25)] ring-1 ring-slate-200 ${className}`}>
      {(titulo || acao) && (
        <div className="-mx-5 -mt-5 mb-5 flex flex-wrap items-center justify-between gap-2 rounded-t-2xl bg-gradient-to-r from-marinho to-blue-700 px-5 py-4 text-white">
          {titulo && <h2 className="text-base font-semibold text-white">{titulo}</h2>}
          <div className="[&_.text-slate-500]:text-blue-100">{acao}</div>
        </div>
      )}
      {children}
    </section>
  );
}

type VarianteBotao = "primario" | "secundario" | "perigo";

export function Botao({
  variante = "primario",
  carregando = false,
  className = "",
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: VarianteBotao; carregando?: boolean }) {
  const estilos: Record<VarianteBotao, string> = {
    primario: "bg-ouro text-marinho hover:bg-ouro/90",
    secundario: "bg-marinho text-white hover:bg-marinho/90",
    perigo: "bg-red-600 text-white hover:bg-red-700",
  };
  return (
    <button
      {...props}
      disabled={props.disabled || carregando}
      className={`rounded-lg px-4 py-2 text-sm font-semibold shadow-sm transition disabled:cursor-not-allowed disabled:opacity-60 ${estilos[variante]} ${className}`}
    >
      {carregando ? "Processando..." : children}
    </button>
  );
}

export function Campo({
  rotulo,
  ajuda,
  children,
}: {
  rotulo: string;
  ajuda?: React.ReactNode;
  children: React.ReactElement;
}) {
  const id = React.useId();
  const idAjuda = `${id}-ajuda`;
  const campo = React.cloneElement(children, {
    id,
    "aria-describedby": ajuda ? idAjuda : undefined,
  });
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
        {rotulo}
      </label>
      {campo}
      {ajuda && (
        <p id={idAjuda} className="mt-1 text-xs text-slate-500">
          {ajuda}
        </p>
      )}
    </div>
  );
}

export const estiloEntrada =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-marinho shadow-sm focus:border-ouro focus:outline-none focus:ring-2 focus:ring-ouro/40";

/**
 * Converte texto digitado no padrão brasileiro em número.
 * Aceita "1.234,56", "1234,56", "1234.56", "2.500" (milhar) e "R$ 10,5".
 */
export function lerNumeroBr(texto: string): number | null {
  let limpo = texto.replace(/R\$|%|\s/g, "");
  if (limpo === "" || limpo === "-") return null;
  if (limpo.includes(",")) {
    limpo = limpo.replace(/\./g, "").replace(",", ".");
  } else if (/^-?\d{1,3}(\.\d{3})+$/.test(limpo)) {
    limpo = limpo.replace(/\./g, ""); // "2.500" = dois mil e quinhentos
  }
  const numero = Number(limpo);
  return Number.isFinite(numero) ? numero : null;
}

function formatarNumeroBr(valor: number, casas: number, fixas: boolean): string {
  return valor.toLocaleString("pt-BR", {
    minimumFractionDigits: fixas ? casas : 0,
    maximumFractionDigits: casas,
  });
}

/**
 * Campo numérico no padrão brasileiro: aceita vírgula decimal e mostra prefixo (R$) ou sufixo (%).
 * Use `moeda` para valores em reais e `inteiro` para quantidades.
 */
export function EntradaNumero({
  valor,
  aoMudar,
  minimo = 0,
  moeda = false,
  inteiro = false,
  sufixo,
  casas,
  disabled,
  ...props
}: {
  valor: number;
  aoMudar: (valor: number) => void;
  minimo?: number;
  moeda?: boolean;
  inteiro?: boolean;
  sufixo?: string;
  casas?: number;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type">) {
  const casasDecimais = inteiro ? 0 : casas ?? (moeda ? 2 : 4);
  const formatar = (v: number) => (Number.isFinite(v) ? formatarNumeroBr(v, casasDecimais, moeda) : "");
  const [texto, setTexto] = React.useState(() => formatar(valor));
  const [editando, setEditando] = React.useState(false);

  // Atualiza o texto quando o valor muda por fora (ex.: nova rodada), mas não durante a digitação
  React.useEffect(() => {
    if (!editando) setTexto(formatar(valor));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valor, editando]);

  function aoDigitar(evento: React.ChangeEvent<HTMLInputElement>) {
    const bruto = evento.target.value.replace(/[^\d.,\-]/g, "");
    setTexto(bruto);
    const numero = lerNumeroBr(bruto);
    if (numero === null) {
      aoMudar(0);
      return;
    }
    aoMudar(inteiro ? Math.round(numero) : numero);
  }

  function aoSair() {
    setEditando(false);
    const numero = lerNumeroBr(texto);
    const final = Math.max(minimo, numero === null ? 0 : inteiro ? Math.round(numero) : numero);
    aoMudar(final);
    setTexto(formatar(final));
  }

  return (
    <div
      className={`flex items-center rounded-lg border border-slate-300 bg-white shadow-sm focus-within:border-ouro focus-within:ring-2 focus-within:ring-ouro/40 ${
        disabled ? "bg-slate-100 opacity-70" : ""
      }`}
    >
      {moeda && <span className="select-none pl-3 text-sm font-medium text-slate-500">R$</span>}
      <input
        {...props}
        disabled={disabled}
        type="text"
        inputMode={inteiro ? "numeric" : "decimal"}
        autoComplete="off"
        value={texto}
        onFocus={() => setEditando(true)}
        onChange={aoDigitar}
        onBlur={aoSair}
        className="w-full min-w-0 rounded-lg bg-transparent px-3 py-2 text-sm text-marinho focus:outline-none disabled:cursor-not-allowed"
      />
      {sufixo && <span className="select-none pr-3 text-sm font-medium text-slate-500">{sufixo}</span>}
    </div>
  );
}

function IconeOlho({ aberto }: { aberto: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" />
      {!aberto && <path d="M4 4l16 16" strokeLinecap="round" />}
    </svg>
  );
}

/** Campo de senha com botão para mostrar ou ocultar o que foi digitado. */
export function EntradaSenha({
  valor,
  aoMudar,
  ...props
}: {
  valor: string;
  aoMudar: (valor: string) => void;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type">) {
  const [visivel, setVisivel] = React.useState(false);
  return (
    <div className="relative">
      <input
        {...props}
        type={visivel ? "text" : "password"}
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        className={`${estiloEntrada} pr-11`}
      />
      <button
        type="button"
        onClick={() => setVisivel(!visivel)}
        aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
        aria-pressed={visivel}
        title={visivel ? "Ocultar senha" : "Mostrar senha"}
        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-slate-500 hover:text-marinho"
      >
        <IconeOlho aberto={visivel} />
      </button>
    </div>
  );
}

export function Aviso({ tipo = "erro", children }: { tipo?: "erro" | "info" | "sucesso"; children: React.ReactNode }) {
  const estilos = {
    erro: "border-red-300 bg-red-50 text-red-800",
    info: "border-sky-300 bg-sky-50 text-sky-900",
    sucesso: "border-emerald-300 bg-emerald-50 text-emerald-800",
  };
  return <div className={`rounded-lg border px-4 py-3 text-sm ${estilos[tipo]}`}>{children}</div>;
}

export function BarraProgresso({ rotulo, valor, escuro = false }: { rotulo: string; valor: number; escuro?: boolean }) {
  const pct = Math.min(100, Math.max(0, valor));
  return (
    <div>
      <div className={`mb-1 flex justify-between text-xs ${escuro ? "text-white/80" : "text-slate-600"}`}>
        <span>{rotulo}</span>
        <span className="font-semibold">{pct.toFixed(0)}</span>
      </div>
      <div className={`h-2 w-full overflow-hidden rounded-full ${escuro ? "bg-white/20" : "bg-slate-200"}`}>
        <div className="h-full rounded-full bg-ouro transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function SeloFase({ fase }: { fase: FaseAtual }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${corFase(fase)}`}>
      {NOME_FASE[fase]}
    </span>
  );
}

export function Indicador({ rotulo, valor, destaque = false }: { rotulo: string; valor: React.ReactNode; destaque?: boolean }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-white/60">{rotulo}</p>
      <p className={`text-xl font-bold ${destaque ? "text-ouro" : "text-white"}`}>{valor}</p>
    </div>
  );
}

export function Carregando({ texto = "Carregando..." }: { texto?: string }) {
  return <div className="p-10 text-center text-sm text-slate-500">{texto}</div>;
}

export function Modal({
  titulo,
  aoFechar,
  children,
  rodape,
}: {
  titulo: string;
  aoFechar: () => void;
  children: React.ReactNode;
  rodape?: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true">
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border-2 border-ouro bg-white shadow-2xl">
        <div className="flex items-center justify-between bg-marinho px-5 py-3">
          <h3 className="text-base font-bold uppercase tracking-wide text-ouro">{titulo}</h3>
          <button onClick={aoFechar} aria-label="Fechar" className="text-2xl leading-none text-white/70 hover:text-white">
            ×
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {rodape && <div className="flex justify-end gap-2 bg-slate-50 px-5 py-3">{rodape}</div>}
      </div>
    </div>
  );
}

const LINHAS_DRE: { chave: keyof Dre; rotulo: string }[] = [
  { chave: "impostos", rotulo: "(−) Tributos" },
  { chave: "cmv", rotulo: "(−) Custo da mercadoria vendida" },
  { chave: "refugos", rotulo: "(−) Perdas por refugo" },
  { chave: "frete", rotulo: "(−) Frete de entrega" },
  { chave: "armazenagem", rotulo: "(−) Armazenagem" },
  { chave: "depreciacao", rotulo: "(−) Depreciação das máquinas" },
  { chave: "folha", rotulo: "(−) Folha de pagamento com encargos" },
  { chave: "beneficios", rotulo: "(−) Benefícios dos funcionários" },
  { chave: "treinamento", rotulo: "(−) Treinamento" },
  { chave: "comissao_canal", rotulo: "(−) Comissão do canal" },
  { chave: "custos_fixos", rotulo: "(−) Custos fixos (aluguel, energia...)" },
  { chave: "marketing", rotulo: "(−) Marketing" },
  { chave: "pd", rotulo: "(−) Pesquisa e desenvolvimento" },
  { chave: "networking", rotulo: "(−) Networking e capacitação" },
  { chave: "rescisoes", rotulo: "(−) Rescisões" },
  { chave: "royalties", rotulo: "(−) Royalties da franquia" },
  { chave: "juros", rotulo: "(−) Juros" },
  { chave: "multas", rotulo: "(−) Multas" },
];

export function TabelaDre({ dre }: { dre: Dre }) {
  return (
    <table className="w-full border-collapse text-sm">
      <tbody>
        <tr className="border-b border-slate-200">
          <td className="py-1.5 font-semibold text-marinho">Receita bruta</td>
          <td className="py-1.5 text-right font-semibold text-marinho">{reais(dre.receita)}</td>
        </tr>
        {LINHAS_DRE.filter(({ chave }) => dre[chave] != null && (dre[chave] !== 0 || ["impostos", "cmv", "custos_fixos"].includes(chave))).map(
          ({ chave, rotulo }) => (
            <tr key={chave} className="border-b border-slate-100">
              <td className="py-1.5 text-slate-600">{rotulo}</td>
              <td className="py-1.5 text-right text-red-700">{reais(-(dre[chave] ?? 0))}</td>
            </tr>
          )
        )}
      </tbody>
      <tfoot>
        <tr className="border-t-2 border-marinho">
          <td className="py-2 font-bold text-marinho">Lucro (prejuízo) do mês</td>
          <td className={`py-2 text-right font-bold ${dre.lucro_liquido >= 0 ? "text-emerald-700" : "text-red-700"}`}>
            {reais(dre.lucro_liquido)}
          </td>
        </tr>
      </tfoot>
    </table>
  );
}

export interface SerieGrafico {
  nome: string;
  cor: string;
  valores: number[];
}

/** Gráfico de linhas simples em SVG (sem bibliotecas externas). */
export function GraficoLinhas({
  rotulosX,
  series,
  formatar = reais,
  altura = 180,
}: {
  rotulosX: string[];
  series: SerieGrafico[];
  formatar?: (v: number) => string;
  altura?: number;
}) {
  const largura = 600;
  const margem = { topo: 10, direita: 10, base: 24, esquerda: 70 };
  const todos = series.flatMap((s) => s.valores);
  if (rotulosX.length === 0 || todos.length === 0) {
    return <p className="text-sm text-slate-500">Os gráficos aparecem depois da primeira rodada.</p>;
  }
  let minimo = Math.min(0, ...todos);
  let maximo = Math.max(...todos);
  if (maximo === minimo) maximo = minimo + 1;
  const folga = (maximo - minimo) * 0.08;
  maximo += folga;
  minimo = minimo < 0 ? minimo - folga : minimo;
  const larguraUtil = largura - margem.esquerda - margem.direita;
  const alturaUtil = altura - margem.topo - margem.base;
  const x = (i: number) => margem.esquerda + (rotulosX.length === 1 ? larguraUtil / 2 : (i / (rotulosX.length - 1)) * larguraUtil);
  const y = (v: number) => margem.topo + alturaUtil - ((v - minimo) / (maximo - minimo)) * alturaUtil;
  const marcas = [0, 0.25, 0.5, 0.75, 1].map((f) => minimo + f * (maximo - minimo));

  return (
    <div>
      <svg viewBox={`0 0 ${largura} ${altura}`} className="w-full" role="img" aria-label={series.map((s) => s.nome).join(", ")}>
        {marcas.map((m) => (
          <g key={m}>
            <line x1={margem.esquerda} x2={largura - margem.direita} y1={y(m)} y2={y(m)} stroke="#102A68" strokeOpacity={0.08} />
            <text x={margem.esquerda - 6} y={y(m) + 3} textAnchor="end" fontSize="10" fill="#64748b">
              {formatar(m)}
            </text>
          </g>
        ))}
        {minimo < 0 && (
          <line x1={margem.esquerda} x2={largura - margem.direita} y1={y(0)} y2={y(0)} stroke="#dc2626" strokeOpacity={0.5} strokeDasharray="4 3" />
        )}
        {rotulosX.map((r, i) => (
          <text key={r} x={x(i)} y={altura - 6} textAnchor="middle" fontSize="10" fill="#64748b">
            {r}
          </text>
        ))}
        {series.map((s) => (
          <g key={s.nome}>
            <polyline
              points={s.valores.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
              fill="none"
              stroke={s.cor}
              strokeWidth={2.5}
              strokeLinejoin="round"
            />
            {s.valores.map((v, i) => (
              <circle key={i} cx={x(i)} cy={y(v)} r={3} fill={s.cor}>
                <title>{`${s.nome} — ${rotulosX[i]}: ${formatar(v)}`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      {series.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-600">
          {series.map((s) => (
            <span key={s.nome} className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-4 rounded" style={{ background: s.cor }} />
              {s.nome}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export const CORES_SERIES = ["#102A68", "#FFC233", "#2A6F97", "#B5523B", "#5C8A4E", "#7D5BA6", "#8C8C8C", "#1F8A8A"];
