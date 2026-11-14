"""Restaura enlaces externos omitidos por el exportador LibreOffice 7 local.

Conserva el contenido y el índice del PDF. Añade anotaciones URI sin borde en
las posiciones del texto ya renderizado y contrasta con los enlaces del DOCX.
"""
from collections import Counter
from pathlib import Path
from urllib.parse import quote
import argparse
import json
import re

import pdfplumber
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, RectangleObject, TextStringObject

HERE=Path(__file__).resolve().parent
DATA=json.loads((HERE/'informe.json').read_text(encoding='utf-8'))
BASE='https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/blob/'+DATA['commit']+'/'
def target(ref):return ref.get('url') or BASE+quote(ref['path'],safe='/')

def repair(source,output):
    reader=PdfReader(source);writer=PdfWriter();writer.clone_document_from_reader(reader)
    uris=[]
    def link(index,page,box,uri):
        rect=RectangleObject([box['x0'],page.height-box['bottom'],box['x1'],page.height-box['top']])
        annotation=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/Link'),
            NameObject('/Rect'):rect,NameObject('/Border'):ArrayObject([NumberObject(0),NumberObject(0),NumberObject(0)]),
            NameObject('/A'):DictionaryObject({NameObject('/S'):NameObject('/URI'),NameObject('/URI'):TextStringObject(uri)})})
        writer.add_annotation(index,annotation);uris.append(uri)
    with pdfplumber.open(source) as pdf:
        for i,page in enumerate(pdf.pages):
            for match in page.search(r'\[E\d+\]'):
                key=match['text'][1:-1];link(i,page,match,target(DATA['references'][key]))
        page=pdf.pages[-1]
        for ref in DATA['references'].values():
            matches=page.search(re.escape(ref['label']))
            assert len(matches)==1,(ref['label'],len(matches))
            link(len(pdf.pages)-1,page,matches[0],target(ref))
            for label,path in ref.get('extra',[]):
                matches=page.search(re.escape(label))
                assert len(matches)==1,(label,len(matches))
                link(len(pdf.pages)-1,page,matches[0],BASE+quote(path,safe='/'))
    doc=Document(HERE.parent/'Informe_Final_AIOps.docx')
    expected=Counter(doc.part.rels[e.get(qn('r:id'))].target_ref for e in doc.element.xpath('.//w:hyperlink') if e.get(qn('r:id')))
    assert Counter(uris)==expected,(len(uris),sum(expected.values()))
    temporary=output.with_suffix('.linked.tmp.pdf')
    with temporary.open('wb') as f:writer.write(f)
    final=PdfReader(temporary)
    actual=Counter()
    for page in final.pages:
        for annotation in page.get('/Annots',[]):
            a=annotation.get_object().get('/A',{})
            if a.get('/URI'):actual[str(a['/URI'])]+=1
    assert actual==expected
    assert len(final.pages)==len(reader.pages)==10
    temporary.replace(output)
    print(json.dumps({'externalLinksRestored':sum(actual.values()),'uniqueUrls':len(actual),'pages':len(final.pages),'docxLinkParity':'PASS'}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();repair(args.source,args.output)
