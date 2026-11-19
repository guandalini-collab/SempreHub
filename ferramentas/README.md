# Coletores de fontes públicas do SempreHub

Busca indicadores oficiais, publicações das associações, bibliografia e notícias, sempre com
**período de referência, data da consulta e link** de cada dado. Não precisa do Google Drive.
Usa só a biblioteca padrão do Python 3.10 ou superior; o servidor MCP exige `pip install "mcp[cli]"`.

## Onde roda

- **No seu computador** (terminal ou Claude Desktop): é a forma recomendada. As APIs do BCB, do
  IBGE, do MDIC, do Crossref, do OpenAlex e do GDELT não são acessíveis a partir das sessões em
  nuvem do Claude; o servidor MCP local usa a internet do seu computador e, nas sessões do Claude
  Desktop, deixa o Claude consultar essas fontes ao vivo.
- **No servidor do SempreHub (Railway)**: o backend já consulta o IBGE e o BCB (IPCA por subitem,
  PMC, Selic). Os módulos daqui podem ser importados pelo backend depois, item a item, com aprovação.

## Uso no terminal

```bash
cd ~/Downloads/SempreHub/ferramentas
export SEMPREHUB_EMAIL_CONTATO="seu-email"     # pedido pelo Crossref e pelo OpenAlex
python3 -m fontes conferir                       # 1º uso: testa cada código na API real
python3 -m fontes macro
python3 -m fontes setor vestuario
python3 -m fontes paginas                        # publicações novas das associações
python3 -m fontes noticias vestuario --dias 30
python3 -m fontes bibliografia --doi 10.1287/msom.2022.1135 --setor ruptura --desde 2020
python3 -m fontes boletim                        # tudo de uma vez
```

As saídas ficam em `ferramentas/saida/AAAA-MM-DD/` em Markdown, CSV e JSON. O relatório separa
três blocos: dados estatísticos oficiais; publicações das associações a conferir; notícias e análises
jornalísticas. As fontes que falharem aparecem num quarto bloco, sem derrubar as demais.

## Claude Desktop (servidor MCP local)

1. `python3 -m pip install "mcp[cli]"`
2. Edite `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "semprehub-fontes": {
      "command": "python3",
      "args": ["/Users/guandalini/Downloads/SempreHub/ferramentas/servidor_mcp.py"],
      "env": {"SEMPREHUB_EMAIL_CONTATO": "seu-email"}
    }
  }
}
```

3. Reinicie o Claude Desktop. Ferramentas: `indicadores_macro`, `indicadores_setor`, `serie_sgs`,
   `publicacoes_associacoes`, `tabela_bibliografica`, `metadados_doi`, `noticias_setor`.

## Agendamento (opcional)

Boletim toda segunda-feira às 7h40 (`crontab -e`):

```
40 7 * * 1 cd /Users/guandalini/Downloads/SempreHub/ferramentas && /usr/bin/python3 -m fontes boletim
```

## Códigos usados

| Tema | Fonte | Código | Situação |
|---|---|---|---|
| Selic meta | BCB SGS | 432 | conferido (em uso no backend) |
| Selic acumulada no mês | BCB SGS | 4390 | conferido (em uso no backend) |
| Dólar comercial, venda, diário | BCB SGS | 1 | conferido (dados abertos BCB) |
| Juros médios do crédito, total | BCB SGS | 20714 | conferido (dados abertos BCB) |
| Juros PF, recursos livres, total | BCB SGS | 20740 | conferido (dados abertos BCB) |
| Juros PF, aquisição de outros bens | BCB SGS | 20750 | conferido (dados abertos BCB) |
| Juros PF, cheque especial | BCB SGS | 20741 | conferido (dados abertos BCB) |
| Endividamento das famílias / renda 12 meses | BCB SGS | 29037 | conferido (dados abertos BCB) |
| IPCA mensal | IBGE SIDRA | 7060, var. 63, cat. 315[7169] | conferido (em uso no backend) |
| IPCA 12 meses | IBGE SIDRA | 7060, variável resolvida pelo nome | resolvido na execução |
| IPCA mensal (alternativa) | BCB SGS | 433 | fonte secundária; preferir SIDRA |
| Expectativas (IPCA, Selic, Câmbio, PIB) | BCB Focus (Olinda) | ExpectativasMercadoAnuais | conferido em fonte secundária |
| PMC volume | IBGE SIDRA | 8882, var. 7169, 11046[56734] | conferido (em uso no backend) |
| PMC receita nominal | IBGE SIDRA | 8883, var. 7169, 11046[56735] | conferido (em uso no backend) |
| PMC atividades | IBGE SIDRA, classif. 85 | 90673 tecidos, vestuário e calçados; 31555 móveis; 103158 outros artigos de uso pessoal e doméstico | conferido |
| PIM-PF | IBGE SIDRA | 8888; atividades resolvidas pelo nome | tabela conferida em fonte secundária |
| Vestuário | Comex Stat | capítulos 61 e 62 | conferido em fonte secundária |
| Colchões | Comex Stat | NCM 9404.21.00 e 9404.29.00 | conferido em fonte secundária |
| Móveis | Comex Stat | posições 9401 e 9403 | conferido em fonte secundária |
| Bicicletas | Comex Stat | NCM 8712.00.10; 8711.60.00; subposições 8714.91 a 8714.99 | 8714.9x a conferir |
| Pet | Comex Stat | NCM 2309.10.00 | conferido em fonte secundária |
| Mochilas e malas | Comex Stat | subposições 4202.11, 4202.12, 4202.19, 4202.92 | conferido em fonte secundária |

Observações:
- 8711.60.00 inclui outros veículos elétricos de duas rodas, não só bicicletas elétricas.
- 4202.92 inclui outros artigos além de mochilas (bolsas, estojos).
- Na PMC, bicicletas e pet estão em "Outros artigos de uso pessoal e doméstico" (aproximação).
- Os nomes dos campos da resposta do Comex Stat não constam da documentação lida; cada registro
  leva a linha original para conferência no primeiro uso.

## Regras de uso dos dados

- Número de associação (ABICOL, ABRACICLO, ABEMPET, ABIT, Aliança Bike etc.) só entra no
  simulador ou no manual depois da leitura do documento e da aprovação do professor. O monitor de
  páginas só avisa que há publicação nova.
- Notícia nunca é dado oficial. Guardam-se título, veículo, autor, data de publicação, link e um
  trecho curto do próprio feed; o texto integral não é copiado.
- Na tabela bibliográfica, o "resumo" é o resumo publicado pelos autores. Nenhuma obra é citada
  no manual sem leitura do texto.
- The Guardian e NYT exigem chave (variáveis `GUARDIAN_API_KEY` e `NYT_API_KEY`); os termos de
  uso dessas APIs restringem a reprodução do conteúdo.
