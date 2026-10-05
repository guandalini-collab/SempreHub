import React, { useState } from "react";

import logoSempreHub from "../assets/logo-semprehub.png";
import { api, iniciarSessao } from "../api";
import { Aviso, Botao, Campo, EntradaSenha, estiloEntrada } from "../componentes/ui";
import type { Papel, Usuario } from "../tipos";

type Modo = "entrar" | "cadastro" | "recuperar";

function Moldura({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-marinho px-4 py-10">
      <div className="w-full max-w-md">
        <p className="mb-4 text-center text-xs uppercase tracking-[0.25em] text-ouro">Ecossistema de Aceleração de Negócios</p>
        <div className="rounded-xl bg-white p-6 shadow-2xl">
          <div className="mb-6 flex flex-col items-center border-b border-slate-100 pb-5 text-center">
            <h1>
              <img src={logoSempreHub} alt="SempreHub" className="mx-auto h-auto w-64 sm:w-72" />
            </h1>
            <p className="mt-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Simulador de Empreendedorismo</p>
          </div>
          {children}
        </div>
        <p className="mt-6 text-center text-xs text-white/50">Instituto Federal Farroupilha</p>
      </div>
    </div>
  );
}

export default function Entrar({ aoEntrar }: { aoEntrar: (usuario: Usuario) => void }) {
  const [modo, setModo] = useState<Modo>("entrar");
  const [papel, setPapel] = useState<Papel>("ALUNO");
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [codigoDocente, setCodigoDocente] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<{ mensagem: string; link?: string } | null>(null);
  const [carregando, setCarregando] = useState(false);

  function trocarModo(novo: Modo) {
    setModo(novo);
    setErro(null);
    setAviso(null);
  }

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setAviso(null);
    if (modo === "cadastro" && senha !== confirmacao) {
      setErro("As senhas não conferem.");
      return;
    }
    setCarregando(true);
    try {
      if (modo === "recuperar") {
        const resposta = await api.post<{ mensagem: string; link_desenvolvimento?: string }>("/api/auth/esqueci-senha", { email });
        setAviso({ mensagem: resposta.mensagem, link: resposta.link_desenvolvimento });
        return;
      }
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
      : "Use seu e-mail institucional (@iffarroupilha.edu.br ou @iffar.edu.br) ou seu Gmail pessoal.";

  return (
    <Moldura>
      {modo !== "recuperar" ? (
        <div className="mb-5 grid grid-cols-2 rounded-lg bg-slate-100 p-1 text-sm font-semibold">
          {(["entrar", "cadastro"] as Modo[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => trocarModo(m)}
              className={`rounded-md py-2 transition ${modo === m ? "bg-white text-marinho shadow" : "text-slate-500"}`}
            >
              {m === "entrar" ? "Entrar" : "Criar conta"}
            </button>
          ))}
        </div>
      ) : (
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-marinho">Recuperar senha</h2>
          <p className="mt-1 text-sm text-slate-500">Informe o e-mail da sua conta para receber um link de redefinição.</p>
        </div>
      )}

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

        <Campo rotulo="E-mail" ajuda={modo === "cadastro" ? dicaEmail : undefined}>
          <input
            className={estiloEntrada}
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Campo>

        {modo !== "recuperar" && (
          <Campo rotulo="Senha" ajuda={modo === "cadastro" ? "Mínimo de 8 caracteres." : undefined}>
            <EntradaSenha
              valor={senha}
              aoMudar={setSenha}
              autoComplete={modo === "entrar" ? "current-password" : "new-password"}
              required
              minLength={modo === "cadastro" ? 8 : undefined}
            />
          </Campo>
        )}

        {modo === "cadastro" && (
          <Campo rotulo="Confirme a senha">
            <EntradaSenha valor={confirmacao} aoMudar={setConfirmacao} autoComplete="new-password" required />
          </Campo>
        )}

        {modo === "cadastro" && papel === "PROFESSOR" && (
          <Campo rotulo="Código de cadastro docente" ajuda="Fornecido pela coordenação do SempreHub.">
            <input className={estiloEntrada} value={codigoDocente} onChange={(e) => setCodigoDocente(e.target.value)} required />
          </Campo>
        )}

        {erro && <Aviso>{erro}</Aviso>}
        {aviso && (
          <Aviso tipo="info">
            {aviso.mensagem}
            {aviso.link && (
              <span className="mt-2 block">
                Modo de desenvolvimento (sem envio de e-mail):{" "}
                <a href={aviso.link.slice(aviso.link.indexOf("#"))} className="font-semibold underline">
                  abrir o link de redefinição
                </a>
                .
              </span>
            )}
          </Aviso>
        )}

        <Botao type="submit" carregando={carregando} className="w-full py-2.5">
          {modo === "entrar" ? "Entrar" : modo === "cadastro" ? "Criar conta" : "Enviar link"}
        </Botao>

        <div className="text-center text-sm">
          {modo === "entrar" && (
            <button type="button" onClick={() => trocarModo("recuperar")} className="font-medium text-slate-500 hover:text-marinho">
              Esqueci minha senha
            </button>
          )}
          {modo === "recuperar" && (
            <button type="button" onClick={() => trocarModo("entrar")} className="font-medium text-slate-500 hover:text-marinho">
              ← Voltar para o login
            </button>
          )}
        </div>
      </form>
    </Moldura>
  );
}

export function RedefinirSenha({ token, aoConcluir }: { token: string; aoConcluir: (usuario: Usuario) => void }) {
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (senha !== confirmacao) {
      setErro("As senhas não conferem.");
      return;
    }
    setCarregando(true);
    try {
      const resposta = await api.post<{ token: string; usuario: Usuario }>("/api/auth/redefinir-senha", {
        token,
        nova_senha: senha,
      });
      iniciarSessao(resposta.token, resposta.usuario);
      aoConcluir(resposta.usuario);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Moldura>
      <h2 className="text-lg font-semibold text-marinho">Criar nova senha</h2>
      <p className="mb-5 mt-1 text-sm text-slate-500">Escolha uma senha com pelo menos 8 caracteres.</p>
      <form onSubmit={enviar} className="space-y-4">
        <Campo rotulo="Nova senha">
          <EntradaSenha valor={senha} aoMudar={setSenha} autoComplete="new-password" required minLength={8} />
        </Campo>
        <Campo rotulo="Confirme a nova senha">
          <EntradaSenha valor={confirmacao} aoMudar={setConfirmacao} autoComplete="new-password" required />
        </Campo>
        {erro && <Aviso>{erro}</Aviso>}
        <Botao type="submit" carregando={carregando} className="w-full py-2.5">
          Salvar nova senha
        </Botao>
        <div className="text-center text-sm">
          <a href="#/" className="font-medium text-slate-500 hover:text-marinho">
            ← Voltar para o login
          </a>
        </div>
      </form>
    </Moldura>
  );
}
