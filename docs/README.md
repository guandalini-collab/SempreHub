# Manuais do SempreHub

Os manuais de uso estão separados por público:

- [Manual do aluno](manual-aluno.md) · [PDF do aluno](gerados/manual-aluno.pdf)
- [Manual do professor](manual-professor.md) · [PDF do professor](gerados/manual-professor.pdf)

Para recriar os PDFs:

```bash
backend/venv/bin/pip install -r docs/requirements.txt
backend/venv/bin/python docs/gerar_manuais.py
```

O gerador precisa de `pandoc` e `WeasyPrint`. Não baixa fontes,
imagens nem dados pela internet. Os diagramas usados pelos dois documentos
ficam em `docs/diagramas/` e a folha de estilo de impressão em `docs/manual.css`.

Os PDFs também são copiados para `frontend/public/manuais/`, servidos pelos
links dos painéis. A geração dos manuais é uma tarefa editorial; o servidor
usa os PDFs já gerados e não exige WeasyPrint em produção.
