import hashlib
import io
import json
from pathlib import Path
import httpx
from pypdf import PdfReader
from playwright.sync_api import sync_playwright, expect

HERE=Path(__file__).resolve().parent
c=httpx.Client(base_url='http://127.0.0.1:8010',timeout=60)
results=[]
def check(name,fn):
    try:detail=fn();row={'test':name,'status':'PASS','detail':detail}
    except Exception as e:row={'test':name,'status':'FAIL','detail':str(e)[:2000]}
    results.append(row);(HERE/'final-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(row,ensure_ascii=True),flush=True)
def gates():
    before=c.get('/api/project-memory').json();routes=[]
    try:
        for ticket,author in [('SEC-210','Sophie Lambert'),('ACC-303','Mélissa Gagnon'),('OPS-601','Olivier Côté')]:
            content=f'From: {author} <reviewer@example.test>\nDate: Sat, 10 Oct 2026 10:00:00 -0400\nSubject: Validation {ticket}\n\n{ticket} est ferme apres re-test. Valide. Je ferme.'.encode()
            draft=c.post('/api/updates/preview',files={'file':('accept-'+ticket+'.eml',content)});assert draft.status_code==200,draft.text
            route='/api/updates/'+draft.json()['id'];routes.append(route)
            response=c.post(route+'/integrate',json={});assert response.status_code==200,response.text
            assert ticket not in [g['id'] for g in c.get('/api/project-memory').json()['gates']],ticket
        current=c.get('/api/project-memory').json();assert not current['gates']
        assert not c.get('/api/dossier').json()['verification_tasks'][0]['id'].startswith('gate-')
        pdf=c.get('/api/brief/pdf');text='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
        assert 'Bloquant · SEC-210' not in text
        return {'remaining_gates':len(current['gates']),'conditional':current['schedule']['conditional'],'completed_tickets':current['stats']['completed_tickets']}
    finally:
        for route in reversed(routes):assert c.post(route+'/remove').status_code==200
        after=c.get('/api/project-memory').json();assert after['gates']==before['gates']
# Covered in the first run; keep re-runs read-only for this scenario.
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
    page.goto('http://localhost:5174');expect(page.locator('.memory-event').first).to_be_visible()
    def nav(label):page.locator('nav').first.get_by_role('button',name=label,exact=True).click()
    def search_errors():
        nav('Evidence');input=page.get_by_label('Evidence query')
        for body,status in [('{}',503),('{}',200)]:
            page.route('**/api/search',lambda route,request,b=body,s=status:route.fulfill(status=s,content_type='application/json',body=b))
            input.fill('SEC-210');input.press('Enter');expect(page.get_by_role('alert')).to_be_visible()
            page.unroute('**/api/search')
        input.fill('SEC-210');input.press('Enter');expect(page.locator('.evidence-card').first).to_be_visible();expect(page.get_by_role('alert')).to_have_count(0)
        input.fill('zzzz-no-match-diagnostic');input.press('Enter');expect(page.get_by_role('status')).to_have_text('Aucun document ne correspond à cette recherche.')
        input.fill(' ');expect(page.get_by_role('button',name='Search',exact=True)).to_be_disabled()
        assert not errors,errors
        return '503, malformed response, retry, Enter, no results and whitespace verified; no browser exceptions.'
    check('Search fix under errors and recovery',search_errors)
    def reader():
        nav('Dossier');expect(page.locator('.dossier-folder-card').first).to_be_visible();page.locator('.dossier-folder-card').first.click()
        page.locator('.dossier-item').first.locator('summary').first.click()
        buttons=page.locator('.dossier-open-folder button').all_text_contents()
        source=page.get_by_role('button',name='Lire le document extrait').first
        if source.count()==0:source=page.get_by_role('button',name='Voir le document').first
        assert source.count(),buttons
        source.click();expect(page.get_by_role('dialog')).to_be_visible();expect(page.locator('#dossier-source-heading')).not_to_have_text('Lecture du document')
        page.keyboard.press('Escape');expect(page.get_by_role('dialog')).to_have_count(0)
        link=page.locator('.dossier-item').first.get_by_role('link',name='Télécharger l’original',exact=False).first
        with page.expect_download() as event:link.click()
        item=event.value;item.save_as(str(HERE/'dossier-original.txt'));assert (HERE/'dossier-original.txt').stat().st_size>0
        return 'Source modal, original download and Escape tested.'
    check('Dossier expanded document and full source modal',reader)
    def archive():
        nav('Timeline');expect(page.locator('.memory-event').first).to_be_visible();page.locator('.memory-event').first.click()
        title=page.locator('#source-title').inner_text();page.get_by_role('button',name='Archiver',exact=True).click();expect(page.get_by_role('dialog')).to_have_count(0)
        summary=page.get_by_text('Tâches et événements archivés / supprimés',exact=False).last;summary.click()
        page.get_by_role('button',name=title+' · Archivé',exact=True).click();page.get_by_role('button',name='Restaurer',exact=True).click();expect(page.get_by_role('dialog')).to_have_count(0)
        return title
    check('Browser event archive and restore',archive)
    def calendar():
        nav('Calendrier');grid=page.locator('button[aria-label]').filter(has_text='29');grid.first.click()
        text=page.locator('main').inner_text();assert '2026' in text
        with page.expect_download() as event:page.get_by_role('button',name='.ics',exact=True).click()
        event.value.save_as(str(HERE/'current-calendar.ics'));raw=(HERE/'current-calendar.ics').read_bytes();assert max(len(line) for line in raw.split(b'\r\n'))<=75
        assert b'DTSTART;VALUE=DATE:20261029' in raw
        return 'Current approved launch exported; calendar RFC line lengths valid.'
    check('Calendar selected day and updated ICS integrity',calendar)
    def mobile():
        measurements={}
        for tab in ['Dashboard','Dossier','Evidence','Timeline','Calendrier','Updates','Bonus']:
            page.set_viewport_size({'width':1440,'height':900});nav(tab)
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150)
            measurements[tab]=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
            if tab=='Updates':
                measurements[tab]['overflow']=page.evaluate('Array.from(document.querySelectorAll("*")).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,15)')
            page.screenshot(path=str(HERE/('mobile-'+tab.lower()+'.png')),full_page=True)
        overflow=page.evaluate('Array.from(document.querySelectorAll("*" )).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,15)')
        assert all(v['viewport']==v['document'] for v in measurements.values()),measurements
        return measurements
    check('All seven non-Ask tabs mobile overflow check',mobile)
    browser.close()
def originals():
    expected=json.loads((HERE/'original-hashes.json').read_text(encoding='utf-8'))
    assert all(Path(path).exists() and hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in expected.items())
    return len(expected)
check('Final original data hash verification',originals)
