#!/usr/bin/env python3
"""Gera três livros em PDF com marca, capa, sumário navegável e paginação.
Requer ReportLab e Pillow. Uso: python3 docs/gerar_manuais_reportlab.py.
"""
from pathlib import Path
import html,re,shutil
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether, PageBreak, CondPageBreak, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs';OUT=DOCS/'gerados';PUBLIC=ROOT/'frontend/public/manuais'
NAVY=colors.HexColor('#0B2545');GOLD=colors.HexColor('#C5A059');INK=colors.HexColor('#24364b')
styles=getSampleStyleSheet()
for name,options in {
 'Corpo':dict(fontSize=10.5,leading=15,spaceAfter=9,textColor=INK,allowWidows=0,allowOrphans=0),
 'Capitulo':dict(fontSize=20,leading=25,spaceAfter=16,textColor=NAVY,keepWithNext=True),
 'Subtitulo':dict(fontSize=13,leading=18,spaceBefore=14,spaceAfter=8,textColor=NAVY,keepWithNext=True),
 'Legenda':dict(fontSize=8,leading=11,spaceAfter=12,textColor=colors.HexColor('#64748b')),
 'Celula':dict(fontSize=8.5,leading=12,wordWrap='CJK',spaceAfter=0,textColor=INK),
 'Capa':dict(fontSize=30,leading=37,textColor=colors.white,spaceAfter=18),
 'CapaTexto':dict(fontSize=12,leading=18,textColor=colors.white,spaceAfter=14),
 'Sumario':dict(fontSize=10.5,leading=14,leftIndent=0,firstLineIndent=0,spaceBefore=5,textColor=NAVY),
}.items():styles.add(ParagraphStyle(name,fontName='Helvetica',**options))

def inline(text):
 text=html.escape(text.strip()).replace('—','-').replace('–','-')
 text=re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)',lambda m:f'<link href="{html.escape(html.unescape(m[2]),quote=True)}" color="#0B2545">{m[1]}</link>',text)
 text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
 text=re.sub(r'`(.+?)`',r'<font name="Courier">\1</font>',text)
 return text

class Livro(SimpleDocTemplate):
 def afterFlowable(self,flowable):
  if isinstance(flowable,Paragraph) and flowable.style.name=='Capitulo':
   title=flowable.getPlainText();key=flowable._bookmark
   self.canv.bookmarkPage(key);self.canv.addOutlineEntry(title,key,0,False)
   self.notify('TOCEntry',(0,title,self.page-1,key))

def build(stem):
 title={'manual-aluno':'Manual do aluno','manual-professor':'Manual do professor','manual-midias':'Manual de mídias e campanhas'}[stem]
 subtitle={'manual-aluno':'Aprenda a decidir, acompanhe sua empresa e transforme resultados em aprendizagem.','manual-professor':'Prepare a turma, conduza as rodadas e acompanhe a aprendizagem das equipes.','manual-midias':'Planeje público, mídia, produção e orçamento antes de contratar uma campanha.'}[stem]
 story=[Spacer(1,250),Paragraph(title,styles['Capa']),Paragraph(subtitle,styles['CapaTexto']),Paragraph('Autor e Fundador: Prof. Guandalini',styles['CapaTexto']),Paragraph('Ensino Médio e Superior' if stem=='manual-aluno' else 'Professores, coordenadores e facilitadores' if stem=='manual-professor' else 'Guia de planejamento de campanhas',styles['CapaTexto']),Spacer(1,20),Paragraph('GUIA PRÁTICO ILUSTRADO<br/>Versão 3.0 | Outubro de 2026',styles['CapaTexto']),PageBreak()]
 toc=TableOfContents();toc.levelStyles=[styles['Sumario']]
 markup=[];chapter=0;first=True
 for block in re.split(r'\n\s*\n',(DOCS/f'{stem}.md').read_text()):
  block=block.strip()
  if not block or block=='---' or block.startswith('<') or block.startswith('# '):continue
  if block.startswith('Versão '):continue
  match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',block)
  if match:
   caption,relative=match.groups();path=DOCS/relative
   with PILImage.open(path) as im:w,h=im.size
   scale=min((A4[0]-100)/w,430/h)
   figura=[]
   if story and isinstance(story[-1],Paragraph) and story[-1].style.name in ('Capitulo','Subtitulo'):figura.append(story.pop())
   story.append(KeepTogether(figura+[Image(str(path),width=w*scale,height=h*scale),Spacer(1,7),Paragraph(inline(caption),styles['Legenda'])]))
   markup.append(f'<figure><img src="../{html.escape(relative)}" alt="{html.escape(caption)}"><figcaption>{inline(caption)}</figcaption></figure>')
  elif block.startswith('##'):
   level=len(block)-len(block.lstrip('#'));text=block[level:].strip()
   if level==2:
    if stem=='manual-midias' and text.startswith('Fontes de preço'):story.append(PageBreak())
    if stem != 'manual-midias' and chapter < 3:
     if not first:story.append(PageBreak())
    elif chapter == (3 if stem != 'manual-midias' else 1):
     heading_toc=Paragraph('Sumário',ParagraphStyle('TituloSumario',parent=styles['Capitulo']))
     story += [PageBreak(),heading_toc,toc,PageBreak()]
    elif not first:story += [CondPageBreak(190),Spacer(1,16)]
    first=False;chapter+=1;heading=Paragraph(inline(text),styles['Capitulo']);heading._bookmark=f'capitulo-{chapter}';story.append(heading)
   else:story.append(Paragraph(inline(text),styles['Subtitulo']))
   markup.append(f'<h{level}>{inline(text)}</h{level}>')
  elif block.startswith('|'):
   rows=[]
   for line in block.splitlines():
    if re.match(r'^\|[\s:|-]+\|?$',line):continue
    cells=[c.strip() for c in line.strip('|').split('|')];rows.append([Paragraph(inline(c),styles['Celula']) for c in cells])
   if rows:
    count=len(rows[0]);rows=[row+[Paragraph('',styles['Celula'])]*(count-len(row)) for row in rows]
    table=Table(rows,colWidths=[(A4[0]-100)/count]*count,repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef5')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#dbe3ec')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story += [table,Spacer(1,10)]
    markup.append('<table>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in line.strip('|').split('|'))+'</tr>' for line in block.splitlines() if not re.match(r'^\|[\s:|-]+\|?$',line))+'</table>')
  else:
   lines=block.splitlines()
   if all(re.match(r'^(\d+\. |\- )',line) for line in lines):
    for line in lines:story.append(Paragraph(inline(line),styles['Corpo']))
    markup.append('<p>'+ '<br/>'.join(inline(line) for line in lines)+'</p>')
   else:
    text=' '.join(lines);story.append(Paragraph(inline(text),styles['Corpo']));markup.append('<p>'+inline(text)+'</p>')
 def page(canvas,doc):
  canvas.saveState()
  if doc.page==1:
   canvas.setFillColor(NAVY);canvas.rect(0,0,*A4,fill=1,stroke=0)
   canvas.setFillColor(GOLD);canvas.rect(0,0,14,A4[1],fill=1,stroke=0)
   canvas.setFillColor(colors.white);canvas.roundRect(50,A4[1]-227,177,177,12,fill=1,stroke=0)
   canvas.drawImage(str(ROOT/'frontend/src/assets/SempreHub.jpg'),58,A4[1]-219,width=161,height=161,preserveAspectRatio=True,mask='auto')
   canvas.setFillColor(GOLD);canvas.setFont('Helvetica-Bold',13);canvas.drawString(50,95,'SEMPREHUB')
   canvas.setFillColor(colors.white);canvas.setFont('Helvetica',10);canvas.drawString(50,75,'Ecossistema dinâmico de aceleração de negócios')
  else:
   canvas.setStrokeColor(GOLD);canvas.line(50,A4[1]-38,A4[0]-50,A4[1]-38)
   canvas.setFillColor(NAVY);canvas.setFont('Helvetica-Bold',9);canvas.drawString(50,A4[1]-29,'SempreHub')
   canvas.setFont('Helvetica',8);canvas.drawRightString(A4[0]-50,A4[1]-29,title)
   canvas.setStrokeColor(GOLD);canvas.line(50,39,A4[0]-50,39)
   canvas.setFillColor(NAVY);canvas.setFont('Helvetica',8);canvas.drawString(50,27,'Conceito SempreHub: Prof. Guandalini | Versão 3.0');canvas.drawRightString(A4[0]-50,27,str(doc.page-1))
  canvas.restoreState()
 pdf=OUT/f'{stem}.pdf';doc=Livro(str(pdf),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=60,bottomMargin=54,title='SempreHub - '+title,author='Prof. Guandalini')
 doc.multiBuild(story,onFirstPage=page,onLaterPages=page)
 (OUT/f'{stem}.html').write_text('<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><title>'+title+'</title><link rel="stylesheet" href="../manual.css"></head><body><h1>'+title+'</h1>'+ '\n'.join(markup)+'</body></html>')
 shutil.copyfile(pdf,PUBLIC/pdf.name);print(f'Gerado {pdf.relative_to(ROOT)} ({pdf.stat().st_size:,} bytes)')

if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
 for stem in ['manual-aluno','manual-professor','manual-midias']:build(stem)
