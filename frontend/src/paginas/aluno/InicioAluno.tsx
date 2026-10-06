import React, { useEffect, useState } from "react";

import { api } from "../../api";
import { BibliotecaAprendizagem, ManualRapido, TourGuiado } from "../../componentes/Aprendizagem";
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
          <p className="text-sm text-slate-500">Acesse suas empresas e as equipes de que você participa.</p>
        </div>
        {!mostrarFormulario && (
          <Botao onClick={() => setMostrarFormulario(true)}>Entrar em uma turma</Botao>
        )}
      </div>

      <TourGuiado perfil="ALUNO" />

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
            {turma.modo_equipe && <p className="mb-3 text-xs text-slate-500">Equipe · {empresa.equipe_membros?.map((m) => m.nome).join(", ") || "Empresa compartilhada"}</p>}
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

      <ManualRapido perfil="ALUNO" />
      <BibliotecaAprendizagem />
    </div>
  );
}

function FormularioEntrada({ aoEntrar, aoCancelar }: { aoEntrar: (id: number) => void; aoCancelar?: () => void }) {
  const [modo, setModo] = useState<"CRIAR" | "EQUIPE">("CRIAR");
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
      if (modo === "EQUIPE") {
        const resposta = await api.post<{ empresa: Empresa }>("/api/aluno/equipes/entrar", { codigo });
        aoEntrar(resposta.empresa.id);
        return;
      }
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
    <Cartao titulo="Participar da simulação">
      <div className="mb-5 grid gap-2 sm:grid-cols-2" role="group" aria-label="Como participar">
        <Botao type="button" variante={modo === "CRIAR" ? "primario" : "secundario"} aria-pressed={modo === "CRIAR"} onClick={() => { setModo("CRIAR"); setCodigo(""); setErro(null); }}>Abrir uma empresa</Botao>
        <Botao type="button" variante={modo === "EQUIPE" ? "primario" : "secundario"} aria-pressed={modo === "EQUIPE"} onClick={() => { setModo("EQUIPE"); setCodigo(""); setErro(null); }}>Entrar em uma equipe</Botao>
      </div>
      <form onSubmit={enviar} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo={modo === "EQUIPE" ? "Código de convite da empresa" : "Código da turma"} ajuda={modo === "EQUIPE" ? "Peça o convite ao colega que abriu a empresa. O código da turma serve para abrir uma empresa." : "Informado pelo professor. Em turmas por equipes, quem abre a empresa assume o cargo de CEO e convida os colegas."}>
            <input
              className={`${estiloEntrada} ${modo === "CRIAR" ? "uppercase tracking-widest" : "font-mono"}`}
              value={codigo}
              onChange={(e) => setCodigo(modo === "CRIAR" ? e.target.value.toUpperCase() : e.target.value)}
              maxLength={modo === "CRIAR" ? 12 : 80}
              autoCapitalize={modo === "CRIAR" ? "characters" : "none"}
              autoComplete="off"
              spellCheck={false}
              required
            />
          </Campo>
          {modo === "CRIAR" && <Campo rotulo="Nome da empresa">
            <input className={estiloEntrada} value={nomeEmpresa} onChange={(e) => setNomeEmpresa(e.target.value)} required />
          </Campo>}
        </div>
        {modo === "CRIAR" && <>
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
        </>}
        {modo === "EQUIPE" && <p className="text-sm text-slate-600">Você compartilhará a mesma empresa e o histórico das rodadas com os colegas. Cada integrante usa sua própria conta para confirmar as decisões.</p>}

        {erro && <Aviso>{erro}</Aviso>}
        <div className="flex justify-end gap-2">
          {aoCancelar && (
            <Botao type="button" variante="secundario" onClick={aoCancelar}>
              Cancelar
            </Botao>
          )}
          <Botao type="submit" carregando={carregando}>
            {modo === "EQUIPE" ? "Entrar na equipe" : "Abrir empresa"}
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
