"""Bounded saved-JSON contact cohort evidence, including per-output power."""
import argparse,fcntl,hashlib,json,os,resource,signal,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from task1_output_power_evidence import output_power_evidence
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();plan=read(a.plan);output=a.output.resolve();assert plan['status']=='preregistered_not_executed'and output==Path(plan['output'])and not output.exists()
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 for name in ('tools/task1_contact_cohort_evidence.py','tools/task1_output_power_evidence.py'):assert subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)==(ROOT/name).read_bytes()
 with (ROOT/'.task1-execution.lock').open('a+')as l:
  fcntl.flock(l,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(l,fcntl.LOCK_EX|fcntl.LOCK_NB)
  bp=ROOT/'runtime/task1-budget.json';b=read(bp);assert b['limit_seconds']==6600 and 6600-b['spent_seconds']>=60;start=time.monotonic();status='failed';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  def timeout(*args):raise TimeoutError('60 second finite saved-JSON evidence deadline')
  signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,60)
  try:
   for name,h in plan['inputs_SHA256'].items():assert sha(name)==h
   rows=[]
   for selected in plan['cases']:
    audit=read(selected['volume_report']);c=next(c for c in audit['cases']if c['case_id']==selected['case_id']);base=next(x for x in audit['cases']if x['summary_path']==c['baseline_summary']);assert c['comparison_signature']==base['comparison_signature']
    s=read(c['summary_path']);condition=next(x for x in s['conditions']if x['id']==c['condition_id']);modes={}
    for mode,m in c['normalizations'].items():
     modes[mode]={'source_Vpp_by_output':[m['source_Vpp_per_output']]*2,'amplitude_scale':m['amplitude_scale'],'source_output_RMS_mA':m['source_output_RMS_by_output_mA'],'sum_source_output_RMS_mA':m['sum_source_output_RMS_mA'],'per_output_power':output_power_evidence(condition['metrics'],amplitude_scale=m['amplitude_scale']),'burdens':m['normalized_burdens'],'numerical_limits':m['baseline_derived_numerical_limits'],'active_skin_contact_caps':m['active_skin_contact_caps'],'includes_source_power_cap':m['includes_source_power_cap'],'includes_1Vpp_ceiling':m['includes_1Vpp_ceiling'],'regions':m['regions']}
    raw=base['normalizations']['raw_1Vpp']['regions'];cutoffs={metric:raw['surface_0_5'][metric]['fixed_baseline_threshold_volume'] for metric in ('maxTIS','fixedTIS','RMS')}
    rows.append({'case_id':c['case_id'],'run_id':c['run_id'],'source_commit':c['source_commit'],'config_SHA256':c['configuration_sha256'],'model_version':c['physical_model_version'],'comparison_signature':c['comparison_signature'],'baseline_case_id':base['case_id'],'baseline_summary':c['baseline_summary'],'circuit':c['circuit'],'baseline_raw_absolute_ROI_and_slab':{k:raw[k]for k in ('primary_r5_depth15_20','supplemental_wholeXY_depth15_20')},'baseline_frozen_cutoff_values_and_baseline_surface_volumes':cutoffs,'normalizations':modes,'candidate_adopted':False})
   for name,h in plan['inputs_SHA256'].items():assert sha(name)==h
   result={'schema':'task1-contact-cohort-absolute-evidence-v1','status':'complete_saved_JSON_evidence','source_commit':commit,'implementation_SHA256':sha(__file__),'preregistration_SHA256':sha(a.plan),'input_SHA256':plan['inputs_SHA256'],'feedback_id':'T1-F010-S2-GH6308380231','new_PDE':0,'native_arrays_read':False,'cases':rows,'units':{'field':'V/m','volume':'m3','current':'mA','power':'W','voltage':'Vpp or RMS as explicitkey'},'interpretation':'Each normalization uses its own contact-model same-grid baseline. Baseline raw means/P10 and physical cutoff values are explicit; model-dependent cutoff movement is not improvement. Common-cutoff classification is a separate artifact, not a mixed-model burden normalization. Cutoffs are numerical comparisons, not biological or safety thresholds.','resources':{'wall_seconds':time.monotonic()-start,'CPU':1,'max_seconds':60},'adopted':False,'experimental_validation':False}
   payload=json.dumps(result,indent=2,allow_nan=False)+'\n';assert len(payload.encode())<10*1024**2
   import shutil
   assert shutil.disk_usage(output.parent).free>=2*1024**3+len(payload.encode())and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<3*1024**3
   with output.open('x')as f:f.write(payload)
   status='complete';print(json.dumps({'status':status,'cases':len(rows),'output':str(output)}))
  except BaseException as e:
   with output.with_suffix('.failure.json').open('x')as f:json.dump({'status':'failed_preserved','error':str(e)},f)
   raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-start;b['spent_seconds']+=elapsed;b['runs'].append({'run_id':output.stem,'stage':'saved_contact_cohort_evidence','seconds':elapsed,'status':status});bp.write_text(json.dumps(b,indent=2)+'\n')
if __name__=='__main__':main()
