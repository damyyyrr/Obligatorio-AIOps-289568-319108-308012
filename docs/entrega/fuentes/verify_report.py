"""Audita contenido, cifras y enlaces del informe sin iniciar infraestructura."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile
import csv
import gzip
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
def norm(text):
    text=unicodedata.normalize('NFKC',text).replace('\u00ad','')
    # Word puede partir identificadores como kubelet-storage al final de línea.
    text=re.sub(r'(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)','-',text)
    return re.sub(r'\s+',' ',text).strip()
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
            elif block['type']=='table':
                for row in [block['headers'],*block['rows']]:
                    for value in row:
                        assert norm(value) in text and norm(value) in norm(full_doc),value
    assert len(doc.element.xpath('.//w:pBdr'))==len(doc.styles.element.xpath('.//w:pBdr'))==0
    assert sum(' TOC ' in (e.text or '') for e in doc.element.xpath('.//w:instrText'))==1
    assert len([p for p in doc.paragraphs if p.style.name=='Heading 1'])==9
    for author in DATA['authors']:assert author in full_doc
    assert DATA['teacher'] in full_doc
    for paragraph in (DATA['intro'], DATA['scope']):
        assert norm(paragraph) in text and norm(paragraph) in norm(full_doc)
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

    # Separación física documentada y siete corridas originales, sin nuevas inyecciones.
    physical_root=ROOT/'docs/evidence/chaos-3pc-20261116'
    physical=read('docs/evidence/chaos-3pc-20261116/summary.json')['runs']
    assert len(physical)==7
    assert Counter(r['status'] for r in physical)=={'PASS':6,'FAIL':1}
    passed={r['scenario']:r for r in physical if r['status']=='PASS'}
    assert set(passed)=={'requests','cpu','ram','storage','network','disconnect'}
    assert all(r['cleanup']=='verified' and r['tAck'] is None for r in physical)
    assert all(r['sourceCommit']=='ae24ebea78174cf6d6a48cabbd95743e29bbf3a5' and not r['dirtyTree'] for r in physical)
    assert passed['requests']['loadHttp']=={'200':111,'429':129}
    assert passed['storage']['storageEvidence']=={'classification':'sustained_io_observed','completedPasses':26,'deviceSaturation':None}
    failed=[r for r in physical if r['status']=='FAIL'][0]
    assert failed['scenario']=='network' and failed['abort']['reason']=='Se perdió evaluación sana de las alertas'
    nodes=read('docs/evidence/chaos-3pc-20261116/nodes.json')
    assert {n['name']:n['labels']['pharmago.io/service'] for n in nodes}=={'pharmago-a':'gateway','pharmago-b':'users','pharmago-c':'pharmacy'}
    assert len({n['internalIP'] for n in nodes})==3
    pods=(physical_root/'pods.txt').read_text(encoding='utf-8')
    for prefix,node,count in [('pharmago-api-gateway-','pharmago-a',1),('pharmago-users-service-','pharmago-b',2),('pharmago-pharmacy-service-','pharmago-c',2)]:
        observed=[line.split() for line in pods.splitlines() if line.startswith(prefix)]
        assert len(observed)==count and all(row[1:3]==['1/1','Running'] and row[6]==node for row in observed)
    for run in physical:
        matches=list((physical_root/'reports').glob('*'+run['runId'][:8]+'-report.json.gz'))
        assert len(matches)==1
        report=json.loads(gzip.decompress(matches[0].read_bytes()))
        for key in ('runId','scenario','status','cleanup','sourceCommit','dirtyTree','tAck'):
            assert report[key]==run[key],(matches[0].name,key)
        if run['scenario']=='requests':
            assert Counter(str(sample['http']) for sample in report['injectionResult'])==run['loadHttp']
        elif run['scenario']=='storage':
            assert report['storageEvidence']['completedPasses']==26
            assert report['storageEvidence']['classification']=='sustained_io_observed'
            assert report['storageEvidence']['deviceSaturation'] is None
            final=json.loads(report['injectionResult'])
            assert final['completedPasses']==29 and final['bytesWritten']==928*2**20
    for file in [physical_root/'nodes.json',physical_root/'pods.txt',physical_root/'topologia-3pc.png',*sorted((physical_root/'reports').glob('*.json.gz'))]:
        relative=file.relative_to(ROOT).as_posix()
        subprocess.run(['git','cat-file','-e',DATA['commit']+':'+relative],cwd=ROOT,check=True,capture_output=True)
        evidence_files.append(relative)
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
        'physicalChaosRuns':7,'physicalChaosPassed':6,'physicalChaosFailed':1,'physicalChaosCleanupVerified':7,
        'physicalRequestsHttp':{'200':111,'429':129},'physicalStoragePasses':26,'physicalStorageDeviceSaturation':None,
        'physicalStorageAgentFinalPasses':29,'physicalStorageAgentLogicalMiB':928,
        'physicalNodeServiceMap':{'pharmago-a':'gateway','pharmago-b':'users','pharmago-c':'pharmacy'},
        'mlConfusionAndF1':'Match original metrics.csv'},
      'sourceEvidenceFiles':sources,'artifacts':artifacts,
      'teamReview':'Content requires review by the three students before submission; no academic approvals or completed defense inferred.',
      'teamDecisions':{'date':'2026-11-14','source':'docs/aiops-open-questions.md',
        'decisions':['D01','D02','D03','D04'],'authority':'Team decision; no teacher approval inferred.',
        'physicalDeploymentEvidence':'docs/evidence/chaos-3pc-20261116/README.md',
        'scopeExtension':'Physical deployment and chaos supplement the earlier local D01 scope; rollout and telemetry validations keep their original environments.'}}
    if prior_visual:result['visualQa']=prior_visual
    (OUT/'validacion-informe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','pdfPages','externalPdfLinks','internalContentsLinks','sourceParagraphsVerifiedInDocxAndPdf','referencedRepositoryFilesVerifiedAtCut')}))

if __name__=='__main__':verify()
