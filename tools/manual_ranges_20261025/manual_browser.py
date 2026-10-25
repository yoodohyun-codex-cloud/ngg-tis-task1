"""Actual browser checks for user-owned ranges; parent owns finite resources."""
from pathlib import Path
import json,os,tempfile

def require(ok,msg):
    if not ok:raise ValueError(msg)
def check(html,guard,state,out):
    from playwright.sync_api import sync_playwright
    errors=[];requests=[];out=Path(out)
    with tempfile.TemporaryDirectory(prefix='mrg-',dir='/dev/shm')as temporary:
        scratch=Path(temporary);state['scratch']=scratch
        for name in('tmp','config','cache','dumps'):(scratch/name).mkdir()
        with sync_playwright()as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'p'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1500,height=1100),
                env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp'),XDG_CONFIG_HOME=str(scratch/'config'),XDG_CACHE_HOME=str(scratch/'cache')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0','--crash-dumps-dir='+str(scratch/'dumps')])
            try:
                page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
                page.on('request',lambda q:requests.append(q.url)if q.url.startswith(('http:','https:'))else None)
                page.set_content(html,wait_until='load');page.wait_for_function('window.task1ManualRanges && window.task1PaperFigure && Object.keys(window.task1ManualRanges.snapshot().charts).length===22',timeout=30000)
                def snapshot():return page.evaluate('window.task1ManualRanges.snapshot()')
                def valid():
                    guard();v=page.evaluate('window.task1ManualRanges.validateForTest()');require(v.get('passed')is True,'Manual state/canvas failure: '+str(v));return v
                initial=valid();science=page.evaluate('window.task1PaperFigure.validateForTest()');require(science.get('passed')is True,'Original scientific regression')
                # Real group form interaction, not only calls to the helper API.
                group=page.locator('[data-manual-group="EColour"]')
                group.locator('[data-field="cMin"]').fill('1');group.locator('[data-field="cMax"]').fill('8');group.locator('[data-action="apply"]').click()
                state1=snapshot();require(all(x['range']['cMin']==1 and x['range']['cMax']==8 for x in state1['charts'].values()if x['kind']=='EMap'),'Actual common colour form failed')
                count=0;expected={}
                # Edit every numerical/XY layout plot with its own actual form.
                for cid,chart in state1['charts'].items():
                    guard();kind=chart['kind'];z=chart['options'].get('axisY')=='z'
                    if kind=='wave':fields=dict(xMin=10,xMax=20,yMin=-5,yMax=7)
                    elif kind=='profile':fields=dict(xMin=10,xMax=20,yMin=0,yMax=5)
                    else:
                        fields=dict(xMin=-6,xMax=6,yMin=13 if z else -6,yMax=21 if z else 6)
                        if kind in('EMap','JMap'):fields.update(cMin=0,cMax=5 if kind=='EMap'else 10)
                    panel=page.locator('details[data-manual-for="'+cid+'"]');panel.evaluate('(e)=>e.open=true')
                    for key,value in fields.items():panel.locator('[data-field="'+key+'"]').fill(str(value))
                    panel.locator('[data-action="apply"]').click();panel.evaluate('(e)=>e.open=false')
                    actual=snapshot()['charts'][cid]['range'];require(all(actual[k]==v for k,v in fields.items()),'Per-plot form failed: '+cid)
                    expected[cid]=fields;count+=1;valid()
                # Invalid range is refused transactionally and shown inline.
                cid='paper-map-TIS-am';panel=page.locator('details[data-manual-for="'+cid+'"]');panel.evaluate('(e)=>e.open=true')
                before=page.evaluate('JSON.stringify(window.task1ManualRanges.exportSettings())')
                panel.locator('[data-field="cMin"]').fill('9');panel.locator('[data-field="cMax"]').fill('1');panel.locator('[data-action="apply"]').click()
                require(page.evaluate('JSON.stringify(window.task1ManualRanges.exportSettings())')==before,'Invalid edit mutated applied state')
                require(panel.locator('[role="alert"]').inner_text().strip(),'Invalid numeric input has no visible error')
                panel.locator('[data-field="cMin"]').fill('0');panel.locator('[data-field="cMax"]').fill('5');panel.locator('[data-action="apply"]').click();panel.evaluate('(e)=>e.open=false')
                combos=0
                def stable():
                    valid();s=snapshot()
                    for cid,fields in expected.items():require(all(s['charts'][cid]['range'][k]==v for k,v in fields.items()),'Changing a variable discarded manual axes: '+cid)
                    waves=page.evaluate('window.task1PaperFigure.getState().manual_wave_windows')
                    require(all(v['first_ms']==10 and v['last_ms']==20 and v['samples']<=40001 for v in waves.values()),'Time axes did not reconstruct the requested actual waveform window')
                for mode in('raw_1Vpp','skin_contact_only'):
                    for match in('ROI_energy_RMS','centre20_E_RMS'):
                        page.select_option('#mode',mode);page.select_option('#match',match)
                        for plane in('XZ','YZ','XY_17.5'):
                            for direction in('x','y','z'):
                                for color in('linear','log'):
                                    page.evaluate('(v)=>{for(const[id,val]of Object.entries(v))document.getElementById(id).value=val;document.getElementById("paper-color").dispatchEvent(new Event("change",{bubbles:true}));}',{'paper-plane':plane,'paper-direction':direction,'paper-color':color,'paper-window':'2'})
                                    stable();combos+=1
                        for plane in('XZ','YZ','XY_17.5'):
                            for tone in('all','3000','3030'):
                                page.evaluate('(v)=>{for(const[id,val]of Object.entries(v))document.getElementById(id).value=val;document.getElementById("shape-time").dispatchEvent(new Event("input",{bubbles:true}));}',{'shape-plane':plane,'shape-frequency':tone,'shape-time':'16.666667'})
                                stable();combos+=1
                        for plane in('xy','xz','yz'):
                            page.select_option('#plane',plane);stable();combos+=1
                saved=page.evaluate('window.task1ManualRanges.exportSettings()');page.evaluate('window.task1ManualRanges.resetAll()');valid()
                page.evaluate('(v)=>window.task1ManualRanges.importSettings(v)',saved);stable()
                require(page.evaluate('JSON.stringify(window.task1ManualRanges.exportSettings())')==json.dumps(saved,separators=(',',':'),ensure_ascii=False),'Settings round-trip changed values')
                clipped=snapshot();require(any((c.get('note')or{}).get('high',0)>0 for c in clipped['charts'].values()),'Manual clipping is not disclosed')
                final_science=page.evaluate('window.task1PaperFigure.validateForTest()');require(final_science.get('passed')is True,'Scientific values changed with manual clipping')
                (out/'manual-settings-example.json').write_text(json.dumps(saved,indent=2))
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS');page.select_option('#paper-plane','XZ');page.select_option('#paper-direction','x');page.select_option('#paper-color','log')
                page.locator('#manual-range-controls').scroll_into_view_if_needed();page.screenshot(path=str(out/'manual-controls-preview.jpg'),type='jpeg',quality=80,full_page=False)
                page.locator('#paper-figure').scroll_into_view_if_needed();page.screenshot(path=str(out/'field-shape-preview.jpg'),type='jpeg',quality=80,full_page=False)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100);width=page.evaluate('document.documentElement.scrollWidth');require(width<=392 and not errors and not requests,'Mobile/offline/JavaScript gate')
                return dict(status='passed',actual_data=True,manually_edited_chart_forms=count,persistence_selection_combinations=combos,invalid_input_transaction_passed=True,
                    arbitrary_time_window_ms=[10,20],settings_export_import_roundtrip_passed=True,clipping_disclosed=True,original_scientific_checks=final_science,
                    mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,new_PDE=0)
            except BaseException as error:
                diagnostic=dict(error_type=type(error).__name__,error=str(error),JS_errors=errors,external_requests=requests)
                try:diagnostic['ready']=page.evaluate('({manual:!!window.task1ManualRanges,paper:!!window.task1PaperFigure,shape:!!window.task1FieldShape,base:!!window.task1Best1Pair})')
                except BaseException:pass
                (out/'browser-diagnostic.json').write_text(json.dumps(diagnostic,indent=2))
                raise
            finally:context.close()
    state.pop('scratch',None)
