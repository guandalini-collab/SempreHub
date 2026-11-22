"""Planilha da curva ABC por produto (aprovada em 22/11/2026).

Base: Levy e Grewal, Retailing Management, 2026 release, p. 347-348 (análise ABC:
ordenar os itens por vendas, margem, giro ou GMROI) e p. 338-339 (itens A não devem
faltar). O livro dá um exemplo de cortes (A = 70% e B = 20% das vendas), não uma
regra; por isso os cortes ficam em células editáveis, com o exemplo como valor inicial.
"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

REFERENCIA = ("LEVY, Michael; GREWAL, Dhruv. Retailing management. 2026 release. "
              "New York: McGraw Hill, 2026. Cap. 12, p. 338-339 e 347-348.")
CORTE_A_EXEMPLO = 0.70
CORTE_B_EXEMPLO = 0.90

FONTE = "Arial"
AZUL = Font(name=FONTE, color="0000FF")
NEGRITO = Font(name=FONTE, bold=True)
NORMAL = Font(name=FONTE)
AMARELO = PatternFill("solid", fgColor="FFFF00")
CABECALHO = PatternFill("solid", fgColor="DCE6F1")
FINA = Side(style="thin", color="999999")
BORDA = Border(left=FINA, right=FINA, top=FINA, bottom=FINA)
MOEDA = '"R$" #,##0.00;-"R$" #,##0.00;-'
PCT = "0.0%;-0.0%;-"
INTEIRO = "#,##0;-#,##0;-"


def produtos_do_resultado(detalhes: dict | None) -> list[dict]:
    detalhes = detalhes or {}
    return detalhes.get("produtos") or (detalhes.get("operacao") or {}).get("produtos") or []


def gerar_planilha(empresa_nome: str, rodada: int, produtos: list[dict]) -> bytes:
    linhas = sorted(
        ({"nome": p.get("nome") or p.get("produto_id") or "Produto",
          "vendas_un": float(p.get("vendas") or 0),
          "falta": float(p.get("falta_clientes_mes") or 0),
          "receita": float(p.get("receita") or 0),
          "cmv": float(p.get("cmv") or 0)} for p in produtos),
        key=lambda x: (-x["receita"], x["nome"]),
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Curva ABC"

    ws["A1"] = f"Curva ABC — {empresa_nome} · mês de operação {rodada}"
    ws["A1"].font = Font(name=FONTE, bold=True, size=13)
    ws["A2"] = ("Dados do simulador (mês fechado), em ordem decrescente de vendas em R$. "
                "Células amarelas: edite. Texto azul: dados do simulador. Texto preto: fórmulas.")
    ws["A2"].font = NORMAL
    ws.row_dimensions[4].height = ws.row_dimensions[5].height = 30

    ws["B4"], ws["B5"] = "Corte da classe A (vendas acumuladas até)", "Corte da classe B (vendas acumuladas até)"
    ws["C4"], ws["C5"] = CORTE_A_EXEMPLO, CORTE_B_EXEMPLO
    for c in ("B4", "B5"):
        ws[c].font = NEGRITO
        ws[c].alignment = Alignment(wrap_text=True)
    for c in ("C4", "C5"):
        ws[c].fill, ws[c].number_format, ws[c].font, ws[c].border = AMARELO, "0%", AZUL, BORDA
    ws["D4"] = ("Valor inicial = exemplo de Levy e Grewal (2026, p. 348): itens A ≈ 70% das vendas, "
                "B ≈ 20%, C ≈ 10%. O livro não fixa cortes: ajuste e justifique a escolha.")
    ws["D5"] = "O restante (acima do corte B) é classe C."
    ws["D4"].font = ws["D5"].font = Font(name=FONTE, italic=True)
    ws["C4"].comment = Comment("Exemplo do livro, não regra. Altere para testar outros cortes.", "SempreHub")

    cab = ["Posição", "Produto", "Unidades vendidas", "Clientes sem produto (falta)", "Vendas (R$)",
           "CMV (R$)", "Margem bruta (R$)", "Margem bruta (%)", "Participação nas vendas",
           "Participação acumulada", "Produtos (acumulado)", "Classe"]
    h = 7
    for j, t in enumerate(cab, 1):
        c = ws.cell(row=h, column=j, value=t)
        c.font, c.fill, c.border = NEGRITO, CABECALHO, BORDA
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ini = h + 1
    fim = ini + max(len(linhas), 1) - 1
    tot = fim + 1
    for i, l in enumerate(linhas):
        r = ini + i
        ws.cell(row=r, column=1, value=i + 1)
        ws.cell(row=r, column=2, value=l["nome"])
        for col, chave in ((3, "vendas_un"), (4, "falta"), (5, "receita"), (6, "cmv")):
            ws.cell(row=r, column=col, value=l[chave]).font = AZUL
        ws.cell(row=r, column=7, value=f"=E{r}-F{r}")
        ws.cell(row=r, column=8, value=f"=IF(E{r}=0,0,G{r}/E{r})")
        ws.cell(row=r, column=9, value=f"=IF($E${tot}=0,0,E{r}/$E${tot})")
        ws.cell(row=r, column=10, value=f"=SUM($I${ini}:I{r})")
        ws.cell(row=r, column=11, value=f"=A{r}/COUNT($A${ini}:$A${fim})")
        # Classe pela participação acumulada até o item (inclusive); o primeiro
        # item é sempre A, mesmo que sozinho passe do corte.
        ws.cell(row=r, column=12, value=f'=IF(OR(A{r}=1,J{r}<=$C$4),"A",IF(J{r}<=$C$5,"B","C"))')
    if not linhas:
        ws.cell(row=ini, column=2, value="Sem produtos vendidos neste mês.")
    for r in range(ini, tot):
        for j in range(1, 13):
            c = ws.cell(row=r, column=j)
            c.border = BORDA
            if c.font != AZUL:
                c.font = NORMAL
        ws.cell(row=r, column=3).number_format = ws.cell(row=r, column=4).number_format = INTEIRO
        for col in (5, 6, 7):
            ws.cell(row=r, column=col).number_format = MOEDA
        for col in (8, 9, 10, 11):
            ws.cell(row=r, column=col).number_format = PCT
        ws.cell(row=r, column=12).alignment = Alignment(horizontal="center")
    ws.cell(row=tot, column=2, value="Total").font = NEGRITO
    for col in (3, 4, 5, 6, 7):
        L = get_column_letter(col)
        c = ws.cell(row=tot, column=col, value=f"=SUM({L}{ini}:{L}{fim})")
        c.font, c.border = NEGRITO, BORDA
        c.number_format = INTEIRO if col < 5 else MOEDA
    c = ws.cell(row=tot, column=8, value=f"=IF(E{tot}=0,0,G{tot}/E{tot})")
    c.font, c.border, c.number_format = NEGRITO, BORDA, PCT

    # Resumo por classe
    s = tot + 2
    ws.cell(row=s, column=2, value="Resumo por classe").font = NEGRITO
    for j, t in enumerate(["Classe", "Nº de produtos", "% dos produtos", "% das vendas", "% da margem bruta"], 2):
        c = ws.cell(row=s + 1, column=j, value=t)
        c.font, c.fill, c.border = NEGRITO, CABECALHO, BORDA
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    ws.row_dimensions[s + 1].height = 30
    for k, classe in enumerate("ABC"):
        r = s + 2 + k
        faixa = f"$L${ini}:$L${fim}"
        ws.cell(row=r, column=2, value=classe)
        ws.cell(row=r, column=3, value=f'=COUNTIF({faixa},B{r})')
        ws.cell(row=r, column=4, value=f'=IF(COUNT($A${ini}:$A${fim})=0,0,C{r}/COUNT($A${ini}:$A${fim}))')
        ws.cell(row=r, column=5, value=f'=IF($E${tot}=0,0,SUMIF({faixa},B{r},$E${ini}:$E${fim})/$E${tot})')
        ws.cell(row=r, column=6, value=f'=IF($G${tot}=0,0,SUMIF({faixa},B{r},$G${ini}:$G${fim})/$G${tot})')
        for j in range(2, 7):
            cel = ws.cell(row=r, column=j)
            cel.border, cel.font = BORDA, NORMAL
            cel.number_format = PCT if j >= 4 else "0"

    # Curva: participação de cada item (barras) e acumulada (linha)
    if linhas:
        barras = BarChart()
        barras.title = "Curva ABC (participação nas vendas)"
        barras.y_axis.title = "Participação"
        barras.y_axis.number_format = "0%"
        barras.y_axis.scaling.min, barras.y_axis.scaling.max = 0, 1
        barras.add_data(Reference(ws, min_col=9, min_row=h, max_row=fim), titles_from_data=True)
        cats = Reference(ws, min_col=2, min_row=ini, max_row=fim)
        barras.set_categories(cats)
        linha = LineChart()
        linha.add_data(Reference(ws, min_col=10, min_row=h, max_row=fim), titles_from_data=True)
        linha.set_categories(cats)
        barras += linha
        barras.roundedCorners = False
        barras.legend.position = "b"
        barras.legend.overlay = False
        barras.title.overlay = False
        barras.y_axis.title.overlay = False
        barras.x_axis.delete = False
        barras.y_axis.delete = False
        barras.height, barras.width = 9, 22
        ws.add_chart(barras, f"B{s + 7}")

    larguras = [9, 34, 12, 14, 15, 15, 15, 12, 14, 14, 13, 9]
    for j, w in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[h].height = 45
    ws.freeze_panes = f"C{ini}"

    # Instruções
    g = wb.create_sheet("Como usar")
    texto = [
        ("Como usar a curva ABC", True),
        ("1. Os produtos já vêm em ordem decrescente de vendas em reais do mês escolhido (Levy; Grewal, 2026, p. 347-348: "
         "a análise ABC começa ordenando os itens por um critério, como vendas, margem, giro ou GMROI).", False),
        ("2. Defina os cortes nas células amarelas da aba \"Curva ABC\". O valor inicial (70% e 90%) repete o exemplo do livro; "
         "o livro não fixa cortes. Mude, observe como as classes mudam e justifique a escolha.", False),
        ("3. Regra da planilha: é A o item cuja participação acumulada (coluna J) fica até o corte A; B, até o corte B; "
         "os demais, C. O primeiro item é sempre A, mesmo que sozinho passe do corte.", False),
        ("4. Use o resultado nas compras: itens A não devem faltar — use nível de serviço mais alto no apoio às compras; "
         "itens C toleram disponibilidade menor (Levy; Grewal, 2026, p. 338-339). Confira a coluna de clientes sem produto.", False),
        ("5. Ordenar por vendas é só um critério. Para comparar, ordene também pela margem bruta (R$) e veja se as classes mudam.", False),
        ("6. Produtos sem venda no mês aparecem no fim (classe C). O livro trata à parte os itens sem venda "
         "(classe D no exemplo): quase não vendem sem remarcação, e a maior parte sai do sortimento (p. 348).", False),
        ("Referência", True),
        (REFERENCIA, False),
    ]
    for i, (t, negrito) in enumerate(texto, 1):
        c = g.cell(row=i * 2 - 1, column=1, value=t)
        c.font = NEGRITO if negrito else NORMAL
        c.alignment = Alignment(wrap_text=True, vertical="top")
    g.column_dimensions["A"].width = 110

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
