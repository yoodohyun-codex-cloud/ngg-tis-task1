"""Synthetic guard fixtures: actual Java/PDE/basis reads/postprocessing forbidden."""
import copy,hashlib,json,signal,subprocess,tempfile,unittest
from contextlib import nullcontext
from pathlib import Path
from unittest import mock
import rs_window_tis_validation as rs

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False)+'\n')
def metric(w,f=1):return dict(waveform=w,thickness_nm=50,boundary_mode='measured_minus_Rs',carrier_Hz=3000,beat_Hz=30,carrier_group=[0,1],phase_deg=[0.,0.],target20_modulation_V_m=3*f,target20_total_E_RMS_V_m=2*f,surface_J_RMS_max_A_m2=10*f,surface_J_RMS_p95_A_m2=7*f,SC_power_W=4*f*f,contact_power_W=9*f*f,contact_voltage_RMS_max_V=5*f,source_power_W=16*f*f)

class Guards(unittest.TestCase):
 def setUp(self):
  self.addCleanup(mock.patch.stopall);self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)/'tis-java';self.prep=self.root/'runs/preparation';self.out=self.root/'runs/rs-window-tis-validation-fixture'
  self.prep.mkdir(parents=True);self.out.mkdir();original=rs.PREPARATION;self.spec=rs.read(original/'preregistration-v2.json');self.real_profile=rs.read(original/'inputs/eis-profiles-windowed.json')[rs.CASE_IDS[0]]
  for d in ('inputs','configs','classes','private-src','logs','cases','bases','postprocess'):(self.out/d).mkdir()
  for c in self.spec['case_plan']:(self.out/c['config_file']).write_bytes((original/c['config_file']).read_bytes())
  for n in set(rs.SOURCES+rs.DEPENDENCIES+rs.TESTS):(self.root/n).write_text('nonexecutable fixture '+n)
  (self.out/'classes/RsWindowTisBasis.class').write_bytes(b'not executable')
  for n in rs.SOURCES:(self.out/'private-src'/n).write_bytes((self.root/n).read_bytes())
  dump(self.out/'inputs/fit-publication.json',dict(status='fixture'))
  dump(self.out/'inputs/eis-profiles-windowed.json',{})
  dump(self.prep/'preregistration-v2.json',self.spec);dump(self.prep/'manifest-v2.json',dict(input_file_sha256={},files={}))
  for k,v in [('ROOT',self.root),('PREPARATION',self.prep),('PREP_SHA',sha(self.prep/'preregistration-v2.json')),('MANIFEST_SHA',sha(self.prep/'manifest-v2.json'))]:mock.patch.object(rs,k,v).start()
  self.reg=dict(source_fit_result_commit=rs.SOURCE_RESULT_COMMIT,source_fit_result_publication_path=str(self.out/'inputs/fit-publication.json'),source_fit_result_publication_sha256=sha(self.out/'inputs/fit-publication.json'),authorization=dict(user_instruction=rs.AUTHORIZATION),maximum_new_PDE_cases=8,semantic_window_slots=10,unique_reused_complete_basis_count=1,reference_alias_slots=2,case_plan=copy.deepcopy(self.spec['case_plan']),resource_limits=copy.deepcopy(rs.LIMITS),numerical_gates=copy.deepcopy(rs.NUMERICAL),normalization_reference=copy.deepcopy(self.spec['normalization_reference']),execution_source_hashes={str(self.root/n):sha(self.root/n) for n in set(rs.SOURCES+rs.DEPENDENCIES+rs.TESTS)})
  dump(self.out/'preregistration.json',self.reg)
  self.m=dict(status='prepared',output_run=str(self.out),preparation_sha256=rs.PREP_SHA,preparation_manifest_sha256=rs.MANIFEST_SHA,preregistration_sha256=sha(self.out/'preregistration.json'),plan=rs.plan_for(self.spec,self.out),classes=str(self.out/'classes'),java='/forbidden/java',preparation_wall_seconds=.01,resource_limits=copy.deepcopy(rs.LIMITS),numerical_gates=copy.deepcopy(rs.NUMERICAL))
  files=[self.out/'preregistration.json',self.prep/'manifest-v2.json',self.prep/'preregistration-v2.json',*[self.root/n for n in set(rs.SOURCES+rs.DEPENDENCIES+rs.TESTS)]]
  files += [p for d in ('inputs','configs','private-src','classes') for p in (self.out/d).iterdir()]
  self.m['guard_hashes']={str(p):sha(p) for p in files};dump(self.out/'manifest.json',self.m)
  self.runner=mock.patch.object(rs.common,'run_guarded',side_effect=AssertionError('real process forbidden')).start()
  self.proc=mock.patch.object(subprocess,'Popen',side_effect=AssertionError('real process forbidden')).start()
  self.load=mock.patch.object(rs,'load_basis',side_effect=AssertionError('real basis forbidden')).start()
  self.summarize=mock.patch.object(rs,'summarize',side_effect=AssertionError('real score forbidden')).start()
  self.analyze=mock.patch.object(rs,'analyze_case',side_effect=AssertionError('real post forbidden')).start()
  mock.patch.object(rs.common,'diagnostic_lock',side_effect=lambda:nullcontext()).start();mock.patch.object(rs.common,'available_disk_bytes',return_value=10*1024**3).start()
 def publish(self):
  dump(self.out/'manifest.json',self.m);dump(self.out/'execution-publication.json',dict(status='published_before_PDE',remote_ref_verified=True,commit='1'*40,manifest_sha256=sha(self.out/'manifest.json'),preregistration_sha256=self.m['preregistration_sha256']))
 def rebind(self):
  dump(self.out/'preregistration.json',self.reg);s=sha(self.out/'preregistration.json');self.m['preregistration_sha256']=s;self.m['guard_hashes'][str(self.out/'preregistration.json')]=s
 def test_exact_ten_nine_eight_two_one_namespace_valid(self):
  self.assertTrue(rs.validate_manifest(self.m));self.assertEqual(len({c['config_sha256'] for c in self.m['plan']}),9)
  self.assertEqual([c['id'] for c in self.m['plan'] if c['execution_action']=='reuse_verified_complete_basis_alias'],list(rs.ALIASES));self.assertEqual(sum(c['execution_action']=='new_private_solve' for c in self.m['plan']),8);self.runner.assert_not_called()
 def test_plan_Rs_phase_frequency_alias_reorder_and_caps_tampering_rejected(self):
  changes=[lambda m:m['plan'].reverse(),lambda m:m['plan'][0].update(selected_Rs_ohm=0),lambda m:m['plan'][0].update(phase_deg=[0,90]),lambda m:m['plan'][0].update(frequencies_Hz=[2000,2010]),lambda m:m['plan'][3].update(execution_action='new_private_solve'),lambda m:m['plan'][0].update(execution_action='reuse_verified_complete_basis_alias'),lambda m:m['resource_limits'].update(per_case_wall_seconds=601),lambda m:m['numerical_gates'].update(max_residual=1),lambda m:m.update(preparation_wall_seconds=float('nan')),lambda m:m.update(classes=str(self.root))]
  for mutate in changes:
   value=copy.deepcopy(self.m);mutate(value)
   with self.subTest(change=mutate),self.assertRaises(ValueError):rs.validate_manifest(value)
 def test_registration_cannot_rebind_scope_or_normalization_reference(self):
  original=copy.deepcopy(self.reg)
  for mutate in [lambda r:r.update(maximum_new_PDE_cases=9),lambda r:r.update(reference_alias_slots=1),lambda r:r['case_plan'].reverse(),lambda r:r['normalization_reference'].update(selected_Rs_ohm=213.88978753372703),lambda r:r['authorization'].update(user_instruction='continue')]:
   self.reg=copy.deepcopy(original);mutate(self.reg);self.rebind()
   with self.subTest(change=mutate),self.assertRaises(ValueError):rs.validate_manifest(self.m)
 def test_missing_code_class_or_rehashed_changed_config_rejected(self):
  for p in (self.root/'RsWindowTisBasis.java',self.out/'classes/RsWindowTisBasis.class'):
   value=copy.deepcopy(self.m);del value['guard_hashes'][str(p)]
   with self.assertRaises(ValueError):rs.validate_manifest(value)
  p=Path(self.m['plan'][0]['config_file']);p.write_bytes(p.read_bytes()+b'\n');self.m['guard_hashes'][str(p)]=sha(p)
  with self.assertRaises(ValueError):rs.validate_manifest(self.m)
 def test_missing_unverified_badcommit_and_wrong_publication_bytes_rejected(self):
  for receipt in ({},dict(status='published_before_PDE',remote_ref_verified=False,commit='1'*40),dict(status='published_before_PDE',remote_ref_verified=True,commit='bad'),dict(status='published_before_PDE',remote_ref_verified=True,commit='1'*40,manifest_sha256='0'*64,preregistration_sha256=self.m['preregistration_sha256'])):
   dump(self.out/'execution-publication.json',receipt)
   with self.assertRaises(ValueError):rs.execute(self.m)
  self.runner.assert_not_called();self.proc.assert_not_called()
 def test_stop_and_attention_markers_preserve_bytes_and_block_all_execution(self):
  self.publish()
  for n in ('STOP','needs_attention','needs_physical_validation'):
   p=self.out/n;p.write_bytes(b'finite explicit hold\n')
   with self.assertRaises(rs.common.ValidationStop):rs.execute(self.m)
   self.assertEqual(p.read_bytes(),b'finite explicit hold\n');self.assertFalse((self.out/'controller.json').exists());p.unlink()
  self.runner.assert_not_called();self.load.assert_not_called()
 def test_failed_partial_prior_summary_case_basis_or_post_never_retried(self):
  self.publish()
  for p in (self.out/'summary.json',self.out/'controller.json',self.out/'failure.json',self.out/'cases/failed.partial.json',self.out/'bases/partial',self.out/'postprocess/failed.gz'):
   p.write_bytes(b'preserve original failure')
   with self.assertRaisesRegex(ValueError,'no retry'):rs.execute(self.m)
   self.assertEqual(p.read_bytes(),b'preserve original failure');p.unlink()
  self.runner.assert_not_called()
 def test_resource_stop_user_interrupt_failure_distinct_and_timer_cleared(self):
  self.publish();original_read=rs.read
  for error,status in ((rs.common.ValidationStop('rss',dict(status='rss_limit')),'resource_stopped'),(rs.common.ValidationStop('STOP',dict(status='user_stopped')),'user_stopped'),(KeyboardInterrupt('signal'),'interrupted'),(ValueError('error'),'failed')):
   def synthetic(p):
    if str(p)==self.spec['normalization_reference']['case_path']:return dict(metrics=[metric(w) for w in rs.WAVES])
    return original_read(p)
   self.runner.side_effect=error;dump(self.out/'inputs/eis-profiles-windowed.json',{self.m['plan'][0]['id']:copy.deepcopy(self.real_profile)})
   with mock.patch.object(rs,'validate_manifest',return_value=True),mock.patch.object(rs,'read',side_effect=synthetic),mock.patch.object(rs.common,'assert_hashes_unchanged'),mock.patch.object(rs,'config_text',return_value='fixture'),mock.patch.object(rs.common,'make_config',return_value=Path(self.m['plan'][0]['config_file']).read_text()):
    with self.assertRaises(type(error)):rs.execute(self.m)
   self.assertEqual(original_read(self.out/'failure.json')['status'],status);self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
   for n in ('summary.json','controller.json','failure.json'):(self.out/n).unlink()
  self.load.assert_not_called();self.summarize.assert_not_called();self.analyze.assert_not_called()

 def test_failed_native_spatial_payload_and_raw_metrics_are_preserved_not_complete(self):
  self.publish();original_read=rs.read;c=self.m['plan'][0]
  rows=[metric(w) for w in rs.WAVES]
  for row in rows:row['thickness_nm']=c['thickness_nm']
  dump(self.out/'inputs/eis-profiles-windowed.json',{c['id']:copy.deepcopy(self.real_profile)})
  def synthetic(p):
   if str(p)==self.spec['normalization_reference']['case_path']:return dict(metrics=rows)
   return original_read(p)
  def fake_solve(*args,**kwargs):
   folder=self.out/'bases'/c['id'];folder.mkdir();dump(folder/'validation.json',dict(cells=791280));dump(folder/'mesh-metadata.json',dict(exporter_class='RsWindowTisBasis'));(folder/'BASIS_COMPLETE').write_bytes(b'')
   return dict(status='complete',returncode=0)
  self.runner.side_effect=fake_solve;self.load.side_effect=None;self.load.return_value={};self.summarize.side_effect=None;self.summarize.return_value=rows
  self.analyze.side_effect=None;self.analyze.return_value=dict(status='failed',verification=dict(spatial_all_complete=False),saved_detail='preserve this failure')
  with mock.patch.object(rs,'validate_manifest',return_value=True),mock.patch.object(rs,'read',side_effect=synthetic),mock.patch.object(rs.common,'assert_hashes_unchanged'),mock.patch.object(rs,'config_text',return_value='fixture'),mock.patch.object(rs.common,'make_config',return_value=Path(c['config_file']).read_text()),mock.patch.object(rs.common,'check_numerical_gates',return_value={}):
   with self.assertRaisesRegex(ValueError,'postprocessing failed'):rs.execute(self.m)
  failure=original_read(self.out/'failure.json');saved=original_read(self.out/'cases'/(c['id']+'.json'))
  self.assertEqual(failure['status'],'postprocessing_failed');self.assertEqual(saved['status'],'postprocessing_failed');self.assertEqual(len(saved['metrics']),3)
  self.assertEqual(saved['postprocess']['status'],'failed');self.assertEqual(sha(Path(saved['postprocess']['path'])),saved['postprocess']['sha256'])
  import gzip
  with gzip.open(saved['postprocess']['path'],'rt') as f:self.assertEqual(json.load(f)['saved_detail'],'preserve this failure')
  self.assertEqual(failure['cases'],[]);self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))

 def test_postprocess_user_resource_interrupt_controls_do_not_become_validation_failures(self):
  import shutil
  original_read=rs.read;c=self.m['plan'][0];rows=[metric(w) for w in rs.WAVES]
  for row in rows:row['thickness_nm']=c['thickness_nm']
  def synthetic(p):
   if str(p)==self.spec['normalization_reference']['case_path']:return dict(metrics=rows)
   return original_read(p)
  def solve(*args,**kwargs):
   folder=self.out/'bases'/c['id'];folder.mkdir();dump(folder/'validation.json',dict(cells=791280));dump(folder/'mesh-metadata.json',{});(folder/'BASIS_COMPLETE').write_bytes(b'')
   return dict(status='complete',returncode=0)
  for error,status in ((rs.common.ValidationStop('STOP',dict(status='user_stopped')),'user_stopped'),(rs.common.ValidationStop('case budget',dict(status='case_timeout')),'resource_stopped'),(KeyboardInterrupt('SIGINT'),'interrupted')):
   self.publish();dump(self.out/'inputs/eis-profiles-windowed.json',{c['id']:copy.deepcopy(self.real_profile)})
   self.runner.side_effect=solve;self.load.side_effect=None;self.load.return_value={};self.summarize.side_effect=None;self.summarize.return_value=rows;self.analyze.side_effect=error
   with mock.patch.object(rs,'validate_manifest',return_value=True),mock.patch.object(rs,'read',side_effect=synthetic),mock.patch.object(rs.common,'assert_hashes_unchanged'),mock.patch.object(rs,'config_text',return_value='fixture'),mock.patch.object(rs.common,'make_config',return_value=Path(c['config_file']).read_text()),mock.patch.object(rs.common,'check_numerical_gates',return_value={}):
    with self.assertRaises(type(error)):rs.execute(self.m)
   self.assertEqual(original_read(self.out/'failure.json')['status'],status)
   saved=original_read(self.out/'cases'/(c['id']+'.json'));self.assertEqual(saved['status'],status);self.assertEqual(len(saved['metrics']),3)
   self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
   for n in ('summary.json','controller.json','failure.json'):(self.out/n).unlink()
   for n in ('cases','bases','postprocess'):
    shutil.rmtree(self.out/n);(self.out/n).mkdir()

class References(unittest.TestCase):
 def test_saved_solver_log_gate_signatures_distinct_from_controls_and_unknown_failure(self):
  with tempfile.TemporaryDirectory() as td:
   output=Path(td);(output/'logs').mkdir();case=dict(id='synthetic');log=output/'logs/synthetic.log';error=rs.common.ValidationStop('process failed',dict(status='process_failed',returncode=1))
   for message,status in (('COCG solver failed','unconverged'),('Residual 0.123','unconverged'),('Numerical conservation gate failed','numerical_failed'),('Nonfinite validation','numerical_failed'),('Physical pad area changed','numerical_failed'),('unknown Java exception','unknown_process_failure_incomplete')):
    log.write_text(message);result=rs.failure_evidence(output,case,'solving',error,'failed');self.assertEqual(result['solver_status'],status);self.assertEqual(result['log_file_sha256'],sha(log))
   log.write_text('COCG solver failed')
   for status in ('user_stopped','resource_stopped','interrupted'):
    result=rs.failure_evidence(output,case,'solving',error,status);self.assertEqual(result['solver_status'],'not_inferred');self.assertFalse(result['unconverged'])
   self.assertEqual(rs.failure_evidence(output,case,'native_and_spatial_postprocessing',error,'postprocessing_failed')['solver_status'],'not_inferred')
 def test_runtime_profile_actual_summarize_contract_uses_window_Rs_and_preserves_input(self):
  import numpy as np
  points=[dict(frequency_Hz=float(f),Z_real_ohm=10.,Z_imag_ohm=-1.,source_range='synthetic') for f in np.geomspace(1,10000,30)]
  source=dict(path='synthetic-fit.json',warnings=['synthetic window warning'])
  original=dict(thickness_nm=10,points=points,selected_fit=dict(Rs_ohm=3),fit_source=source)
  profiles={'synthetic':original};before=copy.deepcopy(profiles)
  c=dict(condition_id='synthetic',thickness_nm=10,selected_Rs_ohm=3,fit_source=source)
  profile=rs.runtime_profile(profiles,c)
  self.assertEqual(profile['warnings'],['synthetic window warning']);self.assertEqual(profiles,before)
  contacts=np.zeros(4,dtype=[('area_m2',float)]);contacts['area_m2']=1e-4
  basis=dict(validation=dict(max_residual=0.,max_power_error=0.),f={})
  for f in rs.FREQUENCIES:
   basis['f'][f]=dict(contacts=contacts,target=np.array([[1.+0j,0j,0j],[0j,1.+0j,0j]]),density=np.array([[1.,0.,1.,0.],[0.,1.,0.,1.]],complex),source=np.eye(2,dtype=complex),loss=np.tile(np.eye(2,dtype=complex)*.001,(6,1,1)))
  design=dict(layout='synthetic',size_mm=15,channels=2,carrier_Hz=3000,beat_Hz=30,boundary_mode='measured_minus_Rs',xy_mm=[[-10,-10],[10,10],[10,-10],[-10,10]])
  rows=rs.summarize(basis,design,profile,'synthetic-analytic-only',50/120)
  self.assertEqual(len(rows),3)
  for row in rows:self.assertEqual(row['coating_model_warnings'],['synthetic window warning']);self.assertTrue(np.isfinite(row['contact_voltage_RMS_max_V']))
  shifted=copy.deepcopy(profiles);shifted['synthetic']['selected_fit']['Rs_ohm']=4;shifted_c=dict(c,selected_Rs_ohm=4)
  shifted_rows=rs.summarize(basis,design,rs.runtime_profile(shifted,shifted_c),'synthetic-analytic-only',50/120)
  self.assertLess(shifted_rows[0]['contact_voltage_RMS_max_V'],rows[0]['contact_voltage_RMS_max_V'])
  self.assertEqual(profiles,before)
 def test_original_relative_input_pins_resolve_from_repository_not_working_directory(self):
  with tempfile.TemporaryDirectory() as td:
   repository=Path(td);java=repository/'tis-java'
   with mock.patch.object(rs,'ROOT',java):
    self.assertEqual(rs.absolute_pins({'data/spectrum.xlsx':'a'*64,str(repository/'data/spectrum.xlsx'):'a'*64}),{str(repository/'data/spectrum.xlsx'):'a'*64})
    with self.assertRaises(ValueError):rs.absolute_pins({'data/spectrum.xlsx':'a'*64,str(repository/'data/spectrum.xlsx'):'b'*64})
 def test_same_wave_original1k_bare_join_not_newwindow(self):
  baseline=[metric(w) for w in rs.WAVES];before=copy.deepcopy(baseline)
  for row in rs.matched_rows([metric(w,2) for w in reversed(rs.WAVES)],baseline):
   cap=row['same_wave_bare_baseline'];self.assertEqual(cap['waveform'],row['waveform']);self.assertEqual(cap['selected_Rs_window_Hz'],1000);self.assertEqual(cap['burden_source_Vpp'],.5);self.assertEqual(cap['power_source_Vpp'],.5)
  self.assertEqual(baseline,before)
 def test_alias_two_slots_copy_same_old_rows_and_native_provenance_without_new_analysis(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);post=root/'post.gz';post.write_bytes(b'preserved native provenance');p=root/'case.json';original=dict(status='complete',config_sha256='a'*64,basis_dir=str(root/'oldbasis'),validation=dict(cells=791280),metrics=[metric(w) for w in rs.WAVES],output_hashes={},producer_kind='private_CoatingRsBasis',producer_source_sha256='b'*64,analysis_code_sha256='c'*64,postprocess=dict(status='complete',path=str(post),sha256=sha(post)))
   dump(p,original);before=p.read_bytes()
   for ident in rs.ALIASES:
    c=dict(id=ident,thickness_nm=50,config_sha256='a'*64,execution_action='reuse_verified_complete_basis_alias',existing_result_link=dict(basis_output_file_sha256={},source_case_path=str(p),source_case_file_sha256=sha(p)))
    with mock.patch.object(rs,'load_basis',side_effect=AssertionError('alias basis forbidden')),mock.patch.object(rs,'summarize',side_effect=AssertionError('alias score forbidden')),mock.patch.object(rs,'analyze_case',side_effect=AssertionError('alias native forbidden')):result=rs.alias_result(c,{})
    self.assertEqual(result['metrics'],original['metrics']);self.assertEqual(result['postprocess']['path'],str(post));self.assertEqual(result['producer_kind'],'private_CoatingRsBasis');self.assertTrue(result['semantic_window_alias_only'])
   self.assertEqual(p.read_bytes(),before)
 def test_wrong_physical_labels_nonfinite_and_zero_burden_rejected(self):
  rows=[metric(w) for w in rs.WAVES]
  for change in ({'thickness_nm':0},{'boundary_mode':'full_measured'},{'phase_deg':[0,90]},{'contact_power_W':float('nan')}):
   values=copy.deepcopy(rows);values[0].update(change)
   with self.assertRaises(ValueError):rs.assert_metric_input(values,dict(thickness_nm=50))
  values=copy.deepcopy(rows);values[0]['SC_power_W']=0
  with self.assertRaises(ValueError):rs.matched_rows(values,rows)
if __name__=='__main__':unittest.main()
