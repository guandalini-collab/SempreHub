"""Apresentação ABNT adaptada a manuais institucionais; sem alterações no simulador.
A4, margens 3/2 cm, corpo 12, entrelinha 1,5, seções e sumário navegável.
"""
from pathlib import Path
from io import BytesIO
import html,re,shutil
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,KeepTogether,Table,TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from PIL import Image as PILImage
from pypdf import PdfReader,PdfWriter,Transformation
ROOT=Path(__file__).resolve().parents[1];DOCS=ROOT/'docs';OUT=DOCS/'gerados';PUBLIC=ROOT/'frontend/public/manuais'
LEFT=TOP=3*cm;RIGHT=BOTTOM=2*cm;WIDTH=A4[0]-LEFT-RIGHT
BLUE=colors.HexColor('#013B9D');CYAN=colors.HexColor('#06A9BF');GOLD=colors.HexColor('#DF9317')
BLACK=colors.black
STYLES={
 'Body':ParagraphStyle('Body',fontName='Helvetica',fontSize=12,leading=18,textColor=BLACK,alignment=4,spaceAfter=12,allowWidows=0,allowOrphans=0),
 'List':ParagraphStyle('List',fontName='Helvetica',fontSize=12,leading=18,textColor=BLACK,spaceAfter=8,leftIndent=12,firstLineIndent=-12,allowWidows=0,allowOrphans=0),
 'Chapter':ParagraphStyle('Chapter',fontName='Helvetica-Bold',fontSize=12,leading=18,textColor=BLACK,spaceAfter=18,keepWithNext=True),
 'Sub':ParagraphStyle('Sub',fontName='Helvetica-Bold',fontSize=12,leading=18,textColor=BLACK,spaceBefore=18,spaceAfter=18,keepWithNext=True),
 'Small':ParagraphStyle('Small',fontName='Helvetica',fontSize=10,leading=12,textColor=BLACK,spaceAfter=12,allowWidows=0,allowOrphans=0),
 'Cell':ParagraphStyle('Cell',fontName='Helvetica',fontSize=10,leading=12,textColor=BLACK,spaceAfter=0),
 'Center':ParagraphStyle('Center',fontName='Helvetica',fontSize=12,leading=18,textColor=BLACK,alignment=1,spaceAfter=18),
 'TOC':ParagraphStyle('TOC',fontName='Helvetica',fontSize=12,leading=18,textColor=BLACK,spaceBefore=8,leftIndent=0,firstLineIndent=0,rightIndent=25),
 'TOCSub':ParagraphStyle('TOCSub',fontName='Helvetica',fontSize=12,leading=18,textColor=BLACK,spaceBefore=5,leftIndent=16,firstLineIndent=0,rightIndent=25),
}
def inline(text):
 text=html.escape(text.strip()).replace('—','-').replace('–','-')
 text=re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)',lambda m:f'<link href="{html.escape(html.unescape(m[2]),quote=True)}">{m[1]}</link>',text)
 text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
 text=re.sub(r'`(.+?)`',r'\1',text)
 return text
class Manual(SimpleDocTemplate):
 def beforeDocument(self):self.text_start=None
 def afterFlowable(self,f):
  if not isinstance(f,Paragraph):return
  if getattr(f,'starts_text',False) and self.text_start is None:
   self.text_start=self.page
   self.canv.saveState();self.canv.setFillColor(BLACK);self.canv.setFont('Helvetica',10)
   self.canv.drawRightString(A4[0]-RIGHT,A4[1]-2*cm,str(self.page-1));self.canv.restoreState()
  if hasattr(f,'bookmark'):
   self.canv.bookmarkPage(f.bookmark);self.canv.addOutlineEntry(f.getPlainText(),f.bookmark,f.outline_level,False)
   if getattr(f,'toc_level',None) is not None:self.notify('TOCEntry',(f.toc_level,f.getPlainText(),self.page-1,f.bookmark))
def build(stem):
 title={'manual-aluno':'Manual do aluno','manual-professor':'Manual do professor'}[stem]
 audience='Ensino Médio e Superior' if stem=='manual-aluno' else 'Professores, coordenadores e facilitadores'
 subtitle='Navegação, decisões e aprendizagem empresarial' if stem=='manual-aluno' else 'Gestão de turmas, rodadas e avaliação pedagógica'
 source=(DOCS/f'{stem}.md').read_text()
 blocks=[b.strip() for b in re.split(r'\n\s*\n',source) if b.strip()]
 covertitle=ParagraphStyle('CoverTitle',parent=STYLES['Center'],fontName='Helvetica-Bold',textColor=BLUE)
 story=[Spacer(1,145),Paragraph('PROFESSOR GUANDALINI',STYLES['Center']),Spacer(1,40),Paragraph('SEMPREHUB',covertitle),Paragraph(title.upper(),covertitle),Paragraph(subtitle,STYLES['Center']),Spacer(1,36),Paragraph(audience,STYLES['Center']),Paragraph('Autor e Fundador: Professor Guandalini',STYLES['Center']),Spacer(1,30),Paragraph('Edição 3.2<br/>2026',STYLES['Center']),PageBreak()]
 story += [Paragraph('PROFESSOR GUANDALINI',STYLES['Center']),Spacer(1,120),Paragraph('SEMPREHUB',covertitle),Paragraph(title.upper(),covertitle),Paragraph(subtitle,STYLES['Center']),Spacer(1,45)]
 nature=ParagraphStyle('Nature',parent=STYLES['Body'],leading=12,leftIndent=WIDTH/2,alignment=4)
 story += [Paragraph('Manual institucional do SempreHub destinado a '+audience.lower()+'. Orienta o uso pedagógico do simulador e a compreensão das decisões empresariais. Conceito, marca e autoria: Professor Guandalini.',nature),Spacer(1,70),Paragraph('Edição 3.2<br/>2026',STYLES['Center']),PageBreak()]
 toc=TableOfContents();toc.levelStyles=[STYLES['TOC'],STYLES['TOCSub']];toc.dotsMinLevel=0
 chapter=sub=figure=tablecount=0;toc_added=False;lastheading='';markup=[]
 for block in blocks:
  if block=='---' or block.startswith('<') or block.startswith('# ') or block.startswith('Versão '):continue
  if block.startswith('##'):
   level=len(block)-len(block.lstrip('#'));text=block[level:].strip();plain=re.sub(r'^\d+\.\s*','',text)
   if level==2:
    if plain=='Carta do Fundador':
     p=Paragraph(plain,ParagraphStyle('LetterHeading',parent=STYLES['Chapter'],alignment=1));p.bookmark='carta';p.outline_level=0;p.toc_level=None;story.append(p)
    else:
     if not toc_added:
      if stem=='manual-aluno' or stem=='manual-professor':story.append(PageBreak())
      story += [Paragraph('SUMÁRIO',ParagraphStyle('TOCHeading',parent=STYLES['Chapter'],alignment=1)),toc,PageBreak()];toc_added=True
     else:story.append(PageBreak())
     chapter+=1;sub=0
     p=Paragraph(f'{chapter} {inline(plain)}',STYLES['Chapter']);p.bookmark=f'section-{chapter}';p.outline_level=0;p.toc_level=0;p.starts_text=True;story.append(p)
   else:
    sub+=1;p=Paragraph(f'{chapter}.{sub} {inline(plain)}',STYLES['Sub']);p.bookmark=f'section-{chapter}-{sub}';p.outline_level=1;p.toc_level=1;story.append(p)
   lastheading=plain;markup.append(f'<h{level}>{inline(plain)}</h{level}>');continue
  match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',block)
  if match:
   caption,rel=match.groups();path=DOCS/rel
   with PILImage.open(path) as im:w,h=im.size
   scale=min(WIDTH/w,390/h);figure+=1
   story.append(KeepTogether([Paragraph(f'Figura {figure} - {inline(caption)}',STYLES['Small']),Image(str(path),width=w*scale,height=h*scale),Spacer(1,6),Paragraph('Fonte: SempreHub, acervo do Professor Guandalini (2026). Tela com dados ilustrativos.',STYLES['Small'])]));markup.append(f'<figure><img src="../{rel}"><figcaption>{inline(caption)}</figcaption></figure>');continue
  if block.startswith('|'):
   rows=[]
   for line in block.splitlines():
    if re.match(r'^\|[\s:|-]+\|?$',line):continue
    cells=[c.strip() for c in line.strip('|').split('|')];rows.append([Paragraph(inline(c),STYLES['Cell']) for c in cells])
   count=max(map(len,rows));rows=[r+[Paragraph('',STYLES['Cell'])]*(count-len(r)) for r in rows];tablecount+=1
   table=Table(rows,colWidths=[WIDTH/count]*count,repeatRows=1,hAlign='LEFT')
   table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,0),.7,BLACK),('LINEBELOW',(0,0),(-1,0),.6,BLACK),('LINEBELOW',(0,-1),(-1,-1),.7,BLACK),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
   story += [Paragraph(f'Tabela {tablecount} - {inline(lastheading)}',STYLES['Small']),table,Spacer(1,6),Paragraph('Fonte: SempreHub, acervo do Professor Guandalini (2026).',STYLES['Small'])];continue
  lines=block.splitlines()
  if all(re.match(r'^(\d+\. |\- )',line) for line in lines):
   story += [Paragraph(inline(line),STYLES['List']) for line in lines]
  else:story.append(Paragraph(inline(' '.join(lines)),STYLES['Body']))
  markup.append('<p>'+inline(' '.join(lines))+'</p>')
 # The source logo is merged as vector PDF after ReportLab pagination; this
 # preserves CorelDRAW paths, the white background, and gradient fills.
 def page(canvas,doc):
  canvas.saveState();w,h=A4
  if doc.page==1:
   canvas.setStrokeColor(CYAN);canvas.setLineWidth(2);canvas.line(LEFT,h-202,w-RIGHT,h-202)
   canvas.setFillColor(GOLD);canvas.rect(LEFT,95,WIDTH,3,fill=1,stroke=0)
  else:
   canvas.setFillColor(BLUE);canvas.setFont('Helvetica',8);canvas.drawRightString(w-RIGHT,h-68,title)
   canvas.setStrokeColor(CYAN);canvas.setLineWidth(.5);canvas.line(LEFT,h-73,w-RIGHT,h-73)
   canvas.setFont('Helvetica',8);canvas.setFillColor(BLUE);canvas.drawString(LEFT,35,'Conceito e marca: Professor Guandalini')
   canvas.drawRightString(w-RIGHT,35,'SempreHub | Edição 3.2')
   if doc.text_start is not None and doc.page>=doc.text_start:
    canvas.setFillColor(BLACK);canvas.setFont('Helvetica',10);canvas.drawRightString(w-RIGHT,h-2*cm,str(doc.page-1))
  canvas.restoreState()
 OUT.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
 raw=BytesIO();doc=Manual(raw,pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,topMargin=TOP,bottomMargin=BOTTOM,title='SempreHub - '+title,author='Professor Guandalini')
 doc.multiBuild(story,onFirstPage=page,onLaterPages=page)
 reader=PdfReader(BytesIO(raw.getvalue()));logo=PdfReader(DOCS/'assets/semprehub-fundo-branco.pdf').pages[0];writer=PdfWriter();writer.clone_document_from_reader(reader)
 for index,p in enumerate(writer.pages):
  width=WIDTH if index==0 else 75
  scale=width/float(logo.mediabox.width);height=float(logo.mediabox.height)*scale
  y=A4[1]-TOP-height if index==0 else A4[1]-69
  p.merge_transformed_page(logo,Transformation().scale(scale).translate(LEFT,y),over=True,expand=False)
 pdf=OUT/f'{stem}.pdf'
 with pdf.open('wb') as f:writer.write(f)
 (OUT/f'{stem}.html').write_text('<!doctype html><html lang="pt-BR"><meta charset="UTF-8"><title>'+title+'</title><link rel="stylesheet" href="../manual.css"><body><h1>'+title+'</h1>'+ '\n'.join(markup)+'</body></html>')
 shutil.copyfile(pdf,PUBLIC/pdf.name);print(f'{stem}: {len(writer.pages)} páginas, edição 3.2, marca vetorial e formatação ABNT adaptada.')
