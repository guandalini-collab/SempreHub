import React, { useEffect, useState } from "react";

import { api } from "../../api";
import { Aviso, Botao, Campo, Cartao, EntradaSenha, estiloEntrada } from "../../componentes/ui";
import type { Usuario } from "../../tipos";

/** Botão que gera uma nova senha para o aluno e a mostra ao professor. */
export function BotaoRedefinirSenha({ alunoId, nome }: { alunoId: number; nome: string }) {
  const [confirmando, setConfirmando] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [novaSenha, setNovaSenha] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [copiada, setCopiada] = useState(false);
  const [erroCopia, setErroCopia] = useState<string | null>(null);

  async function copiarSenha() {
    if (!novaSenha) return;
    setCopiada(false);
    setErroCopia(null);
    try {
      await navigator.clipboard.writeText(novaSenha);
      setCopiada(true);
    } catch {
      setErroCopia("Não foi possível copiar automaticamente. Selecione somente a senha no quadro e copie manualmente.");
    }
  }

  async function redefinir() {
    setCarregando(true);
    setErro(null);
    try {
      const resposta = await api.post<{ nova_senha: string }>(`/api/professor/alunos/${alunoId}/redefinir-senha`, {});
      setNovaSenha(resposta.nova_senha);
      setConfirmando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao redefinir a senha.");
    } finally {
      setCarregando(false);
    }
  }

  if (novaSenha) {
    return (
      <Aviso tipo="sucesso">
        <p>Nova senha de {nome}</p>
        <div className="my-2 flex flex-wrap items-center gap-3">
          <code className="select-all rounded border border-green-200 bg-white px-3 py-2 font-mono text-base">{novaSenha}</code>
          <Botao variante="secundario" type="button" onClick={copiarSenha}>Copiar senha</Botao>
        </div>
        <p role="status" aria-live="polite">{copiada ? "Senha copiada. Repasse ao aluno para entrar com seu e-mail cadastrado." : "Repasse somente a senha do quadro ao aluno, sem espaços ou pontuação adicional."}</p>
        {erroCopia && <p role="alert" className="mt-2">{erroCopia}</p>}
      </Aviso>
    );
  }
  if (confirmando) {
    return (
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-slate-600">Gerar uma nova senha para {nome}? A senha atual deixará de funcionar.</span>
        <Botao variante="secundario" onClick={() => setConfirmando(false)}>
          Voltar
        </Botao>
        <Botao carregando={carregando} onClick={redefinir}>
          Gerar nova senha
        </Botao>
        {erro && <Aviso>{erro}</Aviso>}
      </div>
    );
  }
  return (
    <button type="button" onClick={() => setConfirmando(true)} className="text-sm font-semibold text-marinho underline">
      Redefinir senha do aluno
    </button>
  );
}

export default function AlunosTeste() {
  const [alunos, setAlunos] = useState<Usuario[]>([]);
  const [aberto, setAberto] = useState(false);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    api.get<Usuario[]>("/api/professor/alunos-teste").then(setAlunos).catch(() => undefined);
  }, []);

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setSucesso(null);
    setCarregando(true);
    try {
      const novo = await api.post<Usuario>("/api/professor/alunos-teste", { nome, email, senha });
      setAlunos((lista) => [novo, ...lista]);
      setSucesso(`Conta criada. Para jogar como ${novo.nome}, saia e entre com ${novo.email} e a senha definida.`);
      setNome("");
      setEmail("");
      setSenha("");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao criar a conta.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Cartao
      titulo="Alunos de teste"
      acao={
        !aberto && (
          <Botao variante="secundario" onClick={() => setAberto(true)}>
            Criar aluno de teste
          </Botao>
        )
      }
    >
      <p className="text-sm text-slate-500">
        Contas de aluno criadas por você, com qualquer e-mail (inclusive inexistente), para testar o jogo do ponto de vista do
        aluno ou fazer demonstrações.
      </p>

      {aberto && (
        <form onSubmit={criar} className="mt-4 grid gap-4 sm:grid-cols-3">
          <Campo rotulo="Nome">
            <input className={estiloEntrada} value={nome} onChange={(e) => setNome(e.target.value)} required minLength={3} />
          </Campo>
          <Campo rotulo="E-mail (pode ser fictício)" ajuda="Ex.: teste1@semprehub.teste">
            <input className={estiloEntrada} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Campo>
          <Campo rotulo="Senha" ajuda="Mínimo de 8 caracteres.">
            <EntradaSenha valor={senha} aoMudar={setSenha} autoComplete="new-password" required minLength={8} />
          </Campo>
          <div className="flex justify-end gap-2 sm:col-span-3">
            <Botao type="button" variante="secundario" onClick={() => setAberto(false)}>
              Fechar
            </Botao>
            <Botao type="submit" carregando={carregando}>
              Criar conta
            </Botao>
          </div>
        </form>
      )}

      {erro && (
        <div className="mt-4">
          <Aviso>{erro}</Aviso>
        </div>
      )}
      {sucesso && (
        <div className="mt-4">
          <Aviso tipo="sucesso">{sucesso}</Aviso>
        </div>
      )}

      {alunos.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 text-sm">
          {alunos.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                <span className="font-medium text-marinho">{a.nome}</span>{" "}
                <span className="text-slate-500">· {a.email}</span>
              </span>
              <BotaoRedefinirSenha alunoId={a.id} nome={a.nome} />
            </li>
          ))}
        </ul>
      )}
    </Cartao>
  );
}
