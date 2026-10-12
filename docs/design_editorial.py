"""Identidade editorial compartilhada. Logo e conteúdo contábil são preservados."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
ROOT=Path(__file__).resolve().parent
BLUE=colors.HexColor('#034AA6');ROYAL=colors.HexColor('#0762D9');CYAN=colors.HexColor('#0AADBF');GOLD=colors.HexColor('#D9851E');SOFT=colors.HexColor('#F2F2F2')

def capa(canvas,title,subtitle,audience,edition):
 w,h=A4;left=85;usable=w-142
 canvas.saveState();canvas.setFillColor(SOFT);canvas.rect(0,0,w,h,fill=1,stroke=0)
 canvas.setFillColor(BLUE);canvas.rect(0,h-12,w,12,fill=1,stroke=0)
 canvas.setStrokeColor(CYAN);canvas.setLineWidth(2);canvas.line(left,h-150,left+80,h-150)
 canvas.setFillColor(BLUE);canvas.setFont('Helvetica-Bold',9);canvas.drawString(left,h-173,'O CENTRO DE COMANDO EXECUTIVO DO ESTUDANTE')
 p=Paragraph(title,ParagraphStyle('EditorialCoverTitle',fontName='Helvetica-Bold',fontSize=30,leading=34,textColor=BLUE));pw,ph=p.wrap(usable,100);p.drawOn(canvas,left,h-194-ph)
 p=Paragraph(subtitle,ParagraphStyle('EditorialCoverSubtitle',fontName='Helvetica',fontSize=11,leading=16,textColor=BLUE));pw,ph=p.wrap(usable,55);p.drawOn(canvas,left,h-280-ph)
 art=ROOT/'assets/capa-comando-executivo.png'
 if not art.exists():raise FileNotFoundError('Ilustração final da capa ainda não foi salva no projeto.')
 canvas.drawImage(str(art),left,218,width=usable,height=usable*2/3,preserveAspectRatio=True,anchor='c',mask='auto')
 canvas.setFillColor(BLUE);canvas.setFont('Helvetica-Bold',9);canvas.drawString(left,182,audience)
 canvas.setFont('Helvetica',10);canvas.drawString(left,156,'Autor e Fundador: Professor Guandalini')
 canvas.setFillColor(GOLD);canvas.rect(left,121,usable,4,fill=1,stroke=0)
 canvas.setFillColor(BLUE);canvas.setFont('Helvetica',9);canvas.drawString(left,91,edition)
 canvas.setFont('Helvetica',8);canvas.drawString(left,72,'Conceito, marca e metodologia: Professor Guandalini')
 canvas.restoreState()

def destaque(text,width):
 p=Paragraph(text,ParagraphStyle('EditorialCallout',fontName='Helvetica',fontSize=10,leading=14,textColor=BLUE))
 t=Table([[p]],colWidths=[width]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#FFF9F0')),('LINEBEFORE',(0,0),(0,-1),5,GOLD),('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]));return t
