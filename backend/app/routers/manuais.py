"""PDFs institucionais autenticados, inclusive nas URLs antigas."""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from ..config import FRONTEND_DIST
from ..models import Papel, Usuario
from ..seguranca import usuario_atual

router = APIRouter(tags=['manuais'])
ARQUIVOS = {'manual-aluno.pdf','manual-professor.pdf','manual-midias.pdf'}


@router.get('/api/manuais/{arquivo}')
@router.get('/manuais/{arquivo}')
def obter_manual(arquivo: str, usuario: Usuario = Depends(usuario_atual)):
    if arquivo not in ARQUIVOS:
        raise HTTPException(404,'Manual não encontrado.')
    if arquivo == 'manual-professor.pdf' and usuario.papel != Papel.PROFESSOR:
        raise HTTPException(403,'Manual restrito a professores.')
    caminho = FRONTEND_DIST / 'manuais' / arquivo
    if not caminho.is_file():
        caminho = Path(__file__).resolve().parents[3] / 'docs' / 'gerados' / arquivo
    if not caminho.is_file():
        raise HTTPException(404,'Manual ainda não disponível.')
    return FileResponse(caminho,media_type='application/pdf',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
