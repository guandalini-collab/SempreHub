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

Para gerar os três manuais, instale ReportLab e Pillow no ambiente Python e execute `python3 docs/gerar_manuais_reportlab.py`. Os PDFs são salvos em `docs/gerados/` e copiados para `frontend/public/manuais/`.
