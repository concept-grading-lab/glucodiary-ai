"""Chromium DOM E2E test. The execution sandbox blocks all navigation, so HTML/CSS/JS are injected from the exact bundled files into a blank Chromium document. LocalStorage is emulated using the same Web Storage API to test persistence. No external network is involved."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1] / 'docs'
HTML=(ROOT/'index.html').read_text()
CSS=(ROOT/'demo.css').read_text()
CORE=(ROOT/'demo-core.js').read_text()
JS=(ROOT/'demo.js').read_text()
STORE_JS='''window.__memstore = {}; Object.defineProperty(window,"localStorage",{configurable:true,value:{getItem:(k)=>Object.prototype.hasOwnProperty.call(window.__memstore,k)?window.__memstore[k]:null,setItem:(k,v)=>{window.__memstore[k]=String(v)},removeItem:(k)=>{delete window.__memstore[k]},clear:()=>{window.__memstore={}}}});'''

def boot(page, store=None):
    page.set_content(HTML,wait_until='domcontentloaded',timeout=12000)
    page.add_style_tag(content=CSS)
    page.evaluate(STORE_JS)
    if store:
        page.evaluate('(s)=>Object.assign(window.__memstore,s)',store)
    page.add_script_tag(content=CORE)
    page.add_script_tag(content=JS)
    assert page.locator('#metrics .metric').count()==4

with sync_playwright() as p:
    launch={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
    if Path('/usr/bin/chromium').exists(): launch['executable_path']='/usr/bin/chromium'
    browser=p.chromium.launch(**launch)
    page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m: errors.append('console error: '+m.text) if m.type=='error' and 'ERR_' not in m.text else None)
    boot(page)
    assert 'SYNTHETIC' in page.locator('body').inner_text()
    assert page.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='23'
    assert page.locator('#metrics .metric').nth(3).locator('strong').inner_text()=='23/28'
    assert page.locator('#glucoseChart circle').count()>0
    initial_mean=float(page.locator('#metrics .metric').nth(1).locator('strong').inner_text())
    assert abs(initial_mean-page.evaluate('Core.summaries(Core.starterReadings()).avg'))<0.01
    print('PASS initial render, correctly calculated mean, chart, 23/28 progress')
    page.locator('#sampleAdd').click()
    assert page.locator('#panel-record').is_visible()
    assert page.locator('#readingValue').input_value()=='7.4'
    assert page.locator('#readingDate').input_value()=='2026-10-07'
    assert page.locator('#readingOccasion').input_value()=='before_sleep'
    assert page.locator('#readingTime').input_value()=='22:00'
    page.locator('#readingForm button[type=submit]').click()
    assert 'saved' in page.locator('#toast').inner_text().lower()
    assert page.locator('#entryRows tr').count()==24
    page.locator('[data-tab=dashboard]').click()
    assert page.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='24'
    assert page.locator('#metrics .metric').nth(3).locator('strong').inner_text()=='24/28'
    new_mean=float(page.locator('#metrics .metric').nth(1).locator('strong').inner_text())
    assert abs(new_mean-(initial_mean*23+7.4)/24)<0.02
    print('PASS enter sample, accurate mean, reading list and calendar recalculated')
    page.locator('[data-tab=record]').click()
    page.locator('#readingValue').fill('6.8')
    page.locator('#readingForm button[type=submit]').click()
    assert 'already a reading' in page.locator('#toast').inner_text()
    assert page.locator('#entryRows tr').count()==24
    print('PASS duplicate rejection')
    # Date bounds UI and contextual analysis
    page.locator('[data-tab=dashboard]').click()
    page.locator('#chartContext').select_option('before_sleep')
    assert 'reading' in page.locator('#chartSummary').inner_text()
    assert page.locator('#glucoseChart circle').count()>0
    page.locator('[data-tab=schedule]').click()
    assert page.locator('#scheduledCount').inner_text()=='28'
    assert page.locator('#scheduledCompleted').inner_text()=='24'
    assert page.locator('#scheduledMissing').inner_text()=='4'
    print('PASS filtering chart and schedule summary')
    page.locator('[data-tab=medications]').click()
    assert not page.locator('#supplementBody').is_visible()
    page.locator('#supplementEnabled').check()
    assert page.locator('#supplementBody').is_visible()
    assert page.locator('[data-supp]').count()==4
    page.locator('#previewReminder').click()
    assert 'No email or iPhone push was sent' in page.locator('#reminderPreview').inner_text()
    page.locator('[data-supp="2026-10-13"]').check()
    assert page.locator('[data-supp="2026-10-13"]').is_checked()
    print('PASS supplements optional, taken-state and reminder preview')
    page.locator('[data-tab=food]').click()
    assert not page.locator('#foodBody').is_visible()
    page.locator('#foodEnabled').check()
    assert page.locator('#recipeResults .recipe-card').count()==4
    page.locator('[data-allergy="milk"]').check()
    assert 'Paneer' not in page.locator('#recipeResults').inner_text()
    page.locator('[data-allergy="peanut"]').check()
    assert 'Peanut' not in page.locator('#recipeResults').inner_text()
    page.locator('#excludedIngredients').fill('ginger')
    assert 'chilla' not in page.locator('#recipeResults').inner_text().lower()
    page.locator('#cuisine').select_option('Mediterranean')
    assert 'Chickpea cucumber bowl' in page.locator('#recipeResults').inner_text()
    print('PASS food opt-in, allergy, ingredient and cuisine filters')
    page.locator('[data-tab=agents]').click()
    page.locator('#runTrace').click()
    assert page.locator('#agentTrace .trace-step').count()==4
    assert 'no live LLM call' in page.locator('#agentTrace').inner_text()
    assert 'Readings: 24' in page.locator('#agentTrace').inner_text()
    print('PASS 4-stage deterministic agent trace and evidence updates')
    # Persist browser state in mock localstorage between new page instances.
    store=page.evaluate('window.__memstore')
    page2=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
    page2.on('pageerror',lambda e:errors.append('mobile: '+str(e)))
    boot(page2,store)
    assert page2.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='24'
    page2.locator('[data-tab=food]').click()
    assert page2.locator('#foodEnabled').is_checked()
    assert page2.locator('[data-allergy="milk"]').is_checked()
    assert page2.locator('#cuisine').input_value()=='Mediterranean'
    print('PASS persisted state across new document, mobile viewport')
    # Check mobile page bounds and capture screenshots
    assert page2.evaluate('document.documentElement.scrollWidth <= window.innerWidth+2'),f"mobile horizontal overflow: {page2.evaluate('document.documentElement.scrollWidth')}"
    assert page2.evaluate('document.querySelector("#glucoseChart").getBoundingClientRect().right <= innerWidth'), 'Mobile chart clipped'
    assert page2.evaluate('document.querySelector("#completionRing").getBoundingClientRect().right <= innerWidth'), 'Mobile completion ring clipped'
    page2.locator('[data-tab=dashboard]').click()
    (ROOT.parent / 'tests' / '_screenshots').mkdir(exist_ok=True)
    page2.screenshot(path=str(ROOT.parent / 'tests' / '_screenshots' / 'mobile_test.png'),full_page=True)
    page.locator('#resetDemo').click()
    assert page.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='23'
    assert page.locator('#metrics .metric').nth(3).locator('strong').inner_text()=='23/28'
    print('PASS reset returns original samples')
    # Delete an existing sample and verify the summary changes; then exercise empty-data mode.
    page.locator('[data-tab=record]').click()
    assert page.locator('#entryRows tr').count()==23
    page.locator('#entryRows [data-remove]').first.click()
    assert page.locator('#entryRows tr').count()==22
    page.locator('[data-tab=dashboard]').click()
    assert page.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='22'
    page.locator('[data-tab=record]').click()
    for _ in range(22):
        page.locator('#entryRows [data-remove]').first.click()
    page.locator('[data-tab=dashboard]').click()
    assert page.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='0'
    assert page.locator('#metrics .metric').nth(1).locator('strong').inner_text()=='—'
    assert 'No readings' in page.locator('#glucoseChart text').text_content()
    page.locator('#runTrace').click() if page.locator('#runTrace').is_visible() else None
    page.locator('#resetDemo').click()
    assert page.locator('#metrics .metric').nth(0).locator('strong').inner_text()=='23'
    print('PASS deletion, all-readings-empty mode, zero-data chart and recovery')
    page.screenshot(path=str(ROOT.parent / 'tests' / '_screenshots' / 'desktop_test.png'),full_page=True)
    assert errors==[],f'Errors: {errors}'
    print('PASS no unhandled JavaScript exceptions')
    browser.close()
