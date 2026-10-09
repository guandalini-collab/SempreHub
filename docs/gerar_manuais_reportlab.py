#!/usr/bin/env python3
"""Gera os manuais de aluno e professor com ReportLab, sem serviços externos.
Uso: python3 docs/gerar_manuais_reportlab.py (requer reportlab e pillow).
O manual de mídias possui geração própria em gerar_manuais.py.
"""
from pathlib import Path
import html
import re
import shutil
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from PIL import Image as PILImage
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
OUT = DOCS / 'gerados'
PUBLIC = ROOT / 'frontend/public/manuais'
NAVY = colors.HexColor('#0B2545')
GOLD = colors.HexColor('#C5A059')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Corpo', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=7, textColor=NAVY))
styles.add(ParagraphStyle('Titulo', parent=styles['Corpo'], fontSize=25, leading=29, spaceAfter=18, keepWithNext=True))
styles.add(ParagraphStyle('Capitulo', parent=styles['Corpo'], fontSize=16, leading=20, spaceBefore=16, spaceAfter=9, keepWithNext=True))
styles.add(ParagraphStyle('Subtitulo', parent=styles['Corpo'], fontSize=12, leading=16, spaceBefore=10, keepWithNext=True))
styles.add(ParagraphStyle('Legenda', parent=styles['Corpo'], fontSize=8, leading=11, textColor=colors.HexColor('#64748b'), spaceAfter=12))

def inline(text):
    text=html.escape(text)
    text=re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text=re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
    return text

def build(stem):
    story=[]; markup=[]
    for block in re.split(r'\n\s*\n', (DOCS/f'{stem}.md').read_text()):
        block=block.strip()
        if not block: continue
        match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',block)
        if match:
            caption,relative=match.groups(); path=DOCS/relative
            with PILImage.open(path) as im: w,h=im.size
            scale=min((A4[0]-90)/w,(430 if "matriz-bcg" in relative else 310)/h)
            figure=[Image(str(path),width=w*scale,height=h*scale),Spacer(1,5),Paragraph(inline(caption),styles['Legenda'])]
            if story and isinstance(story[-1],Paragraph) and story[-1].style.name in ('Titulo','Capitulo','Subtitulo'):
                figure.insert(0,story.pop())
            story.append(KeepTogether(figure))
            markup.append(f'<figure><img src="../{html.escape(relative)}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>')
        elif block.startswith('#'):
            level=len(block)-len(block.lstrip('#')); text=block[level:].strip()
            style={1:'Titulo',2:'Capitulo'}.get(level,'Subtitulo')
            story.append(Paragraph(inline(text),styles[style]));markup.append(f'<h{level}>{inline(text)}</h{level}>')
        else:
            lines=block.splitlines()
            if all(re.match(r'^(\d+\. |\- )',line) for line in lines):
                markup.append('<ol>' if lines[0][0].isdigit() else '<ul>')
                for line in lines:
                    story.append(Paragraph(inline(line),styles['Corpo']))
                    markup.append('<li>'+inline(re.sub(r'^(\d+\. |\- )','',line))+'</li>')
                markup.append('</ol>' if lines[0][0].isdigit() else '</ul>')
            else:
                text=' '.join(lines);story.append(Paragraph(inline(text),styles['Corpo']));markup.append('<p>'+inline(text)+'</p>')
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(GOLD);canvas.line(45,39,A4[0]-45,39)
        canvas.setFillColor(NAVY);canvas.setFont('Helvetica',8)
        canvas.drawString(45,27,'SempreHub | Manual '+('do aluno' if stem.endswith('aluno') else 'do professor')+' | versão 2.1')
        canvas.drawRightString(A4[0]-45,27,str(doc.page));canvas.restoreState()
    pdf=OUT/f'{stem}.pdf'
    SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=42,bottomMargin=53,title='SempreHub - '+stem.replace('-',' '),author='SempreHub').build(story,onFirstPage=footer,onLaterPages=footer)
    (OUT/f'{stem}.html').write_text('<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Manual SempreHub</title><link rel="stylesheet" href="../manual.css"></head><body>'+ '\n'.join(markup)+'</body></html>')
    shutil.copyfile(pdf,PUBLIC/pdf.name)
    print(f'Gerado {pdf.relative_to(ROOT)} ({pdf.stat().st_size:,} bytes)')

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    for stem in ['manual-aluno','manual-professor']:build(stem)
