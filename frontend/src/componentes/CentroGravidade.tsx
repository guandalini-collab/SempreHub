import React from "react";
import type { EstudoCentroGravidade } from "../tiposSimulacao";
import { Botao, Campo, EntradaNumero, estiloEntrada } from "./ui";

const VAZIO: EstudoCentroGravidade = { pontos: [], local_x: null, local_y: null, justificativa: "" };
export default function CentroGravidade({ estudo, aoMudar }: { estudo?: EstudoCentroGravidade | null; aoMudar: (estudo: EstudoCentroGravidade) => void }) {
  const dados = estudo ?? VAZIO;
  const total = dados.pontos.reduce((s, p) => s + p.volume, 0);
  const x = total > 0 ? dados.pontos.reduce((s, p) => s + p.x * p.volume, 0) / total : null;
  const y = total > 0 ? dados.pontos.reduce((s, p) => s + p.y * p.volume, 0) / total : null;
  const numero = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const mudar = (indice: number, campos: Partial<EstudoCentroGravidade["pontos"][number]>) => aoMudar({ ...dados, pontos: dados.pontos.map((p, i) => i === indice ? { ...p, ...campos } : p) });
  return <div className="space-y-4 rounded-xl border border-blue-200 bg-blue-50 p-5">
    <h3 className="text-lg font-bold">Localização da operação · centro de gravidade</h3>
    <p className="text-sm">Cadastre os pontos de atendimento e o volume mensal de cada um. Use coordenadas X e Y em quilômetros, com a mesma origem para todos os pontos; não misture latitude e longitude.</p>
    <p className="text-sm text-slate-600">O centro ponderado ajuda a estudar a localização da fábrica ou do centro de distribuição. Avalie também acesso, terreno e restrições antes de escolher.</p>
    {dados.pontos.map((p, i) => <div key={i} className="grid gap-3 rounded-lg bg-white p-4 sm:grid-cols-2 lg:grid-cols-5">
      <Campo rotulo={`Local ${i + 1}`}><input className={estiloEntrada} maxLength={100} value={p.nome} onChange={e => mudar(i, { nome: e.target.value })} /></Campo>
      <Campo rotulo={`X do local ${i + 1} (km)`}><EntradaNumero minimo={-1000000} max={1000000} valor={p.x} aoMudar={x => mudar(i, { x })} /></Campo>
      <Campo rotulo={`Y do local ${i + 1} (km)`}><EntradaNumero minimo={-1000000} max={1000000} valor={p.y} aoMudar={y => mudar(i, { y })} /></Campo>
      <Campo rotulo={`Volume do local ${i + 1}`}><EntradaNumero min={0} max={1000000} valor={p.volume} aoMudar={volume => mudar(i, { volume })} /></Campo>
      <Botao type="button" variante="secundario" onClick={() => aoMudar({ ...dados, pontos: dados.pontos.filter((_, j) => j !== i) })}>Remover local {i + 1}</Botao>
    </div>)}
    <Botao type="button" variante="secundario" disabled={dados.pontos.length >= 20} onClick={() => aoMudar({ ...dados, pontos: [...dados.pontos, { nome: "", x: 0, y: 0, volume: 0 }] })}>Adicionar local</Botao>
    <div className="rounded-lg bg-white p-4" aria-live="polite"><p className="font-bold">{x === null || y === null ? "Informe ao menos um local com volume maior que zero." : `Centro calculado: X = ${numero(x)} km · Y = ${numero(y)} km`}</p><p className="mt-2 text-sm">X = Σ(X × volume) ÷ Σ(volume) · Y = Σ(Y × volume) ÷ Σ(volume)</p><p className="mt-1 text-sm">Volume total: {numero(total)}</p></div>
    <p className="text-sm font-semibold">A escolha é sua: registre a localização e justifique.</p>
    <div className="grid gap-3 sm:grid-cols-2"><Campo rotulo="X da localização escolhida (km)"><input type="number" className={estiloEntrada} step="any" min={-1000000} max={1000000} value={dados.local_x ?? ""} onChange={e => aoMudar({ ...dados, local_x: e.target.value === "" ? null : Number(e.target.value) })} /></Campo><Campo rotulo="Y da localização escolhida (km)"><input type="number" className={estiloEntrada} step="any" min={-1000000} max={1000000} value={dados.local_y ?? ""} onChange={e => aoMudar({ ...dados, local_y: e.target.value === "" ? null : Number(e.target.value) })} /></Campo></div>
    <Campo rotulo="Justificativa da localização"><textarea className={estiloEntrada} maxLength={2000} value={dados.justificativa} onChange={e => aoMudar({ ...dados, justificativa: e.target.value })} /></Campo>
    <p className="text-xs text-slate-600">O estudo fica registrado junto com a decisão. Com localização escolhida e volumes positivos, a distância média ponderada afeta o frete. Consulte a tarifa em Logística; a localização não muda a capacidade das máquinas.</p>
  </div>;
}
