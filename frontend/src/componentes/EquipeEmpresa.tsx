import React, { useState } from "react";

import { api } from "../api";
import type { CargoEquipe, Equipe, MembroEquipe } from "../tipos";
import { Aviso, Botao, Cartao } from "./ui";

export const CARGOS: { codigo: CargoEquipe; nome: string }[] = [
  { codigo: "CEO", nome: "Direção geral" },
  { codigo: "CFO", nome: "Finanças" },
  { codigo: "CMO", nome: "Marketing" },
  { codigo: "COO", nome: "Operações" },
  { codigo: "CHRO", nome: "Pessoas" },
];

export default function EquipeEmpresa({
  empresaId,
  equipe,
  podeEditar = false,
  aoSalvar,
}: {
  empresaId: number;
  equipe: Equipe;
  podeEditar?: boolean;
  aoSalvar?: () => Promise<unknown>;
}) {
  const [editando, setEditando] = useState(false);
  const [membros, setMembros] = useState<MembroEquipe[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  async function copiarConvite() {
    try {
      await navigator.clipboard.writeText(equipe.codigo_convite!);
      setCopiado(true);
    } catch {
      setErro("Selecione o código exibido abaixo e copie para compartilhar com os colegas.");
    }
  }

  async function salvar() {
    setCarregando(true);
    setErro(null);
    try {
      await api.put(`/api/aluno/empresas/${empresaId}/equipe`, {
        membros: membros.map(({ aluno_id, cargos }) => ({ aluno_id, cargos })),
      });
      setEditando(false);
      await aoSalvar?.();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível salvar os cargos.");
    } finally {
      setCarregando(false);
    }
  }

  function mudarCargo(alunoId: number, cargo: CargoEquipe, marcado: boolean) {
    setMembros((atual) => atual.map((m) => m.aluno_id === alunoId
      ? { ...m, cargos: marcado ? [...m.cargos, cargo] : m.cargos.filter((c) => c !== cargo) }
      : m));
  }

  const assinados = new Set(equipe.aprovacoes.map((a) => a.aluno_id));
  return (
    <Cartao titulo={`Equipe da empresa · ${equipe.membros.length} de 5 integrantes`} acao={podeEditar && !editando
      ? <Botao variante="secundario" onClick={() => { setMembros(equipe.membros.map((m) => ({ ...m, cargos: [...m.cargos] }))); setEditando(true); setErro(null); }}>Distribuir cargos</Botao>
      : undefined}>
      <div className="space-y-4">
        {equipe.codigo_convite && podeEditar && <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs font-semibold text-slate-600">Convite para os colegas entrarem nesta empresa</p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <code className="max-w-full select-all break-all text-base font-semibold text-marinho">{equipe.codigo_convite}</code>
            <Botao variante="secundario" onClick={copiarConvite}>{copiado ? "Copiado" : "Copiar convite"}</Botao>
          </div>
          <p className="mt-2 text-xs text-slate-500">Cada colega entra na própria conta, escolhe “Entrar em uma equipe” e informa este convite antes do fechamento da primeira rodada.</p>
        </div>}
        {equipe.meus_cargos.length > 0 && <p className="text-sm text-slate-600">Seus cargos: <strong className="text-marinho">{equipe.meus_cargos.join(", ")}</strong>.</p>}
        <p className="text-xs text-slate-500">Equipes têm 3 a 5 alunos. Cada cargo fica com uma pessoa; uma pessoa pode acumular funções. Todos participam e confirmam a decisão de cada rodada.</p>
        {editando ? <div className="space-y-4">
          {membros.map((m) => <fieldset key={m.aluno_id} disabled={carregando} className="rounded-lg border border-slate-200 p-3">
            <legend className="px-1 text-sm font-semibold text-marinho">{m.nome}</legend>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-2">
              {CARGOS.map((c) => <label key={c.codigo} className="flex items-center gap-2 text-xs text-slate-600">
                <input type="checkbox" checked={m.cargos.includes(c.codigo)} disabled={c.codigo === "CEO"} onChange={(e) => mudarCargo(m.aluno_id, c.codigo, e.target.checked)} />
                {c.codigo} · {c.nome}
              </label>)}
            </div>
          </fieldset>)}
          <p className="text-xs text-slate-500">O fundador permanece como CEO. A distribuição de cargos pode ser ajustada antes do fechamento da primeira rodada.</p>
          <div className="flex justify-end gap-2">
            <Botao variante="secundario" disabled={carregando} onClick={() => setEditando(false)}>Cancelar</Botao>
            <Botao carregando={carregando} onClick={salvar}>Salvar cargos</Botao>
          </div>
        </div> : <ul className="divide-y divide-slate-100">
          {equipe.membros.map((m) => <li key={m.aluno_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <div><p className="font-semibold text-marinho">{m.nome}</p><p className="text-xs text-slate-500">{m.cargos.length ? m.cargos.join(" · ") : "Cargos a definir"}</p></div>
            {equipe.versao_decisao > 0 && <span className={`text-xs font-semibold ${assinados.has(m.aluno_id) ? "text-emerald-700" : "text-amber-700"}`}>{assinados.has(m.aluno_id) ? `Confirmou versão ${equipe.versao_decisao}` : "Confirmação pendente"}</span>}
          </li>)}
        </ul>}
        {equipe.pendencias.length > 0 && <Aviso tipo="info"><p className="font-semibold">Para a equipe concluir esta rodada:</p><ul className="mt-1 list-disc pl-5">{equipe.pendencias.map((p) => <li key={p}>{p}</li>)}</ul></Aviso>}
        {equipe.pronta && <Aviso tipo="sucesso">Todos confirmaram a versão {equipe.versao_decisao}. A empresa está pronta para o professor fechar a rodada.</Aviso>}
        {erro && <Aviso>{erro}</Aviso>}
        {equipe.historico.length > 0 && <details className="text-sm">
          <summary className="cursor-pointer font-semibold text-marinho">Registro das alterações e confirmações</summary>
          <ul className="mt-2 max-h-64 divide-y divide-slate-100 overflow-y-auto text-xs text-slate-600">
            {[...equipe.historico].reverse().map((h, i) => <li key={`${h.data}-${i}`} className="py-2">{h.aluno ?? "Sistema"} · {rotuloAcao(h.acao)} · mês {h.rodada}{h.versao != null ? ` · versão ${h.versao}` : ""}<span className="ml-2 text-slate-400">{new Date(h.data).toLocaleString("pt-BR")}</span></li>)}
          </ul>
        </details>}
      </div>
    </Cartao>
  );
}

function rotuloAcao(acao: string): string {
  const nomes: Record<string, string> = {
    CRIAR_EQUIPE: "Abriu a empresa",
    ENTRAR_EQUIPE: "Entrou na equipe",
    ALTERAR_CARGOS: "Atualizou os cargos",
    SALVAR_DECISAO: "Salvou a decisão",
    APROVAR_DECISAO: "Confirmou a decisão",
    LOGIN: "Acessou sua conta",
  };
  return nomes[acao] ?? acao.replace(/_/g, " ").toLowerCase();
}
