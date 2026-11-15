"""Construye el informe editable y su fuente Markdown; el PDF se renderiza aparte.

Requiere python-docx y Pillow. Usar el runtime documental configurado en Codex.
"""
from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import math
import re
import xml.sax.saxutils as sax

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.opc.constants import RELATIONSHIP_TYPE as RT

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
ROOT=OUT.parent.parent
DATA=json.loads((HERE/'informe.json').read_text(encoding='utf-8'))
FIG=OUT/'figuras'
FIG.mkdir(exist_ok=True)
BASE='https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/blob/'+DATA['commit']+'/'

def url(ref):
    return ref.get('url') or BASE+quote(ref['path'],safe='/')

def diagram():
    w,h=2400,1300
    im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im)
    fontroot=Path('C:/Windows/Fonts')
    regular=fontroot/'arial.ttf';bold=fontroot/'arialbd.ttf'
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
    def text(x,y,s,size=45,heavy=False,center=False):
        f=ImageFont.truetype(str(bold if heavy else regular),size)
        anchor='mm' if center else 'lt'
        d.text((x,y),s,font=f,fill='#111111',anchor=anchor)
        svg.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="{size}" font-weight="{700 if heavy else 400}" dominant-baseline="{("central" if center else "hanging")}" text-anchor="{("middle" if center else "start")}">{sax.escape(s)}</text>')
    def rect(x,y,x2,y2,fill='#FFFFFF',outline='#A3A3A3',width=4):
        d.rectangle((x,y,x2,y2),fill=fill,outline=outline,width=width)
        svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')
    def arrow(x1,y1,x2,y2):
        dx,dy=x2-x1,y2-y1;n=math.hypot(dx,dy);ux,uy=dx/n,dy/n
        a=(x2-25*ux+12*uy,y2-25*uy-12*ux);b=(x2-25*ux-12*uy,y2-25*uy+12*ux)
        d.line((x1,y1,x2,y2),fill='#222222',width=6);d.polygon([(x2,y2),a,b],fill='#222222')
        svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#222" stroke-width="6"/><polygon points="{x2},{y2} {a[0]},{a[1]} {b[0]},{b[1]}" fill="#222"/>')
    def node(x,y,width,height,title,detail):
        rect(x,y,x+width,y+height,fill='#F5F5F5',outline='#777777')
        text(x+width/2,y+height/2-27,title,50,True,True)
        text(x+width/2,y+height/2+34,detail,42,False,True)
    rect(20,20,2380,1280,outline='#555555',width=5)
    text(60,55,'PC Windows   |   Docker Desktop y WSL',52,True)
    rect(60,150,2340,1100,outline='#999999',width=4)
    text(100,180,'Minikube pharmago-issue17-validation   |   1 nodo Kubernetes   |   Calico',46,True)
    node(130,350,360,160,'Angular','1 pod UI')
    node(650,350,450,160,'Gateway','1 réplica')
    node(1270,270,420,150,'Users','2 réplicas')
    node(1270,560,420,150,'Pharmacy','2 réplicas')
    node(1870,415,360,160,'SQL Server','1 réplica y PVC')
    arrow(490,430,650,430)
    arrow(1100,410,1270,345)
    arrow(1100,470,1270,635)
    arrow(1690,345,1870,455)
    arrow(1690,635,1870,535)
    text(210,555,'HTTP',42)
    text(1030,295,'HTTP',42)
    text(1730,355,'SQL',42)
    rect(130,790,2260,1030,fill='#FAFAFA',outline='#B5B5B5')
    text(170,820,'Métricas OTLP → Collector; Prometheus y Grafana',44)
    text(170,890,'Trazas OTLP → Collector → Jaeger',44)
    text(170,960,'Logs JSON → Fluent Bit → Elasticsearch y Kibana',44)
    text(65,1145,'Perfil observado: 17 pods base en pharmago; clientes de prueba efímeros aparte.',43)
    text(65,1195,'Las réplicas comparten nodo y host físico. No representa hosts independientes.',43)
    im.save(FIG/'despliegue-laboratorio.png',dpi=(300,300))
    svg.append('</svg>');(FIG/'despliegue-laboratorio.svg').write_text('\n'.join(svg),encoding='utf-8')

def topology_diagram():
    """Compara la colocación multinodo con el laboratorio de caos en una PC."""
    w,h=2400,1730
    im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im)
    fontroot=Path('C:/Windows/Fonts')
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
    def text(x,y,s,size=42,heavy=False,center=False):
        font=ImageFont.truetype(str(fontroot/('arialbd.ttf' if heavy else 'arial.ttf')),size)
        d.text((x,y),s,font=font,fill='#111111',anchor='mm' if center else 'lt')
        svg.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="{size}" font-weight="{700 if heavy else 400}" dominant-baseline="{"central" if center else "hanging"}" text-anchor="{"middle" if center else "start"}">{sax.escape(s)}</text>')
    def rect(x,y,x2,y2,fill='#FFFFFF',outline='#999999',width=4):
        d.rectangle((x,y,x2,y2),fill=fill,outline=outline,width=width)
        svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')
    def arrow(points):
        x1,y1=points[-2];x2,y2=points[-1]
        dx,dy=x2-x1,y2-y1;n=math.hypot(dx,dy);ux,uy=dx/n,dy/n
        a=(x2-22*ux+11*uy,y2-22*uy-11*ux);b=(x2-22*ux-11*uy,y2-22*uy+11*ux)
        d.line(points,fill='#333333',width=5);d.polygon([(x2,y2),a,b],fill='#333333')
        coordinates=' '.join(f'{x},{y}' for x,y in points)
        svg.append(f'<polyline points="{coordinates}" fill="none" stroke="#333333" stroke-width="5"/><polygon points="{x2},{y2} {a[0]},{a[1]} {b[0]},{b[1]}" fill="#333333"/>')
    def box(x,y,width,title,detail,height=115):
        rect(x,y,x+width,y+height,fill='#F5F5F5',outline='#777777')
        text(x+width/2,y+height/2-22,title,44,True,True)
        text(x+width/2,y+height/2+28,detail,37,False,True)

    rect(20,20,2380,1710,outline='#555555',width=5)
    text(60,55,'Una PC Windows   |   Docker Desktop y WSL',52,True)
    rect(60,145,2340,955)
    text(100,175,'A  Perfil multinodo pharmago-issue3   |   3 nodos Kubernetes',48,True)
    text(100,235,'Distribución de la issue #3; réplicas de aplicación incorporadas en #7.',37)
    for x,name,role in [(105,'pharmago-issue3','Gateway y operaciones'),(865,'pharmago-issue3-m02','Users y frontend'),(1625,'pharmago-issue3-m03','Pharmacy')]:
        rect(x,300,x+670,820,outline='#777777')
        text(x+335,337,name,36,True,True)
        text(x+335,382,role,35,False,True)
    box(145,490,590,'Gateway','1 réplica')
    box(905,490,590,'Users','2 réplicas')
    box(1665,490,590,'Pharmacy','2 réplicas')
    arrow([(735,548),(905,548)])
    text(820,508,'HTTP',31,False,True)
    arrow([(440,490),(440,440),(1960,440),(1960,490)])
    text(1200,418,'HTTP',31,False,True)
    box(145,630,590,'SQL Server','1 réplica y PVC',95)
    text(440,755,'Elasticsearch · Prometheus',35,False,True)
    text(440,797,'Grafana · Collector',35,False,True)
    box(905,665,275,'Angular','1 pod UI',100)
    box(1210,665,285,'Kibana','Logs',100)
    text(100,852,'Flujo funcional: Angular → Gateway → Users / Pharmacy → SQL Server.',39)
    text(100,905,'PV locales en el nodo de operaciones; Fluent Bit y Node Exporter en cada nodo.',36)

    rect(60,990,2340,1600)
    text(100,1020,'B  Laboratorio pharmago-issue17-validation   |   1 nodo   |   Calico',46,True)
    box(120,1190,300,'Angular','1 pod UI')
    box(550,1190,370,'Gateway','1 réplica')
    box(1110,1130,390,'Users','2 réplicas')
    box(1110,1330,390,'Pharmacy','2 réplicas')
    box(1850,1230,370,'SQL Server','1 réplica y PVC')
    arrow([(420,1248),(550,1248)])
    arrow([(920,1220),(1110,1188)])
    arrow([(920,1275),(1110,1388)])
    arrow([(1500,1188),(1850,1255)])
    arrow([(1500,1388),(1850,1315)])
    text(485,1206,'HTTP',30,False,True)
    text(1000,1150,'HTTP',30,False,True)
    text(1680,1195,'SQL',32,False,True)
    text(100,1485,'OTLP → Collector → Prometheus / Grafana y Jaeger; logs → Fluent Bit → Elasticsearch / Kibana.',34)
    text(100,1545,'Perfil observado: 17 pods base; clientes efímeros aparte. Las réplicas comparten el mismo nodo.',35)
    text(65,1650,'Los perfiles se usaron en ejecuciones distintas y no representan hosts físicos independientes.',40)
    im.save(FIG/'despliegue-topologias.png',dpi=(300,300))
    svg.append('</svg>');(FIG/'despliegue-topologias.svg').write_text('\n'.join(svg),encoding='utf-8')

def prop(tag,**attrs):
    e=OxmlElement(tag)
    for k,v in attrs.items():e.set(qn('w:'+k),str(v))
    return e

def hyperlink(p,label,target=None,anchor=None,size=None,color='164C75'):
    h=OxmlElement('w:hyperlink')
    if anchor:h.set(qn('w:anchor'),anchor)
    else:h.set(qn('r:id'),p.part.relate_to(target,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');rp=OxmlElement('w:rPr')
    rp.append(prop('w:rFonts',ascii='Arial',hAnsi='Arial'))
    rp.append(prop('w:color',val=color))
    if size:rp.append(prop('w:sz',val=int(size*2)))
    r.append(rp);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

def rich(p,text):
    for part in re.split(r'(\[E\d+\])',text):
        if re.fullmatch(r'\[E\d+\]',part):hyperlink(p,part,url(DATA['references'][part[1:-1]]))
        else:p.add_run(part)
    return p

def bookmark(p,name,index):
    p._p.insert(0,prop('w:bookmarkStart',id=index,name=name))
    p._p.append(prop('w:bookmarkEnd',id=index))

def field(p,instruction,cache='1'):
    r=p.add_run();r._r.append(prop('w:fldChar',fldCharType='begin'))
    r=p.add_run();i=OxmlElement('w:instrText');i.set(qn('xml:space'),'preserve');i.text=instruction;r._r.append(i)
    p.add_run()._r.append(prop('w:fldChar',fldCharType='separate'))
    p.add_run(cache)
    p.add_run()._r.append(prop('w:fldChar',fldCharType='end'))

def setfont(style,size,bold=False):
    style.font.name='Arial';style.font.size=Pt(size);style.font.bold=bold;style.font.color.rgb=RGBColor(0,0,0)
    style.element.get_or_add_rPr().append(prop('w:rFonts',ascii='Arial',hAnsi='Arial'))

def make_table(doc,block):
    t=doc.add_table(rows=1,cols=len(block['headers']))
    t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    t._tbl.tblPr.append(prop('w:tblLayout',type='fixed'))
    borders=OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        borders.append(prop('w:'+edge,val='single',sz=4,color='D9D9D9'))
    t._tbl.tblPr.append(borders)
    for i,width in enumerate(block['widths']):t.columns[i].width=Inches(width)
    rows=[block['headers']]+block['rows']
    for ri,values in enumerate(rows):
        row=t.rows[0] if ri==0 else t.add_row()
        pr=row._tr.get_or_add_trPr();pr.append(prop('w:cantSplit'))
        if ri==0:pr.append(prop('w:tblHeader'))
        for ci,value in enumerate(values):
            cell=row.cells[ci];cell.width=Inches(block['widths'][ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc=cell._tc.get_or_add_tcPr();tc.append(prop('w:shd',fill='333333' if ri==0 else ('F5F5F5' if ri%2==0 else 'FFFFFF')))
            margins=OxmlElement('w:tcMar')
            for side in ('top','left','bottom','right'):margins.append(prop('w:'+side,w=90,type='dxa'))
            tc.append(margins)
            p=cell.paragraphs[0];p.paragraph_format.space_before=Pt(1);p.paragraph_format.space_after=Pt(1);p.paragraph_format.line_spacing=1.05
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER if ci>0 and len(str(value))<24 else WD_ALIGN_PARAGRAPH.LEFT
            r=p.add_run(str(value));r.font.size=Pt(10);r.bold=ri==0;r.font.color.rgb=RGBColor.from_string('FFFFFF' if ri==0 else '000000')
    doc.add_paragraph().paragraph_format.space_after=Pt(2)

def toc(doc):
    start=doc.add_paragraph();start.paragraph_format.space_after=Pt(2)
    start.add_run()._r.append(prop('w:fldChar',fldCharType='begin'))
    r=start.add_run();i=OxmlElement('w:instrText');i.set(qn('xml:space'),'preserve');i.text=' TOC \\o "1-1" \\h \\z \\u ';r._r.append(i)
    start.add_run()._r.append(prop('w:fldChar',fldCharType='separate'))
    for idx,section in enumerate(DATA['sections'],1):
        p=doc.add_paragraph();p.paragraph_format.space_after=Pt(5);p.paragraph_format.line_spacing=1
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.68),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
        hyperlink(p,section['title'],anchor='seccion'+str(idx),size=10.5,color='000000')
        p.add_run('\t'+str(idx+1)).font.size=Pt(10.5)
    doc.paragraphs[-1].add_run()._r.append(prop('w:fldChar',fldCharType='end'))

def write_markdown():
    parts=['# '+DATA['title'],'','## '+DATA['subtitle'],'',
           '**Integrantes:** '+'; '.join(DATA['authors']), '**Docente:** '+DATA['teacher'],
           '**Corte:** '+DATA['date']+' · `'+DATA['commit']+'`','',DATA['intro'],'',DATA['scope'],'']
    for section in DATA['sections']:
        parts+=['## '+section['title'],'']
        for b in section['blocks']:
            typ=b['type']
            if typ=='p':parts+=[b['text'],'']
            elif typ=='h2':parts+=['### '+b['text'],'']
            elif typ=='number':parts+=['1. '+b['text'],'']
            elif typ=='image':parts+=['!['+b['caption']+'](figuras/'+b['asset']+')','']
            elif typ=='table':
                parts+=['| '+' | '.join(b['headers'])+' |','| '+' | '.join(['---']*len(b['headers']))+' |']
                parts+=['| '+' | '.join(row)+' |' for row in b['rows']];parts+=['']
            elif typ=='references':
                for key,ref in DATA['references'].items():
                    line=key+' · ['+ref['label']+']('+url(ref)+')'
                    for label,path in ref.get('extra',[]):line+=' · ['+label+']('+BASE+quote(path,safe='/')+')'
                    parts+=[line,'']
    text='\n'.join(parts)
    for key,ref in DATA['references'].items():text=text.replace('['+key+']','['+key+']('+url(ref)+')')
    (OUT/'informe-final.md').write_text(text,encoding='utf-8')

def build():
    diagram();topology_diagram();write_markdown();doc=Document();s=doc.sections[0]
    s.page_width=Inches(8.5);s.page_height=Inches(11)
    s.top_margin=Inches(.70);s.bottom_margin=Inches(.68);s.left_margin=Inches(.85);s.right_margin=Inches(.85)
    s.header_distance=Inches(.30);s.footer_distance=Inches(.30);s.different_first_page_header_footer=True
    setfont(doc.styles['Normal'],11)
    doc.styles['Normal'].paragraph_format.line_spacing=1.08
    doc.styles['Normal'].paragraph_format.space_after=Pt(7)
    doc.styles['Normal'].paragraph_format.widow_control=True
    for name,size in [('Title',25),('Subtitle',18),('Heading 1',16),('Heading 2',12.2)]:
        setfont(doc.styles[name],size,name!='Subtitle')
        doc.styles[name].paragraph_format.space_before=Pt(9 if name=='Heading 2' else 0)
        doc.styles[name].paragraph_format.space_after=Pt(8)
        doc.styles[name].paragraph_format.keep_with_next=True
    doc.styles['Caption'].font.name='Arial';doc.styles['Caption'].font.size=Pt(9.2);doc.styles['Caption'].font.color.rgb=RGBColor(0,0,0)
    doc.styles['Caption'].font.italic=False
    doc.styles['Caption'].font.bold=False
    doc.styles['Caption'].paragraph_format.space_after=Pt(7)
    hdr=s.header.paragraphs[0];hdr.add_run('PharmaGo · Obligatorio AIOps').font.size=Pt(9)
    hdr.paragraph_format.space_after=Pt(0)
    for footer in (s.footer,s.first_page_footer):
        p=footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
        p.add_run('AIOps 2026   ·   ').font.size=Pt(9)
        field(p,' PAGE ','1');p.add_run(' / ');field(p,' NUMPAGES ','10')
        for r in p.runs:r.font.size=Pt(9)
    doc.core_properties.title=DATA['title']+' '+DATA['subtitle']
    doc.core_properties.author='Joaquín Decia; Vicente Lavega; Damián Rodríguez'
    doc.core_properties.subject='Informe académico basado en código y evidencias del obligatorio AIOps'
    doc.core_properties.keywords='PharmaGo, AIOps, Kubernetes, OpenTelemetry, caos'
    doc.settings.element.append(prop('w:updateFields',val='true'))
    for label in ('Universidad ORT Uruguay','Ingeniería y Licenciatura en Sistemas · AIOps 2026'):
        p=doc.add_paragraph(label);p.paragraph_format.space_after=Pt(3)
        for r in p.runs:r.font.size=Pt(10)
    doc.add_paragraph().paragraph_format.space_after=Pt(5)
    doc.add_paragraph(DATA['title'],style='Title')
    doc.add_paragraph(DATA['subtitle'],style='Subtitle')
    p=doc.add_paragraph();p.add_run('Integrantes').bold=True
    p.paragraph_format.space_after=Pt(3)
    for author in DATA['authors']:
        p=doc.add_paragraph(author);p.paragraph_format.space_after=Pt(2)
    p=doc.add_paragraph('Docente: '+DATA['teacher']+'   ·   '+DATA['date']);p.paragraph_format.space_before=Pt(6)
    p=doc.add_paragraph('Resumen');p.runs[0].bold=True;p.paragraph_format.space_before=Pt(8);p.paragraph_format.space_after=Pt(4)
    rich(doc.add_paragraph(),DATA['intro'])
    p=rich(doc.add_paragraph(),DATA['scope']);p.paragraph_format.space_after=Pt(6)
    p=doc.add_paragraph('Contenido');p.runs[0].bold=True;p.paragraph_format.space_after=Pt(0)
    toc(doc)
    for idx,section in enumerate(DATA['sections'],1):
        doc.add_page_break()
        p=doc.add_paragraph(section['title'],style='Heading 1');bookmark(p,'seccion'+str(idx),idx)
        for block in section['blocks']:
            typ=block['type']
            if typ=='p':
                p=rich(doc.add_paragraph(),block['text'])
                if block.get('style')=='small':
                    for r in p.runs:r.font.size=Pt(9.4)
            elif typ=='h2':doc.add_paragraph(block['text'],style='Heading 2')
            elif typ=='table':make_table(doc,block)
            elif typ=='image':
                p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
                p.add_run().add_picture(str(FIG/block['asset']),width=Inches(block['width']))
                doc.add_paragraph(block['caption'],style='Caption')
            elif typ=='number':rich(doc.add_paragraph(style='List Number'),block['text'])
            elif typ=='references':
                for key,ref in DATA['references'].items():
                    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1
                    r=p.add_run(key+'  ');r.font.size=Pt(9.2)
                    hyperlink(p,ref['label'],url(ref),size=9.2)
                    for label,path in ref.get('extra',[]):
                        p.add_run(' · ').font.size=Pt(9.2);hyperlink(p,label,BASE+quote(path,safe='/'),size=9.2)
    # Eliminar bordes heredados del estilo Title de la plantilla del runtime.
    for element in (doc.styles.element,doc.element):
        for border in element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    doc.save(OUT/'Informe_Final_AIOps.docx')
    print(json.dumps({'output':str(OUT/'Informe_Final_AIOps.docx'),'plannedPages':10,'sections':len(DATA['sections']),
                      'sourceCommit':DATA['commit'],'sourceSha256':hashlib.sha256((HERE/'informe.json').read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__':build()
