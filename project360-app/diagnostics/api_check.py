import base64
import hashlib
import io
import json
from pathlib import Path
import httpx
from openpyxl import Workbook
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from PIL import Image

HERE = Path(__file__).resolve().parent
client = httpx.Client(base_url='http://127.0.0.1:8010', timeout=60)
results = []
def check(name, function):
    try:
        detail = function()
        result = {'test': name, 'status': 'PASS', 'detail': detail}
    except Exception as exc:
        result = {'test': name, 'status': 'FAIL', 'detail': str(exc)}
    results.append(result)
    (HERE/'api-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True), flush=True)
def get(path):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code, response.text[:300])
    return response.json()
def preview(name, content):
    response = client.post('/api/updates/preview', files={'file': (name, content)})
    assert response.status_code == 200, response.text
    return response.json()
def state():
    memory = get('/api/project-memory')
    return {'target': memory['schedule']['current_target'], 'gates': sorted(g['id'] for g in memory['gates']), 'documents': memory['stats']['documents']}
def endpoints():
    paths = ['/api/health','/api/dashboard','/api/documents','/api/timeline','/api/project-memory','/api/synthesis','/api/dossier','/api/updates','/api/brief','/api/comparison/projects']
    return {path: len(json.dumps(get(path))) for path in paths}
check('All non-LLM read endpoints', endpoints)
def sources():
    docs = get('/api/documents')
    ids = {doc['id'] for doc in docs}
    proofs = [proof for event in get('/api/project-memory')['events'] for proof in event['evidence']]
    for proof in proofs:
        assert proof['document_id'] in ids and proof['locator'] and proof['excerpt']
    for doc in docs:
        response = client.get(f"/api/documents/{doc['id']}/original")
        assert response.status_code == 200 and response.content, doc['path']
        original = HERE/'sandbox'/'corpus'/doc['path']
        assert response.content == original.read_bytes(), doc['path']
    assert client.get('/api/documents/missing').status_code==404
    assert client.get('/api/documents/missing/original').status_code==404
    return {'documents': len(docs), 'event_proofs': len(proofs)}
check('Every original download and timeline source resolves exactly', sources)
def formats():
    text = 'Date : 6 octobre 2026\nSophie Lambert doit effectuer le re-test SEC-210 avant le 12 octobre 2026.'
    files = [('diagnostic.txt', text.encode()),('diagnostic.md', ('# Diagnostic\n'+text).encode()),('diagnostic.csv', ('type,contenu\ninfo,"'+text+'"').encode())]
    workbook=Workbook();workbook.active.append(['Date','Information']);workbook.active.append(['2026-10-06',text]);stream=io.BytesIO();workbook.save(stream);files.append(('diagnostic.xlsx',stream.getvalue()))
    stream=io.BytesIO();pdf=canvas.Canvas(stream);pdf.drawString(30,800,'Date : 6 octobre 2026. SEC-210 re-test avant le 12 octobre 2026.');pdf.save();files.append(('diagnostic.pdf',stream.getvalue()))
    details=[]
    for name,content in files:
        before=state();draft=preview(name, content);assert draft['extracted_text'].strip(),name;assert state()==before
        analysis=client.post(f"/api/updates/{draft['id']}/analyze",json={});assert analysis.status_code==200,analysis.text;assert state()==before
        details.append({'format':name,'text':draft['extracted_text'][:100]})
    for extension in ('png','jpg','jpeg','webp'):
        stream=io.BytesIO();Image.new('RGB',(10,10),'white').save(stream,format='JPEG' if extension in ('jpg','jpeg') else extension.upper())
        draft=preview('diagnostic.'+extension,stream.getvalue())
        assert draft['warnings'],draft
        details.append({'format':extension,'warnings':draft['warnings']})
    return details
check('TXT Markdown CSV XLSX PDF and image preview fallback; preview does not mutate memory', formats)
def errors():
    cases=[]
    for name,content in [('bad.exe',b'content'),('empty.txt',b'')]:
        response=client.post('/api/updates/preview',files={'file':(name,content)});assert response.status_code==400,response.text;cases.append([name,response.status_code])
    draft=preview('date-check.txt',b'Date : 7 octobre 2026\nSEC-210 diagnostic date.')
    for payload in ({'document_date':'2026-99-99'},{'reviewed_text':''}):
        response=client.post(f"/api/updates/{draft['id']}/integrate",json=payload);assert response.status_code==400,response.text
    assert client.post('/api/updates/not-valid/integrate',json={}).status_code==400
    assert client.post('/api/events/missing/state',json={'action':'archived'}).status_code==400
    assert client.post('/api/search',json={}).status_code==422
    broken=preview('broken.pdf',b'not a PDF')
    assert broken['warnings'] and not broken['extracted_text']
    return cases
check('Input validation and corrupt-file recovery', errors)
def update_roundtrip():
    before=state()
    draft=preview('diagnostic-approved.txt',b'Date : 8 octobre 2026\nDecision : la date cible de mise en production est deplacee au 5 novembre 2026. Donc approuve. Le 5 novembre devient la date officielle.')
    route=f"/api/updates/{draft['id']}"
    response=client.post(route+'/integrate',json={});assert response.status_code==200,response.text
    integrated=response.json();doc=integrated['analysis']['document'];identifier=doc['id']
    assert state()['target']=='2026-11-05',state()
    for path in ['/api/project-memory','/api/dashboard','/api/dossier','/api/synthesis','/api/timeline']:
        assert identifier in json.dumps(get(path)),path
    assert identifier in client.post('/api/search',json={'query':'5 novembre'}).text
    again=client.post(route+'/integrate',json={});assert again.json()==integrated
    removed=client.post(route+'/remove');assert removed.status_code==200,removed.text;assert state()==before,(before,state())
    assert client.get(f'/api/documents/{identifier}').status_code==404
    assert client.post('/api/ingest').status_code==200;assert state()==before
    restored=client.post(route+'/restore');assert restored.status_code==200,restored.text;assert state()['target']=='2026-11-05'
    assert client.post(route+'/remove').status_code==200;assert state()==before
    return {'before':before,'imported_target':'2026-11-05','all_views_updated':True,'idempotent':True,'restored_original_state':True}
check('Approved date propagates everywhere; integrate/remove/restore/idempotence/reingest', update_roundtrip)
def proposal_supplier():
    before=state()
    draft=preview('diagnostic-supplier.eml',b'From: Julien Moreau <julien@example.test>\nDate: Fri, 9 Oct 2026 10:00:00 -0400\nSubject: Supplier diagnostic\n\nSEC-210 est ferme. Correctif deploye. Proposition : mise en production le 12 novembre 2026.')
    route=f"/api/updates/{draft['id']}";response=client.post(route+'/integrate',json={});assert response.status_code==200,response.text
    assert state()['target']==before['target'];assert state()['gates']==before['gates']
    assert client.post(route+'/remove').status_code==200
    return 'Supplier delivery does not close reviewer gate or approve proposed launch date.'
check('Proposal and supplier closure authority', proposal_supplier)
def event_roundtrip():
    before=state();memory=get('/api/project-memory');event=memory['events'][0];route=f"/api/events/{event['id']}/state"
    for action in ['archived','deleted']:
        assert client.post(route,json={'action':action}).status_code==200
        current=get('/api/project-memory');assert event['id'] not in [e['id'] for e in current['events']]
        assert event['id'] in [e['id'] for e in current['hidden_events']]
        assert state()==before
    assert client.post(route,json={'action':'restore'}).status_code==200
    assert event['id'] in [e['id'] for e in get('/api/timeline')]
    return 'Visibility changes preserve ticket states and launch conditions.'
check('Event archive delete restore cross-view state integrity', event_roundtrip)
def comparison():
    before=state();name='Diagnostic separate project'
    content=base64.b64encode(b'Date : 9 octobre 2026\nDecision : budget approuve de 200 000 $ CAD.').decode()
    response=client.post('/api/comparison/projects',json={'name':name,'files':[{'name':'budget.txt','content':content}]});assert response.status_code==200,response.text
    identifier=response.json()['id'];response=client.post('/api/comparison/compare',json={'projects':['nova',identifier]});assert response.status_code==200,response.text
    result=response.json();assert len(result['projects'])==2
    for project in result['projects']:
        for entries in project['axes'].values():
            for entry in entries:
                for proof in entry['evidence']:
                    path=f"/api/comparison/projects/{proof['project_id']}/documents/{proof['document_id']}/original"
                    assert client.get(path).status_code==200,path
    assert client.post('/api/comparison/compare',json={'projects':['nova','nova']}).status_code==400
    assert state()==before
    return {'projects':2,'separate_storage':True}
check('Comparison custom project upload and scoped proof downloads', comparison)
def stale_brief():
    live=get('/api/project-memory');brief=get('/api/brief');dossier=get('/api/dossier')
    launch=next(s for s in dossier['sections'] if s['id']=='go-live')
    result={'live_target':live['schedule']['current_target'],'legacy_brief':brief,'launch_facts':launch.get('facts'),'launch_open_items':launch.get('open_items')}
    (HERE/'summary-consistency.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    assert live['schedule']['current_target'] in json.dumps(brief), 'Live target '+str(live['schedule']['current_target'])+' absent from existing briefing; briefing still says '+str(brief['top_points'])
check('Existing briefing agrees with imported current target', stale_brief)
def pdf_check():
    response=client.get('/api/brief/pdf');assert response.status_code==200
    reader=PdfReader(io.BytesIO(response.content));text='\n'.join(page.extract_text() for page in reader.pages)
    (HERE/'brief-after-update.txt').write_text(text,encoding='utf-8')
    assert state()['target'] in text
    return {'pages':len(reader.pages),'live_target_in_pdf':True}
check('Updated PDF readable with current target and source references', pdf_check)
def commitments():
    docs=get('/api/documents');doc=next(d for d in docs if 'NOVA_TEST_Report_lancement_et_SEC210' in d['path']);groups=get('/api/synthesis')['groups']
    items=[item for item in groups['engagements'] if any(p['document_id']==doc['id'] for p in item['evidence'])]
    (HERE/'email-commitments.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
    assert any(item['owner']=='Sophie Lambert' and item['due']=='2026-10-12' for item in items),items
    assert any(item['owner']=='Mélissa Gagnon' and item['due']=='2026-10-13' for item in items),'Melissa commitment absent: '+json.dumps(items,ensure_ascii=False)
    assert any(item['owner']=='Nicolas Perron' and item['due']=='2026-10-07' for item in items),'Nicolas first-person commitment absent'
    return items
check('All three explicit email commitments and deadlines extracted', commitments)
def unchanged():
    expected=json.loads((HERE/'original-hashes.json').read_text(encoding='utf-8'))
    changed=[path for path,digest in expected.items() if not Path(path).exists() or hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest]
    assert not changed,changed
    return {'original_files_checked':len(expected),'changed':0}
check('Working corpus and project data unchanged', unchanged)
client.close()
