import React, { useEffect, useState } from "react";

import { encerrarSessao, quandoSessaoExpirar, sessaoSalva } from "./api";
import { Cabecalho } from "./componentes/ui";
import Entrar, { RedefinirSenha } from "./paginas/Entrar";
import InicioAluno from "./paginas/aluno/InicioAluno";
import PainelEmpresa from "./paginas/aluno/PainelEmpresa";
import InicioProfessor from "./paginas/professor/InicioProfessor";
import PainelTurma from "./paginas/professor/PainelTurma";
import type { Usuario } from "./tipos";

/** Rotas simples baseadas no endereço após "#", para funcionar em qualquer hospedagem estática. */
type Rota =
  | { pagina: "inicio" }
  | { pagina: "empresa"; id: number }
  | { pagina: "turma"; id: number }
  | { pagina: "redefinir"; token: string };

function lerRota(): Rota {
  const [, pagina, id] = window.location.hash.replace(/^#/, "").split("/");
  if (pagina === "redefinir-senha" && id) {
    return { pagina: "redefinir", token: id };
  }
  if ((pagina === "empresa" || pagina === "turma") && Number(id) > 0) {
    return { pagina, id: Number(id) };
  }
  return { pagina: "inicio" };
}

function irPara(caminho: string) {
  window.location.hash = caminho;
}

export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(() => sessaoSalva());
  const [rota, setRota] = useState<Rota>(lerRota);

  useEffect(() => {
    const aoMudar = () => setRota(lerRota());
    window.addEventListener("hashchange", aoMudar);
    quandoSessaoExpirar(() => setUsuario(null));
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [rota]);

  if (rota.pagina === "redefinir") {
    return (
      <RedefinirSenha
        token={rota.token}
        aoConcluir={(novo) => {
          setUsuario(novo);
          irPara("/");
        }}
      />
    );
  }

  if (!usuario) {
    return <Entrar aoEntrar={setUsuario} />;
  }

  function sair() {
    encerrarSessao();
    setUsuario(null);
    irPara("/");
  }

  const ehProfessor = usuario.papel === "PROFESSOR";
  let conteudo: React.ReactNode;
  if (ehProfessor) {
    conteudo =
      rota.pagina === "turma" ? (
        <PainelTurma key={rota.id} turmaId={rota.id} />
      ) : (
        <InicioProfessor abrirTurma={(id) => irPara(`/turma/${id}`)} />
      );
  } else {
    conteudo =
      rota.pagina === "empresa" ? (
        <PainelEmpresa key={rota.id} empresaId={rota.id} />
      ) : (
        <InicioAluno abrirEmpresa={(id) => irPara(`/empresa/${id}`)} />
      );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-slate-50 to-indigo-100 text-marinho">
      <Cabecalho usuario={usuario} aoSair={sair} aoInicio={() => irPara("/")} />
      <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6">
        {rota.pagina !== "inicio" && (
          <button onClick={() => irPara("/")} className="mb-4 text-sm font-medium text-slate-500 hover:text-marinho">
            ← {ehProfessor ? "Minhas turmas" : "Minhas empresas"}
          </button>
        )}
        {conteudo}
      </main>
    </div>
  );
}
