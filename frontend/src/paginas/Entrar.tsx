import React, { useState } from "react";

import logoSempreHub from "../assets/SempreHub.jpg";
import { api, iniciarSessao } from "../api";
import { Aviso, Botao, Campo, estiloEntrada } from "../componentes/ui";
import type { Papel, Usuario } from "../tipos";

type Modo = "entrar" | "cadastro";

export default function Entrar({ aoEntrar }: { aoEntrar: (usuario: Usuario) => void }) {
  const [modo, setModo] = useState<Modo>("entrar");
  const [papel, setPapel] = useState<Papel>("ALUNO");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [codigoDocente, setCodigoDocente] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (modo === "cadastro" && senha !== confirmacao) {
      setErro("As senhas não conferem.");
      return;
    }
    setCarregando(true);
    try {
      const resposta =
        modo === "entrar"
          ? await api.post<{ token: string; usuario: Usuario }>("/api/auth/login", { email, senha })
          : await api.post<{ token: string; usuario: Usuario }>("/api/auth/cadastro", {
              nome,
              email,
              senha,
              papel,
              codigo_docente: papel === "PROFESSOR" ? codigoDocente : null,
            });
      iniciarSessao(resposta.token, resposta.usuario);
      aoEntrar(resposta.usuario);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setCarregando(false);
    }
  }

  const dicaEmail =
    papel === "ALUNO"
      ? "Use seu e-mail @aluno.iffarroupilha.edu.br ou @aluno.iffar.edu.br."
      : "Use seu e-mail institucional @iffarroupilha.edu.br ou @iffar.edu.br.";

  return (
    <div className="flex min-h-screen items-center justify-center bg-marinho px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <img src={logoSempreHub} alt="Logotipo SempreHub" className="mb-4 h-24 w-24 rounded-xl object-contain ring-1 ring-ouro/40" />
          <h1 className="text-3xl font-bold tracking-tight text-white">SempreHub</h1>
          <p className="mt-1 text-xs uppercase tracking-[0.25em] text-ouro">Simulador de Empreendedorismo</p>
        </div>

        <div className="rounded-xl bg-white p-6 shadow-2xl">
          <div className="mb-5 grid grid-cols-2 rounded-lg bg-slate-100 p-1 text-sm font-semibold">
            {(["entrar", "cadastro"] as Modo[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setModo(m);
                  setErro(null);
                }}
                className={`rounded-md py-2 transition ${modo === m ? "bg-white text-marinho shadow" : "text-slate-500"}`}
              >
                {m === "entrar" ? "Entrar" : "Criar conta"}
              </button>
            ))}
          </div>

          <form onSubmit={enviar} className="space-y-4">
            {modo === "cadastro" && (
              <>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {(["ALUNO", "PROFESSOR"] as Papel[]).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPapel(p)}
                      className={`rounded-lg border px-3 py-2 font-medium ${
                        papel === p ? "border-ouro bg-ouro/10 text-marinho" : "border-slate-200 text-slate-500"
                      }`}
                    >
                      {p === "ALUNO" ? "Sou aluno(a)" : "Sou professor(a)"}
                    </button>
                  ))}
                </div>
                <Campo rotulo="Nome completo">
                  <input className={estiloEntrada} value={nome} onChange={(e) => setNome(e.target.value)} required minLength={3} />
                </Campo>
              </>
            )}

            <Campo rotulo="E-mail institucional" ajuda={modo === "cadastro" ? dicaEmail : undefined}>
              <input
                className={estiloEntrada}
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </Campo>

            <Campo rotulo="Senha" ajuda={modo === "cadastro" ? "Mínimo de 8 caracteres." : undefined}>
              <input
                className={estiloEntrada}
                type="password"
                autoComplete={modo === "entrar" ? "current-password" : "new-password"}
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
                minLength={modo === "cadastro" ? 8 : undefined}
              />
            </Campo>

            {modo === "cadastro" && (
              <Campo rotulo="Confirme a senha">
                <input
                  className={estiloEntrada}
                  type="password"
                  autoComplete="new-password"
                  value={confirmacao}
                  onChange={(e) => setConfirmacao(e.target.value)}
                  required
                />
              </Campo>
            )}

            {modo === "cadastro" && papel === "PROFESSOR" && (
              <Campo rotulo="Código de cadastro docente" ajuda="Fornecido pela coordenação do SempreHub.">
                <input
                  className={estiloEntrada}
                  value={codigoDocente}
                  onChange={(e) => setCodigoDocente(e.target.value)}
                  required
                />
              </Campo>
            )}

            {erro && <Aviso>{erro}</Aviso>}

            <Botao type="submit" carregando={carregando} className="w-full py-2.5">
              {modo === "entrar" ? "Entrar" : "Criar conta"}
            </Botao>
          </form>
        </div>
        <p className="mt-6 text-center text-xs text-white/50">Instituto Federal Farroupilha</p>
      </div>
    </div>
  );
}
