"""Audita contenido, cifras y enlaces del informe sin iniciar infraestructura."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile
import csv
import hashlib
import json
import re
import subprocess
import unicodedata

from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
ROOT=OUT.parent.parent
DATA=json.loads((HERE/'informe.json').read_text(encoding='utf-8'))
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def norm(text):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text).replace('\u00ad','')).strip()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    prior_visual=None
    audit_path=OUT/'validacion-informe.json'
    if audit_path.exists():
        prior=json.loads(audit_path.read_text(encoding='utf-8'))
        if all(prior.get('artifacts',{}).get(n,{}).get('sha256')==digest(OUT/n) for n in ('Informe_Final_AIOps.pdf','Informe_Final_AIOps.docx')):
            prior_visual=prior.get('visualQa')
    reader=PdfReader(OUT/'Informe_Final_AIOps.pdf')
    assert len(reader.pages)==10
    text=norm(' '.join(p.extract_text() for p in reader.pages))
    doc=Document(OUT/'Informe_Final_AIOps.docx')
    full_doc=' '.join(e.text or '' for e in doc.element.xpath('.//w:t'))
    page_map={}
    checked_paragraphs=0
    for i,section in enumerate(DATA['sections'],2):
        assert norm(section['title']) in norm(reader.pages[i-1].extract_text())
        page_map[section['title']]=i
        for block in section['blocks']:
            if block['type']=='p':
                assert norm(block['text']) in text,block['text'][:80]
                assert norm(block['text']) in norm(full_doc),block['text'][:80]
                checked_paragraphs+=1
    assert len(doc.element.xpath('.//w:pBdr'))==len(doc.styles.element.xpath('.//w:pBdr'))==0
    assert sum(' TOC ' in (e.text or '') for e in doc.element.xpath('.//w:instrText'))==1
    assert len([p for p in doc.paragraphs if p.style.name=='Heading 1'])==9
    for author in DATA['authors']:assert author in full_doc
    assert DATA['teacher'] in full_doc
    expected=Counter(doc.part.rels[e.get(qn('r:id'))].target_ref for e in doc.element.xpath('.//w:hyperlink') if e.get(qn('r:id')))
    actual=Counter()
    internal=0
    for page in reader.pages:
        for value in page.get('/Annots',[]):
            annotation=value.get_object();a=annotation.get('/A',{})
            if a.get('/URI'):actual[str(a['/URI'])]+=1
            elif annotation.get('/Dest'):internal+=1
    assert actual==expected
    assert internal==9
    evidence_files=[]
    for ref in DATA['references'].values():
        for path in ([ref['path']] if 'path' in ref else [])+[p for _,p in ref.get('extra',[])]:
            assert (ROOT/path).is_file(),path
            subprocess.run(['git','cat-file','-e',DATA['commit']+':'+path],cwd=ROOT,check=True,capture_output=True)
            evidence_files.append(path)

    # Afirmaciones cuantitativas contra los resultados originales.
    ha=read('docs/evidence/issue-7-20261110/proof.json')
    assert [e['readyAgainSeconds'] for e in ha['experiments']]==[40.57,37.77,34.95]
    rollout=read('docs/evidence/issue-8-20261111/proof.json')
    assert rollout['summary']['sent']==rollout['summary']['success']==226
    assert Counter(s['path'] for s in rollout['samples'])=={'/api/drug':95,'/api/roles':95,'/api/login':36}
    assert all(s['http']==200 and s['validResponse'] for s in rollout['samples'])
    bdd=read('docs/evidence/issue-15-20261112/live-after-fix/summary.json')
    assert bdd['browserExecuted'] and bdd['status']=='PASS' and bdd['counts']=={'total':4,'passed':4,'failed':0,'pending':0,'skipped':0}
    net=read('docs/evidence/test-isolation-20261114/summary.json')
    assert net['totals']=={'total':319,'passed':319,'failed':0,'skipped':0}
    operator=read('docs/evidence/issue-16-20261113/resumen.json')
    assert operator['manualTrialCount']==operator['passedManualTrialCount']==6 and operator['screenshots']==37
    storage=read('docs/evidence/storage-io-20261114/summary.json')
    assert storage['status']=='PASS' and storage['cleanup']=='verified'
    assert storage['agentFinalResult']['completedPasses']==29 and storage['agentFinalResult']['bytesWritten']==928*2**20
    assert sum(s['samples'] for s in storage['httpPhases'].values())==61
    assert all(s['samples']==s['validSamples']==s['httpCounts']['200'] for s in storage['httpPhases'].values())
    assert round(storage['verifiedStableSeconds'],2)==125.33
    assert storage['storageEvidence']['deviceSaturation'] is None
    metrics=list(csv.DictReader((ROOT/'docs/evidence/issue-14-20261112/results/metrics.csv').open(encoding='utf-8')))
    assert len(metrics)==2
    for row,expected_values in zip(metrics,[(24,6,29,241,.578313),(18,11,35,236,.439024)]):
        for key,value in zip(('tp','fp','fn','tn'),expected_values[:4]):assert int(row[key])==value
        assert abs(float(row['f1'])-expected_values[4])<.000001

    # Validación de vínculos Markdown y ausencia de marcadores editoriales.
    markdown=(OUT/'informe-final.md').read_text(encoding='utf-8')
    assert not re.search(r'TODO|\[PENDIENTE\]|\[NOMBRE\]|\[COMPLETAR\]',markdown)
    for link in re.findall(r'\]\(([^)]+)\)',markdown):
        if '://' not in link:assert (OUT/link.split('#')[0]).exists(),link
    sources={p:{'sha256':digest(ROOT/p)} for p in evidence_files}
    artifacts={}
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name!='validacion-informe.json' and '__pycache__' not in p.parts and p.suffix!='.pyc':
            artifacts[p.relative_to(OUT).as_posix()]={'bytes':p.stat().st_size,'sha256':digest(p)}
    result={'checkedUtc':datetime.now(timezone.utc).isoformat(),'result':'PASS','scope':'Document verification only; no new application or infrastructure trials',
      'codeCut':DATA['commit'],'reportDate':DATA['date'],'pdfPages':10,'pageLimitIncludesCoverAndContents':True,
      'rubricSections':8,'additionalSection':'Agile reflection and AI use','sectionPages':page_map,
      'sourceParagraphsVerifiedInDocxAndPdf':checked_paragraphs,'externalPdfLinks':sum(actual.values()),'uniqueExternalUrls':len(actual),
      'internalContentsLinks':internal,'pdfAndDocxLinkParity':True,'referencedRepositoryFilesVerifiedAtCut':len(evidence_files),
      'numericChecks':{'processRecoverySeconds':[40.57,37.77,34.95],'rolloutValid':226,'bddPassed':4,'dotnetPassed':319,
        'operatorChaosPassed':6,'operatorScreenshots':37,'storageAgentPasses':29,'storageLogicalMiB':928,'storageValidHttp':61,'storageStableSeconds':125.329704,
        'mlConfusionAndF1':'Match original metrics.csv'},
      'sourceEvidenceFiles':sources,'artifacts':artifacts,
      'teamReview':'Content requires review by the three students before submission; no academic approvals or completed defense inferred.',
      'teamDecisions':{'date':'2026-11-14','source':'docs/aiops-open-questions.md',
        'decisions':['D01','D02','D03','D04'],'authority':'Team decision; no teacher approval inferred.'}}
    if prior_visual:result['visualQa']=prior_visual
    (OUT/'validacion-informe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','pdfPages','externalPdfLinks','internalContentsLinks','sourceParagraphsVerifiedInDocxAndPdf','referencedRepositoryFilesVerifiedAtCut')}))

if __name__=='__main__':verify()
