"""Diagramas explicativos com a marca vetorial original, sem redesenhar o símbolo."""
from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pypdf import PdfReader,PdfWriter,Transformation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/diagramas'
BLUE='#013B9D';CYAN='#06A9BF';GOLD='#DF9317'
def generate(role):
 OUT.mkdir(exist_ok=True);stream=BytesIO();c=canvas.Canvas(stream,pagesize=(600,430))
 c.setTitle('Anatomia da marca SempreHub');c.setAuthor('Professor Guandalini')
 def text(x,y,value,size=11,color=BLUE,bold=False):
  c.setFillColor(HexColor(color));c.setFont('Helvetica-Bold' if bold else 'Helvetica',size);c.drawString(x,y,value)
 def line(points,color):
  c.setStrokeColor(HexColor(color));c.setLineWidth(1.3);p=c.beginPath();p.moveTo(*points[0])
  for pt in points[1:]:p.lineTo(*pt)
  c.drawPath(p);x,y=points[-1];c.setFillColor(HexColor(color));c.circle(x,y,2.5,fill=1,stroke=0)
 text(18,397,'1  DEPARTAMENTOS',12,BLUE,True)
 text(18,380,'Nós azuis e cianos',10,BLUE)
 text(230,397,'2  INTERDEPENDÊNCIA',12,BLUE,True)
 text(230,380,'Linhas que conectam decisões',10,BLUE)
 text(457,397,'3  TIPOGRAFIA',12,CYAN,True)
 text(457,380,'Sempre + Hub',10,CYAN)
 # Logo itself is inserted below as a separate vector page. Callouts only
 # occupy the surrounding whitespace and terminate at the relevant artwork.
 line([(90,370),(90,341),(142,308)],BLUE)
 line([(270,370),(270,341),(169,287)],BLUE)
 line([(500,370),(500,341),(410,250)],CYAN)
 text(18,142,'4  NÚCLEOS CENTRAIS',12,GOLD,True)
 text(18,126,'Tomada de decisão e resposta do mercado' if role=='aluno' else 'Tomada de decisão e motor de Inteligência Artificial',10,GOLD)
 line([(27,154),(27,218),(109,233)],GOLD)
 text(335,142,'FUNDO BRANCO',12,CYAN,True)
 text(335,126,'Contraste e clareza para a leitura',10,CYAN)
 c.setStrokeColor(HexColor('#d7e5ec'));c.line(18,108,582,108)
 for x,color,title,rows in [
  (18,BLUE,'ÁREAS DA EMPRESA',['P&D, Produção e Logística','Marketing, RH e Finanças']),
  (218,CYAN,'CONEXÕES',['Uma decisão influencia','as outras áreas da empresa.']),
  (418,GOLD,'VALOR E APRENDIZAGEM',['Decidir, observar resultados','e ajustar a estratégia.'])]:
  text(x,85,title,10,color,True)
  for i,row in enumerate(rows):text(x,65-i*15,row,10,'#222222')
 c.showPage();c.save();r=PdfReader(BytesIO(stream.getvalue()));writer=PdfWriter();writer.clone_document_from_reader(r)
 logo=PdfReader(ROOT/'docs/assets/semprehub-fundo-branco.pdf').pages[0];scale=480/float(logo.mediabox.width)
 # Insert below annotation strokes, preserving the original paths/gradients.
 writer.pages[0].merge_transformed_page(logo,Transformation().scale(scale).translate(60,180),over=False,expand=False)
 path=OUT/f'anatomia-marca-{role}.pdf'
 with path.open('wb') as f:writer.write(f)
 print(path.relative_to(ROOT))
if __name__=='__main__':
 for role in ['aluno','professor']:generate(role)
