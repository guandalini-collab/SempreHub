"""Pesquisa, revisão e publicação separadas das decisões dos alunos."""
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ConteudoMercado, RelatorioEmpresarial, Usuario, StatusTurma
from ..seguranca import exigir_professor, exigir_aluno
from ..inteligencia_mercado import gerar_json
from ..relatorios import _rodada
from .professor import _turma_do_professor
from .aluno import _empresa_do_aluno

router = APIRouter(tags=["mercado"])
SETORES = ["Eletrônicos e Tecnologia", "Alimentos e Bebidas", "Vestuário e Moda", "Cosméticos e Beleza", "Móveis e Decoração", "Automotivo", "Esportes e Fitness", "Saúde e Bem-estar", "Educação e Cursos", "Pet Care", "Construção e Materiais", "Entretenimento e Mídia"]

class Pesquisa(BaseModel):
    setor: str = Field(min_length=3, max_length=120)
    comercio: Literal["B2C", "B2B", "HIBRIDO"] = "B2C"
    noticias: int = Field(3, ge=0, le=10)
    analises: int = Field(2, ge=0, le=10)
    produtos: int = Field(3, ge=1, le=10)

class Fonte(BaseModel):
    titulo: str = Field(min_length=1, max_length=500)
    url: str = Field(max_length=2000)

class Artigo(BaseModel):
    titulo: str = Field(min_length=3, max_length=300)
    texto: str = Field(min_length=20, max_length=12000)
    data: str = Field(min_length=4, max_length=40)
    fontes: list[Fonte] = Field(min_length=1, max_length=10)

class Produto(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=3, max_length=200)
    descricao: str = Field(min_length=10, max_length=3000)
    custo_unitario: float = Field(gt=0, le=1000000)
    unidade: str = Field(min_length=1, max_length=100)
    base_custo: str = Field(min_length=10, max_length=2000)
    data: str = Field(min_length=4, max_length=40)
    fontes: list[Fonte] = Field(min_length=1, max_length=10)

class Edicao(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    setor: str
    comercio: Literal["B2C", "B2B", "HIBRIDO"]
    noticias: list[Artigo] = Field(max_length=10)
    analises: list[Artigo] = Field(max_length=10)
    produtos: list[Produto] = Field(min_length=1, max_length=10)


def serializar(e):
    return {"id": e.id, "rodada": e.rodada, "publicado": e.publicado, "dados": e.dados}


def _url_sem_rastreamento(url):
    partes = urlparse(url)
    consulta = urlencode([(k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True) if not k.lower().startswith("utm_")])
    return urlunparse(partes._replace(query=consulta, fragment=""))


def validar_fontes(dados, pesquisadas=None):
    urls = []
    for item in dados.noticias + dados.analises + dados.produtos:
        for fonte in item.fontes:
            if urlparse(fonte.url).scheme != "https" or not urlparse(fonte.url).hostname:
                raise HTTPException(422, "As fontes precisam ter URLs HTTPS válidas.")
            urls.append(fonte.url)
    if pesquisadas is not None and any(_url_sem_rastreamento(url) not in {_url_sem_rastreamento(u) for u in pesquisadas} for url in urls):
        raise HTTPException(502, "A pesquisa não confirmou todas as fontes; nenhuma edição foi salva.")
    if len({p.id for p in dados.produtos}) != len(dados.produtos):
        raise HTTPException(422, "Os códigos dos produtos devem ser únicos.")

@router.get("/api/professor/turmas/{turma_id}/mercado")
def listar(turma_id:int, db:Session=Depends(get_db), usuario:Usuario=Depends(exigir_professor)):
    _turma_do_professor(db,turma_id,usuario)
    return {"setores":SETORES,"edicoes":[serializar(e) for e in db.query(ConteudoMercado).filter_by(turma_id=turma_id).order_by(ConteudoMercado.id.desc()).all()]}

@router.post("/api/professor/turmas/{turma_id}/mercado/pesquisar")
def pesquisar(turma_id:int, dados:Pesquisa, db:Session=Depends(get_db), usuario:Usuario=Depends(exigir_professor)):
    turma=_turma_do_professor(db,turma_id,usuario)
    rodada=turma.rodada_atual
    if turma.status != StatusTurma.ABERTA: raise HTTPException(409,"Turma encerrada.")
    instrucoes='''Pesquise na web dados atuais do mercado brasileiro do setor informado. Não invente notícias, datas, URLs ou custos. Produza exatamente as quantidades solicitadas. JSON: {setor,comercio,noticias:[{titulo,texto,data,fontes:[{titulo,url}]}],analises:[mesmo formato],produtos:[{id,nome,descricao,custo_unitario,unidade,base_custo,data,fontes:[{titulo,url}]}]}. id deve ser texto, custo_unitario deve ser número em BRL, sem símbolos ou separadores locais. Use somente URLs que aparecem nas citações da ferramenta. Custo unitário em BRL: preço documentado de aquisição/atacado; nunca rotule preço de varejo como custo industrial. Se usar preço público de aquisição, explique isso em base_custo, sem afirmar custo de fabricação. Notícias factuais datadas e análises profissionais com distinção entre fato e interpretação. Não dê decisões prontas aos alunos, não mencione ferramentas de geração. No modo STARTUP, pesquise exclusivamente serviços digitais recorrentes com custo documentado por cliente/mês; nos demais modos, produtos físicos com custo por unidade. Evite marcas específicas quando possível, mas descreva produto comparável à fonte. Se não houver evidência suficiente não fabrique valores.'''
    bruto,fontes=gerar_json(instrucoes,{**dados.model_dump(),"modo_operacao":turma.modo_jogo,"data_consulta":datetime.now(timezone.utc).date().isoformat()},True,Edicao.model_json_schema())
    if isinstance(bruto, dict):
        nomes = {"noticias": "notícias", "analises": "análises", "produtos": "produtos com custo documentado"}
        faltas = [f"{nomes[k]}: {len(bruto[k])} de {getattr(dados,k)}" for k in nomes if isinstance(bruto.get(k),list) and len(bruto[k]) < getattr(dados,k)]
        if faltas:
            raise HTTPException(502, "A busca confirmou menos itens que o solicitado (" + "; ".join(faltas) + "). Nenhuma edição foi salva. Tente novamente ou reduza a quantidade.")
    try: edicao=Edicao.model_validate(bruto)
    except ValidationError as erro:
        campos = sorted({str(e["loc"][0]) for e in erro.errors() if e["loc"]})
        raise HTTPException(502,"A pesquisa retornou campos incompletos em " + ", ".join(campos) + ". Nenhuma edição foi salva. Tente novamente.") from None
    if len(edicao.noticias)!=dados.noticias or len(edicao.analises)!=dados.analises or len(edicao.produtos)!=dados.produtos:
        raise HTTPException(502,"A pesquisa não entregou as quantidades solicitadas.")
    validar_fontes(edicao,fontes)
    db.refresh(turma)
    if turma.rodada_atual != rodada: raise HTTPException(409,"A rodada avançou durante a pesquisa. Repita para a rodada atual.")
    e=ConteudoMercado(turma_id=turma_id,rodada=rodada,dados=edicao.model_dump())
    db.add(e);db.commit();db.refresh(e)
    return serializar(e)

@router.put("/api/professor/turmas/{turma_id}/mercado/{edicao_id}")
def revisar(turma_id:int, edicao_id:int,dados:Edicao, db:Session=Depends(get_db), usuario:Usuario=Depends(exigir_professor)):
    _turma_do_professor(db,turma_id,usuario)
    validar_fontes(dados)
    n=db.execute(update(ConteudoMercado).where(ConteudoMercado.id==edicao_id,ConteudoMercado.turma_id==turma_id,ConteudoMercado.publicado.is_(False)).values(dados=dados.model_dump())).rowcount
    if not n: raise HTTPException(409,"Edição inexistente ou já publicada; o histórico é preservado.")
    db.commit();return {"salvo":True}

@router.post("/api/professor/turmas/{turma_id}/mercado/{edicao_id}/publicar")
def publicar(turma_id:int,edicao_id:int, db:Session=Depends(get_db), usuario:Usuario=Depends(exigir_professor)):
    from ..equipes import bloquear_turma
    _turma_do_professor(db,turma_id,usuario)
    turma=bloquear_turma(db,turma_id)
    e=db.get(ConteudoMercado,edicao_id)
    if not e or e.turma_id!=turma_id: raise HTTPException(404,"Edição não encontrada.")
    if e.publicado: return serializar(e)
    if e.rodada!=turma.rodada_atual or turma.status!=StatusTurma.ABERTA: raise HTTPException(409,"Só é possível publicar na rodada aberta.")
    if db.query(ConteudoMercado).filter_by(turma_id=turma_id,rodada=e.rodada,publicado=True).first(): raise HTTPException(409,"Esta rodada já tem edição publicada.")
    e.publicado=True;db.commit();return serializar(e)

@router.get("/api/aluno/empresas/{empresa_id}/mercado-real")
def mercado_aluno(empresa_id:int,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_aluno)):
    empresa=_empresa_do_aluno(db,empresa_id,usuario)
    edicoes=db.query(ConteudoMercado).filter(ConteudoMercado.turma_id==empresa.turma_id,ConteudoMercado.publicado.is_(True),ConteudoMercado.rodada<=empresa.turma.rodada_atual).order_by(ConteudoMercado.rodada.desc()).all()
    return {"edicoes":[serializar(e) for e in edicoes]}

@router.post("/api/professor/turmas/{turma_id}/empresas/{empresa_id}/relatorio-empresarial/{rodada}")
def gerar_relatorio(turma_id:int,empresa_id:int,rodada:int,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_professor)):
    turma=_turma_do_professor(db,turma_id,usuario)
    empresa=next((e for e in turma.empresas if e.id==empresa_id),None)
    if not empresa: raise HTTPException(404,"Empresa não encontrada.")
    antigo=db.query(RelatorioEmpresarial).filter_by(empresa_id=empresa_id,rodada=rodada).first()
    if antigo: return {"texto":antigo.texto}
    resultado=next((r for r in empresa.resultados if r.rodada==rodada),None)
    if not resultado: raise HTTPException(409,"A rodada ainda não foi encerrada.")
    decisao=next((d for d in empresa.decisoes if d.rodada==rodada),None)
    dados=_rodada(empresa,resultado,decisao)
    if not dados.get("balanco"):
        from ..serializacao import resultado as serializar_resultado
        dados["balanco_basico"] = serializar_resultado(resultado)["balanco_basico"]
    dados.pop("participacao",None)
    dados["plano_marketing"]=(decisao.plano_comercial if decisao else None)
    if dados.get("decisao"):
        dados["decisao"].pop("aprovacoes", None)
    dados["historico"]=[{"rodada":r.rodada,"receita":r.receita,"lucro":r.lucro_liquido,"caixa":r.caixa_final} for r in empresa.resultados if r.rodada<rodada]
    bruto,_=gerar_json('''Redija um relatório empresarial em português com tom frio, objetivo e profissional. JSON {texto:string}. Use apenas os dados fornecidos, não invente indicadores nem atribua causalidade não comprovada. Inclua resultado comercial, DRE, fluxo de caixa, balanço quando disponível, riscos e comparação histórica. Discuta decisões sem escolher a próxima decisão pela equipe. Não mencione IA, ferramentas, professor ou avaliações pedagógicas. Não trate plano comercial como executado se os dados não comprovam sua execução. Não exponha dados pessoais. Até 8000 caracteres.''',dados)
    texto=bruto.get("texto") if isinstance(bruto,dict) else None
    if not isinstance(texto,str) or not 30<=len(texto)<=24000: raise HTTPException(502,"Relatório inválido.")
    from sqlalchemy.exc import IntegrityError
    db.add(RelatorioEmpresarial(empresa_id=empresa_id,rodada=rodada,texto=texto))
    try: db.commit()
    except IntegrityError:
        db.rollback()
        existente=db.query(RelatorioEmpresarial).filter_by(empresa_id=empresa_id,rodada=rodada).first()
        if existente: return {"texto":existente.texto}
        raise
    return {"texto":texto}

@router.get("/api/aluno/empresas/{empresa_id}/relatorios-empresariais")
def relatorios(empresa_id:int,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_aluno)):
    _empresa_do_aluno(db,empresa_id,usuario)
    return [{"rodada":r.rodada,"texto":r.texto} for r in db.query(RelatorioEmpresarial).filter_by(empresa_id=empresa_id).order_by(RelatorioEmpresarial.rodada.desc()).all()]

@router.get("/api/educacao/campanhas")
def campanhas():
    from ..catalogo_campanhas import catalogo
    return {"midias":catalogo(),"observacao":"Tabela de custos da simulação. Quantidade × preço unitário determina o investimento. Valores não são cotações comerciais atuais. CPM corresponde a um lote de mil impressões; CPC, a um clique."}


def validar_plano(db,empresa,dados):
    from math import isclose
    from ..catalogo_campanhas import catalogo
    plano=dados.plano_comercial
    if plano is None:
        if any(d.plano_comercial for d in empresa.decisoes) or db.query(ConteudoMercado).filter(ConteudoMercado.turma_id==empresa.turma_id,ConteudoMercado.publicado.is_(True),ConteudoMercado.rodada<=empresa.turma.rodada_atual).first():
            raise HTTPException(422,"Escolha o produto e complete o mix de marketing antes de enviar.")
        return
    e=db.get(ConteudoMercado,plano.edicao_id)
    if not e or e.turma_id!=empresa.turma_id or not e.publicado or e.rodada>empresa.turma.rodada_atual:
        raise HTTPException(422,"Escolha um produto de uma edição publicada pelo sistema.")
    produto=next((p for p in e.dados["produtos"] if p["id"]==plano.produto_id),None)
    if not produto: raise HTTPException(422,"Produto indisponível.")
    anterior=max((d for d in empresa.decisoes if d.plano_comercial and d.rodada<empresa.turma.rodada_atual),key=lambda d:d.rodada,default=None)
    if empresa.turma.modo_jogo=="TRADICIONAL" and anterior and (anterior.plano_comercial["produto_id"],anterior.plano_comercial["edicao_id"])!=(plano.produto_id,plano.edicao_id):
        raise HTTPException(422,"Mantenha o produto no modo industrial: estoques e máquinas estão vinculados à operação original.")
    plano.custo_unitario=produto["custo_unitario"]
    plano.produto_nome=produto["nome"]
    midias={m["id"]:m for m in catalogo()}
    if len({m.id for m in plano.midias})!=len(plano.midias): raise HTTPException(422,"Mídias duplicadas.")
    if any(m.id not in midias for m in plano.midias): raise HTTPException(422,"Mídia inválida.")
    total=round(sum(midias[m.id]["preco_unitario"]*m.quantidade for m in plano.midias),2)
    if not isclose(total,dados.marketing,abs_tol=.01): raise HTTPException(422,"Marketing deve corresponder ao total das mídias escolhidas.")
    if dados.simulacao:
        dados.simulacao.marketing_digital=round(sum(midias[m.id]["preco_unitario"]*m.quantidade for m in plano.midias if midias[m.id]["categoria"] in ("Digital","Display")),2)
        dados.simulacao.canal="DISTRIBUIDOR" if "ATACADO" in plano.canais else "DIGITAL" if any(c in plano.canais for c in ("ECOMMERCE","MARKETPLACE")) else "DIRETO"
        dados.simulacao.posicionamento="CUSTO" if plano.posicionamento=="PRECO" else "DIFERENCIACAO"
    for chave,valor in plano.estrategias.items():
        if chave not in ("SWOT","PORTER","BCG","PESTEL","DEMOGRAFICA","GEOGRAFICA","PSICOGRAFICA","COMPORTAMENTAL") or len(valor)>12000:
            raise HTTPException(422,"Análise estratégica inválida.")


def preparar_relatorios_automaticos(turma_id, professor_id, rodada):
    import os
    import logging
    from ..database import SessionLocal
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("SEMPREHUB_OPENAI_API_KEY")):
        return
    with SessionLocal() as db:
        usuario=db.get(Usuario,professor_id)
        turma=_turma_do_professor(db,turma_id,usuario)
        ids=[e.id for e in turma.empresas]
        for empresa_id in ids:
            try:
                gerar_relatorio(turma_id,empresa_id,rodada,db,usuario)
            except Exception:
                db.rollback()
                logging.getLogger(__name__).warning("Relatório pendente para empresa %s, rodada %s; pode ser repetido no painel docente.",empresa_id,rodada)
