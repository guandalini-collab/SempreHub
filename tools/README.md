# Verificação da interface e imagens do manual

Na raiz do projeto, com Node.js e Playwright disponíveis, inicie o frontend em outra janela:

```
cd frontend
npm run dev -- --host 127.0.0.1 --port 4173
```

Depois, na raiz:

```
node tools/validar_interface.mjs
```

O teste usa dados ilustrativos locais e intercepta todas as chamadas à API. Não acessa contas de alunos nem a API de pesquisa. Usa Chrome instalado ou o navegador instalado pelo Playwright. Confere ingresso, equipes, liderança, BCG em tela pequena e bloqueio de envio; salva oito imagens em `docs/diagramas/`. Os arquivos temporários `frontend/qa-manual*` devem permanecer ignorados pelo Git.

Para gerar os manuais do aluno e do professor, instale ReportLab, Pillow e pypdf e execute `python3 docs/gerar_manuais_reportlab.py`. Os PDFs são salvos em `docs/gerados/` e copiados para `frontend/public/manuais/`. O manual de mídia é independente; use `--midias` somente quando houver uma revisão autorizada dele.

A marca nova está em `docs/assets/semprehub-fundo-branco.svg`, preservada como recebida. `node tools/preparar_logo_manual.mjs` prepara uma versão vetorial em PDF com Chromium/Playwright, mantendo fundo branco, traços e gradientes. O arquivo preparado é versionado; não há dependência de navegador na geração Python ou no Railway.

A apresentação dos dois manuais usa as regras ABNT aplicáveis a documentos institucionais: A4; margens superior/esquerda de 3 cm e inferior/direita de 2 cm; texto 12 com entrelinha 1,5; exceções menores e espaço simples para fontes, legendas e notas; seções em fluxo contínuo para reduzir espaços vazios; numeração progressiva; sumário navegável antes da parte textual; contagem desde a carta do fundador, com numeral visível na parte textual. Consulte `docs/formatacao-manuais.md`.

## Homologação com backend real

`node tools/homologar_fluxo.mjs` testa o frontend compilado servido pelo FastAPI local em http://127.0.0.1:8000. Antes de executar, inicie o backend com um DATABASE_URL exclusivo para QA, código docente qa-local-isolado, credenciais externas vazias e SEMPREHUB_CALENDARIO_TESTE=1. Nunca conecte esse servidor ao banco de produção. O roteiro cria turmas novas separadas por modelo e não apaga equipes ou altera modelos existentes. As evidências e capturas ficam em tmp/qa.

O fluxo confere integrantes e líder, rascunho persistido, pendências, confirmação final pela interface, modo leitura, fechamento manual, duas rodadas, cenários extremos, histórico, isolamento dos submenus e PDFs autenticados. Limites temporais e fechamento concorrente são cobertos pelos testes backend/tests/test_prazos.py. A suíte unitária usa seu banco de teste isolado; SEMPREHUB_TESTE_DB deve apontar somente para banco descartável, pois as fixtures recriam suas tabelas.
