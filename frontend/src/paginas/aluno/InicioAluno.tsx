import React, { useEffect, useState } from "react";

import { api } from "../../api";
import { BibliotecaAprendizagem, ManualRapido, TourGuiado } from "../../componentes/Aprendizagem";
import { Aviso, Botao, Campo, Carregando, Cartao, estiloEntrada } from "../../componentes/ui";
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

interface Sala { formacao_encerrada: boolean; disponiveis: {aluno_id:number;nome:string}[]; equipes: {empresa_id:number;nome:string;vagas:number;completa:boolean;membros:{aluno_id:number;nome:string}[]}[] }
interface Matricula { turma: Turma; sala: Sala }

export default function InicioAluno({ abrirEmpresa }: { abrirEmpresa: (id: number) => void }) {
  const [itens,setItens] = useState<Item[]>([]), [matricula,setMatricula] = useState<Matricula|null>(null);
  const [turmas,setTurmas] = useState<Turma[]>([]), [pronto,setPronto] = useState(false);
  const [erro,setErro] = useState(""), [ocupado,setOcupado] = useState(false), [criar,setCriar] = useState(false);
  async function carregar() {
    try { const [empresas,vinculo,disponiveis] = await Promise.all([api.get<Item[]>("/api/aluno/empresas"),api.get<Matricula|null>("/api/aluno/matricula"),api.get<Turma[]>("/api/aluno/turmas")]); setItens(empresas);setMatricula(vinculo);setTurmas(disponiveis);setPronto(true);setErro(""); }
    catch(e){setErro(e instanceof Error?e.message:"Erro ao carregar a turma.");}
  }
  useEffect(()=>{carregar();const intervalo=window.setInterval(carregar,15000);return()=>window.clearInterval(intervalo);},[]);
  async function entrar(turmaId:number){setOcupado(true);setErro("");try{await api.post("/api/aluno/matricula",{turma_id:turmaId});setCriar(false);await carregar();}catch(e){setErro(e instanceof Error?e.message:"Não foi possível entrar.");}finally{setOcupado(false);}}
  async function equipe(empresaId:number){setOcupado(true);setErro("");try{await api.post("/api/aluno/equipes/entrar",{empresa_id:empresaId});abrirEmpresa(empresaId);}catch(e){setErro(e instanceof Error?e.message:"Não foi possível entrar na equipe.");}finally{setOcupado(false);}}
  if(!pronto&&!erro)return <Carregando/>;
  return <div className="space-y-6"><h1 className="text-2xl font-bold text-marinho">{matricula?matricula.turma.nome:"Escolha sua turma"}</h1>{erro&&<Aviso>{erro}</Aviso>}
    {!matricula&&<Cartao titulo="Turmas disponíveis"><p className="mb-4 text-sm">Selecione pelo nome a turma indicada pelo professor. Ao entrar, você fica vinculado a ela; outra turma exige autorização.</p><div className="grid gap-3 sm:grid-cols-2">{turmas.map(t=><Botao key={t.id} disabled={ocupado} onClick={()=>entrar(t.id)}>{t.nome} · Prof. {t.professor}</Botao>)}</div>{!turmas.length&&<p>Nenhuma turma liberada para ingresso. Procure seu professor.</p>}</Cartao>}
    {matricula&&turmas.some(t=>t.id!==matricula.turma.id)&&<Cartao titulo="Troca autorizada pelo professor">{turmas.filter(t=>t.id!==matricula.turma.id).map(t=><Botao key={t.id} disabled={ocupado} onClick={()=>entrar(t.id)}>Entrar em {t.nome}</Botao>)}</Cartao>}
    <TourGuiado perfil="ALUNO"/>
    {matricula&&!itens.length&&<Cartao titulo="Forme sua equipe por afinidade"><p className="mb-4">Converse com os colegas e escolha uma equipe. Cada equipe terá de 3 a 5 integrantes e escolherá seu líder.</p><h3 className="font-bold">Colegas disponíveis</h3><ul className="my-3 flex flex-wrap gap-2">{matricula.sala.disponiveis.map(a=><li key={a.aluno_id} className="rounded-lg bg-slate-100 px-3 py-2">{a.nome}</li>)}</ul><h3 className="mb-3 font-bold">Equipes da turma</h3><div className="grid gap-3 md:grid-cols-2">{matricula.sala.equipes.map(e=><article key={e.empresa_id} className="rounded-xl border p-4"><h4 className="font-bold">{e.nome}</h4><p className="my-2 text-sm">{e.membros.map(m=>m.nome).join(", ")}</p><p className="mb-3 text-sm">{e.membros.length}/5 integrantes · {e.vagas} vagas</p><Botao disabled={ocupado||e.completa||matricula.sala.formacao_encerrada} onClick={()=>equipe(e.empresa_id)}>{e.completa?"Equipe completa":"Entrar nesta equipe"}</Botao></article>)}</div>{matricula.sala.formacao_encerrada?<Aviso tipo="info">A formação foi encerrada. Se você ficou sem equipe, procure o professor para conferir sua distribuição.</Aviso>:<Botao variante="secundario" onClick={()=>setCriar(true)}>{matricula.turma.modo_equipe?"Criar uma nova equipe":"Abrir minha empresa"}</Botao>}</Cartao>}
    {criar&&matricula&&!itens.length&&!matricula.sala.formacao_encerrada&&<FormularioEntrada turmaId={matricula.turma.id} aoCancelar={()=>setCriar(false)} aoEntrar={abrirEmpresa}/>}
    <div className="grid gap-4 md:grid-cols-2">{itens.map(({empresa,turma})=><button key={empresa.id} onClick={()=>abrirEmpresa(empresa.id)} className="rounded-xl bg-white p-5 text-left shadow-sm ring-1 ring-slate-200 hover:ring-ouro"><h2 className="text-lg font-bold text-marinho">{empresa.nome}</h2><p className="text-sm">{turma.nome} · Prof. {turma.professor}</p><p className="my-3 text-sm">{empresa.equipe_membros?.map(m=>m.nome).join(", ")}</p><p>Caixa: {reais(empresa.caixa)} · Rodada {turma.rodada_atual}/{turma.total_rodadas}</p><span className="mt-4 block rounded-lg bg-blue-700 p-3 text-center font-bold text-white">Abrir empresa e rodada atual →</span></button>)}</div>
    <ManualRapido perfil="ALUNO"/><BibliotecaAprendizagem/>
  </div>;
}

function FormularioEntrada({ turmaId, aoEntrar, aoCancelar }: { turmaId: number; aoEntrar: (id: number) => void; aoCancelar?: () => void }) {
  const modo = "CRIAR";
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
        turma_id: turmaId,
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
      <form onSubmit={enviar} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
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
