import React, { useEffect, useState } from "react";
import { api } from "../api";
import { reais, percentual } from "../formatos";
import { Botao, Cartao } from "./ui";

interface Midia { slug: string; nome: string; finalidade: string; unidade_venda: string; custo_entrada: string; pagamento_prazo: string; efeito_caixa: string }
interface Catalogo { midias: Midia[]; ressalvas: Record<string,string> }
interface Jornal { orientacao: string; edicoes: { rodada: number; titulo: string; narrativa: string; mercado: { preco_medio: number; unidades_vendidas: number; receita_total: number } | null }[] }
interface Relatorio extends Catalogo { empresa: string; turma: string; evento: {titulo:string;narrativa:string}|null; perguntas:string[]; resultado: { preco:number; unidades_vendidas:number; participacao_mercado:number; dre:Record<string,number>; dfc:Record<string,unknown>|null; balanco:Record<string,number>|null; alertas:string[]; participacao:{membros:{aluno_id:number;nome:string;cargos:string[];confirmou_versao:boolean|null}[]} } }

export function CatalogoCompleto({ catalogo }: { catalogo?: Catalogo }) {
  const [dados,setDados] = useState<Catalogo | null>(catalogo ?? null);
  const [erro,setErro] = useState("");
  const [filtro,setFiltro] = useState("");
  useEffect(() => { if (!catalogo) api.get<Catalogo>("/api/educacao/midias").then(setDados).catch(e => setErro(e.message)); }, [catalogo]);
  return <div><p className="mb-3 text-sm">Marketing inclui tráfego pago, conteúdo, SEO, CRM, identidade visual, eventos e parcerias. Planeje o orçamento considerando receita, margem, objetivos e caixa disponível.</p><label className="block text-sm">Buscar mídia<input className="mb-3 mt-1 block w-full rounded border p-2" value={filtro} onChange={e => setFiltro(e.target.value)} /></label>{erro && <p role="alert">{erro}</p>}<div className="grid gap-3 md:grid-cols-2">{dados?.midias.filter(m => `${m.nome} ${m.finalidade}`.toLocaleLowerCase().includes(filtro.toLocaleLowerCase())).map(m => <article key={m.slug} className="rounded-lg border p-4 text-sm"><h3 className="font-bold">{m.nome}</h3><p className="my-2">{m.finalidade}</p><p><strong>Unidade:</strong> {m.unidade_venda}</p><p><strong>Faixa de planejamento:</strong> {m.custo_entrada}</p><p><strong>Pagamento e prazo:</strong> {m.pagamento_prazo}</p><p className="mt-2"><strong>Efeito no caixa:</strong> {m.efeito_caixa}</p></article>)}</div><div className="mt-4 space-y-2 text-xs text-slate-500">{Object.entries(dados?.ressalvas ?? {}).map(([k,v]) => <p key={k}>{v}</p>)}</div></div>;
}

export function NewsRodada({empresaId,rodada}:{empresaId:number;rodada?:number}) {
  const [dados,setDados] = useState<Jornal|null>(null);
  const [erro,setErro] = useState("");
  useEffect(() => { api.get<Jornal>(`/api/aluno/empresas/${empresaId}/news`).then(setDados).catch(e => setErro(e.message)); }, [empresaId,rodada]);
  return <div><h3 className="text-xl font-bold">SempreHub News</h3><p className="mb-4 text-sm">{dados?.orientacao}</p>{erro && <p role="alert">{erro}</p>}{dados?.edicoes.length === 0 && <p>A primeira edição será disponibilizada após o fechamento da rodada pelo sistema.</p>}{dados?.edicoes.map(e => <article key={e.rodada} className="mb-3 rounded-lg border p-4"><h4 className="font-bold">Rodada {e.rodada} · {e.titulo}</h4><p className="my-2 text-sm">{e.narrativa}</p>{e.mercado && <p className="text-sm">Preço médio: {reais(e.mercado.preco_medio)} · Vendas: {e.mercado.unidades_vendidas.toLocaleString("pt-BR")} · Receita do mercado: {reais(e.mercado.receita_total)}</p>}<p className="mt-2 text-xs text-slate-500">Compare o evento com demanda, custos, juros e resultados da empresa.</p></article>)}</div>;
}

export function RelatorioPrimeiraRodada({empresaId,disponivel}:{empresaId:number;disponivel:boolean}) {
  const [dados,setDados] = useState<Relatorio|null>(null);
  const [erro,setErro] = useState("");
  const [aberto,setAberto] = useState(false);
  useEffect(() => { if (disponivel) api.get<Relatorio>(`/api/aluno/empresas/${empresaId}/relatorio-primeira-rodada`).then(setDados).catch(e => setErro(e.message)); }, [empresaId,disponivel]);
  return <Cartao titulo="Relatório da primeira rodada"><p className="mb-3 text-sm">{disponivel ? "Devolutiva da equipe preservada para consulta nas próximas rodadas." : "Disponível após o fechamento da primeira rodada."}</p>{erro && <p role="alert">{erro}</p>}{dados && <><Botao variante="secundario" onClick={() => setAberto(!aberto)}>{aberto ? "Recolher relatório" : "Abrir relatório"}</Botao>{aberto && <div className="mt-4 space-y-4"><h3 className="font-bold">{dados.empresa} · {dados.turma} · Rodada 1</h3><p className="text-sm">Preço: {reais(dados.resultado.preco)} · Vendas: {dados.resultado.unidades_vendidas.toLocaleString("pt-BR")} · Participação: {percentual(dados.resultado.participacao_mercado)}</p>{dados.evento && <p className="text-sm"><strong>{dados.evento.titulo}:</strong> {dados.evento.narrativa}</p>}{[["DRE",dados.resultado.dre],["DFC",dados.resultado.dfc],["Balanço",dados.resultado.balanco]].map(([nome,valores]) => <section key={String(nome)}><h4 className="font-bold">{String(nome)}</h4>{valores && typeof valores === "object" ? Object.entries(valores).filter(([,v]) => typeof v === "number").map(([k,v]) => <p key={k} className="text-sm">{k.split("_").join(" ")}: {reais(v as number)}</p>) : <p className="text-sm">Indisponível neste modo de simulação.</p>}</section>)}<h4 className="font-bold">Participação</h4>{dados.resultado.participacao.membros.map(m => <p key={m.aluno_id} className="text-sm">{m.nome} · {m.cargos.join(", ") || "Individual"}{m.confirmou_versao !== null ? ` · ${m.confirmou_versao ? "Confirmou" : "Sem confirmação"}` : ""}</p>)}{dados.resultado.alertas.map(a => <p key={a} className="text-sm">{a}</p>)}<h4 className="font-bold">Reflexão para a próxima rodada</h4><ul className="list-disc pl-5">{dados.perguntas.map(p => <li key={p} className="text-sm">{p}</li>)}</ul><h4 className="font-bold">Mídias: conceito, finalidade, custo e prazo</h4><CatalogoCompleto catalogo={dados}/></div>}</>}</Cartao>;
}
