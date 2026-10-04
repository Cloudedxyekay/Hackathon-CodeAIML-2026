import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

HERE = Path(__file__).resolve().parent
results, errors, failed_requests, excluded = [], [], [], []

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda response: failed_requests.append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
    def block(route):
        excluded.append(route.request.url)
        route.abort()
    page.route('**/api/ask', block)
    page.route('**/api/project-memory/enrich', block)
    page.on('dialog', lambda dialog: dialog.accept())
    def step(name, action):
        before = len(errors)
        try:
            detail = action()
            if len(errors) > before:
                raise AssertionError(errors[before:])
            results.append({'test': name, 'status': 'PASS', 'detail': detail})
        except Exception as error:
            results.append({'test': name, 'status': 'FAIL', 'detail': str(error)[:1600]})
            page.screenshot(path=str(HERE / ('failure-' + str(len(results)) + '.png')), full_page=True)
        (HERE / 'browser-results.json').write_text(json.dumps({'results': results, 'page_errors': errors, 'http_errors': failed_requests, 'excluded_calls': excluded}, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(results[-1], ensure_ascii=True), flush=True)
    def nav(name):
        page.locator('nav').first.get_by_role('button', name=name, exact=True).click()
        expect(page.locator('.topbar h1')).to_have_text(name)
    def download(button, filename):
        with page.expect_download() as event:
            button.click()
        item = event.value
        item.save_as(str(HERE / filename))
        assert (HERE / filename).stat().st_size > 0
        return item.suggested_filename
    step('Initial timeline load', lambda: (page.goto('http://localhost:5174'), expect(page.locator('.memory-event').first).to_be_visible(), page.locator('.memory-event').count())[-1])
    def dashboard():
        nav('Dashboard')
        expect(page.get_by_text('Cible approuvée', exact=True)).to_be_visible()
        page.get_by_role('button', name='Ouvrir la mémoire').click()
        expect(page.locator('.topbar h1')).to_have_text('Timeline')
    step('Dashboard and linked navigation', dashboard)
    def timeline_filters():
        field = page.get_by_role('textbox', name='Rechercher dans les événements')
        field.fill('SEC-210')
        expect(page.locator('.memory-event').first).to_be_visible()
        titles = page.locator('.memory-event h3').all_text_contents()
        assert titles
        field.fill('zzzz-diagnostic-no-match')
        expect(page.locator('.memory-event')).to_have_count(0)
        field.fill('')
        for label in ['Type d’événement', 'Acteur cité', 'Sujet', 'Nature de la date']:
            select = page.get_by_role('combobox', name=label)
            values = select.locator('option').evaluate_all('(opts) => opts.map(o=>o.value)')
            if len(values)>1:
                select.select_option(values[1])
                select.select_option('')
        return titles
    step('Timeline search, no results and all filters', timeline_filters)
    def sources():
        page.locator('.memory-event').first.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.get_by_role('button', name='Lire le document extrait').first.click()
        expect(page.locator('.full-document pre')).to_be_visible()
        page.get_by_role('button', name='Fermer les sources').click()
        expect(page.get_by_role('dialog')).to_have_count(0)
    step('Timeline evidence and full source reader', sources)
    step('Filtered calendar ICS export', lambda: download(page.get_by_role('button', name='.ics', exact=True), 'timeline.ics'))
    def calendar():
        nav('Calendrier')
        page.get_by_role('button', name='Mois suivant').click()
        page.get_by_role('button', name='Mois précédent').click()
        day = page.locator('button[aria-label]').filter(has_text='22')
        labels = page.locator('button[aria-label]').evaluate_all('(els)=>els.map(e=>e.getAttribute("aria-label"))')
        assert any('événements' in s for s in labels)
        return labels[-10:]
    step('Calendar navigation and day grid', calendar)
    def progress():
        page.get_by_role('button', name='Avancement', exact=True).click()
        expect(page.get_by_text('SEC-210', exact=True).first).to_be_visible()
        return page.locator('main').inner_text()[-1500:]
    step('Progress plan and ticket register', progress)
    def dossier():
        nav('Dossier')
        expect(page.locator('.dossier-folder-card').first).to_be_visible()
        page.locator('.dossier-folder-card').first.click()
        expect(page.locator('.dossier-open-folder')).to_be_visible()
        return page.locator('.dossier-open-folder').inner_text()[:1000]
    step('Dossier category explorer', dossier)
    def dossier_filters():
        for select in page.locator('.dossier-filters select').all():
            values = select.locator('option').evaluate_all('(opts)=>opts.map(o=>o.value)')
            if len(values)>1:
                select.select_option(values[1]); select.select_option('')
        page.get_by_role('button', name='Réinitialiser les filtres').click()
        page.get_by_role('button', name=re.compile('Dossiers terminés')).click()
        page.get_by_role('button', name=re.compile('Dossiers à suivre')).click()
    step('Dossier filters and completed archive', dossier_filters)
    step('Dossier JSON export', lambda: download(page.get_by_role('button', name='Exporter le dossier JSON'), 'dossier.json'))
    def evidence():
        nav('Evidence')
        for query in ['INV-003', 'SEC-210', 'sécurité', 'accessibilité', 'zzzz-diagnostic-no-match']:
            page.locator('main input').fill(query)
            with page.expect_response('**/api/search'):
                page.get_by_role('button', name='Search', exact=True).click()
            page.wait_for_timeout(100)
            count = page.locator('.evidence-card').count()
            assert (count==0) if query.startswith('zzzz') else (count>0), (query, count)
    step('Evidence identifiers, accents and empty results', evidence)
    def bonus():
        nav('Bonus')
        expect(page.get_by_role('heading', name='Comparaison de projets')).to_be_visible()
        page.get_by_text('Ajouter un autre projet', exact=True).click()
        page.get_by_role('button', name=re.compile('Ajouter ATLAS')).click()
        expect(page.get_by_role('button', name='Comparer les projets')).to_be_enabled()
        page.get_by_role('button', name='Comparer les projets').click()
        expect(page.locator('.bonus-project-card')).to_have_count(2)
        for value in ['scope','decisions','owners','commitments','schedule','finance','risks','quality','']:
            page.locator('.bonus-actions select').select_option(value)
        return page.locator('.bonus-project-card').all_text_contents()
    step('Bonus demo comparison and all comparison axes', bonus)
    step('Comparison JSON export', lambda: download(page.get_by_role('button', name='Exporter', exact=True), 'comparison.json'))
    step('Executive PDF download', lambda: download(page.get_by_role('button', name='Générer le briefing PDF'), 'brief.pdf'))
    def brief():
        page.get_by_text('Briefing exécutif NOVA', exact=True).last.click()
        page.get_by_role('button', name='Afficher le briefing existant').click()
        expect(page.get_by_role('heading', name='Brief executif NOVA')).to_be_visible()
    step('Existing executive brief', brief)
    def import_event():
        nav('Updates')
        page.get_by_label('Fichier du nouvel événement').set_input_files('C:/Users/raman/AppData/Local/Temp/NOVA_TEST_Report_lancement_et_SEC210.eml')
        expect(page.get_by_role('button', name='Intégrer au projet')).to_be_enabled(timeout=30000)
        preview = page.locator('main').inner_text()
        (HERE/'import-preview.txt').write_text(preview, encoding='utf-8')
        page.get_by_role('button', name='Intégrer au projet').click()
        expect(page.get_by_role('button', name='Voir le calendrier')).to_be_visible(timeout=30000)
        (HERE/'import-integrated.txt').write_text(page.locator('main').inner_text(), encoding='utf-8')
        page.get_by_role('button', name='Voir le calendrier').click()
        expect(page.locator('.topbar h1')).to_have_text('Calendrier')
        nav('Dashboard')
        return page.locator('main').inner_text()
    step('Import IDE test email and linked dashboard/calendar refresh', import_event)
    def remove_restore():
        nav('Updates')
        first = page.locator('.update-history li').first
        first.get_by_role('button', name='Retirer cet import').click()
        expect(first.get_by_role('button', name='Restaurer cet import')).to_be_visible(timeout=30000)
        first.get_by_role('button', name='Restaurer cet import').click()
        expect(first.get_by_role('button', name='Retirer cet import')).to_be_visible(timeout=30000)
    step('Import removal and restoration', remove_restore)
    step('Local re-analysis', lambda: (nav('Timeline'), page.get_by_role('button',name='Ré-analyser',exact=True).click(), expect(page.get_by_role('button',name='Ré-analyser',exact=True)).to_be_enabled(timeout=30000)))
    def responsive():
        for width in [1440, 768, 390]:
            page.set_viewport_size({'width': width, 'height': 900})
            page.screenshot(path=str(HERE/f'timeline-{width}.png'), full_page=True)
        return page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    step('Desktop tablet and mobile layout', responsive)
    context.close(); browser.close()
