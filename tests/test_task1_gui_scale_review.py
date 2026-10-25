"""Actual compact-data regression; no solves or native filesystem access.
Run: python tests/test_task1_gui_scale_review.py BASELINE.html OUTPUT_DIRECTORY
Requires existing Playwright and Chromium, never installs anything.
"""
import base64, gzip, hashlib, json, math, re, statistics, struct, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from task1_top5_gui_refresh import refresh

baseline=Path(sys.argv[1]);out=Path(sys.argv[2]);modified=out/'index.html'
def packed(text):
    return re.search(r'<script id="packed" type="application/octet-stream">(.*?)</script>',text,re.S).group(1)
def sha(b):return hashlib.sha256(b).hexdigest()
a,b=baseline.read_text(),modified.read_text()
assert refresh(a)==b
assert packed(a)==packed(b)
payload=gzip.decompress(base64.b64decode(packed(a)));data=json.loads(payload)
# Byte identity covers catalog, rank order, holds, all values, masks, hashes and limits.
display=data['display'];grid=display['grid'];case=display['cases'][0]
assert case['id']==data['catalog']['canonical_baseline']['id']
def decode(s):return [x[0] for x in struct.iter_unpack('<e',base64.b64decode(s))]
xz=decode(case['planes']['maxTIS']['xz']);nx=len(grid['x_edges_mm'])-1
fat=[v for j,(z0,z1) in enumerate(zip(grid['z_faces_mm'],grid['z_faces_mm'][1:])) if 5.1<=(z0+z1)/2<10.1 for v in xz[j*nx:(j+1)*nx] if math.isfinite(v)]
assert (len(fat),min(fat),statistics.median(fat),max(fat),len(set(fat)))==(1120,8.,21.078125,32.59375,528)
xy=decode(case['planes']['maxTIS']['xy'][1]);valid=[v for v in xy if math.isfinite(v)]
assert len(valid)==5024 and min(valid)==4.04296875 and sum(v<8 for v in valid)==182
errors=[];requests=[];checks=0
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
    page=browser.new_page(viewport={'width':1540,'height':1100})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
    page.set_content(a);page.wait_for_function('window.task1Top5')
    baseline_fat=page.locator('.field-map').first.evaluate("c=>{const w=c.width,h=c.height,a=c.getContext('2d').getImageData(Math.floor(w*.45),Math.floor(h*.25),40,20).data;let yellow=0;for(let i=0;i<a.length;i+=4)if(a[i]===253&&a[i+1]===231&&a[i+2]===37)yellow++;return {yellow,total:a.length/4}}")
    assert baseline_fat['yellow']>baseline_fat['total']/2,baseline_fat
    page.locator('.case-card').first.screenshot(path=str(out/'baseline-panel.png'))
    page.close()
    page=browser.new_page(viewport={'width':1540,'height':1100})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
    page.set_content(b);page.wait_for_function("document.querySelectorAll('.panel-scale').length===12")
    assert page.locator('.panel-scale').count()==12
    assert page.locator('.field-map').first.get_attribute('data-vmax')=='5.028619255810101'
    before=page.evaluate('JSON.stringify(window.task1Top5)')
    for mode in display['color_limits']:
      page.select_option('#mode',mode)
      for metric in ('maxTIS','fixedTIS','RMS'):
        page.select_option('#metric',metric)
        for plane in ('xy','xz','yz'):
          page.select_option('#plane',plane)
          for depth in (range(5) if plane=='xy' else [0]):
            if plane=='xy':page.select_option('#depth',str(depth))
            for scope in ('global','primary_ROI'):
              page.select_option('#range',scope)
              limits=page.locator('.field-map').evaluate_all('(cs)=>cs.map(c=>Number(c.dataset.vmax))')
              assert limits==[display['color_limits'][mode][metric][scope][1]]*6
              assert len(set(page.locator('.contact-map').evaluate_all('(cs)=>cs.map(c=>c.dataset.vmax)')))==1
              assert page.locator('.panel-scale').count()==12
              checks+=1
    for i in range(12):
      page.select_option('#range','global' if i%2 else 'primary_ROI');page.evaluate('window.task1Top5.render()')
      assert page.locator('.panel-scale').count()==12
    page.select_option('#mode','skin_contact_only');page.select_option('#metric','maxTIS');page.select_option('#plane','xz');page.select_option('#range','primary_ROI')
    assert page.evaluate('JSON.stringify(window.task1Top5)')==before
    canvas=page.locator('.field-map').first
    values=canvas.evaluate('(c)=>({valid:Number(c.dataset.validCount),over:Number(c.dataset.overCount)})')
    assert values=={'valid':sum(map(math.isfinite,xz)),'over':sum(math.isfinite(v) and v>5.028619255810101 for v in xz)}
    canvas.scroll_into_view_if_needed();box=canvas.bounding_box()
    page.mouse.move(box['x']+43+(box['width']-55)/2,box['y']+11+7.6/25.1*218)
    assert '표시 상한 초과, 물리적 포화 아님' in page.locator('#hover').inner_text()
    assert 'Float16' in page.locator('#hover').inner_text()
    page.locator('.case-card').first.screenshot(path=str(out/'preview.png'),style='.controls,.hover{visibility:hidden}')
    page.select_option('#range','global');assert canvas.get_attribute('data-vmax')=='1346.400298562412'
    page.locator('.case-card').first.screenshot(path=str(out/'global-panel.png'),style='.controls,.hover{visibility:hidden}')
    page.select_option('#range','primary_ROI');page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250)
    assert page.evaluate('document.documentElement.scrollWidth')<=392
    page.screenshot(path=str(out/'mobile.png'))
    assert not errors and not requests,(errors,requests)
    version=browser.version;browser.close()
report={'status':'passed','source_commit':'f0749c17b99a4d4096b9b0fdbd070a3518190651','source_HTML_SHA256':sha(a.encode()),'modified_HTML_SHA256':sha(b.encode()),'packed_bytes_identical':True,'uncompressed_payload_SHA256':sha(payload),'catalog_arrays_ranking_holds_provenance_hashes_and_limits_unchanged':True,'original_native_files_independently_hashed':False,'browser':{'engine':'Chromium','version':version,'combinations':checks,'repeated_updates':12,'panel_colorbars':12,'baseline_yellow_pixel':baseline_fat,'hover_overrange_and_precision':True,'mobile_width':390,'errors':errors,'external_requests':requests},'slice_regression':{'XZ_actual_y_mm':grid['XZ_actual_y_mm'],'fat_display_cells':len(fat),'fat_min_median_max': [min(fat),statistics.median(fat),max(fat)],'fat_distinct_values':len(set(fat)),'XY_actual_z_mm':grid['XY_actual_depths_mm'][1],'XY_valid_cells':len(valid),'XY_min':min(valid),'XY_cells_below_8':sum(v<8 for v in valid),'scope':'Float16 finite display cells only, not whole-fat volume extrema or physical validation'},'new_PDE':0,'native_read':False,'full_convergence_or_physical_validation':False,'deployed':False}
(out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
