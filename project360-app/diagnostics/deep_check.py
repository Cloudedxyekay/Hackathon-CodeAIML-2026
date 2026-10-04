import io
import json
from pathlib import Path
import httpx
from pypdf import PdfReader
from playwright.sync_api import sync_playwright, expect

HERE=Path(__file__).resolve().parent
c=httpx.Client(base_url='http://127.0.0.1:8010',timeout=60)
imports=c.get('/api/updates').json()['imports']
email=next(item for item in imports if item['filename']=='NOVA_TEST_Report_lancement_et_SEC210.eml')
assert c.post(f"/api/updates/{email['id']}/restore").status_code==200
docs=c.get('/api/documents').json();doc=next(d for d in docs if d['id']==email['analysis']['document']['id'])
synthesis=c.get('/api/synthesis').json()
items=[item for item in synthesis['groups']['engagements'] if any(p['document_id']==doc['id'] for p in item['evidence'])]
memory=c.get('/api/project-memory').json();dossier=c.get('/api/dossier').json();brief=c.get('/api/brief').json()
pdf=c.get('/api/brief/pdf');pdftext='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
results={'target':memory['schedule']['current_target'],'gates':[g['id'] for g in memory['gates']], 'email_commitments':items,'email_events':[{'title':e['title'],'date':e['date'],'status':e['status'],'type':e['type']} for e in memory['events'] if any(p['document_id']==doc['id'] for p in e['evidence'])],'legacy_brief':brief,'launch_section':next(s for s in dossier['sections'] if s['id']=='go-live'),'pdf_text':pdftext,'browser':[]}
def save():
    (HERE/'deep-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
save()
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
    errors=[];page.on('pageerror',lambda err:errors.append(str(err)));page.on('dialog',lambda d:d.accept())
    page.goto('http://localhost:5174');expect(page.locator('.memory-event').first).to_be_visible()
    def nav(label):page.locator('nav').first.get_by_role('button',name=label,exact=True).click()
    def check(name,fn):
        try:detail=fn();result={'test':name,'status':'PASS','detail':detail}
        except Exception as e:result={'test':name,'status':'FAIL','detail':str(e)[:1500]}
        results['browser'].append(result);save();print(json.dumps(result,ensure_ascii=True),flush=True)
    def email_import():
        nav('Updates');first=page.locator('.update-history li').filter(has_text='NOVA_TEST_Report_lancement_et_SEC210.eml').first
        first.get_by_role('button').first.click()
        links=page.locator('.update-affected button');assert links.count()>0
        links.first.click();expect(page.get_by_role('dialog')).to_be_visible();page.get_by_role('button',name='Fermer les sources').click()
        nav('Updates');first=page.locator('.update-history li').filter(has_text='NOVA_TEST_Report_lancement_et_SEC210.eml').first
        first.get_by_role('button',name='Retirer cet import').click();expect(first.get_by_role('button',name='Restaurer cet import')).to_be_visible()
        assert c.get('/api/project-memory').json()['schedule']['current_target']=='2026-10-22'
        first.get_by_role('button',name='Restaurer cet import').click();expect(first.get_by_role('button',name='Retirer cet import')).to_be_visible()
        assert c.get('/api/project-memory').json()['schedule']['current_target']=='2026-10-29'
        return 'Correct import selected; actual target checked before and after restoration.'
    check('Email affected links and exact import remove/restore',email_import)
    def dossier_reader():
        nav('Dossier');expect(page.locator('.dossier-folder-card').first).to_be_visible();page.locator('.dossier-folder-card').first.click()
        return {'buttons':page.locator('.dossier-open-folder button').all_text_contents(),'details':page.locator('.dossier-open-folder summary').all_text_contents()[:5]}
    check('Inspect dossier source interactions',dossier_reader)
    def date_edit():
        nav('Updates');page.get_by_label('Fichier du nouvel événement').set_input_files({'name':'dirty-check.txt','mimeType':'text/plain','buffer':b'Date : 10 octobre 2026\nSEC-210 re-test a venir.'})
        expect(page.get_by_role('button',name='Intégrer au projet')).to_be_enabled()
        page.locator('#update-text').fill('Date : 10 octobre 2026\nSophie Lambert doit effectuer le re-test SEC-210 avant le 12 octobre 2026.')
        expect(page.get_by_role('button',name='Intégrer au projet')).to_be_disabled()
        page.get_by_role('button',name='Analyser les impacts').click();expect(page.get_by_role('button',name='Intégrer au projet')).to_be_enabled()
        return 'Editing text requires fresh analysis before integration.'
    check('Update text edits cannot integrate stale analysis',date_edit)
    def evidence_failure():
        nav('Evidence');page.route('**/api/search',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Diagnostic service unavailable"}'))
        page.get_by_role('button',name='Search',exact=True).click();page.wait_for_timeout(300)
        alerts=page.get_by_role('alert').all_text_contents();assert alerts,'No visible error; browser errors: '+str(errors)
        page.unroute('**/api/search');return alerts
    check('Evidence handles unavailable backend without crashing',evidence_failure)
    results['page_errors']=errors;save();browser.close()
print(json.dumps({'target':results['target'],'gates':results['gates'],'commitments': [{'owner':x['owner'],'due':x['due'],'title':x['title']} for x in items]},ensure_ascii=True),flush=True)
