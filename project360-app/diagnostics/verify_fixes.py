"""Verify the four reported bugs with the actual IDE email on copied data."""
import hashlib
import io
import json
from pathlib import Path
import httpx
from pypdf import PdfReader
from playwright.sync_api import sync_playwright, expect

HERE = Path(__file__).resolve().parent
client = httpx.Client(base_url='http://127.0.0.1:8010', timeout=60)
results = []
def memory(): return client.get('/api/project-memory').json()
def save(): (HERE/'fix-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width':1440, 'height':1000}, accept_downloads=True)
    page.set_default_timeout(15000)
    errors=[];models=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.on('dialog',lambda dialog:dialog.accept())
    def block(route):models.append(route.request.url);route.abort()
    page.route('**/api/ask',block);page.route('**/api/project-memory/enrich',block)
    def nav(label):page.locator('nav').first.get_by_role('button',name=label,exact=True).click()
    def check(name,fn):
        try:detail=fn();result={'test':name,'status':'PASS','detail':detail}
        except Exception as exc:result={'test':name,'status':'FAIL','detail':str(exc)[:2000]}
        results.append(result);save();print(json.dumps(result,ensure_ascii=True),flush=True)
    page.goto('http://localhost:5174');expect(page.locator('.memory-event').first).to_be_visible()
    def integrate():
        assert memory()['schedule']['current_target']=='2026-10-22'
        nav('Updates');page.get_by_label('Fichier du nouvel événement').set_input_files('C:/Users/raman/AppData/Local/Temp/NOVA_TEST_Report_lancement_et_SEC210.eml')
        expect(page.get_by_role('button',name='Intégrer au projet')).to_be_enabled()
        actions=page.locator('.update-actions').inner_text()
        for phrase in ['Je mettrai','Sophie Lambert doit','Melissa Gagnon doit']:
            assert phrase in actions,actions
        with page.expect_response('**/integrate') as event:page.get_by_role('button',name='Intégrer au projet').click()
        integrated=event.value.json()
        (HERE/'fixed-import.json').write_text(json.dumps(integrated,ensure_ascii=False,indent=2),encoding='utf-8')
        expect(page.get_by_role('button',name='Voir le dossier')).to_be_visible()
        assert memory()['schedule']['current_target']=='2026-10-29'
        assert sorted(g['id'] for g in memory()['gates'])==['ACC-303','OPS-601','SEC-210']
        return {'target':'2026-10-29','specific_actions':3,'gates_still_open':3}
    check('Actual email preview and integration includes three specific actions',integrate)
    def dossier():
        nav('Dossier');expect(page.locator('.dossier-brief')).to_contain_text('2026-10-29')
        page.locator('.dossier-folder-card').filter(has_text='Date de lancement et préparatifs').click()
        folder=page.locator('.dossier-open-folder')
        expect(folder.locator('.dossier-column').first).to_contain_text('2026-10-29')
        historical=folder.locator('details.dossier-column');historical.locator('summary').click()
        expect(historical).to_contain_text('22 octobre')
        actions=folder.locator('.dossier-column').filter(has=page.get_by_role('heading',name='Actions / points ouverts'))
        for value in ['2026-10-07','2026-10-12','2026-10-13']:expect(actions).to_contain_text(value)
        with page.expect_download() as event:page.get_by_role('button',name='Exporter le dossier JSON').click()
        event.value.save_as(str(HERE/'fixed-dossier.json'))
        data=json.loads((HERE/'fixed-dossier.json').read_text(encoding='utf-8'));assert '2026-10-29' in data['summary']['status']
        return 'Current facts, header, deadlines, historical disclosure and JSON export verified.'
    check('Dossier current versus historical state and all new deadlines',dossier)
    def brief():
        nav('Bonus');page.locator('details.panel').filter(has=page.locator('summary',has_text='Briefing exécutif NOVA')).locator('summary').click()
        page.get_by_role('button',name='Afficher le briefing existant').click();expect(page.get_by_role('heading',name='Brief executif NOVA')).to_be_visible()
        expect(page.locator('main')).to_contain_text('2026-10-29')
        data=client.get('/api/brief').json();assert data['as_of']=='2026-10-05'
        assert {'2026-10-07','2026-10-12','2026-10-13'}.issubset({item['due'] for item in data['open_actions']})
        return {'as_of':data['as_of'],'live_target_in_brief':True,'new_actions_in_brief':True}
    check('Existing executive briefing uses current evidence and commitments',brief)
    def pdf():
        with page.expect_download() as event:page.get_by_role('button',name='Générer le briefing PDF').click()
        event.value.save_as(str(HERE/'fixed-brief.pdf'));text='\n'.join(p.extract_text() for p in PdfReader(str(HERE/'fixed-brief.pdf')).pages)
        for value in ['2026-10-29','2026-10-07','2026-10-12','2026-10-13']:assert value in text,value
        section=text[text.rfind('2026-10-05 · Le lancement est reporté'):]
        section=section[:section.find('Ce qui reste à faire')]
        assert 'Nicolas Perron' in section,section
        assert 'connecteur' not in section.lower(),section
        assert 're-test' in section,section
        return 'Downloaded PDF has updated target, three actions, Nicolas attribution and new-source context only.'
    check('PDF rationale attribution and task propagation',pdf)
    def lifecycle():
        nav('Updates');first=page.locator('.update-history li').first
        first.get_by_role('button',name='Retirer cet import').click();expect(first.get_by_role('button',name='Restaurer cet import')).to_be_visible()
        assert memory()['schedule']['current_target']=='2026-10-22'
        for endpoint in ['/api/dossier','/api/brief']:assert '2026-10-22' in client.get(endpoint).json()['summary']['status'] if endpoint=='/api/dossier' else '2026-10-22' in client.get(endpoint).json()['status']
        nav('Dossier');expect(page.locator('.dossier-brief')).to_contain_text('2026-10-22')
        nav('Updates');first=page.locator('.update-history li').first;first.get_by_role('button',name='Restaurer cet import').click();expect(first.get_by_role('button',name='Retirer cet import')).to_be_visible()
        assert memory()['schedule']['current_target']=='2026-10-29'
        page.reload();expect(page.locator('.memory-event').first).to_be_visible()
        nav('Dossier');expect(page.locator('.dossier-brief')).to_contain_text('2026-10-29')
        page.get_by_role('button',name='Ré-analyser le corpus').click();expect(page.get_by_role('button',name='Ré-analyser le corpus')).to_be_enabled(timeout=30000)
        expect(page.locator('.dossier-brief')).to_contain_text('2026-10-29')
        nav('Dashboard');expect(page.locator('main')).to_contain_text('29 octobre')
        return 'Removal, restoration, page reload and local re-analysis keep summaries and dashboard consistent.'
    check('Import remove restore reload re-analysis consistency',lifecycle)
    check('No browser exceptions or model calls',lambda: (not errors and not models) or (_ for _ in ()).throw(AssertionError({'errors':errors,'models':models})))
    browser.close()
hashes=json.loads((HERE/'original-hashes.json').read_text(encoding='utf-8'))
assert all(Path(name).exists() and hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in hashes.items())
results.append({'test':'Original data unchanged','status':'PASS','detail':len(hashes)});save()
