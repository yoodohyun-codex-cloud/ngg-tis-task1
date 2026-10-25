#!/usr/bin/env python3
"""One finite owner: actual two-tone waveform metric check, immutable export,
cloud copy, and exact blocked next-batch status. No PDE or budget expansion."""
import os,sys,time,json,hashlib,base64,gzip,signal,subprocess,threading,shutil,math
from pathlib import Path
sys.dont_write_bytecode=True
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['GODEBUG']='http2client=0'
ROOT=Path('/workspace/ngg-tis-task1');RUN=Path('/workspace/task1-experiment-2000-2010-20261025-run');OUT=RUN/'final-delivery-r2';SOURCE=Path('/dev/shm/task1-experiment-report-20261025/source');DOC='docs/TASK1_EXPERIMENT_2000_2010_20261025';LEDGER=ROOT/'runtime/task1-budget.json';REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020';PARENT='cb47b5f91338d306ffa177f6e4689ccf3c04c3f7';CAP=30;CASE='baseline-square15-human-sine2000-2010-xy80'
sys.path[:0]=[str(ROOT/'tools'),str(SOURCE)]
import task1_bounded_continuation as bounded,task1_resource_policy as policy

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,obj):
 with Path(p).open('x')as f:json.dump(obj,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
def main():
 with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
  ledger=policy.load_ledger(LEDGER);require(policy.remaining_seconds(ledger)>=CAP,'Originaltimebudget');require(not OUT.exists(),'Preserve attempts');OUT.mkdir();start=time.monotonic();deadline=start+CAP;pid=os.getpid();ticks=bounded.ticks(pid);owned={pid:ticks};stop=threading.Event();state=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  receipt=dict(status='failed_preserved',schema='task1-2k-final-delivery-v1',new_PDE=0,started_utc=bounded.now(),pid=pid,proc_start_ticks=ticks,cap_seconds=CAP,Windows_saved=False)
  def guard():
   rss=sum(bounded.rss(p)for p,t in bounded.owned_descendants(pid,ticks,dict(owned)).items()if bounded.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));require(time.monotonic()<deadline,'Finitefinaldeadline');require(rss+tmp<=3*1024**3,'OriginalRAM3GiB')
  def interrupt(s,f):raise TimeoutError(state.get('error','Finitefinalinterrupted'))
  def monitor():
   while not stop.wait(1):
    try:guard()
    except BaseException as e:state['error']=str(e);os.kill(pid,signal.SIGTERM);return
  handlers={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
  for s in handlers:signal.signal(s,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def api(endpoint,obj=None,method='GET'):
   guard();argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
   if obj is not None:argv+=['--input','-']
   p=subprocess.Popen(argv,stdin=subprocess.PIPE if obj is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,TMPDIR=str(RUN/'tmp')));owned[p.pid]=bounded.ticks(p.pid)
   try:
    raw,err=p.communicate(input=None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode(),timeout=max(.05,deadline-time.monotonic()));require(p.returncode==0,'GitHubrequestfailed: '+err.decode(errors='replace')[:500]);return json.loads(raw)
   finally:
    if p.poll()is None:p.kill();p.wait(timeout=2)
  def publish(files,parent,message):
   require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrentadvancepreserved');base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
   for target,p in files.items():
    raw=p.read_bytes();created=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');gitsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();require(created['sha']==gitsha,'Exactblob');back=base64.b64decode(api('git/blobs/'+gitsha)['content']);require(back==raw,'Fullreadback');entries.append(dict(path=target,mode='100644',type='blob',sha=gitsha));proof[target]=dict(SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),Git_blob_SHA=gitsha,readback_passed=True)
   tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrentadvance');api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Refreadback');return dict(status='published_readback_verified',commit=commit,files=proof)
  try:
   new(OUT/'registration.json',dict(new_PDE=0,source_SHA256=sha(__file__),finite_seconds=CAP,remaining_before_seconds=policy.remaining_seconds(ledger),waveform_QA=dict(window_s=.1,samples=65536,envelope_relative_tolerance=.001,RMS_relative_tolerance=1e-10,FFT_phasor_relative_tolerance=1e-10),scope='Actual native electric-field projections; not probe potential Vpp or hardware'))
   import numpy as np
   summary=read(RUN/'modulation-completion/summary.json');stats=summary['scenarios']['human_2000_2010_sine']['statistics'];basis=RUN/'bases'/CASE;n=351680
   def field(f,c):return np.frombuffer(gzip.decompress((basis/('field-'+str(f)+'.bin.gz')).read_bytes()),dtype='<c16').reshape(2,n,3)[c]
   E1=field(2000,0);E2=field(2010,1)
   with np.load(RUN/'modulation-completion/scalars.npz',allow_pickle=False)as a:winners=np.array(a['winner_direction_index'],copy=True)
   sys.path.insert(0,'/dev/shm/task1-experiment-2000-2010-20261025/source');from experiment_math import _directions
   directions=_directions();centre=summary['actual_native_waveform_check']['native_cell_index'];points=[('near_centre20',centre),('target_max',stats['target']['fundamental_maxTIS_2074_V_m']['maximum_location']['native_cell_index']),('target_P10_representative',stats['target']['fundamental_maxTIS_2074_V_m']['quantiles']['P10']['representative']['native_cell_index']),('global_SC_hotspot',stats['total']['fundamental_maxTIS_2074_V_m']['maximum_location']['native_cell_index']),('surface_without_SC_max',stats['surface_without_SC']['fundamental_maxTIS_2074_V_m']['maximum_location']['native_cell_index'])];N=65536;t=np.arange(N)*.1/N;rows=[];hilbert=np.zeros(N);hilbert[0]=hilbert[N//2]=1;hilbert[1:N//2]=2
   for label,i in points:
    guard();direction=directions[winners[i]];a=complex(E1[i]@direction);b=complex(E2[i]@direction);wave=np.real(a*np.exp(2j*np.pi*2000*t)+b*np.exp(2j*np.pi*2010*t));spectrum=np.fft.fft(wave);envelope=abs(np.fft.ifft(spectrum*hilbert));theory=2*min(abs(a),abs(b));measured=float(envelope.max()-envelope.min());rms=float(np.sqrt(np.mean(wave**2)));analytic=float(np.sqrt((abs(a)**2+abs(b)**2)/2));am_error=abs(measured-theory)/max(theory,1e-30);fft_error=max(abs(2*spectrum[200]/N-a),abs(2*spectrum[201]/N-b))/max(abs(a),abs(b),1e-30);passed=am_error<=.001 and abs(rms-analytic)<=1e-12+1e-10*analytic and fft_error<=1e-10;require(passed,'Predeclaredactualwaveformgatefailed');rows.append(dict(label=label,native_cell_index=i,direction=direction.tolist(),analytic_AM_V_m=theory,Hilbert_envelope_max_minus_min_V_m=measured,AM_relative_error=am_error,temporal_RMS_V_m=rms,analytic_RMS_V_m=analytic,FFT_phasor_relative_error=float(fft_error),passed=bool(passed)))
   del E1,E2,winners;new(OUT/'waveform-validation.json',dict(status='five_actual_native_projections_passed',new_PDE=0,window_seconds=.1,samples=N,metric='Hilbert analytic-envelope maximum minus minimum, comparedwith2min(|n.E1|,|n.E2|); common integer-period record',predeclared_QA=read(OUT/'registration.json')['waveform_QA'],rows=rows,scope='NativeEprojectionV/m; finite2074sampleddirections; not Vpp probe, activation or safety validation'))
   oldgui=RUN/'publication-recovery-r2/GUI/index.html';document=oldgui.read_text();table='<section><h2>새 2 kHz native 합성파 검증</h2><p>실제 전기장 방향 투영의 0.1초·65,536표본에서 Hilbert envelope·RMS·FFT를 확인했습니다. 프로브 전위차 Vpp나 장비 검증과 구분합니다.</p><div class="scroll"><table><tr><th>위치</th><th>이론 변조 V/m</th><th>합성파 envelope 차이 V/m</th><th>상대 차이</th></tr>'+''.join('<tr><td>'+r['label']+'</td><td>'+format(r['analytic_AM_V_m'],'.7g')+'</td><td>'+format(r['Hilbert_envelope_max_minus_min_V_m'],'.7g')+'</td><td>'+format(r['AM_relative_error'],'.3g')+'</td></tr>'for r in rows)+'</table></div></section>'
   with(OUT/'verified-waveforms.html').open('x')as f:f.write(document.replace('</main>',table+'</main>',1))
   nextbatch=dict(schema='task1-next-minimum-XY-diagnostic-proposal-v1',feedback_id='T1-F010:MIN2K-20261025',adopted_source_commit='1d32c5734cce73fd13a671edfc264d9d9cb327e4',executed_result_commit=PARENT,latest_run=RUN.name,native_gates='five passed; independent5percentQA failed',next_condition=dict(status='selected_not_started_time_budget_insufficient',frequency_Hz=2000,RHS=2,geometry_mm=[50,.1,5,5,15],XY_mm=.5,SC_cells=2,bulk_cells=[14,14,40],pads=4,outputs=2,return_topology='common-return; inactiveoutput0V/50ohm',only_change='XY0.625to0.5; singlecarrierdiagnostic, not new fullTISresult',purpose='Separate XY/staircase contribution to independentinterface mismatch',finite_stage_caps_seconds=dict(prepare=15,publish_source=20,execute=60,postprocess=20,publish_results=55,persist=5),total_reservation_seconds=175,estimate_basis='Onecarrier/twoRHS versus current2carriers/fourRHS40.443s; largerXYgrid, conservative60s execution cap; complete verification/publication tail reserved'),live_PDE_workers=0,source_not_yet_compiled_or_preregistered=True,Windows_saved=False,COMSOL_runtime_verified=False)
   new(OUT/'feedback-and-next-batch.json',nextbatch)
   firstfiles={DOC+'/'+name:OUT/name for name in('waveform-validation.json','verified-waveforms.html','feedback-and-next-batch.json')};firstfiles.update({'tools/experiment_report_20261025/'+name:SOURCE/name for name in('finalize.py','experiment_export.py')});first=publish(firstfiles,PARENT,'Verify actual native two-tone waveforms and record blocked minimumXYbatch');new(OUT/'waveform-publication.json',first)
   import experiment_export
   resultpub=read(RUN/'result-publication.json');sourcepub=read(RUN/'source-publication.json');nativepub={**resultpub,'files':{k:v for k,v in resultpub['files'].items()if not k.startswith(DOC+'/')}};guipub={**resultpub,'files':{k:v for k,v in resultpub['files'].items()if k.startswith(DOC+'/')}};entries=experiment_export.build_entries([('SOURCE',sourcepub),('EXPERIMENT',nativepub),('GUI',guipub),('GUI',first)])
   with(OUT/'Save-TIS-2k-Results.ps1').open('x',encoding='ascii')as f:f.write(experiment_export.powershell_document(entries))
   new(OUT/'windows-export-manifest.json',experiment_export.manifest_document(entries));export=publish({DOC+'/'+name:OUT/name for name in('Save-TIS-2k-Results.ps1','windows-export-manifest.json')},first['commit'],'Add immutable2k native and GUI Windows handoff');new(OUT/'export-publication.json',export)
   dest=Path('/workspace/task1-experiment-report-20261025');require(not dest.exists(),'Preserve cloudGUIcopies');dest.mkdir()
   for p in [oldgui,OUT/'verified-waveforms.html',OUT/'waveform-validation.json',OUT/'Save-TIS-2k-Results.ps1',OUT/'windows-export-manifest.json',OUT/'feedback-and-next-batch.json']:
    shutil.copyfile(p,dest/p.name);require(sha(p)==sha(dest/p.name),'Verifiedcloudcopy')
   runtime=ROOT/'runtime';targetdata=read(runtime/'task1-windows-storage-target.json')
   def targets(obj):
    if isinstance(obj,str)and obj.replace('\\','/').startswith('C:/'):yield obj
    elif isinstance(obj,dict):
     for v in obj.values():yield from targets(v)
   target=list(targets(targetdata));require(target,'ExistingprivateWindowsdestination');private_destination=next((s for s in target if 'yoodohyun1' in s),target[0])
   script_url='https://raw.githubusercontent.com/'+REPO+'/'+export['commit']+'/'+DOC+'/Save-TIS-2k-Results.ps1';h=sha(OUT/'Save-TIS-2k-Results.ps1');launcher="$ErrorActionPreference='Stop'\n$destination='"+private_destination.replace("'","''")+"'\n$installer=Join-Path $env:TEMP ('TIS-2k-'+[Guid]::NewGuid().ToString('N')+'.ps1')\nInvoke-WebRequest -UseBasicParsing -Uri '"+script_url+"' -OutFile $installer\nif((Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant() -ne '"+h+"'){throw 'Installer SHA256 mismatch; retained for inspection.'}\n& $installer -Destination $destination\n"
   with(runtime/'Save-2k-Results-To-Requested-Windows.ps1').open('x',encoding='utf-8-sig')as f:f.write(launcher)
   new(runtime/'task1-current-GUI-20261025.json',dict(unified_GUI='/workspace/task1-gui-unified-20261025/index.html',latest_2k_GUI=str(dest/'verified-waveforms.html'),GUI_commit=first['commit'],export_commit=export['commit'],Windows_saved=False,OneDrive_sync_verified=False))
   body='완성된2k native E의5개위치·각각선택된2074방향에서 실제합성파65536표본/0.1초의Hilbert envelope 차이=2min공식, RMS, FFT복소진폭을사전수치기준으로확인했습니다. 새PDE0이며프로브Vpp/장비/안전검증과구분합니다.\n\n최신GUI: https://github.com/'+REPO+'/raw/'+first['commit']+'/'+DOC+'/verified-waveforms.html\nWindows전달: https://github.com/'+REPO+'/raw/'+export['commit']+'/'+DOC+'/Save-TIS-2k-Results.ps1\n\n다음은2000Hz단일carrier의XY0.625→0.5mm/2RHS 계면진단조건을선정했습니다. 준비15+소스게시20+실행60+후처리20+결과게시55+보존5=175초유한예약이필요하며,원래13800초한도의잔여가이에못미쳐미시작입니다. 예산을초기화/확대하지않았습니다. feedback-and-next-batch.json의재개조건은승인된잔여175초이상확보입니다. 현재계산PID0이고기존원본/실패는보존했습니다. Windows실제저장/OneDrive동기화는미확인입니다.'
   comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='waveform_verified_export_published_cloud_copy_verified',GUI_commit=first['commit'],export_commit=export['commit'],comment_url=comment['html_url'],export_files=len(entries),export_bytes=sum(x['bytes']for x in entries),waveform_locations_passed=5,cloud_GUI=str(dest/'verified-waveforms.html'),Windows_saved=False)
  except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for p,t in bounded.owned_descendants(pid,ticks,dict(owned)).items():
    if p!=pid and bounded.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=RUN.name,stage='actual_waveform_and_final_delivery',status=receipt['status'],seconds=elapsed,finished_utc=bounded.now()));tmp=LEDGER.with_name('task1-budget-final-delivery.tmp')
   with tmp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
   os.replace(tmp,LEDGER);receipt.update(elapsed_seconds=elapsed,finished_utc=bounded.now(),remaining_approved_seconds=policy.remaining_seconds(ledger),resources=state);new(OUT/'receipt.json',receipt)
   checkpoint=dict(status='blocked_time_budget_for_next_finite_PDE',updated_utc=bounded.now(),live_PDE_workers=0,remaining_seconds=policy.remaining_seconds(ledger),next_minimum_reservation_seconds=175,minimum_additional_seconds=math.ceil(max(0,175-policy.remaining_seconds(ledger))),resume_condition='Approved remaining time>=175s then source/config/material/mesh preregistration; one lock owner',last_complete_run=RUN.name,last_result_commit=PARENT,last_GUI_commit=receipt.get('GUI_commit'),Windows_saved=False)
   new(ROOT/'runtime/task1-next-minimum-XY-20261025-r2.json',checkpoint)
   for s,h in handlers.items():signal.signal(s,h)
   print(json.dumps(receipt,ensure_ascii=False));print(json.dumps(checkpoint,ensure_ascii=False))
if __name__=='__main__':main()
