import CentroGravidade from "./CentroGravidade";
import { ControleVisual } from "./Experiencia";
import React from "react";

import { inteiro, percentual, reais, umDecimal } from "../formatos";
import type { ConfiguracaoMotor, DecisaoSimulacao, DetalhesSimulacao, EstadoSimulacao, ModoJogo, PreviaSimulacao } from "../tiposSimulacao";
import { Campo, Cartao, EntradaNumero, estiloEntrada } from "./ui";

export function ControlesSimulacao({ modo, valores, aoMudar, config, salarioBase, marketing, mixSelecionado = false, area = "decisoes", rodada }: {
  modo: ModoJogo;
  valores: DecisaoSimulacao;
  aoMudar: (valores: DecisaoSimulacao) => void;
  config: ConfiguracaoMotor;
  salarioBase: number;
  marketing: number;
  mixSelecionado?: boolean;
  area?: string;
  rodada: number;
}) {
  const estudo = valores.centro_gravidade;
  const volume = estudo?.pontos.reduce((s, p) => s + p.volume, 0) ?? 0;
  const temLocalizacao = !!estudo && estudo.local_x != null && estudo.local_y != null && volume > 0;
  const distancia = temLocalizacao ? estudo!.pontos.reduce((s, p) => s + Math.hypot(p.x - estudo!.local_x!, p.y - estudo!.local_y!) * p.volume, 0) / volume : 0;
  const taxaKm = config.custo_frete_km ?? 0.1;
  const adicionalFrete = Math.round(distancia * taxaKm * 100) / 100;
  const baseFrete = valores.modal === "RAPIDO" ? config.frete_rapido : valores.modal === "ECONOMICO" ? config.frete_economico : config.frete_padrao;
  const mudar = <K extends keyof DecisaoSimulacao>(campo: K, valor: DecisaoSimulacao[K]) => aoMudar({ ...valores, [campo]: valor });
  return <div className="space-y-6">
    {modo === "TRADICIONAL" && <>
      <Secao titulo="Produção e investimento" oculto={area !== "producao"}>
        <Campo rotulo="Produção planejada" ajuda="Unidades a produzir neste mês. Matéria-prima, pessoas e máquinas limitam a produção; sobrecarga pode gerar refugo."><ControleVisual rotulo="producao" moeda={false} inteiro valor={valores.producao} aoMudar={(v) => mudar("producao", v)} limite={10000} /></Campo>
        <Campo rotulo="Comprar matéria-prima" ajuda="Unidades a comprar neste mês. O que não for consumido continua no estoque para as próximas rodadas."><ControleVisual rotulo="comprar mp" moeda={false} inteiro valor={valores.comprar_mp} aoMudar={(v) => mudar("comprar_mp", v)} limite={10000} /></Campo>
        {rodada >= 3 ? <><Campo rotulo="Comprar máquinas" ajuda={`Cada máquina custa ${reais(config.preco_maquina)} e entra em operação na rodada seguinte. É investimento; a depreciação aparece no lucro.`}><ControleVisual rotulo="comprar maquinas" moeda={false} inteiro valor={valores.comprar_maquinas} aoMudar={(v) => mudar("comprar_maquinas", v)} limite={100} /></Campo><dl className="mt-3 grid gap-2 rounded-lg bg-blue-50 p-4 text-sm sm:grid-cols-2"><div><dt>Investimento total</dt><dd className="font-bold">{reais(valores.comprar_maquinas * config.preco_maquina)}</dd></div><div><dt>Capacidade adicional nominal</dt><dd className="font-bold">{inteiro(valores.comprar_maquinas * config.capacidade_maquina)} un./mês</dd></div><div><dt>Disponível no mês</dt><dd className="font-bold">{rodada + 1}</dd></div><div><dt>Depreciação mensal estimada</dt><dd className="font-bold">{reais(valores.comprar_maquinas * config.preco_maquina / config.vida_util_maquina)}</dd></div></dl><p className="mt-2 text-xs text-slate-600">A capacidade efetiva também depende de pessoas, matéria-prima e condição das máquinas. A compra reduz o caixa; a depreciação afeta o lucro nos meses de operação.</p></> : <p className="rounded-lg bg-blue-50 p-4 text-sm text-blue-900"><strong>Expansão do maquinário a partir do mês 3.</strong> Nos dois primeiros meses, planeje a produção com as máquinas iniciais e cuide da manutenção.</p>}
        <Campo rotulo="Manutenção do mês" ajuda="Cuida das condições das máquinas e da capacidade das próximas rodadas."><ControleVisual rotulo="manutencao"  valor={valores.manutencao} aoMudar={(v) => mudar("manutencao", v)} limite={100000} /></Campo>

      </Secao>
      <div hidden={area !== "producao"}><CentroGravidade estudo={valores.centro_gravidade} aoMudar={(estudo) => mudar("centro_gravidade", estudo)} /></div>
      <Secao titulo="Logística e entregas" oculto={area !== "logistica"}>
        <Campo rotulo="Entrega" ajuda="O frete é cobrado por unidade vendida. A experiência da entrega afeta a satisfação futura.">
          <select className={estiloEntrada} value={valores.modal} onChange={(e) => mudar("modal", e.target.value as DecisaoSimulacao["modal"])}>
            <option value="RAPIDO">Rápida · {reais(config.frete_rapido)} por unidade</option>
            <option value="PADRAO">Padrão · {reais(config.frete_padrao)} por unidade</option>
            <option value="ECONOMICO">Econômica · {reais(config.frete_economico)} por unidade</option>
          </select>
        </Campo>
      </Secao>
      {area === "logistica" && <div className="rounded-lg bg-blue-50 p-4 text-sm"><h3 className="font-bold">Frete e localização</h3><p className="mt-2">Modalidade: {reais(baseFrete)}/unidade · taxa didática: {reais(taxaKm)}/unidade/km.</p><p className="mt-2">Distância média ponderada: {distancia.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} km · adicional: {reais(adicionalFrete)}/unidade.</p><p className="mt-2 font-bold">Frete estimado: {reais(baseFrete + adicionalFrete)} por unidade vendida.</p><p className="mt-2">{temLocalizacao ? "A localização escolhida em Produção afeta o frete registrado na DRE e no caixa." : "Sem localização definida e volumes positivos, aplica-se apenas o custo da modalidade. Complete o estudo em Produção para incluir as distâncias."}</p></div>}
      <Secao titulo="Compras a prazo" oculto={area !== "financas"}>
        <Campo rotulo="Parcela das compras a prazo" ajuda="A compra entra no estoque agora; o pagamento ocorre no vencimento. O restante é pago à vista."><EntradaNumero valor={valores.compras_prazo * 100} sufixo="%" aoMudar={(v) => mudar("compras_prazo", v / 100)} /></Campo>
        <Campo rotulo="Prazo de pagamento" ajuda="Contado a partir desta rodada."><select className={estiloEntrada} value={valores.prazo_pagamento} onChange={(e) => mudar("prazo_pagamento", Number(e.target.value))}>{[1, 2, 3].map((prazo) => <option key={prazo} value={prazo}>{prazo} mês(es)</option>)}</select></Campo>
      </Secao>
    </>}
    {modo === "STARTUP" && <>
      <Secao titulo="Capacidade do serviço digital" oculto={area !== "producao"}>
      <Campo rotulo="Capacidade da nuvem" ajuda="Número de clientes que a operação consegue atender neste mês. Os clientes sem atendimento continuam na base, com impacto na satisfação."><ControleVisual rotulo="capacidade nuvem" moeda={false} inteiro valor={valores.capacidade_nuvem} aoMudar={(v) => mudar("capacidade_nuvem", v)} limite={10000} /></Campo>
      </Secao>
      <Secao titulo="Investidores e financiamento" oculto={area !== "financas"}>
      <Campo rotulo="Aporte de investidores" ajuda="Entrada de capital no caixa em troca de participação. Não é receita nem lucro e pode reduzir a participação dos fundadores."><ControleVisual rotulo="aporte"  valor={valores.aporte} aoMudar={(v) => mudar("aporte", v)} limite={100000} /></Campo>
      <Campo rotulo="Valuation antes do aporte" ajuda="Valor da empresa usado para definir a participação do investidor."><ControleVisual rotulo="valuation"  minimo={0.01} valor={valores.valuation} aoMudar={(v) => mudar("valuation", v)} limite={100000} /></Campo>
    </Secao>
      {area === "logistica" && <div className="rounded-xl bg-blue-50 p-5 text-sm"><h3 className="font-bold">Operação digital</h3><p className="mt-2">A entrega deste serviço acontece pela nuvem. Planeje a capacidade de atendimento em Produção e operação.</p></div>}
    </>}
    <Secao titulo="Pessoas e desenvolvimento" oculto={area !== "decisoes"}>
      <Campo rotulo="Salário da equipe de funcionários" ajuda={`O padrão da turma é ${reais(salarioBase)} por funcionário. Salários, benefícios e treinamento influenciam moral, qualificação e rotatividade.`}>
        <select className={estiloEntrada} value={valores.salario === null ? "PADRAO" : "PROPRIO"} onChange={(e) => mudar("salario", e.target.value === "PADRAO" ? null : salarioBase)}><option value="PADRAO">Usar salário-base da turma</option><option value="PROPRIO">Definir salário da empresa</option></select>
      </Campo>
      {valores.salario !== null && <Campo rotulo="Salário por funcionário"><ControleVisual rotulo="salario"  valor={valores.salario} aoMudar={(v) => mudar("salario", v)} limite={100000} /></Campo>}
      <Campo rotulo="Benefício por funcionário" ajuda="Valor mensal por empregado; aparece como despesa de benefícios."><ControleVisual rotulo="beneficio"  valor={valores.beneficio} aoMudar={(v) => mudar("beneficio", v)} limite={100000} /></Campo>
      <Campo rotulo="Treinamento do mês" ajuda="Investimento total em capacitação dos funcionários; o desenvolvimento passa para as rodadas seguintes."><ControleVisual rotulo="treinamento"  valor={valores.treinamento} aoMudar={(v) => mudar("treinamento", v)} limite={100000} /></Campo>
    </Secao>
    {!mixSelecionado && <Secao titulo="Posicionamento e canais" oculto={area !== "decisoes"}>
      <Campo rotulo="Estratégia de posicionamento"><select className={estiloEntrada} value={valores.posicionamento} onChange={(e) => mudar("posicionamento", e.target.value as DecisaoSimulacao["posicionamento"])}><option value="CUSTO">Liderança em custo</option><option value="DIFERENCIACAO">Diferenciação</option></select></Campo>
      <Campo rotulo="Canal de venda"><select className={estiloEntrada} value={valores.canal} onChange={(e) => mudar("canal", e.target.value as DecisaoSimulacao["canal"])}><option value="DIRETO">Venda direta</option><option value="DISTRIBUIDOR">Distribuidor</option><option value="DIGITAL">Digital</option></select></Campo>
      <Campo rotulo="Marketing direcionado ao digital" ajuda={`Parcela do orçamento de marketing que vai ao digital. Limite atual: ${reais(marketing)}; este valor já está incluído no marketing total.`}><EntradaNumero moeda max={marketing} valor={valores.marketing_digital} aoMudar={(v) => mudar("marketing_digital", v)} /></Campo>
    </Secao>
    }
    <Secao titulo="Vendas a prazo" oculto={area !== "financas"}>
      <Campo rotulo="Parcela das vendas a prazo" ajuda="A venda gera receita e lucro nesta rodada, mas o dinheiro só chega ao caixa no vencimento."><EntradaNumero valor={valores.vendas_prazo * 100} sufixo="%" aoMudar={(v) => mudar("vendas_prazo", v / 100)} /></Campo>
      <Campo rotulo="Prazo de recebimento" ajuda="Contado a partir desta rodada."><select className={estiloEntrada} value={valores.prazo_recebimento} onChange={(e) => mudar("prazo_recebimento", Number(e.target.value))}>{[1, 2, 3].map((prazo) => <option key={prazo} value={prazo}>{prazo} mês(es)</option>)}</select></Campo>
    </Secao>
  </div>;
}

export function PainelOperacional({ estado, modo }: { estado: EstadoSimulacao; modo: ModoJogo }) {
  return <div className="grid gap-6 lg:grid-cols-2">
    <Cartao titulo={modo === "STARTUP" ? "Clientes e participação" : "Estoque e máquinas"}>
      <dl className="grid grid-cols-2 gap-4 text-sm">
        {modo === "STARTUP" ? <>
          <Dado rotulo="Clientes na base" valor={inteiro(estado.clientes)} />
          <Dado rotulo="Participação dos fundadores" valor={percentual(estado.participacao_fundadores, 1)} />
          <Dado rotulo="Capital aportado" valor={reais(estado.capital_aportado)} />
        </> : <>
          <Dado rotulo="Matéria-prima" valor={`${inteiro(estado.estoque_mp.quantidade)} un. · ${reais(estado.estoque_mp.valor)}`} />
          <Dado rotulo="Produtos acabados" valor={`${inteiro(estado.estoque_pa.quantidade)} un. · ${reais(estado.estoque_pa.valor)}`} />
          <Dado rotulo="Estoque obsoleto" valor={`${inteiro(estado.estoque_obsoleto.quantidade)} un. · ${reais(estado.estoque_obsoleto.valor)}`} />
          <Dado rotulo="Máquinas" valor={inteiro(estado.maquinas.length)} />
        </>}
        <Dado rotulo="Satisfação dos clientes" valor={`${umDecimal(estado.satisfacao)} de 100`} />
      </dl>
      {modo === "TRADICIONAL" && estado.maquinas.length > 0 && <ul className="mt-4 divide-y divide-slate-100 text-xs text-slate-600">{estado.maquinas.map((m, i) => <li key={i} className="py-2">Máquina {i + 1}: condição {percentual(m.condicao, 0)} · valor líquido {reais(m.valor_liquido)} · disponível a partir do mês {m.ativacao}</li>)}</ul>}
      <p className="mt-3 text-xs text-slate-500">Esses dados passam para a próxima rodada. O histórico mantém o estado de cada mês concluído.</p>
    </Cartao>
    <Cartao titulo="Pessoas e vencimentos">
      <dl className="mb-4 grid grid-cols-3 gap-3 text-sm">
        <Dado rotulo="Moral" valor={`${umDecimal(estado.rh.moral)} / 100`} />
        <Dado rotulo="Qualificação" valor={umDecimal(estado.rh.qualificacao)} />
        <Dado rotulo="Saídas acumuladas" valor={inteiro(estado.rh.rotatividade_acumulada)} />
      </dl>
      <div className="grid gap-3 sm:grid-cols-2">
        <Titulos titulo="A receber" titulos={estado.receber} />
        <Titulos titulo="A pagar" titulos={estado.pagar} />
      </div>
      {estado.vencimento_divida && <p className="mt-3 rounded-lg bg-amber-50 p-2 text-xs text-amber-900">A dívida inicial da recuperação vence no mês {estado.vencimento_divida}. Planeje a amortização e acompanhe os alertas do fechamento.</p>}
    </Cartao>
  </div>;
}

export function RelatorioFinanceiro({ detalhes }: { detalhes: DetalhesSimulacao }) {
  const { dfc, balanco } = detalhes;
  return <div className="space-y-4">
    <p className="rounded-lg bg-sky-50 p-3 text-xs leading-relaxed text-sky-900">Lucro e caixa medem coisas diferentes. A DRE registra o resultado das vendas e despesas; o fluxo de caixa registra o dinheiro que entrou e saiu. Estoque, prazos, investimentos e financiamentos explicam as diferenças.</p>
    <div className="grid gap-4 lg:grid-cols-2">
      <Cartao titulo="Fluxo de caixa da rodada">
        <ListaFinanceira linhas={[
          ["Caixa no início", dfc.caixa_inicial],
          ["Recebimentos operacionais", dfc.recebimentos],
          ["Pagamentos operacionais", -dfc.pagamentos],
          ["Saldo operacional", dfc.operacional],
          ["Investimentos", dfc.investimento],
          ["Financiamentos", dfc.financiamento],
          ["Variação de caixa", dfc.variacao],
          ["Caixa no fim", dfc.caixa_final],
        ]} />
      </Cartao>
      <Cartao titulo="Balanço patrimonial ao fim da rodada">
        <ListaFinanceira linhas={[
          ["Caixa", balanco.caixa],
          ["Contas a receber", balanco.receber],
          ["Estoques", balanco.estoques],
          ["Máquinas líquidas de depreciação", balanco.imobilizado],
          ["Total do ativo", balanco.caixa + balanco.receber + balanco.estoques + balanco.imobilizado],
          ["Contas a pagar", balanco.pagar],
          ["Dívida", balanco.divida],
          ["Total do passivo", balanco.pagar + balanco.divida],
          ["Patrimônio líquido", balanco.patrimonio],
          ["Passivo + patrimônio líquido", balanco.pagar + balanco.divida + balanco.patrimonio],
          ["Capital de giro", balanco.capital_giro],
        ]} />
      </Cartao>
    </div>
    <Cartao titulo={detalhes.modo === "STARTUP" ? "Aquisição e retenção de clientes" : "Produção e entregas da rodada"}>
      <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
        {detalhes.modo === "STARTUP" ? <>
          <Operacao detalhes={detalhes} campo="clientes_iniciais" rotulo="Clientes no início" />
          <Operacao detalhes={detalhes} campo="clientes_perdidos" rotulo="Cancelamentos" />
          <Operacao detalhes={detalhes} campo="clientes_adquiridos" rotulo="Novos clientes" />
          <Operacao detalhes={detalhes} campo="clientes_atendidos" rotulo="Clientes atendidos" />
          <Operacao detalhes={detalhes} campo="clientes_finais" rotulo="Clientes na base ao fim" />
          <Operacao detalhes={detalhes} campo="churn" rotulo="Taxa de cancelamento" tipo="percentual" />
          <Operacao detalhes={detalhes} campo="cac" rotulo="CAC · custo de aquisição" tipo="moeda" />
          <Operacao detalhes={detalhes} campo="ltv" rotulo="LTV · valor do cliente" tipo="moeda" />
          <Operacao detalhes={detalhes} campo="runway" rotulo="Meses de caixa estimados" tipo="decimal" />
          <Operacao detalhes={detalhes} campo="participacao_fundadores" rotulo="Participação dos fundadores" tipo="percentual" />
        </> : <>
          <Operacao detalhes={detalhes} campo="producao_planejada" rotulo="Produção planejada" />
          <Operacao detalhes={detalhes} campo="producao_real" rotulo="Produção realizada" />
          <Operacao detalhes={detalhes} campo="producao_boa" rotulo="Produtos aproveitáveis" />
          <Operacao detalhes={detalhes} campo="refugo" rotulo="Refugo" />
          <Operacao detalhes={detalhes} campo="vendas" rotulo="Unidades vendidas" />
          <Operacao detalhes={detalhes} campo="ruptura" rotulo="Demanda não atendida" />
          <Operacao detalhes={detalhes} campo="capacidade_produtiva" rotulo="Capacidade produtiva" />
          <Operacao detalhes={detalhes} campo="estoque_pa_final" rotulo="Produtos no estoque final" />
        </>}
      </dl>
      {detalhes.modo === "STARTUP" && <p className="mt-3 text-xs text-slate-500">Indicadores sem uma base válida aparecem como “—”. CAC e LTV são estimativas da simulação, calculadas a partir desta rodada.</p>}
    </Cartao>
  </div>;
}

export function PreviaOperacional({ simulacao, modo }: { simulacao: PreviaSimulacao; modo: ModoJogo }) {
  return <div className="mt-3 border-t border-slate-200 pt-3">
    <dl className="grid grid-cols-2 gap-3 text-xs">
      {modo === "TRADICIONAL" && simulacao.producao != null && <Dado rotulo="Produção preparada" valor={`${inteiro(simulacao.producao)} un.`} />}
      {simulacao.estado && modo === "TRADICIONAL" && <Dado rotulo="Matéria-prima após preparo" valor={`${inteiro(simulacao.estado.estoque_mp.quantidade)} un.`} />}
      {simulacao.estado && modo === "STARTUP" && <Dado rotulo="Participação após aporte" valor={percentual(simulacao.estado.participacao_fundadores, 1)} />}
    </dl>
    <p className="mt-2 text-xs text-slate-500">{simulacao.aviso ?? "Estimativa antes da demanda desta rodada. As vendas, recebimentos e resultados finais dependem do mercado."}</p>
  </div>;
}

function Secao({ titulo, children, oculto = false }: { titulo: string; children: React.ReactNode; oculto?: boolean }) {
  return <fieldset hidden={oculto}><legend className="mb-3 border-b border-slate-200 pb-1 text-sm font-semibold text-marinho">{titulo}</legend><div className="grid gap-4 sm:grid-cols-2">{children}</div></fieldset>;
}

function Dado({ rotulo, valor }: { rotulo: string; valor: React.ReactNode }) {
  return <div><dt className="text-xs text-slate-500">{rotulo}</dt><dd className="mt-0.5 font-semibold text-marinho">{valor}</dd></div>;
}

function Titulos({ titulo, titulos }: { titulo: string; titulos: EstadoSimulacao["receber"] }) {
  return <div className="rounded-lg bg-slate-50 p-3"><p className="mb-2 text-xs font-semibold text-marinho">{titulo}</p>{titulos.length ? <ul className="max-h-32 space-y-1 overflow-y-auto text-xs text-slate-600">{titulos.map((t, i) => <li key={i}>Mês {t.vencimento} · {reais(t.valor)}</li>)}</ul> : <p className="text-xs text-slate-500">Nenhum vencimento pendente.</p>}</div>;
}

function ListaFinanceira({ linhas }: { linhas: [string, number][] }) {
  return <dl className="divide-y divide-slate-100 text-sm">{linhas.map(([rotulo, valor]) => <div key={rotulo} className="flex justify-between gap-3 py-1.5"><dt className="text-slate-600">{rotulo}</dt><dd className={`whitespace-nowrap font-semibold ${valor < 0 ? "text-red-700" : "text-marinho"}`}>{reais(valor)}</dd></div>)}</dl>;
}

function Operacao({ detalhes, campo, rotulo, tipo = "inteiro" }: { detalhes: DetalhesSimulacao; campo: string; rotulo: string; tipo?: "inteiro" | "moeda" | "percentual" | "decimal" }) {
  const valor = detalhes.operacao[campo];
  const exibido = typeof valor !== "number" || !Number.isFinite(valor) ? "—" : tipo === "moeda" ? reais(valor) : tipo === "percentual" ? percentual(valor, 1) : tipo === "decimal" ? umDecimal(valor) : inteiro(valor);
  return <Dado rotulo={rotulo} valor={exibido} />;
}
