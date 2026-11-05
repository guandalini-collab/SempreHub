import React, { useEffect, useState } from "react";

import { api } from "../../api";
import { BibliotecaAprendizagem, TourGuiado } from "../../componentes/Aprendizagem";
import { Aviso, Botao, Campo, Carregando, Cartao, estiloEntrada } from "../../componentes/ui";
import type { Turma } from "../../tipos";
import AlunosTeste from "./AlunosTeste";
import ConfiguracaoSimulacao from "../../componentes/ConfiguracaoSimulacao";
import { EditorParametros, useParametros } from "./Parametros";

type Docente={id:number;nome:string;email:string;turmas:number};

export default function InicioProfessor({ abrirTurma, proprietario=false }: { abrirTurma: (id: number) => void; proprietario?:boolean }) {
  const [turmas, setTurmas] = useState<Turma[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [criando, setCriando] = useState(false);
  const [aba,setAba]=useState("turmas");
  const [pagina,setPagina]=useState(0);
  const [busca,setBusca]=useState("");

  useEffect(() => {
    api
      .get<Turma[]>("/api/professor/turmas")
      .then((lista) => {
        setTurmas(lista);
        setCriando(lista.length === 0);
      })
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar."));
  }, []);

  if (erro) return <Aviso>{erro}</Aviso>;
  if (!turmas) return <Carregando />;

  const filtradas=turmas.filter(t=>t.nome.toLocaleLowerCase("pt-BR").includes(busca.toLocaleLowerCase("pt-BR")));
  return (
    <div className="inicio-professor space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-marinho">Minhas turmas</h1>
          <p className="text-sm text-slate-500">Crie uma turma, divulgue o código e conduza as rodadas.</p>
        </div>
        {!criando && <Botao onClick={() => {setCriando(true);setAba("turmas");}}>Nova turma</Botao>}
      </div>

      <nav className="etapas-curtas" aria-label="Área do professor">{[{id:"turmas",titulo:proprietario?"Turmas do SempreHub":"Minhas turmas"},...(proprietario?[{id:"professores",titulo:"Professores"}]:[]),{id:"teste",titulo:"Alunos de teste"},{id:"referencias",titulo:"Referências"},{id:"marca",titulo:"Identidade do programa"}].map(a=><button key={a.id} type="button" aria-pressed={aba===a.id} onClick={()=>{setAba(a.id);setCriando(false);}}>{a.titulo}</button>)}</nav>
      {turmas.length===0&&!criando&&aba==="turmas"&&<TourGuiado perfil="PROFESSOR"/>}

      {criando && (
        <NovaTurma aoCriar={(t) => abrirTurma(t.id)} aoCancelar={turmas.length ? () => setCriando(false) : undefined} />
      )}

      {aba==="turmas"&&!criando&&<><input aria-label="Buscar turma" placeholder="Buscar turma" className={estiloEntrada} value={busca} onChange={e=>{setBusca(e.target.value);setPagina(0);}}/><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtradas.slice(pagina*3,pagina*3+3).map((t) => (
          <button
            key={t.id}
            onClick={() => abrirTurma(t.id)}
            className="rounded-xl bg-white p-5 text-left shadow-sm ring-1 ring-slate-200 transition hover:ring-ouro"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-lg font-semibold text-marinho">{t.nome}</p>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  t.status === "ABERTA" ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-600"
                }`}
              >
                {t.status === "ABERTA" ? "Em andamento" : "Encerrada"}
              </span>
            </div>
            <p className="mt-3 font-mono text-2xl tracking-[0.3em] text-ouro">{t.codigo}</p>
            <p className="mt-2 text-sm text-slate-500">
              {t.quantidade_empresas} empresa(s) · {t.status === "ABERTA" ? `rodada ${t.rodada_atual} de ${t.total_rodadas}` : `${t.total_rodadas} rodadas`}
            </p>
            <p className="mt-1 text-xs text-slate-500">{t.modo_equipe ? "Equipes de 3 a 5 alunos" : "Participação individual"} · {t.modo_jogo === "STARTUP" ? "Startup" : t.modo_jogo === "TRADICIONAL" ? "Empresa tradicional" : "Modelo básico"}{t.cenario === "CRISE" ? " · recuperação" : ""}</p>
            <span className="mt-4 block rounded-lg bg-blue-700 px-4 py-3 text-center text-sm font-bold text-white">Abrir turma e rodada atual →</span>
          </button>
        ))}
      </div>

      <nav aria-label="Paginação de turmas" className="flex justify-between text-sm"><button disabled={pagina===0} onClick={()=>setPagina(pagina-1)}>← Anterior</button><span>{filtradas.length} turma(s) · Página {pagina+1}</span><button disabled={(pagina+1)*3>=filtradas.length} onClick={()=>setPagina(pagina+1)}>Próxima →</button></nav></>}
      {aba==="teste"&&<AlunosTeste />}
      {aba==="professores"&&proprietario&&<GestaoProfessores />}
      {aba==="referencias"&&<BibliotecaAprendizagem />}
      {aba==="marca"&&<Cartao titulo="Comunicação do programa">
        <p className="mb-2 text-sm text-slate-600">Use a identidade do SempreHub nos materiais de apresentação da turma.</p>
        <a href="/marca/semprehub-original.svg" download className="text-sm font-semibold text-marinho underline">Baixar logo do SempreHub</a>
      </Cartao>}
    </div>
  );
}

function GestaoProfessores(){
 const [docentes,setDocentes]=useState<Docente[]|null>(null);const [nome,setNome]=useState('');const [email,setEmail]=useState('');const [senha,setSenha]=useState('');const [erro,setErro]=useState<string|null>(null);const [mensagem,setMensagem]=useState<string|null>(null);const [salvando,setSalvando]=useState(false);
 const carregar=()=>api.get<Docente[]>('/api/professor/proprietario/professores').then(setDocentes).catch(e=>setErro(e instanceof Error?e.message:'Não foi possível carregar os professores.'));
 useEffect(()=>{carregar();},[]);
 async function criar(e:React.FormEvent){e.preventDefault();setErro(null);setMensagem(null);setSalvando(true);try{const r=await api.post<{mensagem:string}>('/api/professor/proprietario/professores',{nome,email,senha_provisoria:senha});setMensagem(r.mensagem);setNome('');setEmail('');setSenha('');carregar();}catch(e){setErro(e instanceof Error?e.message:'Não foi possível criar a conta.');}finally{setSalvando(false);}}
 return <div className="grid gap-4 lg:grid-cols-2"><Cartao titulo="Conceder acesso docente"><p className="mb-4 text-sm text-slate-600">A conta criada aqui acessa apenas as turmas sob responsabilidade do professor. Ela não visualiza a administração geral do SempreHub.</p><form className="space-y-3" onSubmit={criar}><Campo rotulo="Nome"><input required className={estiloEntrada} value={nome} onChange={e=>setNome(e.target.value)}/></Campo><Campo rotulo="E-mail institucional"><input required type="email" className={estiloEntrada} value={email} onChange={e=>setEmail(e.target.value)}/></Campo><Campo rotulo="Senha provisória" ajuda="Compartilhe-a apenas por um canal seguro."><input required minLength={8} type="password" className={estiloEntrada} value={senha} onChange={e=>setSenha(e.target.value)}/></Campo>{erro&&<Aviso>{erro}</Aviso>}{mensagem&&<p role="status" className="text-sm text-emerald-700">{mensagem}</p>}<Botao type="submit" carregando={salvando}>Criar acesso de professor</Botao></form></Cartao><Cartao titulo="Professores com acesso">{docentes===null?<Carregando/>:docentes.length===0?<p>Nenhum professor convidado ainda.</p>:<div className="space-y-3">{docentes.map(d=><div key={d.id} className="rounded-lg border border-slate-200 p-3"><strong>{d.nome}</strong><p className="text-sm text-slate-600">{d.email} · {d.turmas} turma(s)</p></div>)}</div>}</Cartao></div>;
}

function NovaTurma({ aoCriar, aoCancelar }: { aoCriar: (t: Turma) => void; aoCancelar?: () => void }) {
  const [nome, setNome] = useState("");
  const [parametros, setParametros] = useParametros();
  const [avancado, setAvancado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const turma = await api.post<Turma>("/api/professor/turmas", { nome, ...parametros });
      aoCriar(turma);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao criar a turma.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Cartao titulo="Nova turma">
      <form onSubmit={enviar} className="space-y-5">
        <Campo rotulo="Nome da turma" ajuda="Ex.: Empreendedorismo — 3º ano Técnico em Administração — 2026/2">
          <input className={estiloEntrada} value={nome} onChange={(e) => setNome(e.target.value)} required minLength={1} />
        </Campo>
        <ConfiguracaoSimulacao valores={parametros} aoMudar={(jogo) => setParametros({ ...parametros, ...jogo })} />
        <Campo rotulo="Participação dos alunos" ajuda="Equipes dividem os cargos de gestão e confirmam as decisões em conjunto.">
          <select className={estiloEntrada} value={parametros.modo_equipe ? "EQUIPE" : "INDIVIDUAL"} onChange={(e) => setParametros({ ...parametros, modo_equipe: e.target.value === "EQUIPE" })}>
            <option value="EQUIPE">Equipes de 3 a 5 alunos</option>
            <option value="INDIVIDUAL">Individual</option>
          </select>
        </Campo>
        <button type="button" className="text-sm font-semibold text-marinho underline" onClick={() => setAvancado(!avancado)}>
          {avancado ? "Ocultar parâmetros do mercado" : "Ajustar parâmetros do mercado (opcional)"}
        </button>
        {avancado && <EditorParametros valores={parametros} aoMudar={setParametros} exibirModo={false} />}
        {erro && <Aviso>{erro}</Aviso>}
        <div className="flex justify-end gap-2">
          {aoCancelar && (
            <Botao type="button" variante="secundario" onClick={aoCancelar}>
              Cancelar
            </Botao>
          )}
          <Botao type="submit" carregando={carregando}>
            Criar turma
          </Botao>
        </div>
      </form>
    </Cartao>
  );
}
