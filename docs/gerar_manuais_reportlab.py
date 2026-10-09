#!/usr/bin/env python3
"""Gera três livros em PDF com marca, capa, sumário navegável e paginação.
Requer ReportLab e Pillow. Uso: python3 docs/gerar_manuais_reportlab.py.
"""
from pathlib import Path
import html,re,shutil,base64
from io import BytesIO
from xml.etree import ElementTree
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether, PageBreak, CondPageBreak, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage, ImageChops
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs';OUT=DOCS/'gerados';PUBLIC=ROOT/'frontend/public/manuais'
NAVY=colors.HexColor('#0B2545');GOLD=colors.HexColor('#D9851E');INK=colors.HexColor('#24364b')
CYAN=colors.HexColor('#0AADBF');ROYAL=colors.HexColor('#034AA6')
LOGO=DOCS/'assets/semprehub-oficial.svg'
# Preserve the supplied SVG verbatim. Its artwork is an embedded PNG, so place
# those original bytes without resampling. Clip only the blank artwork margins
# on the PDF canvas; the source SVG and the founder's image remain unchanged.
svg=ElementTree.parse(LOGO).getroot()
embedded=svg.find('{http://www.w3.org/2000/svg}image')
if embedded is None:raise ValueError('O SVG oficial exige um renderizador vetorial; não substituir por outra marca.')
href=embedded.get('{http://www.w3.org/1999/xlink}href') or embedded.get('href')
if not href or not href.startswith('data:image/png;base64,'):raise ValueError('Imagem incorporada não suportada no SVG oficial.')
logo_bytes=base64.b64decode(href.split(',',1)[1]);logo_image=PILImage.open(BytesIO(logo_bytes)).convert('RGB')
logo_width,logo_height=logo_image.size
bounds=ImageChops.difference(logo_image,PILImage.new('RGB',logo_image.size,'white')).convert('L').point(lambda value:255 if value>20 else 0).getbbox()
if not bounds:raise ValueError('Marca oficial sem conteúdo visível.')
left,top,right,bottom=bounds
logo_bounds=(max(0,left-12),max(0,top-12),min(logo_width,right+12),min(logo_height,bottom+12))
logo_reader=ImageReader(BytesIO(logo_bytes))

def draw_logo(canvas,x,y,width):
 left,top,right,bottom=logo_bounds
 scale=width/(right-left);height=(bottom-top)*scale
 canvas.saveState();clip=canvas.beginPath();clip.rect(x,y,width,height);canvas.clipPath(clip,stroke=0)
 canvas.drawImage(logo_reader,x-left*scale,y-(logo_height-bottom)*scale,width=logo_width*scale,height=logo_height*scale)
 canvas.restoreState()

styles=getSampleStyleSheet()
for name,options in {
 'Corpo':dict(fontSize=10.5,leading=15,spaceAfter=9,textColor=INK,allowWidows=0,allowOrphans=0),
 'Capitulo':dict(fontSize=20,leading=25,spaceAfter=16,textColor=NAVY,keepWithNext=True),
 'Subtitulo':dict(fontSize=13,leading=18,spaceBefore=14,spaceAfter=8,textColor=NAVY,keepWithNext=True),
 'Legenda':dict(fontSize=8,leading=11,spaceAfter=12,textColor=colors.HexColor('#64748b')),
 'Celula':dict(fontSize=8.5,leading=12,wordWrap='CJK',spaceAfter=0,textColor=INK),
 'Capa':dict(fontSize=36,leading=43,textColor=NAVY,spaceAfter=20),
 'CapaTexto':dict(fontSize=12,leading=19,textColor=INK,spaceAfter=14),
 'Sumario':dict(fontSize=10.5,leading=14,leftIndent=0,firstLineIndent=0,spaceBefore=5,textColor=NAVY),
}.items():styles.add(ParagraphStyle(name,fontName='Helvetica-Bold' if name in ('Capa','Capitulo','Subtitulo') else 'Helvetica',**options))

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
 if stem != "manual-midias":
  from manual_abnt import build as build_abnt
  return build_abnt(stem)
 title={'manual-aluno':'Manual do aluno','manual-professor':'Manual do professor','manual-midias':'Manual de mídias e campanhas'}[stem]
 subtitle={'manual-aluno':'Aprenda a decidir, acompanhe sua empresa e transforme resultados em aprendizagem.','manual-professor':'Prepare a turma, conduza as rodadas e acompanhe a aprendizagem das equipes.','manual-midias':'Planeje público, mídia, produção e orçamento antes de contratar uma campanha.'}[stem]
 audience={'manual-aluno':'ENSINO MÉDIO E SUPERIOR','manual-professor':'PROFESSORES, COORDENADORES E FACILITADORES','manual-midias':'PLANEJAMENTO DE MÍDIAS E CAMPANHAS'}[stem]
 story=[Spacer(1,225),Paragraph(title,styles['Capa']),Paragraph(subtitle,styles['CapaTexto']),PageBreak()]

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
  width,height=A4
  if doc.page==1:
   canvas.setFillColor(colors.white);canvas.rect(0,0,width,height,fill=1,stroke=0)
   draw_logo(canvas,50,height-181,365)
   canvas.setStrokeColor(CYAN);canvas.setLineWidth(2);canvas.line(50,height-207,145,height-207)
   canvas.setFillColor(ROYAL);canvas.setFont('Helvetica-Bold',9)
   canvas.drawString(50,height-234,'SIMULADOR DE EMPREENDEDORISMO')
   canvas.setFillColor(INK);canvas.setFont('Helvetica-Bold',8.5);canvas.drawString(50,294,audience)
   canvas.setFillColor(colors.HexColor('#64748b'));canvas.setFont('Helvetica',8);canvas.drawString(50,268,'AUTOR E FUNDADOR')
   canvas.setFillColor(NAVY);canvas.setFont('Helvetica-Bold',15);canvas.drawString(50,244,'Prof. Guandalini')
   canvas.setFillColor(NAVY);canvas.rect(0,0,width,190,fill=1,stroke=0)
   canvas.setFillColor(CYAN);canvas.rect(50,146,44,3,fill=1,stroke=0)
   canvas.setFillColor(colors.white);canvas.setFont('Helvetica-Bold',19)
   canvas.drawString(50,112,'Conhecimento que se transforma')
   canvas.drawString(50,85,'em decisões e aprendizagem.')
   canvas.setFillColor(colors.HexColor('#b8d9e5'));canvas.setFont('Helvetica',9)
   canvas.drawString(50,38,'MANUAL INSTITUCIONAL  |  EDIÇÃO 3.1  |  OUTUBRO DE 2026')
  else:
   draw_logo(canvas,50,height-43,93)
   canvas.setFillColor(NAVY);canvas.setFont('Helvetica',9);canvas.drawRightString(width-50,height-31,title)
   canvas.setStrokeColor(colors.HexColor('#d5e3eb'));canvas.setLineWidth(.6);canvas.line(50,height-55,width-50,height-55)
   canvas.line(50,40,width-50,40)
   canvas.setFillColor(INK);canvas.setFont('Helvetica',7.5)
   canvas.drawString(50,26,'Conceito e marca: Professor Guandalini')
   canvas.setFillColor(colors.HexColor('#64748b'));canvas.drawRightString(width-78,26,'SempreHub | Edição 3.1')
   canvas.setFillColor(NAVY);canvas.setFont('Helvetica-Bold',9);canvas.drawRightString(width-50,26,f'{doc.page-1:02d}')
  canvas.restoreState()

 pdf=OUT/f'{stem}.pdf';doc=Livro(str(pdf),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=75,bottomMargin=58,title='SempreHub - '+title,author='Prof. Guandalini')
 doc.multiBuild(story,onFirstPage=page,onLaterPages=page)
 (OUT/f'{stem}.html').write_text('<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><title>'+title+'</title><link rel="stylesheet" href="../manual.css"></head><body><h1>'+title+'</h1>'+ '\n'.join(markup)+'</body></html>')
 shutil.copyfile(pdf,PUBLIC/pdf.name);print(f'Gerado {pdf.relative_to(ROOT)} ({pdf.stat().st_size:,} bytes)')

if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
 import sys
 stems=['manual-midias'] if '--midias' in sys.argv else ['manual-aluno','manual-professor']
 for stem in stems:build(stem)
