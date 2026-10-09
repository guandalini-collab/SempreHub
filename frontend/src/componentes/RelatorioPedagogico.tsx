import React, { useCallback, useEffect, useRef, useState } from "react";

import { api, baixarArquivo } from "../api";
import { percentual, reais, umDecimal } from "../formatos";
import { Aviso, Botao, Cartao } from "./ui";

interface Relatorio {
  rubrica: {
    pesos: { lucro: number; patrimonio: number; satisfacao: number; participacao: number };
    observacao: string;
  };
  ranking: {
    posicao: number | null;
    empresa_id: number;
    empresa: string;
    pontuacao_didatica: number | null;
    nota_semestre: number | null;
    nota_provisoria: boolean;
    lucro_acumulado: number;
    patrimonio_sem_aportes: number | null;
    satisfacao: number | null;
    participacao: number | null;
  }[];
  observacoes: string[];
}

export default function RelatorioPedagogico({ turmaId, rodada, temResultados, abrirEmpresa }: {
  turmaId: number;
  rodada: number;
  temResultados: boolean;
  abrirEmpresa: (id: number) => void;
}) {
  const [dados, setDados] = useState<Relatorio | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const sequencia = useRef(0);

  const carregar = useCallback(async () => {
    const atual = ++sequencia.current;
    setCarregando(true);
    setErro(null);
    try {
      const relatorio = await api.get<Relatorio>(`/api/professor/turmas/${turmaId}/relatorio`);
      if (atual === sequencia.current) setDados(relatorio);
    } catch (e) {
      if (atual === sequencia.current) setErro(e instanceof Error ? e.message : "Não foi possível carregar o relatório.");
    } finally {
      if (atual === sequencia.current) setCarregando(false);
    }
  }, [turmaId]);

  useEffect(() => {
    setDados(null);
    if (temResultados) carregar();
    return () => { sequencia.current += 1; };
  }, [carregar, rodada, temResultados]);

  async function exportar() {
    setErro(null);
    try {
      await baixarArquivo(`/api/professor/turmas/${turmaId}/relatorio.csv`, `semprehub_relatorio_${turmaId}.csv`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível exportar o relatório.");
    }
  }

  return <Cartao titulo="Avaliação pedagógica e relatório" acao={temResultados && <div className="flex flex-wrap gap-2"><Botao variante="secundario" carregando={carregando} onClick={carregar}>Atualizar relatório</Botao><Botao variante="secundario" onClick={exportar}>Baixar relatório completo</Botao></div>}>
    <p className="mb-4 text-sm text-slate-600">A pontuação didática compara resultados econômicos, patrimônio, satisfação e participação nas decisões. A nota automática de 0 a 10 é calculada pelo desempenho para apoiar sua avaliação do semestre. É provisória durante as rodadas e final ao encerrar a turma; o lançamento acadêmico cabe ao professor.</p>
    {!temResultados && <p className="text-sm text-slate-500">O relatório aparece depois do fechamento da primeira rodada.</p>}
    {erro && <Aviso>{erro}</Aviso>}
    {dados && <>
      <p className="mb-3 text-xs text-slate-500">Nota = pontuação ponderada / 10. Lucro e patrimônio são comparados entre as empresas; empates recebem 50/100 nesses critérios. Critérios ausentes têm pesos redistribuídos. Comprar ou investir não gera pontos diretamente.</p>
      <p className="mb-3 text-xs text-slate-500">Pesos: lucro {percentual(dados.rubrica.pesos.lucro, 0)} · patrimônio {percentual(dados.rubrica.pesos.patrimonio, 0)} · satisfação {percentual(dados.rubrica.pesos.satisfacao, 0)} · participação nas decisões {percentual(dados.rubrica.pesos.participacao, 0)}.</p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-sm">
          <thead><tr className="text-left text-xs uppercase text-slate-500"><th className="pb-2">#</th><th className="pb-2">Empresa</th><th className="pb-2 text-right">Nota automática / 10</th><th className="pb-2 text-right">Lucro acumulado</th><th className="pb-2 text-right">Patrimônio sem aportes</th><th className="pb-2 text-right">Satisfação / 100</th><th className="pb-2 text-right">Participação nas decisões</th></tr></thead>
          <tbody>{dados.ranking.map((r) => <tr key={r.empresa_id} className="border-t border-slate-100"><td className="py-2 font-semibold text-ouro">{r.posicao == null ? "—" : `${r.posicao}º`}</td><td className="py-2"><button className="font-semibold text-marinho underline" onClick={() => abrirEmpresa(r.empresa_id)}>{r.empresa}</button></td><td className="py-2 text-right font-semibold text-marinho">{r.nota_semestre == null ? "—" : r.nota_semestre.toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2})}<span className="block text-xs font-normal text-slate-500">{r.nota_semestre == null ? "Sem rodadas" : r.nota_provisoria ? "Provisória" : "Final"}</span></td><td className="py-2 text-right">{reais(r.lucro_acumulado)}</td><td className="py-2 text-right">{r.patrimonio_sem_aportes == null ? "—" : reais(r.patrimonio_sem_aportes)}</td><td className="py-2 text-right">{r.satisfacao == null ? "—" : umDecimal(r.satisfacao)}</td><td className="py-2 text-right">{r.participacao == null ? "—" : percentual(r.participacao)}</td></tr>)}</tbody>
        </table>
      </div>
      {dados.observacoes.length > 0 && <ul className="mt-4 space-y-1 text-xs text-slate-500">{dados.observacoes.map((o) => <li key={o}>{o}</li>)}</ul>}
      <p className="mt-3 text-xs text-slate-500">O arquivo completo inclui todas as rodadas, decisões, demonstrativos e registros de participação da equipe.</p>
    </>}
  </Cartao>;
}
