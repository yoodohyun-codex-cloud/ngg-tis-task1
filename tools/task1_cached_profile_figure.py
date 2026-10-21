"""Plot pinned, completed depth-profile JSON; no native fields or PDE."""
import argparse,csv,fcntl,hashlib,json,os,resource,signal,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();plan=read(a.plan);out=a.output.resolve()
 assert plan['status']=='preregistered_not_executed' and plan['new_PDE']==0 and out==Path(plan['output']) and not out.exists()
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 assert subprocess.check_output(['git','show',commit+':tools/task1_cached_profile_figure.py'],cwd=ROOT)==Path(__file__).read_bytes()
 with (ROOT/'.task1-execution.lock').open('a+')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  bp=ROOT/'runtime/task1-budget.json';b=read(bp);assert b['limit_seconds']==6600 and 6600-b['spent_seconds']>=60
  start=time.monotonic();status='failed';out.mkdir();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  def timeout(*args):raise TimeoutError('60 second finite cached-profile plot limit')
  signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,60)
  try:
   import shutil
   assert shutil.disk_usage(out).free>=2*1024**3+10*1024**2
   for name,h in plan['inputs_SHA256'].items():assert sha(name)==h
   v=read(plan['volume_audit']);cases=[next(c for c in v['cases']if c['case_id']==x['case_id'])for x in plan['cases']]
   rows=[];profiles=[]
   for declared,c in zip(plan['cases'],cases):
    j=read(declared['spatial_audit']);assert j['status']=='computed_spatial_and_skinJ_audit'and j['case_id']==c['case_id']and j['summary_sha256']==sha(c['summary_path'])
    q=next(q for q in j['conditions']if q['condition_id']==c['condition_id']);scale=c['normalizations']['skin_contact_only']['amplitude_scale'];planes=q['spatial']['depth_planes'];profiles.append((declared['label'],scale,planes))
    for plane in planes:
     for column in ('central_r5_column','whole_plane'):
      for metric in ('maxTIS','fixedTIS','RMS'):
       stats=plane[column][metric];rows.append(dict(case_id=c['case_id'],depth_mm=plane['depth_from_surface_mm'],tissue_id=plane['tissue_id'],region=column,metric=metric,skin_cap_amplitude_scale=scale,mean_V_cm=stats['mean']*scale/100,p10_V_cm=stats['p10']*scale/100,p95_V_cm=stats['p95']*scale/100,represented_volume_m3=stats['represented_volume_m3']))
   assert cases[0]['comparison_signature']==cases[1]['comparison_signature']
   assert [(x['depth_from_surface_mm'],x['tissue_id'])for x in profiles[0][2]]==[(x['depth_from_surface_mm'],x['tissue_id'])for x in profiles[1][2]]
   import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
   fig,axes=plt.subplots(3,2,figsize=(10,11),sharey=True);columns=('central_r5_column','whole_plane');metrics=('maxTIS','fixedTIS','RMS')
   for i,metric in enumerate(metrics):
    allvalues=[]
    for k,column in enumerate(columns):
     ax=axes[i,k]
     for label,scale,planes in profiles:
      x=[z[column][metric]['mean']*scale/100 for z in planes];y=[z['depth_from_surface_mm']for z in planes];assert min(x)>0;allvalues+=x;ax.plot(x,y,label=label,lw=1.5)
     ax.set_xscale('log');ax.set_ylim(25.1,0);ax.axhspan(15,20,color='#cfe9d2',alpha=.6)
     for z in (.1,5.1,10.1):ax.axhline(z,color='#999999',lw=.6,ls=':')
     ax.set_xlabel(metric+' plane mean (V/cm)');ax.set_ylabel('Depth +z from top (mm)');ax.grid(alpha=.2);ax.legend(fontsize=8)
     if i==0:ax.set_title('Central r<=5 mm column'if k==0 else'Whole modeled XY plane')
    for ax in axes[i]:ax.set_xlim(min(allvalues)*.9,max(allvalues)*1.1)
   fig.suptitle('Four pads / two outputs: matched skin-contact burden\nFundamental TIS and all-harmonic vector RMS are separate',fontsize=12)
   fig.subplots_adjust(left=.10,right=.98,bottom=.12,top=.90,hspace=.36,wspace=.24)
   fig.text(.1,.025,'Top z=0; +z enters phantom. Green: target depth 15-20 mm. Native volume-weighted planes.\nCommon amplitude scaling only; no field reconstruction. Tissue interfaces are not evidence of deep focus.',fontsize=8)
   fig.savefig(out/'depth-profiles.png',dpi=150);fig.savefig(out/'depth-profiles.svg');plt.close(fig)
   with (out/'depth-profiles.csv').open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
   for name,h in plan['inputs_SHA256'].items():assert sha(name)==h
   assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==commit
   total=sum(p.stat().st_size for p in out.iterdir());assert total<10*1024**2 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<3*1024**3
   receipt={'status':'complete_cached_profile_visualization','source_commit':commit,'plot_code_SHA256':sha(__file__),'preregistration':str(a.plan.resolve()),'preregistration_SHA256':sha(a.plan),'inputs_SHA256':plan['inputs_SHA256'],'CSV_rows':len(rows),'new_PDE':0,'native_arrays_read':False,'normalization':'skin_contact_only: eight numerical burdens, no source-power/1Vpp ceiling','coordinates':'x,y horizontal; z=0 top; +z depth','ROIs':'Centralr5column and wholeXYplanes; targetdepth15-20 separately shaded; means native-volume-weighted','source_case_provenance':[{'case_id':c['case_id'],'source_commit':c['source_commit'],'config_SHA256':c['configuration_sha256']}for c in cases],'artifacts':{p.name:{'SHA256':sha(p),'bytes':p.stat().st_size}for p in out.iterdir()},'resources':{'wall_seconds':time.monotonic()-start,'CPU':1,'max_seconds':60,'max_added_bytes':10*1024**2},'adopted':False,'experimental_validation':False}
   (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');status='complete';print(json.dumps({'status':status,'output':str(out)}))
  except BaseException as e:
   (out/'failure.json').write_text(json.dumps({'status':'failed_preserved','error':type(e).__name__+': '+str(e)})+'\n');raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-start;b['spent_seconds']+=elapsed;b['runs'].append({'run_id':out.name,'stage':'cached_profile_visualization','seconds':elapsed,'status':status});bp.write_text(json.dumps(b,indent=2)+'\n')
if __name__=='__main__':main()
