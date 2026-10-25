"""Synthetic coherent-drive JSON display contracts; no native arrays or jobs."""
from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
PRIMARY='primary_r5_depth15_20'
SQUARE='cached_original_square_3000_3030_caps'
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
PARAMETERS=tuple((ratio,phase)for ratio in(.5,1.)for phase in(0,90,180,270))
GATES=[dict(name='primary_maxTIS_'+stat,unit='V/m',required_direction='greater')for stat in('mean','p10')]
for _region in('surface_0_5','primary_complement'):
    GATES.append(dict(name=_region+'_maxTIS_p95',unit='V/m',required_direction='less'))
    GATES.extend(dict(name=_region+'_high_volume_at_'+PRIMARY+'_'+stat,unit='m3',required_direction='less')for stat in('mean','p10'))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Selects(HTMLParser):
    def __init__(self):super().__init__();self.ids=set()
    def handle_starttag(self,tag,attrs):
        if tag=='select':self.ids.add(dict(attrs).get('id'))


class CoherentDriveViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'tools'))
        for name,path in(('cached_fixture',ROOT/'tests/test_task1_frequency_results_view.py'),
                         ('view',ROOT/'tools/task1_coherent_drive_results_view.py')):
            spec=importlib.util.spec_from_file_location('coherent_view_'+name,path)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
            setattr(cls,name,module)
        cls.cached_fixture.FrequencyResultsViewTests.setUpClass()

    def setUp(self):
        self.cached=self.cached_fixture.FrequencyResultsViewTests('runTest');self.cached.setUp();self.addCleanup(self.cached.doCleanups)
        self.cached.conditions[0]['shared_square_baseline_cutoffs_V_m']=copy.deepcopy(self.cached.baseline_case['fixed_same_grid_baseline_cutoffs_V_m'])
        self.cached.rewrite_condition(0)
        self.root=self.cached.root;self.run=self.root/'coherent-run';self.run.mkdir()
        self.summary_path=self.run/'summary.json';self.condition_paths=[];self.probe_paths=[];self.conditions=[];self.probes=[];refs=[]
        for index,(ratio,phase)in enumerate(PARAMETERS):
            identifier=f'coherent-r{"0p5"if ratio==.5 else"1"}-p{phase:03d}';folder=self.run/identifier;folder.mkdir()
            probe=self.cached.probe_fixture((3000,3030));probe['source_drive']='Both tones coherent on both physical outputs'
            probe['actual_source_Vpp_intervals_V']=[[.9999998,1.],[.9999998,1.]]
            condition=self.condition_fixture(identifier,ratio,phase,probe,index)
            cp=folder/'condition.json';cp.write_text(json.dumps(condition));pp=folder/'probes.json';pp.write_text(json.dumps(probe))
            archive=folder/'volume.npz';archive.write_bytes(b'opaque synthetic native archive; never open')
            metrics=folder/'native-volume-metrics.json';metrics.write_text('{"status":"complete"}')
            refs.append(dict(id=identifier,status='calculated_unadopted',mix_ratio=ratio,phase_deg=phase,canonical_screen_all_passed=False,
                artifacts={p.name:dict(path=str(p),SHA256=digest(p))for p in(cp,pp,archive,metrics)}))
            self.conditions.append(condition);self.probes.append(probe);self.condition_paths.append(cp);self.probe_paths.append(pp)
        self.registration_path=self.run/'preregistration.json'
        self.registration=dict(schema='task1-coherent-drive-scout-preregistration-v1',status='preregistered_not_executed',
            new_PDE_conditions=0,conditions=[dict(id=row['id'],mix_ratio=row['mix_ratio'],phase_deg=row['phase_deg'])for row in refs],
            baseline_summary=self.cached.baseline_case['summary_path'])
        self.registration_path.write_text(json.dumps(self.registration))
        self.summary=dict(schema='task1-coherent-drive-scout-v1',status='calculated_unadopted',conditions=refs,new_PDE=0,
            cached_exclusive_sine_control=dict(id=self.cached.conditions[0]['id'],summary_path=str(self.cached.summary_path),
                artifacts=copy.deepcopy(self.cached.summary['conditions'][0]['artifacts']),source_case_id='baseline-square15-xy80',
                new_PDE=0,new_condition=False,recomposed=False),
            canonical_square_reference=dict(condition_id=self.cached.baseline_case['condition_id'],
                summary_path=self.cached.baseline_case['summary_path'],burdens=copy.deepcopy(self.cached.baseline_case['normalizations']['raw_1Vpp']['normalized_burdens'])),
            actual_fundamental_Hz=[3000,3030],beat_frequency_Hz=30,candidate_adopted=False,full_convergence_validated=False,
            experimentally_validated=False,inputs_unchanged=True,holds=['No hardware phase synchronization, absorption, loaded ETA or experimental validation'],
            preregistration=dict(path=str(self.registration_path),SHA256=digest(self.registration_path)),
            input_sha256={self.cached.baseline_case['summary_path']:digest(self.cached.baseline_case['summary_path']),
                str(self.cached.condition_paths[0]):digest(self.cached.condition_paths[0]),str(self.cached.probe_paths[0]):digest(self.cached.probe_paths[0])})
        self.write_summary()

    @staticmethod
    def power_fixture():
        return dict(schema='task1-output-power-evidence-v1',source_resistance_ohm=50.,
            outputs=[dict(output_index=i,ideal_source_power_W=ideal,metal_delivered_power_W=metal,source_resistor_loss_W=loss,
                current_RMS_mA=1.,spectrum=[dict(frequency_Hz=f,ideal_source_power_W=ideal/2,
                    metal_delivered_power_W=metal/2,source_resistor_loss_W=loss/2)for f in(3000,3030)])
                for i,ideal,metal,loss in((0,-.001,-.002,.001),(1,.011,.006,.005))],
            requires_source_power_absorption=True,has_negative_metal_delivered_power=True,
            requires_output_power_absorption=True,has_negative_per_frequency_ideal_source_power=True,
            hardware_absorption_and_compliance_validated=False,numerical_or_experimental_validation_promoted=False,
            unscaled_saved_metric_verification=dict(source_power_W=[dict(passed=True)],source_resistor_power_W=[dict(passed=True)],
                source_current_RMS_by_output_mA=[dict(passed=True),dict(passed=True)]),
            totals=dict(ideal_source_power_W=.01,metal_delivered_power_W=.004,source_resistor_loss_W=.006))

    def condition_fixture(self,identifier,ratio,phase,probes,index):
        modes=copy.deepcopy(self.cached.conditions[0]['cohorts'][SQUARE]['normalizations'])
        modes['raw_1Vpp']=modes.pop('raw_sine_1Vpp')
        for mode in modes.values():
            mode.pop('source_Vpp_by_output');scale=mode['amplitude_scale']
            mode['actual_source_Vpp_intervals_V']=[[.9999998*scale,scale],[.9999998*scale,scale]]
            mode['source_Vpp_upper_by_output_V']=[scale,scale];mode['unitary_after_Vpp_normalization']=False
            mode['signed_per_output_power_evidence']=self.power_fixture();mode['physical_pad_current_RMS_mA']=[scale]*4
            mode['probe40_unloaded']=[dict(id=r['id'],RMS_V=r['RMS_V'],Vpp_lower_V=r['Vpp_lower_V'],
                Vpp_upper_V=r['Vpp_upper_V'],fundamental_envelope_variation_V=.01)for r in probes['measurements']]
            mode['regions'][PRIMARY]['maxTIS']['mean']=1.2345678901234567+index
        checks=[dict(definition,baseline=4.,candidate=3.,passed=i<2,relative_change_percent=-25.,arithmetic_tolerance=1e-10)
                for i,definition in enumerate(GATES)]
        return dict(schema='task1-coherent-drive-condition-v1',status='calculated_unadopted',id=identifier,mix_ratio=ratio,phase_deg=phase,
            source_case_id='baseline-square15-xy80',source_run_id='synthetic-run',source_commit='a'*40,configuration_sha256='b'*64,
            source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
                return_topology='all_return_pads_ideal_common_GND',source_resistance_ohm=50.,
                active_frequencies_by_output_Hz={'0':[3000,3030],'1':[3000,3030]},uncommanded_frequency_termination='0V through50ohm',
                hardware_multitone_phase_sync_power_sink_compliance='unverified; not experimental-ready'),
            actual_fundamental_Hz=[3000,3030],beat_frequency_Hz=30,active_frequencies_Hz=[3000,3030],harmonics_active=False,
            coefficient_vectors={'3000':dict(real=[.8,.4],imaginary=[0.,0.]),'3030':dict(real=[-.4,.8],imaginary=[0.,0.])},
            source_waveform=dict(source_Vpp_intervals_V=[[.9999998,1.],[.9999998,1.]],maximum_bracket_width_V=2e-7,
                hard_maximum_bracket_width_V=1e-6,seed_unitary=True,unitary_after_Vpp_normalization=False,source_peak_basis_V=.5,
                source_resistance_ohm=50,common_period_s=1/30),
            normalizations=modes,field_waveform_audit=dict(passed=True),probe_waveform_audit=dict(passed=True),
            canonical_skin_cap_screen=dict(checks=checks,all_screen_checks_passed=False,
                failed_checks=[c['name']for c in checks if not c['passed']],normalization='skin_contact_only'),
            shared_original_square_cutoffs_V_m=copy.deepcopy(self.cached.baseline_case['fixed_same_grid_baseline_cutoffs_V_m']),
            output_power_evidence=self.power_fixture(),physical_pad_current_evidence=dict(physical_pad_current_RMS_mA=[1.]*4),
            new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False)

    def write_summary(self):self.summary_path.write_text(json.dumps(self.summary,ensure_ascii=False))

    def rewrite_condition(self,index):
        p=self.condition_paths[index];p.write_text(json.dumps(self.conditions[index],ensure_ascii=False))
        self.summary['conditions'][index]['artifacts']['condition.json']['SHA256']=digest(p);self.write_summary()

    def rewrite_probe(self,index):
        p=self.probe_paths[index];p.write_text(json.dumps(self.probes[index],ensure_ascii=False))
        self.summary['conditions'][index]['artifacts']['probes.json']['SHA256']=digest(p);self.write_summary()

    def model(self):return self.view.load_model(self.summary_path,self.cached.baseline.path,self.cached.old_gui)

    def test_exact_eight_coherent_conditions_and_original_square_and_cached_sine_controls(self):
        model=self.model();serialized=json.dumps(model)
        for condition in self.conditions:self.assertIn(condition['id'],serialized)
        self.assertIn('baseline-square15-xy80',serialized);self.assertIn('sine-3000-3030-beat30',serialized)
        self.assertIn('1.2345678901234567',serialized)
        self.assertEqual(len(model['conditions']),9);self.assertEqual(len(model['screens']),8)
        for item,source in zip(model['conditions'][1:],self.conditions):
            expected=copy.deepcopy(source['normalizations'])
            for mode in expected.values():mode['source_Vpp_by_output']=copy.deepcopy(mode['source_Vpp_upper_by_output_V'])
            self.assertEqual(item['condition']['cohorts'][SQUARE]['normalizations'],expected)
        expected=copy.deepcopy(self.cached.conditions[0]['cohorts'][SQUARE]['normalizations'])
        expected['raw_1Vpp']=expected.pop('raw_sine_1Vpp')
        self.assertEqual(model['conditions'][0]['condition']['cohorts'][SQUARE]['normalizations'],expected)

    def test_no_native_array_is_opened_by_metadata_model(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            if Path(path).suffix in('.npz','.bin','.gz'):raise AssertionError('Native archive opened')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):self.model()

    def test_terminal_status_source_hash_and_registration_hash_are_required(self):
        original=copy.deepcopy(self.summary)
        for key,value in(('status','running'),('new_PDE',1),('inputs_unchanged',False),('candidate_adopted',True),
                         ('full_convergence_validated',True),('experimentally_validated',True),('input_sha256',{})):
            self.summary=copy.deepcopy(original);self.summary[key]=value;self.write_summary()
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()
        self.summary=copy.deepcopy(original);self.summary['preregistration']['SHA256']='0'*64;self.write_summary()
        with self.assertRaises(ValueError):self.model()

    def test_condition_and_cached_sine_artifact_sha_are_bound(self):
        original=self.condition_paths[0].read_bytes();self.condition_paths[0].write_bytes(original+b' ')
        with self.assertRaises(ValueError):self.model()
        self.condition_paths[0].write_bytes(original);self.cached.condition_paths[0].write_text('{"tampered":true}')
        with self.assertRaises(ValueError):self.model()

    def test_exact_mix_phase_pool_cannot_be_missing_duplicated_or_relabelled(self):
        original=copy.deepcopy(self.summary)
        for variant in('missing','duplicate','ratio','phase'):
            self.summary=copy.deepcopy(original)
            if variant=='missing':self.summary['conditions'].pop()
            elif variant=='duplicate':self.summary['conditions'][1]=copy.deepcopy(self.summary['conditions'][0])
            elif variant=='ratio':self.summary['conditions'][0]['mix_ratio']=.25
            else:self.summary['conditions'][0]['phase_deg']=45
            self.write_summary()
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.model()

    def test_two_outputs_each_carry_both_frequencies_in_the_common_ground_network(self):
        original=copy.deepcopy(self.conditions[0])
        for variant in('outputs','pads','return','resistance','exclusive_tones'):
            self.conditions[0]=copy.deepcopy(original);circuit=self.conditions[0]['source_circuit']
            if variant=='outputs':circuit['n_outputs']=4
            elif variant=='pads':circuit['n_pads']=8
            elif variant=='return':circuit['n_return_nodes']=2
            elif variant=='resistance':circuit['source_resistance_ohm']=0
            else:circuit['active_frequencies_by_output_Hz']={'0':[3000],'1':[3030]}
            self.rewrite_condition(0)
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.model()

    def test_actual_full_wave_source_intervals_and_one_microvolt_bracket_are_required(self):
        original=copy.deepcopy(self.conditions[0])
        for variant in('upper','wide','reported_width','hard_limit','seed_unitary','normalized_unitary'):
            self.conditions[0]=copy.deepcopy(original);proof=self.conditions[0]['source_waveform']
            if variant=='upper':proof['source_Vpp_intervals_V'][0][1]=2.
            elif variant=='wide':proof['source_Vpp_intervals_V'][0][0]=.99
            elif variant=='reported_width':proof['maximum_bracket_width_V']=.01
            elif variant=='hard_limit':proof['hard_maximum_bracket_width_V']=.01
            elif variant=='seed_unitary':proof['seed_unitary']=False
            else:proof['unitary_after_Vpp_normalization']=True
            self.rewrite_condition(0)
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.model()

    def test_five_modes_preserve_signed_power_four_pad_currents_and_source_intervals(self):
        model=self.model();serialized=json.dumps(model)
        self.assertIn('-0.001',serialized);self.assertIn('physical_pad_current_RMS_mA',serialized)
        original=copy.deepcopy(self.conditions[0])
        for variant in('mode','power','currents','source_intervals','probe_rows'):
            self.conditions[0]=copy.deepcopy(original);modes=self.conditions[0]['normalizations'];mode=modes['skin_contact_only']
            if variant=='mode':modes.pop('equal_total_power')
            elif variant=='power':mode.pop('signed_per_output_power_evidence')
            elif variant=='currents':mode['physical_pad_current_RMS_mA']=[1.,1.]
            elif variant=='source_intervals':mode['actual_source_Vpp_intervals_V']=[[.5,1.]]
            else:mode['probe40_unloaded'].pop()
            self.rewrite_condition(0)
            with self.subTest(variant=variant),self.assertRaises((ValueError,KeyError)):self.model()

    def test_waveform_checks_and_stored_eight_gate_flags_are_required(self):
        original=copy.deepcopy(self.conditions[0])
        for variant in('field','probe','gate_count','gate_flag','allpassed','failed_list'):
            self.conditions[0]=copy.deepcopy(original);c=self.conditions[0]
            if variant=='field':c['field_waveform_audit']['passed']=False
            elif variant=='probe':c['probe_waveform_audit']['passed']=False
            elif variant=='gate_count':c['canonical_skin_cap_screen']['checks'].pop()
            elif variant=='gate_flag':c['canonical_skin_cap_screen']['checks'][0]['passed']=1
            elif variant=='allpassed':c['canonical_skin_cap_screen']['all_screen_checks_passed']=True
            else:c['canonical_skin_cap_screen']['failed_checks']=[]
            self.rewrite_condition(0)
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.model()

    def test_native_phi_probe_geometry_spectra_and_unloaded_scope_are_verified(self):
        original=copy.deepcopy(self.probes[0])
        for variant in('gap','depth','duplicate','loaded','spectrum'):
            self.probes[0]=copy.deepcopy(original);probe=self.probes[0]
            if variant=='gap':probe['measurement_grid']['tip_gap_mm']=10.
            elif variant=='depth':probe['measurements'][0]['depth_from_skin_surface_mm']=25.
            elif variant=='duplicate':probe['measurements'][-1]['id']=probe['measurements'][0]['id']
            elif variant=='loaded':probe['unloaded_prediction']=False
            else:probe['measurements'][0]['spectrum'][0]['frequency_Hz']=9000
            self.rewrite_probe(0)
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.model()

    def test_each_coherent_source_identity_must_match_the_displayed_square_baseline(self):
        original=copy.deepcopy(self.conditions[0])
        for key,value in(('source_run_id','another-run'),('source_commit','e'*40),('configuration_sha256','f'*64)):
            self.conditions[0]=copy.deepcopy(original);self.conditions[0][key]=value;self.rewrite_condition(0)
            with self.subTest(key=key),self.assertRaises(ValueError):self.model()

    def test_synthetic_inline_javascript_passes_static_node_syntax_check(self):
        node=shutil.which('node')
        if node is None:self.skipTest('node is unavailable for optional static JavaScript syntax check')
        document=self.view.render_html(self.model(),self.root/'synthetic.html')
        scripts=re.findall(r'<script>(.*?)</script>',document,re.DOTALL)
        self.assertTrue(scripts)
        for script in scripts:
            result=subprocess.run([node,'--check'],input=script,text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_safe_offline_selectors_json_roundtrip_and_stored_values_unchanged(self):
        literal='</script><script>literal only</script> 한글 Ω'
        self.summary['holds'].append(literal);self.write_summary();model=self.model();before=copy.deepcopy(model)
        document=self.view.render_html(model,self.root/'coherent.html');self.assertEqual(model,before)
        parser=Selects();parser.feed(document)
        self.assertTrue({'normalization-select','roi-select','metric-select'}<=parser.ids)
        self.assertIn(self.cached.old_gui.name,document);self.assertIn('unloaded',document.lower())
        self.assertNotIn('<script src=',document);self.assertNotIn('fetch(',document)
        raw=re.search(r'<script\b[^>]*type="application/json"[^>]*>(.*?)</script\s*>',document,re.DOTALL).group(1)
        self.assertIn(literal,json.dumps(json.loads(raw),ensure_ascii=False));self.assertNotIn('</script>',raw.lower())


if __name__=='__main__':unittest.main()
