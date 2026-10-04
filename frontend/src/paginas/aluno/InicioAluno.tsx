import React, { useEffect, useState } from "react";

import { api } from "../../api";
import { Aviso, Botao, Campo, Carregando, Cartao, SeloFase, estiloEntrada } from "../../componentes/ui";
import {
  DESCRICAO_DORNELAS,
  DESCRICAO_GEM,
  DESCRICAO_REGIME,
  NOME_DORNELAS,
  NOME_GEM,
  NOME_REGIME,
  reais,
} from "../../formatos";
import type { ClasseDornelas, Empresa, RegimeTributario, TipoEntradaGem, Turma } from "../../tipos";

interface Item {
  empresa: Empresa;
  turma: Turma;
}

export default function InicioAluno({ abrirEmpresa }: { abrirEmpresa: (id: number) => void }) {
  const [itens, setItens] = useState<Item[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);

  async function carregar() {
    try {
      const lista = await api.get<Item[]>("/api/aluno/empresas");
      setItens(lista);
      setMostrarFormulario(lista.length === 0);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar.");
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  if (erro) return <Aviso>{erro}</Aviso>;
  if (!itens) return <Carregando />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-marinho">Minhas empresas</h1>
          <p className="text-sm text-slate-500">Cada turma em que você joga tem a sua própria empresa.</p>
        </div>
        {!mostrarFormulario && (
          <Botao onClick={() => setMostrarFormulario(true)}>Entrar em uma turma</Botao>
        )}
      </div>

      {mostrarFormulario && (
        <FormularioEntrada
          aoCancelar={itens.length ? () => setMostrarFormulario(false) : undefined}
          aoEntrar={(id) => abrirEmpresa(id)}
        />
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {itens.map(({ empresa, turma }) => (
          <button
            key={empresa.id}
            onClick={() => abrirEmpresa(empresa.id)}
            className="rounded-xl bg-white p-5 text-left shadow-sm ring-1 ring-slate-200 transition hover:ring-ouro"
          >
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <p className="text-lg font-semibold text-marinho">{empresa.nome}</p>
                <p className="text-xs text-slate-500">
                  {turma.nome} · Prof. {turma.professor}
                </p>
              </div>
              <SeloFase fase={empresa.fase_atual} />
            </div>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <p className="text-xs text-slate-500">Caixa</p>
                <p className="font-semibold text-marinho">{reais(empresa.caixa)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Regime</p>
                <p className="font-semibold text-marinho">{NOME_REGIME[empresa.regime_tributario]}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Rodada</p>
                <p className="font-semibold text-marinho">
                  {turma.status === "ENCERRADA" ? "Encerrada" : `${turma.rodada_atual} de ${turma.total_rodadas}`}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function FormularioEntrada({ aoEntrar, aoCancelar }: { aoEntrar: (id: number) => void; aoCancelar?: () => void }) {
  const [codigo, setCodigo] = useState("");
  const [nomeEmpresa, setNomeEmpresa] = useState("");
  const [gem, setGem] = useState<TipoEntradaGem>("OPORTUNIDADE");
  const [classe, setClasse] = useState<ClasseDornelas>("SERIAL");
  const [regime, setRegime] = useState<RegimeTributario>("MEI");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const resposta = await api.post<{ empresa: Empresa }>("/api/aluno/turmas/entrar", {
        codigo,
        nome_empresa: nomeEmpresa,
        tipo_entrada_gem: gem,
        classe_dornelas: classe,
        regime_tributario: regime,
      });
      aoEntrar(resposta.empresa.id);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Cartao titulo="Abrir sua empresa em uma turma">
      <form onSubmit={enviar} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Código da turma" ajuda="Informado pelo professor (6 caracteres).">
            <input
              className={`${estiloEntrada} uppercase tracking-widest`}
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.toUpperCase())}
              maxLength={12}
              required
            />
          </Campo>
          <Campo rotulo="Nome da empresa">
            <input className={estiloEntrada} value={nomeEmpresa} onChange={(e) => setNomeEmpresa(e.target.value)} required />
          </Campo>
        </div>

        <Grupo titulo="Por que você está empreendendo? (GEM)">
          {(Object.keys(NOME_GEM) as TipoEntradaGem[]).map((g) => (
            <Opcao key={g} ativo={gem === g} aoEscolher={() => setGem(g)} titulo={NOME_GEM[g]} descricao={DESCRICAO_GEM[g]} />
          ))}
        </Grupo>

        <Grupo titulo="Que tipo de empreendedor você é? (Dornelas)">
          {(Object.keys(NOME_DORNELAS) as ClasseDornelas[]).map((c) => (
            <Opcao
              key={c}
              ativo={classe === c}
              aoEscolher={() => setClasse(c)}
              titulo={NOME_DORNELAS[c]}
              descricao={DESCRICAO_DORNELAS[c]}
            />
          ))}
        </Grupo>

        <Grupo titulo="Regime tributário inicial">
          {(Object.keys(NOME_REGIME) as RegimeTributario[]).map((r) => (
            <Opcao key={r} ativo={regime === r} aoEscolher={() => setRegime(r)} titulo={NOME_REGIME[r]} descricao={DESCRICAO_REGIME[r]} />
          ))}
        </Grupo>

        {erro && <Aviso>{erro}</Aviso>}
        <div className="flex justify-end gap-2">
          {aoCancelar && (
            <Botao type="button" variante="secundario" onClick={aoCancelar}>
              Cancelar
            </Botao>
          )}
          <Botao type="submit" carregando={carregando}>
            Abrir empresa
          </Botao>
        </div>
      </form>
    </Cartao>
  );
}

function Grupo({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">{titulo}</legend>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
    </fieldset>
  );
}

function Opcao({
  ativo,
  aoEscolher,
  titulo,
  descricao,
}: {
  ativo: boolean;
  aoEscolher: () => void;
  titulo: string;
  descricao: string;
}) {
  return (
    <button
      type="button"
      onClick={aoEscolher}
      aria-pressed={ativo}
      className={`rounded-lg border p-3 text-left transition ${
        ativo ? "border-ouro bg-ouro/10 ring-1 ring-ouro" : "border-slate-200 hover:border-slate-300"
      }`}
    >
      <p className="text-sm font-semibold text-marinho">{titulo}</p>
      <p className="mt-1 text-xs leading-snug text-slate-500">{descricao}</p>
    </button>
  );
}
