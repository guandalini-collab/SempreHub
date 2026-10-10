import type { Usuario } from "./tipos";

const BASE = import.meta.env.VITE_API_URL ?? "";
const CHAVE_TOKEN = "semprehub.token";
const CHAVE_USUARIO = "semprehub.usuario";

function lerArmazenamento(chave: string): string | null {
  try {
    return window.localStorage.getItem(chave);
  } catch {
    return null;
  }
}

function gravarArmazenamento(chave: string, valor: string | null) {
  try {
    if (valor === null) window.localStorage.removeItem(chave);
    else window.localStorage.setItem(chave, valor);
  } catch {
    /* navegação privada: a sessão vale só enquanto a aba estiver aberta */
  }
}

let token: string | null = lerArmazenamento(CHAVE_TOKEN);
let aoExpirar: (() => void) | null = null;

export function sessaoSalva(): Usuario | null {
  const bruto = lerArmazenamento(CHAVE_USUARIO);
  if (!token || !bruto) return null;
  try {
    return JSON.parse(bruto) as Usuario;
  } catch {
    return null;
  }
}

export function iniciarSessao(novoToken: string, usuario: Usuario) {
  token = novoToken;
  gravarArmazenamento(CHAVE_TOKEN, novoToken);
  gravarArmazenamento(CHAVE_USUARIO, JSON.stringify(usuario));
}

export function encerrarSessao() {
  token = null;
  gravarArmazenamento(CHAVE_TOKEN, null);
  gravarArmazenamento(CHAVE_USUARIO, null);
}

export function quandoSessaoExpirar(callback: () => void) {
  aoExpirar = callback;
}

export class ErroApi extends Error {
  status: number;
  constructor(mensagem: string, status: number) {
    super(mensagem);
    this.status = status;
  }
}

function mensagemDeErro(corpo: unknown, status: number): string {
  if (corpo && typeof corpo === "object" && "detail" in corpo) {
    const detalhe = (corpo as { detail: unknown }).detail;
    if (typeof detalhe === "string") return detalhe;
    if (Array.isArray(detalhe) && detalhe.length > 0) {
      const primeiro = detalhe[0] as { loc?: unknown[]; msg?: string };
      const campo = primeiro.loc ? String(primeiro.loc[primeiro.loc.length - 1]) : "";
      return `Verifique o campo "${campo}": ${primeiro.msg ?? "valor inválido"}.`;
    }
  }
  return `Erro inesperado (HTTP ${status}).`;
}

export async function requisitar<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const cabecalhos: Record<string, string> = { "Content-Type": "application/json" };
  if (token) cabecalhos.Authorization = `Bearer ${token}`;
  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, { ...opcoes, headers: { ...cabecalhos, ...opcoes.headers } });
  } catch {
    throw new ErroApi("Não foi possível falar com o servidor. Verifique se o backend está rodando.", 0);
  }
  const texto = await resposta.text();
  const corpo = texto ? JSON.parse(texto) : null;
  if (!resposta.ok) {
    if (resposta.status === 401 && token) {
      encerrarSessao();
      aoExpirar?.();
    }
    throw new ErroApi(mensagemDeErro(corpo, resposta.status), resposta.status);
  }
  return corpo as T;
}

export const api = {
  get: <T,>(caminho: string) => requisitar<T>(caminho),
  post: <T,>(caminho: string, dados?: unknown) =>
    requisitar<T>(caminho, { method: "POST", body: JSON.stringify(dados ?? {}) }),
  put: <T,>(caminho: string, dados?: unknown) =>
    requisitar<T>(caminho, { method: "PUT", body: JSON.stringify(dados ?? {}) }),
};

export async function baixarArquivo(caminho: string, nome: string) {
  const resposta = await fetch(`${BASE}${caminho}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resposta.ok) throw new ErroApi("Não foi possível gerar o arquivo.", resposta.status);
  const blob = await resposta.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  link.click();
  URL.revokeObjectURL(url);
}


export async function visualizarArquivo(caminho: string) {
  const aba = window.open('about:blank', '_blank');
  if (aba) aba.opener = null;
  try {
    const resposta = await fetch(`${BASE}${caminho}`, {headers: token ? {Authorization: `Bearer ${token}`} : {}});
    if (!resposta.ok) throw new ErroApi('Não foi possível abrir o manual. Confira sua sessão e permissão.', resposta.status);
    const url = URL.createObjectURL(await resposta.blob());
    if (aba) aba.location.href = url;
    else {const link = document.createElement('a');link.href=url;link.download='SempreHub-manual.pdf';link.click();}
    window.setTimeout(()=>URL.revokeObjectURL(url),60000);
  } catch (erro) {aba?.close();throw erro;}
}
