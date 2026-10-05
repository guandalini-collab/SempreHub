from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS, FRONTEND_DIST
from .migracoes import preparar_banco
from .routers import aluno, auth, professor, relatorios

preparar_banco()

app = FastAPI(
    title="SempreHub — Simulador de Empreendedorismo",
    description="API do simulador: professores conduzem turmas; alunos dirigem empresas.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(professor.router)
app.include_router(aluno.router)
app.include_router(relatorios.router)


@app.get("/api/saude")
def saude():
    return {"status": "ok", "servico": "SempreHub"}


# Em produção, o frontend compilado (frontend/dist) é servido pelo próprio FastAPI.
if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
    _assets = FRONTEND_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def frontend(caminho: str):
        if caminho.startswith("api/"):
            raise HTTPException(404, "Rota não encontrada.")
        arquivo = (FRONTEND_DIST / caminho).resolve()
        if caminho and arquivo.is_file() and Path(FRONTEND_DIST.resolve()) in arquivo.parents:
            return FileResponse(arquivo)
        return FileResponse(FRONTEND_DIST / "index.html")
