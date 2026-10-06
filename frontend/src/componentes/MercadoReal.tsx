import React, { useEffect, useState } from "react";
import { api } from "../api";
import { reais } from "../formatos";
import { Botao, Cartao, estiloEntrada } from "./ui";
interface Fonte {
    titulo: string;
    url: string;
}
interface Artigo {
    titulo: string;
    texto: string;
    data: string;
    fontes: Fonte[];
}
interface Produto {
    id: string;
    nome: string;
    descricao: string;
    custo_unitario: number;
    unidade: string;
    base_custo: string;
    data: string;
    fontes: Fonte[];
}
interface Dados {
    setor: string;
    comercio: string;
    noticias: Artigo[];
    analises: Artigo[];
    produtos: Produto[];
}
interface Edicao {
    id: number;
    rodada: number;
    publicado: boolean;
    dados: Dados;
}
interface Midia {
    id: string;
    nome: string;
    categoria: string;
    preco_unitario: number;
    unidade: string;
}
export interface PlanoComercial {
    edicao_id: number;
    produto_id: string;
    estrategia_preco: string;
    posicionamento: string;
    canais: string[];
    cobertura: string;
    intensidade: string;
    midias: {
        id: string;
        quantidade: number;
    }[];
    estrategias: Record<string, string>;
    custo_unitario?: number;
    produto_nome?: string;
}
const canais = ["VAREJO", "ECOMMERCE", "MARKETPLACE", "ATACADO", "FRANQUIA", "DIRETO"];
function Fontes({ fontes }: {
    fontes: Fonte[];
}) { return <ul className="mt-2 text-xs text-slate-500">{fontes.map(f => <li key={f.url}><a href={f.url} target="_blank" rel="noreferrer" className="underline">{f.titulo}</a></li>)}</ul>; }
function Artigos({ itens }: {
    itens: Artigo[];
}) { return <div className="grid gap-3 md:grid-cols-2">{itens.map((a, i) => <article key={i} className="rounded border p-3"><h4 className="font-bold">{a.titulo}</h4><p className="text-xs">{a.data}</p><p className="mt-2 whitespace-pre-wrap text-sm">{a.texto}</p><Fontes fontes={a.fontes}/></article>)}</div>; }
export function MercadoPublicado({ empresaId, rodada, visao = "mercado" }: {
    visao?: "mercado" | "relatorios";
    empresaId: number;
    rodada: number;
}) {
    const [edicoes, setEdicoes] = useState<Edicao[]>([]);
    const [erro, setErro] = useState("");
    const [relatorios, setRelatorios] = useState<{
        rodada: number;
        texto: string;
    }[]>([]);
    useEffect(() => { api.get<{
        edicoes: Edicao[];
    }>(`/api/aluno/empresas/${empresaId}/mercado-real`).then(d => setEdicoes(d.edicoes)).catch(e => setErro(e.message)); api.get<{
        rodada: number;
        texto: string;
    }[]>(`/api/aluno/empresas/${empresaId}/relatorios-empresariais`).then(setRelatorios).catch(e => setErro(e.message)); }, [empresaId, rodada]);
    return <Cartao titulo={visao === "mercado" ? "SempreHub News e análises de mercado" : "Relatórios empresariais"}>{erro && <p role="alert">{erro}</p>}{visao === "mercado" && edicoes.length === 0 && <p className="text-sm">O sistema ainda não disponibilizou uma edição de mercado.</p>}{visao === "mercado" && edicoes.map(e => <details key={e.id} className="mb-4 rounded border p-3" open={e.rodada === rodada}><summary className="font-bold">Rodada {e.rodada} · {e.dados.setor} · {e.dados.comercio}</summary><h3 className="my-3 font-bold">SempreHub News · notícias de mercado</h3><Artigos itens={e.dados.noticias}/><h3 className="my-3 font-bold">Análises de mercado</h3><Artigos itens={e.dados.analises}/></details>)}{visao === "relatorios" && relatorios.length === 0 && <p className="text-sm">Os relatórios estarão disponíveis após o encerramento da rodada e sua disponibilização pelo sistema.</p>}{visao === "relatorios" && relatorios.map(r => <details key={r.rodada} className="mb-3 rounded border p-3"><summary className="font-bold">Relatório empresarial · rodada {r.rodada}</summary><p className="mt-3 whitespace-pre-wrap text-sm">{r.texto}</p></details>)}</Cartao>;
}
export function GestaoMercado({ turmaId, rodada, empresas }: {
    turmaId: number;
    rodada: number;
    empresas: {
        id: number;
        nome: string;
    }[];
}) {
    const [edicoes, setEdicoes] = useState<Edicao[]>([]), [setores, setSetores] = useState<string[]>([]), [setor, setSetor] = useState("Eletrônicos e Tecnologia"), [comercio, setComercio] = useState("B2C"), [noticias, setNoticias] = useState(3), [analises, setAnalises] = useState(2), [produtos, setProdutos] = useState(3), [ocupado, setOcupado] = useState(false), [mensagem, setMensagem] = useState(""), [editor, setEditor] = useState<{
        id: number;
        dados: Dados;
    } | null>(null);
    async function carregar() { const d = await api.get<{
        setores: string[];
        edicoes: Edicao[];
    }>(`/api/professor/turmas/${turmaId}/mercado`); setSetores(d.setores); setEdicoes(d.edicoes); }
    useEffect(() => { carregar().catch(e => setMensagem(e.message)); }, [turmaId, rodada]);
    async function agir(f: () => Promise<unknown>) { setOcupado(true); setMensagem(""); try {
        await f();
        await carregar();
        setMensagem("Operação concluída.");
    }
    catch (e) {
        setMensagem(e instanceof Error ? e.message : "Erro na operação.");
    }
    finally {
        setOcupado(false);
    } }
    return <Cartao titulo="Pesquisa e revisão de mercado"><p className="mb-3 text-sm">Defina as quantidades para esta rodada. A pesquisa prepara notícias, análises e produtos com fontes; revise e publique para liberar aos alunos. Edições publicadas permanecem no histórico.</p><div className="grid gap-3 sm:grid-cols-5"><label>Setor<select className={estiloEntrada} value={setor} onChange={e => setSetor(e.target.value)}>{setores.map(s => <option key={s}>{s}</option>)}</select></label><label>Comércio<select className={estiloEntrada} value={comercio} onChange={e => setComercio(e.target.value)}>{["B2C", "B2B", "HIBRIDO"].map(s => <option key={s}>{s}</option>)}</select></label>{[["Notícias", noticias, setNoticias], ["Análises", analises, setAnalises], ["Produtos", produtos, setProdutos]].map(([n, v, f]) => <label key={String(n)}>{String(n)}<input className={estiloEntrada} type="number" min={n === "Produtos" ? 1 : 0} max={10} value={v as number} onChange={e => (f as (v: number) => void)(Number(e.target.value))}/></label>)}</div><div className="my-3"><Botao disabled={ocupado} onClick={() => agir(() => api.post(`/api/professor/turmas/${turmaId}/mercado/pesquisar`, { setor, comercio, noticias, analises, produtos }))}>{ocupado ? "Processando…" : "Pesquisar e preparar edição"}</Botao></div><p role="status" className="mb-3 text-sm">{mensagem}</p>{edicoes.map(e => <details key={e.id} className="mb-3 rounded border p-4"><summary className="font-bold">Rodada {e.rodada} · {e.dados.setor} · {e.publicado ? "Publicada" : "Aguardando revisão"}</summary><Artigos itens={[...e.dados.noticias, ...e.dados.analises]}/>{e.dados.produtos.map(p => <article key={p.id} className="my-3 rounded bg-slate-50 p-3"><h4 className="font-bold">{p.nome} · {reais(p.custo_unitario)} / {p.unidade}</h4><p>{p.descricao}</p><p className="text-sm">Base de custo: {p.base_custo} · {p.data}</p><Fontes fontes={p.fontes}/></article>)}{!e.publicado && <div className="flex gap-3"><Botao variante="secundario" disabled={ocupado} onClick={() => setEditor({ id: e.id, dados: JSON.parse(JSON.stringify(e.dados)) })}>Editar conteúdo</Botao><Botao disabled={ocupado} onClick={() => agir(() => api.post(`/api/professor/turmas/${turmaId}/mercado/${e.id}/publicar`, {}))}>Revisado · liberar edição</Botao></div>}</details>)}{editor && <div className="my-3 rounded border p-3"><h3 className="font-bold">Revisar edição</h3>{(["noticias", "analises"] as const).map(tipo => editor.dados[tipo].map((a, i) => <div key={`${tipo}-${i}`} className="my-3"><label>Título<input className={estiloEntrada} value={a.titulo} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, [tipo]: editor.dados[tipo].map((x, j) => j === i ? { ...x, titulo: e.target.value } : x) } })}/></label><label>Texto<textarea className={`${estiloEntrada} h-40`} value={a.texto} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, [tipo]: editor.dados[tipo].map((x, j) => j === i ? { ...x, texto: e.target.value } : x) } })}/></label><Fontes fontes={a.fontes}/></div>))}{editor.dados.produtos.map((p, i) => <div key={p.id} className="my-3"><label>Produto<input className={estiloEntrada} value={p.nome} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, nome: e.target.value } : x) } })}/></label><label>Descrição<textarea className={estiloEntrada} value={p.descricao} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, descricao: e.target.value } : x) } })}/></label><label>Custo unitário<input type="number" min={0.01} step={0.01} className={estiloEntrada} value={p.custo_unitario} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, custo_unitario: Number(e.target.value) } : x) } })}/></label><label>Base do custo<textarea className={estiloEntrada} value={p.base_custo} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, base_custo: e.target.value } : x) } })}/></label><Fontes fontes={p.fontes}/></div>)}<Botao disabled={ocupado} onClick={() => agir(async () => { await api.put(`/api/professor/turmas/${turmaId}/mercado/${editor.id}`, editor.dados); setEditor(null); })}>Salvar revisão</Botao></div>}<h3 className="my-3 font-bold">Relatórios empresariais das rodadas encerradas</h3><p className="text-xs">O relatório usa decisões e resultados registrados; depois de gerado fica preservado e disponível para a equipe.</p>{rodada <= 1 ? <p className="mt-3 text-sm text-slate-500">Os relatórios estarão disponíveis após o encerramento da primeira rodada.</p> : empresas.map(e => <div key={e.id} className="my-2 flex items-center gap-3"><span>{e.nome}</span><Botao variante="secundario" disabled={ocupado || rodada <= 1} onClick={() => agir(() => api.post(`/api/professor/turmas/${turmaId}/empresas/${e.id}/relatorio-empresarial/${rodada - 1}`, {}))}>Gerar relatório · rodada {rodada - 1}</Botao></div>)}</Cartao>;
}
export function EditorMix({ empresaId, rodada, plano, aoMudar }: {
    empresaId: number;
    rodada: number;
    plano: PlanoComercial | null | undefined;
    aoMudar: (p: PlanoComercial | null, total: number) => void;
}) {
    const [edicao, setEdicao] = useState<Edicao | null>(null), [midias, setMidias] = useState<Midia[]>([]), [erro, setErro] = useState("");
    useEffect(() => { api.get<{
        edicoes: Edicao[];
    }>(`/api/aluno/empresas/${empresaId}/mercado-real`).then(d => setEdicao(d.edicoes.find(e => e.id === plano?.edicao_id) ?? d.edicoes.find(e => e.rodada === rodada) ?? d.edicoes[0] ?? null)).catch(e => setErro(e.message)); api.get<{
        midias: Midia[];
    }>("/api/educacao/campanhas").then(d => setMidias(d.midias)).catch(e => setErro(e.message)); }, [empresaId, rodada]);
    const total = (p: PlanoComercial) => Math.round(p.midias.reduce((s, a) => s + (midias.find(m => m.id === a.id)?.preco_unitario ?? 0) * a.quantidade, 0) * 100) / 100;
    function mudar(p: PlanoComercial) { aoMudar(p, total(p)); }
    if (!edicao)
        return erro ? <p role="alert">{erro}</p> : null;
    function selecionarProduto(id: string) { const edicaoAtual = edicao; if (!edicaoAtual) return;  if (!id) {
        aoMudar(null, 0);
        return;
    } mudar({ ...plano, edicao_id: edicaoAtual.id, produto_id: id, custo_unitario: edicaoAtual.dados.produtos.find(p => p.id === id)?.custo_unitario, estrategia_preco: plano?.estrategia_preco ?? "COMPETITIVO", posicionamento: plano?.posicionamento ?? "QUALIDADE", canais: plano?.canais ?? ["DIRETO"], cobertura: plano?.cobertura ?? "LOCAL", intensidade: plano?.intensidade ?? "MEDIA", midias: plano?.midias ?? [], estrategias: plano?.estrategias ?? {} }); }
    return <fieldset className="mb-6 rounded border p-4"><legend className="font-bold">Mix de marketing · decisões da equipe</legend><p className="mb-3 text-sm">Produtos disponibilizados pelo sistema. Escolha seu produto, preço no campo de venda, canais e mídias. Quantidade e preço da mídia determinam o gasto em marketing; não há obrigação de consumir todo o caixa.</p><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Produtos disponíveis">{edicao.dados.produtos.map(p => <button type="button" key={p.id} aria-pressed={plano?.produto_id === p.id} className={`rounded-2xl border-2 p-5 text-left transition ${plano?.produto_id === p.id ? "border-ouro bg-amber-50" : "border-slate-200 bg-white hover:border-ouro"}`} onClick={() => selecionarProduto(p.id)}><span className="text-xs font-semibold text-slate-500">{plano?.produto_id === p.id ? "✓ Produto selecionado · configurar abaixo" : "Selecionar e configurar produto ↓"}</span><h3 className="my-2 text-lg font-bold">{p.nome}</h3><p className="mb-3 text-sm text-slate-600">{p.descricao}</p><strong>{reais(p.custo_unitario)} / {p.unidade}</strong><p className="mt-3 rounded-lg bg-blue-600 px-3 py-2 text-center text-sm font-bold text-white">{plano?.produto_id === p.id ? "Configuração aberta abaixo ↓" : "Selecionar e configurar ↓"}</p><p className="text-xs text-slate-500">Custo de aquisição</p></button>)}</div>{plano && <><button type="button" onClick={() => aoMudar(null, 0)} className="mt-3 text-sm text-slate-500 underline">Limpar seleção de produto</button><div className="my-3">{edicao.dados.produtos.filter(p => p.id === plano.produto_id).map(p => <article key={p.id}><p>{p.descricao}</p><p className="text-xs">{p.base_custo} · consulta: {p.data}</p><Fontes fontes={p.fontes}/></article>)}</div><div className="my-3 grid gap-3 sm:grid-cols-2">{([['estrategia_preco', 'Estratégia de preço', ['PENETRACAO', 'COMPETITIVO', 'DESNATAMENTO', 'VALOR']], ['posicionamento', 'Posicionamento', ['QUALIDADE', 'PRECO', 'INOVACAO']], ['cobertura', 'Cobertura', ['LOCAL', 'REGIONAL', 'NACIONAL', 'INTERNACIONAL']], ['intensidade', 'Intensidade', ['BAIXA', 'MEDIA', 'ALTA', 'INTENSIVA']]] as const).map(([k, n, op]) => <div key={k}><p className="mb-2 font-semibold">{n}</p><div className="grid grid-cols-2 gap-2">{op.map(o => <button type="button" key={o} aria-pressed={plano[k] === o} onClick={() => mudar({ ...plano, [k]: o })} className={`rounded-xl border px-3 py-3 text-left text-xs font-semibold ${plano[k] === o ? "border-ouro bg-amber-50" : "border-slate-200 bg-white hover:border-ouro"}`}>{o.replace(/_/g, " ")}</button>)}</div></div>)}</div><p className="text-sm">Estratégia de preço, cobertura e intensidade registram o planejamento. Revise o preço de venda, o custo por unidade e o investimento total antes de enviar a decisão.</p><h4 className="my-3 font-bold">Canais de distribuição</h4><div className="flex flex-wrap gap-3">{canais.map(c => <label key={c}><input type="checkbox" checked={plano.canais.includes(c)} onChange={e => mudar({ ...plano, canais: e.target.checked ? [...plano.canais, c] : plano.canais.filter(x => x !== c) })}/> {c}</label>)}</div><h4 className="my-3 font-bold">Catálogo de mídias · total {reais(total(plano))}</h4><p className="mb-3 text-xs">Custos da tabela de simulação, não cotações atuais. Informe lotes para CPM (mil impressões) e unidades para CPC, envios e inserções.</p><div className="max-h-96 space-y-2 overflow-auto">{midias.map(m => { const a = plano.midias.find(a => a.id === m.id); return <div key={m.id} className={`rounded-xl border p-4 text-sm ${a ? "border-ouro bg-amber-50" : "border-slate-200 bg-white"}`}><label><input type="checkbox" role="switch" aria-label={m.nome} className="h-5 w-5 accent-[#FFC233]" checked={!!a} onChange={e => mudar({ ...plano, midias: e.target.checked ? [...plano.midias, { id: m.id, quantidade: 1 }] : plano.midias.filter(a => a.id !== m.id) })}/> {m.nome} · {m.categoria} · {reais(m.preco_unitario)} / {m.unidade}</label>{a && <label className="ml-3">Quantidade <input type="number" className="w-24 rounded border p-1" min={1} max={1000000} value={a.quantidade} onChange={e => mudar({ ...plano, midias: plano.midias.map(x => x.id === m.id ? { ...x, quantidade: Number(e.target.value) } : x) })}/></label>}</div>; })}</div><h4 className="my-3 font-bold">Ferramentas estratégicas e segmentação</h4><p className="text-xs">Registre as análises da equipe. Elas permanecem junto das decisões desta rodada.</p><div className="grid gap-3 sm:grid-cols-2">{["SWOT", "PORTER", "BCG", "PESTEL", "DEMOGRAFICA", "GEOGRAFICA", "PSICOGRAFICA", "COMPORTAMENTAL"].map(k => <label key={k}>{k}<textarea className={estiloEntrada} maxLength={12000} value={plano.estrategias[k] ?? ""} onChange={e => mudar({ ...plano, estrategias: { ...plano.estrategias, [k]: e.target.value } })}/></label>)}</div></>}</fieldset>;
}
