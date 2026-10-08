import { contratarServicos, custosCampanha, TabelaServicos, type ServicoMidia } from "./CustosCampanha";
import FerramentasEstrategicas, { analisesIniciais, type AnalisesEstrategicas } from "./FerramentasEstrategicas";
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
    natureza?: "FISICO" | "SERVICO_DIGITAL" | null;
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
    modo_operacao?: "LEGADO" | "TRADICIONAL" | "STARTUP" | null;
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
    descricao?: string;
    servicos_obrigatorios?: ServicoMidia[]; escopo_pacote?: string; custos_sob_consulta?: string; dependencias?: string;
}
export interface MixProduto {
    produto_id: string; preco: number; peso: number; revisado: boolean;
    estrategia_preco: string; posicionamento: string; canais: string[]; cobertura: string; intensidade: string;
    servicos?: {id:string;quantidade:number}[];
    servicos_cotados?: {midia_id:string;valor:number;fonte_url:string}[];
    midias: { id: string; quantidade: number }[]; custo_unitario?: number; produto_nome?: string;
}
export interface PlanoComercial {
    versao_custos?: 2;
    produtos?: MixProduto[];
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
    analises?: AnalisesEstrategicas | null;
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
export function GestaoMercado({ turmaId, rodada }: {
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
    return <Cartao titulo="Pesquisa e revisão de mercado"><p className="mb-3 text-sm">Defina as quantidades para esta rodada. A pesquisa prepara notícias, análises e produtos com fontes; revise e publique para liberar aos alunos. Edições publicadas permanecem no histórico.</p><div className="grid gap-3 sm:grid-cols-5"><label>Setor<select className={estiloEntrada} value={setor} onChange={e => setSetor(e.target.value)}>{setores.map(s => <option key={s}>{s}</option>)}</select></label><label>Comércio<select className={estiloEntrada} value={comercio} onChange={e => setComercio(e.target.value)}>{["B2C", "B2B", "HIBRIDO"].map(s => <option key={s}>{s}</option>)}</select></label>{[["Notícias", noticias, setNoticias], ["Análises", analises, setAnalises], ["Produtos", produtos, setProdutos]].map(([n, v, f]) => <label key={String(n)}>{String(n)}<input className={estiloEntrada} type="number" min={n === "Produtos" ? 1 : 0} max={10} value={v as number} onChange={e => (f as (v: number) => void)(Number(e.target.value))}/></label>)}</div><div className="my-3"><Botao disabled={ocupado} onClick={() => agir(() => api.post(`/api/professor/turmas/${turmaId}/mercado/pesquisar`, { setor, comercio, noticias, analises, produtos }))}>{ocupado ? "Processando…" : "Pesquisar e preparar edição"}</Botao></div><p role="status" className="mb-3 text-sm">{mensagem}</p>{edicoes.map(e => <details key={e.id} className="mb-3 rounded border p-4"><summary className="font-bold">Rodada {e.rodada} · {e.dados.setor} · {e.publicado ? "Publicada" : "Aguardando revisão"}</summary><Artigos itens={[...e.dados.noticias, ...e.dados.analises]}/>{e.dados.produtos.map(p => <article key={p.id} className="my-3 rounded bg-slate-50 p-3"><h4 className="font-bold">{p.nome} · {reais(p.custo_unitario)} / {p.unidade}</h4><p>{p.descricao}</p><p className="text-sm">Base de custo: {p.base_custo} · {p.data}</p><Fontes fontes={p.fontes}/></article>)}{!e.publicado && <div className="flex gap-3"><Botao variante="secundario" disabled={ocupado} onClick={() => setEditor({ id: e.id, dados: JSON.parse(JSON.stringify(e.dados)) })}>Editar conteúdo</Botao><Botao disabled={ocupado} onClick={() => agir(() => api.post(`/api/professor/turmas/${turmaId}/mercado/${e.id}/publicar`, {}))}>Revisado · liberar edição</Botao></div>}</details>)}{editor && <div className="my-3 rounded border p-3"><h3 className="font-bold">Revisar edição</h3>{(["noticias", "analises"] as const).map(tipo => editor.dados[tipo].map((a, i) => <div key={`${tipo}-${i}`} className="my-3"><label>Título<input className={estiloEntrada} value={a.titulo} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, [tipo]: editor.dados[tipo].map((x, j) => j === i ? { ...x, titulo: e.target.value } : x) } })}/></label><label>Texto<textarea className={`${estiloEntrada} h-40`} value={a.texto} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, [tipo]: editor.dados[tipo].map((x, j) => j === i ? { ...x, texto: e.target.value } : x) } })}/></label><Fontes fontes={a.fontes}/></div>))}{editor.dados.produtos.map((p, i) => <div key={p.id} className="my-3"><label>Produto<input className={estiloEntrada} value={p.nome} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, nome: e.target.value } : x) } })}/></label><label>Natureza do produto<select className={estiloEntrada} value={p.natureza ?? ""} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, natureza: e.target.value as "FISICO" | "SERVICO_DIGITAL" } : x) } })}><option value="" disabled>Classificar produto</option><option value="FISICO">Produto físico</option><option value="SERVICO_DIGITAL">Serviço digital recorrente</option></select></label><label>Unidade do custo<input className={estiloEntrada} value={p.unidade} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, unidade: e.target.value } : x) } })}/></label><label>Descrição<textarea className={estiloEntrada} value={p.descricao} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, descricao: e.target.value } : x) } })}/></label><label>Custo unitário<input type="number" min={0.01} step={0.01} className={estiloEntrada} value={p.custo_unitario} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, custo_unitario: Number(e.target.value) } : x) } })}/></label><label>Base do custo<textarea className={estiloEntrada} value={p.base_custo} onChange={e => setEditor({ ...editor, dados: { ...editor.dados, produtos: editor.dados.produtos.map((x, j) => j === i ? { ...x, base_custo: e.target.value } : x) } })}/></label><Fontes fontes={p.fontes}/></div>)}<Botao disabled={ocupado} onClick={() => agir(async () => { await api.put(`/api/professor/turmas/${turmaId}/mercado/${editor.id}`, editor.dados); setEditor(null); })}>Salvar revisão</Botao></div>}</Cartao>;
}
export function EditorMix({ empresaId, rodada, plano, precoAtual, aoMudar, visao = "mix", aoNavegar }: {
    visao?: "mix" | "estrategia"; aoNavegar?: (area: string) => void;
    empresaId: number; rodada: number; precoAtual: number; plano: PlanoComercial | null | undefined;
    aoMudar: (p: PlanoComercial | null, total: number, preco?: number) => void;
}) {
    const [edicao,setEdicao]=useState<Edicao|null>(null),[midias,setMidias]=useState<Midia[]>([]),[erro,setErro]=useState("");
    const [buscaMidia,setBuscaMidia]=useState("");
    const [preparando,setPreparando]=useState(false),[erroDiagnostico,setErroDiagnostico]=useState("");
    const [diagnostico,setDiagnostico]=useState<{rodada:number;dados: Pick<AnalisesEstrategicas,"swot"|"porter"|"pestel">}|null>(null);
    useEffect(()=>{api.get<{edicoes:Edicao[]}>(`/api/aluno/empresas/${empresaId}/mercado-real`).then(d=>setEdicao(d.edicoes.find(e=>e.id===plano?.edicao_id)??d.edicoes[0]??null)).catch(e=>setErro(e.message));api.get<{midias:Midia[]}>("/api/educacao/campanhas").then(d=>setMidias(d.midias)).catch(e=>setErro(e.message));},[empresaId,rodada]);
    const total=(p:PlanoComercial)=>Math.round((p.produtos??[]).reduce((s,item)=>s+custosCampanha(item.midias,midias,item.servicos_cotados).total,0)*100)/100;
    function mudar(p:PlanoComercial){const itens=p.produtos??[];const peso=itens.reduce((s,i)=>s+i.peso,0);p={...p,custo_unitario:peso?itens.reduce((s,i)=>s+(edicao?.dados.produtos.find(x=>x.id===i.produto_id)?.custo_unitario??0)*i.peso,0)/peso:p.custo_unitario};aoMudar(p,total(p),peso?Math.round(itens.reduce((s,i)=>s+i.preco*i.peso,0)/peso*100)/100:undefined);}
    useEffect(()=>{if(!edicao||!midias.length)return;
        const itens=edicao.dados.produtos.map(p=>plano?.produtos?.find(i=>i.produto_id===p.id)??{produto_id:p.id,produto_nome:p.nome,custo_unitario:p.custo_unitario,preco:p.id===plano?.produto_id?precoAtual:Math.round(p.custo_unitario*1.3*100)/100,peso:1,revisado:false,estrategia_preco:plano?.estrategia_preco??"COMPETITIVO",posicionamento:plano?.posicionamento??"QUALIDADE",canais:plano?.canais??["DIRETO"],cobertura:plano?.cobertura??"LOCAL",intensidade:plano?.intensidade??"MEDIA",midias:p.id===plano?.produto_id?(plano?.midias??[]):[]});
        if(!plano?.produtos?.length||plano.versao_custos!==2)mudar({...plano,versao_custos:2,edicao_id:edicao.id,produto_id:itens[0].produto_id,produtos:itens.map(i=>({...i,revisado: false,servicos:contratarServicos(i.midias,midias)})),estrategia_preco:plano?.estrategia_preco??"COMPETITIVO",posicionamento:plano?.posicionamento??"QUALIDADE",canais:plano?.canais??["DIRETO"],cobertura:plano?.cobertura??"LOCAL",intensidade:plano?.intensidade??"MEDIA",midias:[],estrategias:plano?.estrategias??{}});
    },[edicao,midias]);
    async function preparar(){if(!edicao)return;setPreparando(true);setErroDiagnostico("");try{setDiagnostico(await api.post(`/api/aluno/empresas/${empresaId}/diagnostico/${edicao.id}`,{}));}catch(e){setErroDiagnostico(e instanceof Error?e.message:"Diagnóstico indisponível.");}finally{setPreparando(false);}}
    useEffect(()=>{if(visao==="estrategia"&&edicao&&!diagnostico&&!preparando&&!erroDiagnostico)preparar();},[visao,edicao]);
    useEffect(()=>{if(diagnostico&&plano){const a={...analisesIniciais(),...plano.analises,...diagnostico.dados,diagnostico_automatico:true};a.swot={...a.swot,diretriz:plano.analises?.swot.diretriz??null};mudar({...plano,analises:a});}},[diagnostico]);
    if(!edicao||!plano?.produtos?.length)return erro?<p role="alert">{erro}</p>:<p>Carregando catálogo de produtos…</p>;
    function cotar(produtoId:string,midiaId:string,campos:{valor?:number;fonte_url?:string}){const item=plano?.produtos?.find(p=>p.produto_id===produtoId);if(!item)return;const atual=item.servicos_cotados?.find(c=>c.midia_id===midiaId)??{midia_id:midiaId,valor:0,fonte_url:""};atualizar(produtoId,{servicos_cotados:[...(item.servicos_cotados??[]).filter(c=>c.midia_id!==midiaId),{...atual,...campos}]});}
    function atualizar(id:string,campos:Partial<MixProduto>){if(!plano)return;if(campos.midias){const anterior=plano.produtos?.find(i=>i.produto_id===id)?.midias??[];const pares=["flyer-impressao","flyer-distribuicao"];const alterado=pares.find(k=>JSON.stringify(anterior.find(m=>m.id===k))!==JSON.stringify(campos.midias?.find(m=>m.id===k)));if(alterado){const escolhido=campos.midias.find(m=>m.id===alterado);campos.midias=campos.midias.filter(m=>!pares.includes(m.id));if(escolhido)campos.midias.push(...pares.map(id=>({id,quantidade:escolhido.quantidade})));}campos.servicos=contratarServicos(campos.midias,midias);campos.servicos_cotados=(plano.produtos?.find(i=>i.produto_id===id)?.servicos_cotados??[]).filter(c=>campos.midias?.some(m=>m.id===c.midia_id));}mudar({...plano,versao_custos:2,produtos:plano.produtos?.map(i=>i.produto_id===id?{...i,...campos,revisado:campos.revisado??false}:i)});}
    const pesos=plano.produtos.reduce((s,i)=>s+i.peso,0), completos=plano.produtos.filter(i=>i.revisado).length;
    return <fieldset className="mb-6 rounded-2xl border-2 border-blue-200 p-4 sm:p-6"><legend className="px-2 text-lg font-bold">{visao==="estrategia"?"Diagnóstico e público-alvo":"Mix de todos os produtos"}</legend>
    <div hidden={visao!=="mix"}><p className="mb-4 rounded-xl bg-blue-50 p-4">Configure e revise os <strong>{plano.produtos.length} produtos</strong>. Cada produto possui preço, canais e campanha próprios. A capacidade total de produção e as compras de insumos são divididas conforme os pesos definidos abaixo. O estoque permanece separado por produto.</p>
    <p className="mb-3 font-bold text-blue-800">{completos} de {plano.produtos.length} mixes revisados · campanha total {reais(total(plano))}</p><progress className="mb-4 h-3 w-full accent-blue-700" max={plano.produtos.length} value={completos} aria-label="Mixes revisados"/>
    <a href="#" onClick={e=>{e.preventDefault();aoNavegar?.("midias");}} className="mb-4 inline-block font-semibold text-blue-700 underline">Consultar manual de mídias →</a>
    <div className="space-y-4">{plano.produtos.map((item,index)=>{const produto=edicao.dados.produtos.find(p=>p.id===item.produto_id);const faltaCotacao=item.midias.some(m=>midias.find(c=>c.id===m.id)?.custos_sob_consulta&&!item.servicos_cotados?.some(c=>c.midia_id===m.id&&c.valor>=.01&&/^https?:\/\/[^\s]+$/.test(c.fonte_url)));return <details key={item.produto_id} open={index===0} className="rounded-2xl border-2 border-blue-200 bg-white p-4"><summary className="cursor-pointer text-lg font-bold text-[#102A68]">{produto?.nome??item.produto_id} · {item.revisado?"Revisado ✓":"Configurar mix ↓"} · {reais(item.preco)}</summary><p className="mt-3 text-sm">{produto?.descricao}</p><p className="my-2 font-bold">Custo unitário: {reais(produto?.custo_unitario??0)} · margem antes de despesas: {reais(item.preco-(produto?.custo_unitario??0))}</p>{produto&&<Fontes fontes={produto.fontes}/>}
    <div className="my-4 grid gap-3 sm:grid-cols-2"><label className="font-semibold">Preço de venda · {produto?.nome}<input aria-label={`Preço: ${produto?.nome}`} className={estiloEntrada} type="number" min={.01} max={100000} step={.01} value={item.preco} onChange={e=>atualizar(item.produto_id,{preco:Number(e.target.value)})}/></label><label className="font-semibold">Peso da operação · {(item.peso/Math.max(1,pesos)*100).toFixed(1)}% da capacidade<input aria-label={`Peso: ${produto?.nome}`} className={estiloEntrada} type="number" min={.01} max={100} step={.01} value={item.peso} onChange={e=>atualizar(item.produto_id,{peso:Number(e.target.value)})}/></label></div>
    <div className="grid gap-3 sm:grid-cols-2">{([['estrategia_preco','Estratégia de preço',['PENETRACAO','COMPETITIVO','DESNATAMENTO','VALOR']],['posicionamento','Posicionamento',['QUALIDADE','PRECO','INOVACAO']],['cobertura','Cobertura',['LOCAL','REGIONAL','NACIONAL','INTERNACIONAL']],['intensidade','Intensidade',['BAIXA','MEDIA','ALTA','INTENSIVA']]] as const).map(([k,n,op])=><label key={k}>{n}<select aria-label={`${n}: ${produto?.nome}`} className={estiloEntrada} value={item[k]} onChange={e=>atualizar(item.produto_id,{[k]:e.target.value})}>{op.map(o=><option key={o}>{o}</option>)}</select></label>)}</div>
    <h4 className="my-3 font-bold">Canais de distribuição</h4><div className="flex flex-wrap gap-3">{canais.map(c=><label key={c}><input type="checkbox" checked={item.canais.includes(c)} onChange={e=>atualizar(item.produto_id,{canais:e.target.checked?[...item.canais,c]:item.canais.filter(x=>x!==c)})}/> {c}</label>)}</div>
    <h4 className="my-3 font-bold">Mídias deste produto</h4><p className="mb-2 text-sm">A contratação inclui mídia e serviços obrigatórios. CPM compra mil impressões; CPC compra cliques. Produção não compra audiência. Confira o custo completo antes de revisar o mix.</p><label className="mb-3 block text-sm font-semibold">Encontrar mídia<input aria-label="Encontrar mídia" className={estiloEntrada} value={buscaMidia} onChange={e=>setBuscaMidia(e.target.value)} placeholder="Ex.: TV, rádio, panfletos…"/></label><div className="max-h-96 space-y-2 overflow-auto">{midias.filter(m=>`${m.nome} ${m.categoria}`.toLocaleLowerCase().includes(buscaMidia.toLocaleLowerCase())).map(m=>{const escolhida=item.midias.find(x=>x.id===m.id);return <article key={m.id} className={`rounded-xl border p-3 ${escolhida?"border-blue-700 bg-blue-50":"bg-slate-50"}`}><label className="font-semibold"><input type="checkbox" aria-label={`${m.nome}: ${produto?.nome}`} checked={!!escolhida} onChange={e=>atualizar(item.produto_id,{midias:e.target.checked?[...item.midias,{id:m.id,quantidade:1}]:item.midias.filter(x=>x.id!==m.id)})}/> {m.nome} · {reais(m.preco_unitario)} / {m.unidade}</label><p className="mt-1 text-sm text-slate-600">{m.descricao}</p><p className="mt-1 text-xs text-slate-600">{m.escopo_pacote}</p>{m.dependencias&&<p className="mt-2 text-xs font-semibold text-blue-800">{m.dependencias}</p>}{m.custos_sob_consulta&&<p className="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-900">Custos sem cotação pública validada: {m.custos_sob_consulta} Informe o orçamento dos serviços para concluir esta contratação.</p>}<TabelaServicos servicos={item.midias.some(x=>x.id==="jingle")&&["radio-spot","radio-streaming"].includes(m.id)?[]:m.servicos_obrigatorios??[]} quantidade={escolhida?.quantidade??1}/>{item.midias.some(x=>x.id==="jingle")&&["radio-spot","radio-streaming"].includes(m.id)&&<p className="text-xs text-emerald-800">A produção do jingle contratado fornece o áudio; não cobramos outro spot simples.</p>}{escolhida&&m.custos_sob_consulta&&<div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3"><h5 className="font-bold">Orçamento obrigatório do serviço</h5><p className="text-xs">Valor total para todas as unidades deste formato, produto e mês. Informe a cotação obtida com o fornecedor; o sistema registra a fonte, mas não verifica a proposta automaticamente.</p><div className="mt-2 grid gap-2 sm:grid-cols-2"><label className="text-sm">Custo total dos serviços (R$)<input aria-label={`Orçamento ${m.nome}: ${produto?.nome}`} type="number" min="0.01" step="0.01" className={estiloEntrada} value={item.servicos_cotados?.find(c=>c.midia_id===m.id)?.valor??""} onChange={e=>cotar(item.produto_id,m.id,{valor:Number(e.target.value)})}/></label><label className="text-sm">Link do orçamento / fornecedor<input aria-label={`Fonte orçamento ${m.nome}: ${produto?.nome}`} type="url" placeholder="https://…" className={estiloEntrada} value={item.servicos_cotados?.find(c=>c.midia_id===m.id)?.fonte_url??""} onChange={e=>cotar(item.produto_id,m.id,{fonte_url:e.target.value})}/></label></div></div>}{escolhida&&<label>Quantidade<input aria-label={`Quantidade ${m.nome}: ${produto?.nome}`} type="number" min={1} max={1000000} className={estiloEntrada} value={escolhida.quantidade} onChange={e=>atualizar(item.produto_id,{midias:item.midias.map(x=>x.id===m.id?{...x,quantidade:Number(e.target.value)}:x)})}/></label>}</article>;})}</div>
    <div className="mt-4 grid gap-2 rounded-xl bg-slate-100 p-4 sm:grid-cols-3"><p className="text-sm">Mídia / pacote<br/><strong>{reais(custosCampanha(item.midias,midias,item.servicos_cotados).veiculacao)}</strong></p><p className="text-sm">Produção e serviços<br/><strong>{reais(custosCampanha(item.midias,midias,item.servicos_cotados).servicos)}</strong></p><p className="text-sm text-emerald-800">{faltaCotacao?"Subtotal · falta orçamento":"Total da contratação"}<br/><strong>{reais(custosCampanha(item.midias,midias,item.servicos_cotados).total)}</strong></p></div>
    {faltaCotacao&&<p role="status" className="mt-3 rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-900">Complete o valor e a fonte dos serviços sob consulta para revisar este mix. O subtotal ainda não contempla a contratação completa.</p>}<label className="mt-4 flex items-center gap-2 rounded-lg bg-blue-100 p-3 font-bold"><input aria-label={`Revisar mix: ${produto?.nome}`} disabled={faltaCotacao} type="checkbox" checked={item.revisado} onChange={e=>atualizar(item.produto_id,{revisado:e.target.checked})}/>Revisei preço, canais e custo completo da campanha, incluindo os serviços</label></details>;})}</div>
    <button type="button" className="mt-4 rounded-xl bg-blue-700 px-4 py-3 font-bold text-white" onClick={()=>aoNavegar?.("estrategia")}>Consultar diagnósticos e definir público-alvo →</button></div>
    <div hidden={visao!=="estrategia"}><p className="mb-3 rounded-xl bg-blue-50 p-3">SWOT, Porter e PESTEL são preparados automaticamente pelo sistema com informações da empresa e da edição de mercado. Consulte o diagnóstico para tomar suas decisões; BCG e segmentação ficam a cargo da equipe.</p>{preparando&&<p role="status">Preparando diagnósticos do mês…</p>}{erroDiagnostico&&<div role="alert"><p>{erroDiagnostico}</p><Botao type="button" onClick={preparar} disabled={preparando}>Tentar preparar diagnóstico novamente</Botao></div>}<FerramentasEstrategicas automatico valor={plano.analises} aoMudar={analises=>mudar({...plano,analises})} produtos={edicao.dados.produtos} midias={midias} comercio={edicao.dados.comercio} legado={plano.estrategias} rodada={rodada}/></div></fieldset>;
}

export function RelatoriosEmpresariaisProfessor({ turmaId, ultimaRodada, empresas }: { turmaId: number; ultimaRodada: number; empresas: { id: number; nome: string }[] }) {
    const [ocupado, setOcupado] = useState(false);
    const [mensagem, setMensagem] = useState("");
    async function gerar(empresaId: number) {
        setOcupado(true);
        setMensagem("");
        try {
            await api.post(`/api/professor/turmas/${turmaId}/empresas/${empresaId}/relatorio-empresarial/${ultimaRodada}`, {});
            setMensagem("Relatório disponível para a empresa.");
        } catch (e) {
            setMensagem(e instanceof Error ? e.message : "Erro ao gerar relatório.");
        } finally {
            setOcupado(false);
        }
    }
    return <Cartao titulo="Relatórios empresariais das rodadas encerradas">
        <p className="text-sm">O relatório usa decisões e resultados registrados; depois de gerado fica preservado e disponível para a equipe.</p>
        <p role="status" className="my-3 text-sm">{mensagem}</p>
        {ultimaRodada < 1 ? <p className="text-sm text-slate-500">Os relatórios estarão disponíveis após o encerramento da primeira rodada.</p> : empresas.map(e => <div key={e.id} className="my-2 flex items-center gap-3"><span>{e.nome}</span><Botao variante="secundario" disabled={ocupado} onClick={() => gerar(e.id)}>Gerar relatório · rodada {ultimaRodada}</Botao></div>)}
    </Cartao>;
}
