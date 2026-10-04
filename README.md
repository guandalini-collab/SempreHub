# Udyama Simulador

Simulador de empreendedorismo brasileiro com backend em FastAPI (Python) e frontend em React + TypeScript + Tailwind CSS.

## Estrutura do projeto

- `backend/` — API em FastAPI, modelos em SQLAlchemy, banco de dados SQLite local (`udyama.db`).
- `frontend/` — Dashboard em React + Vite + Tailwind CSS.

Backend e frontend rodam de forma independente, cada um no seu terminal.

## 1. Rodando o Backend

Pré-requisito: Python 3.10 ou superior (confira com `python3 --version`).

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. A documentação interativa (Swagger) fica em `http://127.0.0.1:8000/docs`.

Para sair do ambiente virtual depois, use `deactivate`.

## 2. Rodando o Frontend

Pré-requisito: Node.js 18 ou superior (confira com `node --version`). Se não tiver, instale com `brew install node` ou pelo site https://nodejs.org.

```bash
cd frontend
npm install
npm run dev
```

O Dashboard abre em `http://localhost:5173`.

## 3. Usando os dois juntos

Abra dois terminais:

1. No primeiro, siga o passo 1 (Backend) e deixe o `uvicorn` rodando.
2. No segundo, siga o passo 2 (Frontend) e deixe o `npm run dev` rodando.

Com os dois no ar, o Dashboard no navegador consegue chamar a API em `http://127.0.0.1:8000` ao clicar em "Avançar Turno".
