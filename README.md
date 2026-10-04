# SempreHub — Simulador de Empreendedorismo

Jogo de empresas para o ensino de empreendedorismo. Cada aluno dirige uma empresa que disputa
o mesmo mercado com as empresas dos colegas. O professor conduz a turma: abre as rodadas
(cada rodada é um mês), escolhe ou sorteia os eventos macroeconômicos e acompanha os resultados.

- **Backend:** FastAPI (Python), SQLAlchemy, SQLite ou PostgreSQL.
- **Frontend:** React + TypeScript + Tailwind CSS (Vite).

## Como funciona

**Professor**
1. Cria a conta com e-mail `@iffarroupilha.edu.br` ou `@iffar.edu.br` e o **código de cadastro docente**.
2. Cria uma turma e, se quiser, ajusta os parâmetros do mercado (caixa inicial, preço de referência, salários, juros etc.).
3. Divulga o código de 6 caracteres da turma.
4. A cada mês, acompanha quem já enviou decisões e **fecha a rodada**, escolhendo o evento do mês ou deixando-o ser sorteado.
5. Acompanha o ranking, abre o histórico de cada empresa e exporta tudo em CSV.

**Aluno**
1. Cria a conta com e-mail `@aluno.iffarroupilha.edu.br` ou `@aluno.iffar.edu.br`.
2. Entra na turma pelo código e define o perfil da empresa: motivação (GEM), tipo de empreendedor (Dornelas) e regime tributário inicial.
3. Em cada mês decide preço, marketing, P&D, networking, contratações e demissões, empréstimos e amortizações, além de mudanças de regime.
4. Após o fechamento do mês, vê o demonstrativo de resultado, os alertas, o evento ocorrido, o mercado e a sua posição no ranking.

Quem não envia decisão tem as decisões do mês anterior repetidas automaticamente, mas sem contratações, demissões ou empréstimos.
Alunos só podem entrar antes do fechamento da 1ª rodada.

## Regras do modelo

| Elemento | Regra |
| --- | --- |
| **Mercado** | Demanda total = demanda base × nº de empresas × crescimento mensal × efeito do preço médio × evento. A demanda é dividida pela **atratividade** de cada empresa: preço relativo (peso maior), marca (acumulada com marketing) e qualidade (acumulada com P&D). |
| **Capacidade** | (1 + funcionários) × produtividade. Quem não consegue atender perde vendas; metade desses clientes compra de concorrentes com capacidade ociosa. |
| **Porter** | Preço abaixo do mercado com gasto alto em diferenciação ("meio-termo") reduz a atratividade em 30%. Preço premium sem marca nem qualidade reduz em 20%. |
| **MEI** | DAS fixo mensal, no máximo 1 empregado. Ao passar do teto anual, até 20% acima: imposto sobre o excesso e migração para o Simples. Acima de 20%: desenquadramento retroativo, com tributos do Simples sobre todo o faturamento do ano. |
| **Simples Nacional** | Anexo I (comércio), com alíquota efetiva calculada pela fórmula da LC 123/2006 sobre a RBT12. No início de atividade, usa a média mensal × 12. |
| **Lucro Presumido** | 5,93% de tributos federais sobre a receita, mais ICMS sobre o valor agregado (receita − CMV). |
| **Folha** | Salário × 1,45 (MEI/Simples) ou × 1,82 (Lucro Presumido). Cada rescisão custa um salário. |
| **Crédito** | Empréstimos até o limite da turma, com juros mensais sobre o saldo. Caixa negativo paga juros de cheque especial, e o banco não empresta a quem está com caixa negativo. |
| **Dornelas** | Fases: planejamento, captação (com dívida), operação estável e **sobrevivência** (caixa menor que um mês de custos fixos e folha). A empresa pode sair da sobrevivência. |
| **Comportamento** | Autoeficácia sobe com lucro e cai com prejuízo e caixa negativo; abaixo de 30, a produtividade cai 10%. Networking ≥ 30 evita a multa da notificação fiscal. |
| **Perfil inicial** | Oportunidade/necessidade (GEM) definem a autoeficácia inicial. O serial começa com mais networking; o franqueado tem marca, mas paga 5% de royalties; o corporativo começa com qualidade maior; o social, com rede comunitária. |
| **Eventos (Knight)** | Greve na logística (CMV +40% por 2 meses), notificação fiscal, alta ou queda da Selic (±0,5 p.p.), demanda aquecida (+25%) e retração (−25%). Atingem toda a turma no mesmo mês. |

**Simplificações e valores a conferir.** Os valores padrão do teto do MEI (R$ 81.000/ano), do DAS
(R$ 81/mês) e do ICMS (17%) são parâmetros didáticos e **devem ser conferidos com a legislação vigente**
antes de cada uso. Todos podem ser alterados por turma. Também não estão modelados:
- a transição da reforma tributária (CBS/IBS);
- o adicional de IRPJ;
- a regra de que a opção pelo Simples só vale a partir de janeiro. No jogo, a mudança de regime vale no próprio mês.

## Rodando no computador (desenvolvimento)

Pré-requisitos: Python 3.9 ou superior (recomendado 3.11+) e Node.js 18 ou superior.

**Backend**, num terminal:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API fica em `http://127.0.0.1:8000`, com documentação em `http://127.0.0.1:8000/docs`.
Em desenvolvimento, o código de cadastro docente é `docente-iffar` (troque-o no `.env`).

**Frontend**, em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173`.

**Testes do backend:**

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

## Publicando em servidor

O caminho mais simples é a imagem Docker, que compila o frontend e serve tudo pelo FastAPI numa única porta:

```bash
cp .env.example .env        # ajuste SEMPREHUB_SECRET_KEY, SEMPREHUB_CODIGO_DOCENTE e DATABASE_URL
docker build -t semprehub .
docker run -d -p 8000:8000 --env-file .env -v semprehub-dados:/app/dados semprehub
```

Sem Docker: rode `npm run build` em `frontend/`. Depois, em `backend/`, rode
`pip install -r requirements-postgres.txt` e
`SEMPREHUB_AMBIENTE=producao uvicorn app.main:app --host 0.0.0.0 --port 8000`.
O backend encontra e serve `frontend/dist` automaticamente.

Observações:
- Use **HTTPS** (por exemplo, com Nginx ou Caddy como proxy reverso). As senhas trafegam no login.
- Para várias turmas simultâneas, prefira **PostgreSQL** a SQLite.
- Hospedagens compartilhadas tradicionais em geral não mantêm um processo Python rodando continuamente. Neste caso, é preciso um VPS ou um serviço que execute contêineres. Confirme com o provedor antes de contratar.
- O banco é criado automaticamente na primeira execução. Para mudar o esquema com dados reais, será preciso adotar migrações (Alembic).

## Variáveis de ambiente

Veja `.env.example`. As principais:

| Variável | Uso |
| --- | --- |
| `SEMPREHUB_AMBIENTE` | `producao` exige chave secreta e código docente próprios. |
| `SEMPREHUB_SECRET_KEY` | Assina os tokens de login. |
| `SEMPREHUB_CODIGO_DOCENTE` | Código exigido no cadastro de professores. |
| `DATABASE_URL` | SQLite (padrão) ou `postgresql://...`. |
| `SEMPREHUB_DOMINIOS_ALUNO` / `SEMPREHUB_DOMINIOS_PROFESSOR` | Domínios de e-mail aceitos. |
| `SEMPREHUB_CORS_ORIGINS` | Necessário só se o frontend for hospedado em outro domínio (junto de `VITE_API_URL` no build). |

## Estrutura

```
backend/app/
  main.py            aplicação FastAPI e entrega do frontend compilado
  config.py          configuração por variáveis de ambiente
  models.py          usuários, turmas, empresas, decisões, resultados, eventos
  seguranca.py       senhas (PBKDF2) e tokens (JWT)
  routers/           rotas de autenticação, professor e aluno
  motor/simulacao.py fechamento da rodada: mercado, DRE, caixa, fases
  motor/tributos.py  MEI, Simples Nacional (Anexo I) e Lucro Presumido
  motor/eventos.py   eventos macroeconômicos
backend/tests/       testes automatizados (pytest)
frontend/src/
  App.tsx            rotas e sessão
  paginas/aluno/     entrada na turma e painel de decisões
  paginas/professor/ turmas, fechamento de rodadas, ranking e parâmetros
  componentes/ui.tsx componentes visuais da marca
```
