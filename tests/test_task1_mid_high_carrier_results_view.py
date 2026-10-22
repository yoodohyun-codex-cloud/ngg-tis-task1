"""Synthetic mid/high-carrier JSON display contracts; no native arrays or jobs."""
from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
PAIRS=((5000,5030),(9000,9030))
COHORTS=('cached_original_square_3000_3030_caps','cached_sine_3000_3030_caps')
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power',
       'skin_contact_only','legacy_composite_full_skin')
PRIMARY='primary_r5_depth15_20'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_condition(value,identifier):
    if isinstance(value,dict):
        if value.get('id')==identifier and 'cohorts'in value:return value
        for child in value.values():
            result=find_condition(child,identifier)
            if result is not None:return result
    elif isinstance(value,list):
        for child in value:
            result=find_condition(child,identifier)
            if result is not None:return result
    return None


class Selects(HTMLParser):
    def __init__(self):super().__init__();self.ids=set()
    def handle_starttag(self,tag,attrs):
        if tag=='select':self.ids.add(dict(attrs).get('id'))


class MidHighCarrierViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'tools'))
        for name,path in (('cached_fixture',ROOT/'tests/test_task1_frequency_results_view.py'),
                          ('view',ROOT/'tools/task1_mid_high_carrier_results_view.py')):
            spec=importlib.util.spec_from_file_location('mid_high_view_'+name,path)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
            setattr(cls,name,module)
        cls.cached_fixture.FrequencyResultsViewTests.setUpClass()

    def setUp(self):
        fixture=self.cached_fixture.FrequencyResultsViewTests('runTest');fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.cached=fixture;self.root=fixture.root
        self.cutoffs=copy.deepcopy(fixture.baseline_case['fixed_same_grid_baseline_cutoffs_V_m'])
        fixture.conditions[0]['shared_square_baseline_cutoffs_V_m']=copy.deepcopy(self.cutoffs)
        fixture.rewrite_condition(0)
        self.run=self.root/'cloud-mid-high-synthetic';self.run.mkdir()
        self.registration_path=self.run/'preregistration.json';self.summary_path=self.run/'summary.json'
        self.condition_paths=[];self.probe_paths=[];self.conditions=[];self.probes=[];references=[]
        self.assembly=self.assembly_fixture()
        for pair in PAIRS:
            identifier=f'sine-{pair[0]}-{pair[1]}-beat30';folder=self.run/identifier;folder.mkdir()
            probe=fixture.probe_fixture(pair)
            for key in ('actual_fundamental_Hz','beat_frequency_Hz','waveform','actual_source_Vpp_by_output'):
                probe.pop(key,None)  # The actual mid/high producer does not add these top-level convenience fields.
            condition=self.mid_high_condition(pair,identifier,probe)
            pp=folder/'probes.json';pp.write_text(json.dumps(probe));cp=folder/'condition.json';cp.write_text(json.dumps(condition))
            native=folder/'volume.npz';native.write_bytes(b'opaque synthetic archive; never decode')
            metrics=folder/'native-volume-metrics.json';metrics.write_text('{"status":"complete"}')
            references.append(dict(id=identifier,status='calculated_unadopted',actual_fundamental_Hz=list(pair),beat_frequency_Hz=30,
                canonical_screen_all_passed=condition['canonical_square_cap_screen']['all_screen_checks_passed'],
                artifacts={p.name:dict(path=str(p),SHA256=digest(p))for p in (cp,pp,native,metrics)}))
            self.conditions.append(condition);self.probes.append(probe);self.condition_paths.append(cp);self.probe_paths.append(pp)
        baseline=copy.deepcopy(fixture.baseline_case)
        cached_sine=fixture.conditions[0]
        source_refs={baseline['summary_path']:digest(baseline['summary_path']),
            str(fixture.condition_paths[0]):digest(fixture.condition_paths[0])}
        self.donor=dict(run_path='/synthetic/failed-donor',basis_path='/synthetic/failed-donor/bases/regression-3000-3030',
            source_commit='a'*40,original_registration_SHA256='b'*64,
            original_failure=dict(path='/synthetic/failed-donor/failure.json',SHA256='c'*64),
            native_file_inventory_sha256={'/synthetic/failed-donor/bases/regression-3000-3030/source-3000.bin':'f'*64})
        self.failed_charge=dict(seconds=10.,status='failed_preserved',run_id='original-failed-stage')
        self.regression_path=self.run/'producer-regression.json'
        self.regression=dict(status='passed',reused_regression_RHS_solves=4,new_regression_RHS_solves=0,
            reused_from_donor=copy.deepcopy(self.donor))
        self.regression_path.write_text(json.dumps(self.regression))
        self.registration=dict(schema='task1-mid-high-carrier-preregistration-v1',status='prepared',source_commit='d'*40,
            source_baseline_summary=baseline['summary_path'],source_and_input_sha256=copy.deepcopy(source_refs),
            input_sha256=copy.deepcopy(source_refs),regression_required_before_new_bundle=True,
            new_native_frequencies_Hz=[5000,5030,9030],analysis_frequency_pairs_Hz=[list(p)for p in PAIRS],
            cached_frequency_Hz=9000,cached_9000_readback_required=True,
            actual_new_native_RHS_solves_max=6,reused_9000_RHS_solves=2,reused_regression_RHS_solves=4,
            donor_reference=dict(copy.deepcopy(self.donor),actual_reused_RHS_solves=4,new_regression_RHS_solves=0,
                original_failed_stage_charge=copy.deepcopy(self.failed_charge)),
            original_square_volume_reference_row=baseline,fixed_square_SC2_cutoffs_V_m=copy.deepcopy(self.cutoffs),
            conditions=[dict(id=f'sine-{a}-{b}-beat30',actual_fundamental_Hz=[a,b],beat_frequency_Hz=30)for a,b in PAIRS],
            comparison_references={COHORTS[0]:dict(id=baseline['condition_id'],waveform='square_3h',actual_fundamental_Hz=[3000,3030],
                burdens=copy.deepcopy(baseline['normalizations']['raw_1Vpp']['normalized_burdens']),currents=[1.,1.]),
                COHORTS[1]:dict(id=cached_sine['id'],waveform='sine',actual_fundamental_Hz=[3000,3030],
                burdens=copy.deepcopy(cached_sine['cohorts']['fresh_sine_3000_3030_caps']['normalizations']['raw_sine_1Vpp']['normalized_burdens']),currents=[1.,1.])})
        self.registration_path.write_text(json.dumps(self.registration))
        self.summary=dict(schema='task1-mid-high-carrier-result-v1',status='calculated_unadopted',run_id=self.run.name,source_commit='d'*40,
            registration_sha256=digest(self.registration_path),conditions=references,actual_frequency_pairs=[list(p)for p in PAIRS],
            actual_beat_frequencies_Hz=[30,30],producer_regression=dict(status='passed',path=str(self.regression_path),SHA256=digest(self.regression_path)),
            resources=dict(actual_native_RHS_solves=6,reused_9000_RHS_solves=2,reused_regression_RHS_solves=4),
            frequency_assembly=copy.deepcopy(self.assembly),
            donor_reference=dict(copy.deepcopy(self.donor),reused_regression_RHS_solves=4,new_regression_RHS_solves=0,
                original_failed_stage_charge=copy.deepcopy(self.failed_charge)),candidate_adopted=False,
            full_convergence_validated=False,experimentally_validated=False,inputs_unchanged=True,
            input_sha256=copy.deepcopy(source_refs),new_native_jobs_started=2,
            cases=[dict(id='regression-3000-3030',status='producer_regression_passed'),
                   dict(id='mid-high-5000-5030-9030',status='calculated_unadopted')],
            holds=['Electrical proxies only; no experimental or instrument loading validation'])
        self.write_summary()

    def assembly_fixture(self):
        raw=dict(frequencies_Hz=[5000,5030,9030],actual_basis_RHS_solves=6,
            exporter_class='CloudFrequencyMidHighBasis',exporter_kind='mid_high_frequency_native',config_sha256='e'*64)
        cached=dict(frequencies_Hz=[3000,3030,9000,9090],exporter_class='CloudShapeBasis',
            exporter_kind='selectivity_native',config_sha256='c'*64)
        metadata=dict(schema='task1-mid-high-cached-frequency-assembly-v1',
            source='explicit_frequency_native_and_cached9000_assembly',actual_new_basis_RHS_solves=6,
            cached_basis_RHS_reused=2,total_analysis_basis_vectors=8,analysis_frequencies_Hz=[5000,5030,9000,9030],
            raw_native_metadata_frequencies_Hz=[5000,5030,9030],raw_metadata_modified=False,
            single_four_frequency_native_producer_claimed=False,inputs_unchanged=True)
        sources={}
        for frequency in (5000,5030,9000,9030):
            original=cached if frequency==9000 else raw
            sources[str(frequency)]=dict(frequency_Hz=frequency,
                kind='reused_cached_native'if frequency==9000 else'new_native',
                basis_folder='/synthetic/cached9000'if frequency==9000 else'/synthetic/new-native',
                exporter_class=original['exporter_class'],exporter_kind=original['exporter_kind'],
                config_sha256=original['config_sha256'],mask_sha256='a'*64,basis_RHS_vectors=2,
                input_sha256={f'/synthetic/field-{frequency}.bin.gz':'f'*64})
        return dict(assembly_metadata=metadata,frequency_sources=sources,raw_new_frequency_metadata=raw,
            cached_frequency_metadata={'9000':cached})

    def mid_high_condition(self,pair,identifier,probes):
        c=copy.deepcopy(self.cached.conditions[0]);c.update(schema='task1-mid-high-carrier-condition-v1',id=identifier,
            actual_fundamental_Hz=list(pair),beat_frequency_Hz=30,new_physical_PDE_bundle='mid-high-5000-5030-9030',
            full_convergence_validated=False,fixed_square_SC2_cutoffs_V_m=copy.deepcopy(self.cutoffs),
            source_reference_scope='Three new native frequencies and one reused cached9000 basis; references are cached caps only',
            carrier_and_beat_scope='Allnewconditions beat30Hz; initialbare2000/2010Hz separate',holds=['No loading/physiology/convergence claim'])
        c.pop('new_PDE',None);c.pop('numerical_validation_promoted',None)
        c['source_provenance']=dict(run_id=self.run.name,native_case_id='mid-high-5000-5030-9030',source_commit='d'*40,
            configuration_sha256='e'*64,native_input_sha256={'/synthetic/field.bin.gz':'f'*64},
            circuit=copy.deepcopy(self.cached.baseline_case['circuit']))
        c['source_provenance']['circuit']['carrier_assignment_Hz']=list(pair)
        c['source_provenance'].update(copy.deepcopy(self.assembly))
        c['source_provenance']['configuration_hash_scope']='Original new three-frequency config SHA; cached9000 config remains distinct'
        cohorts={}
        for new,old in zip(COHORTS,('cached_original_square_3000_3030_caps','fresh_sine_3000_3030_caps')):
            cohort=copy.deepcopy(c['cohorts'][old]);cohort['normalizations']['raw_1Vpp']=cohort['normalizations'].pop('raw_sine_1Vpp')
            for mode in cohort['normalizations'].values():
                mode['source_Vpp_per_output']=mode['source_Vpp_by_output'][0]
                mode['regions'][PRIMARY]['maxTIS']['mean']=1.2345678901234567 if pair[0]==5000 else 4.987654321098765
                mode['probe40_unloaded']=[dict(id=r['id'],RMS_V=r['RMS_V'],Vpp_lower_V=r['Vpp_lower_V'],
                    Vpp_upper_V=r['Vpp_upper_V'],fundamental_envelope_variation_V=.01)for r in probes['measurements']]
            cohorts[new]=cohort
        c['cohorts']=cohorts
        checks=[dict(name='primary_maxTIS_mean'if i==0 else'gate_'+str(i),unit='V/m',required_direction='greater'if i<2 else'less',
            baseline=4.,candidate=3.,relative_change_percent=-25.,arithmetic_tolerance=1e-10,passed=i>=2)for i in range(8)]
        c['canonical_square_cap_screen']=dict(normalization='skin_contact_only',checks=checks,all_screen_checks_passed=False,
            fixed_definition_source='/synthetic/fixed-screen.json',candidate_adopted=False,interpretation='Screen only; never adoption')
        c['field_waveform_audit']=dict(passed=True);c['probe_waveform_audit']=dict(passed=True)
        c['output_power_evidence']=dict(status='calculated')
        return c

    def write_summary(self):self.summary_path.write_text(json.dumps(self.summary,ensure_ascii=False))

    def rewrite_registration(self):
        self.registration_path.write_text(json.dumps(self.registration,ensure_ascii=False))
        self.summary['registration_sha256']=digest(self.registration_path);self.write_summary()

    def rewrite_regression_proof(self):
        self.regression_path.write_text(json.dumps(self.regression,ensure_ascii=False))
        self.summary['producer_regression']['SHA256']=digest(self.regression_path);self.write_summary()

    def rewrite_condition(self,index):
        p=self.condition_paths[index];p.write_text(json.dumps(self.conditions[index],ensure_ascii=False))
        self.summary['conditions'][index]['artifacts']['condition.json']['SHA256']=digest(p);self.write_summary()

    def rewrite_probe(self,index):
        p=self.probe_paths[index];p.write_text(json.dumps(self.probes[index],ensure_ascii=False))
        self.summary['conditions'][index]['artifacts']['probes.json']['SHA256']=digest(p);self.write_summary()

    def model(self):return self.view.load_model(self.summary_path,self.registration_path,self.cached.summary_path,self.cached.old_gui)

    def test_two_new_actual_pairs_and_cached_three_k_reference_preserve_values(self):
        model=self.model()
        for expected in self.conditions:
            actual=find_condition(model,expected['id']);self.assertIsNotNone(actual)
            self.assertEqual(actual['actual_fundamental_Hz'],expected['actual_fundamental_Hz'])
            for cohort in COHORTS:
                self.assertEqual(actual['cohorts'][cohort]['normalizations'],expected['cohorts'][cohort]['normalizations'])
        cached=find_condition(model,'sine-3000-3030-beat30');self.assertIsNotNone(cached)
        self.assertEqual(cached['actual_fundamental_Hz'],[3000,3030])
        old=self.cached.conditions[0]['cohorts']['fresh_sine_3000_3030_caps']['normalizations']['raw_sine_1Vpp']
        self.assertEqual(cached['cohorts'][COHORTS[1]]['normalizations']['raw_1Vpp'],old)

    def test_terminal_regression_and_registration_hash_are_required(self):
        original=copy.deepcopy(self.summary)
        for key,value in (('status','running'),('inputs_unchanged',False),('producer_regression',{'status':'failed'}),
                          ('registration_sha256','0'*64),('candidate_adopted',True)):
            self.summary=copy.deepcopy(original);self.summary[key]=value;self.write_summary()
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_new_condition_sha_and_cached_reference_sha_are_bound(self):
        self.condition_paths[0].write_text('{"tampered":true}')
        with self.assertRaises((ValueError,RuntimeError)):self.model()
        self.rewrite_condition(0)
        self.cached.condition_paths[0].write_text('{"tampered":true}')
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_no_native_archive_field_or_potential_is_opened(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            if Path(path).suffix in ('.npz','.bin','.gz'):raise AssertionError('JSON view opened native data')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):self.model()

    def test_new_conditions_cannot_use_cached_carrier_labels_or_four_outputs(self):
        original=copy.deepcopy(self.conditions[0])
        for variant in ('carrier','beat','outputs'):
            self.conditions[0]=copy.deepcopy(original)
            if variant=='carrier':self.conditions[0]['actual_fundamental_Hz']=[3000,3030]
            elif variant=='beat':self.conditions[0]['beat_frequency_Hz']=10
            else:self.conditions[0]['source_provenance']['circuit']['n_outputs']=4
            self.rewrite_condition(0)
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_five_norms_and_saved_eight_gate_flags_are_not_silently_fabricated(self):
        self.conditions[0]['cohorts'][COHORTS[0]]['normalizations'].pop('equal_total_power');self.rewrite_condition(0)
        with self.assertRaises((ValueError,RuntimeError)):self.model()
        self.conditions[0]=self.mid_high_condition(PAIRS[0],self.conditions[0]['id'],self.probes[0])
        self.conditions[0]['canonical_square_cap_screen']['all_screen_checks_passed']=True;self.rewrite_condition(0)
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_probe_spectra_depth_gap_and_unloaded_contract_are_validated(self):
        original=copy.deepcopy(self.probes[0])
        for variant in ('spectrum','gap','depth','loaded'):
            self.probes[0]=copy.deepcopy(original)
            if variant=='spectrum':self.probes[0]['measurements'][0]['spectrum'][0]['frequency_Hz']=3000
            elif variant=='gap':self.probes[0]['measurements'][0]['tip_gap_mm']=10
            elif variant=='depth':self.probes[0]['measurements'][0]['depth_from_skin_surface_mm']=25
            else:self.probes[0]['unloaded_prediction']=False
            self.rewrite_probe(0)
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_nonfinite_statistics_are_rejected_even_with_matching_JSON_SHA(self):
        self.conditions[1]['cohorts'][COHORTS[1]]['normalizations']['raw_1Vpp']['regions'][PRIMARY]['maxTIS']['mean']=float('nan')
        self.rewrite_condition(1)
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_offline_display_does_not_mutate_or_recalculate_stored_values(self):
        model=self.model();before=copy.deepcopy(model)
        document=self.view.render_html(model,self.root/'new.html',self.root/'cached-frequency.html')
        self.assertEqual(model,before);self.assertIn('1.2345678901234567',document)
        parser=Selects();parser.feed(document)
        self.assertTrue({'cohort-select','roi-select','metric-select','normalization-select'}<=parser.ids)
        self.assertIn('unloaded',document.lower());self.assertIn('ETA',document)
        self.assertNotIn('<script src=',document);self.assertNotIn('fetch(',document)
        self.assertIn(self.cached.old_gui.name,document)

    def test_script_terminator_and_unicode_roundtrip_without_execution(self):
        literal='</script><script>literal only</script> 한글 Ω 👩‍🔬'
        self.summary['holds'].append(literal);self.write_summary();model=self.model()
        document=self.view.render_html(model,self.root/'new.html',self.root/'cached-frequency.html')
        raw=re.search(r'<script\b[^>]*type="application/json"[^>]*>(.*?)</script\s*>',document,re.DOTALL).group(1)
        self.assertIn(literal,json.dumps(json.loads(raw),ensure_ascii=False));self.assertNotIn('</script>',raw.lower())

    def test_exact_six_new_two_cached_and_four_regression_rhs_counters(self):
        original=copy.deepcopy(self.summary)
        for field,value in (('actual_native_RHS_solves',12),('actual_native_RHS_solves',4),('reused_9000_RHS_solves',0),('reused_regression_RHS_solves',0)):
            self.summary=copy.deepcopy(original);self.summary['resources'][field]=value;self.write_summary()
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.model()
        self.summary=copy.deepcopy(original);self.write_summary()
        self.registration['actual_new_native_RHS_solves_max']=12;self.rewrite_registration()
        with self.assertRaises(ValueError):self.model()

    def test_regression_proof_hash_and_reused_new_accounting_are_bound(self):
        self.regression_path.write_text('{"tampered":true}')
        with self.assertRaises(ValueError):self.model()
        self.regression['new_regression_RHS_solves']=4;self.rewrite_regression_proof()
        with self.assertRaises(ValueError):self.model()

    def test_donor_chain_and_original_failed_charge_must_match(self):
        original=copy.deepcopy(self.summary)
        self.summary['donor_reference']['source_commit']='e'*40;self.write_summary()
        with self.assertRaises(ValueError):self.model()
        self.summary=copy.deepcopy(original);self.summary['donor_reference']['original_failed_stage_charge']['seconds']=0.;self.write_summary()
        with self.assertRaises(ValueError):self.model()
        self.summary=copy.deepcopy(original);self.write_summary()
        self.regression['reused_from_donor'].pop('original_failure');self.rewrite_regression_proof()
        with self.assertRaises((ValueError,KeyError)):self.model()

    def test_old_failed_donor_paths_are_metadata_only_and_never_opened(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            if str(path).startswith('/synthetic/failed-donor'):
                raise AssertionError('Viewer reopened an old failed-donor artifact')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):self.model()

    def test_actual_assembly_distinguishes_six_new_rhs_from_two_cached_rhs(self):
        model=self.model()
        self.assertEqual(model['summary_metadata']['frequency_assembly'],self.assembly)
        self.assertEqual([item['display_role']for item in model['conditions']],
            ['new_analysis','new_analysis','cached_reference'])
        self.view.validate_frequency_assembly(self.assembly,'e'*64)
        for field,value in (('actual_new_basis_RHS_solves',8),('cached_basis_RHS_reused',0),
                            ('total_analysis_basis_vectors',6),('raw_metadata_modified',True),
                            ('single_four_frequency_native_producer_claimed',True),('inputs_unchanged',False)):
            assembly=copy.deepcopy(self.assembly);assembly['assembly_metadata'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.view.validate_frequency_assembly(assembly)

    def test_each_frequency_keeps_exact_native_or_cached_provenance(self):
        variants=(('kind','new_native'),('config_sha256','e'*64),('mask_sha256','b'*64),
                  ('exporter_class','CloudFrequencyMidHighBasis'),('basis_RHS_vectors',4),
                  ('frequency_Hz',9030),('basis_folder',''),('input_sha256',{}))
        for field,value in variants:
            assembly=copy.deepcopy(self.assembly);assembly['frequency_sources']['9000'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.view.validate_frequency_assembly(assembly)
        assembly=copy.deepcopy(self.assembly);assembly['frequency_sources'].pop('5030')
        with self.assertRaises(ValueError):self.view.validate_frequency_assembly(assembly)
        with self.assertRaises(ValueError):self.view.validate_frequency_assembly(self.assembly,'0'*64)

    def test_raw_new_three_frequency_list_and_cached_four_frequency_list_stay_separate(self):
        for target,field,value in (
                ('raw_new_frequency_metadata','frequencies_Hz',[5000,5030,9000,9030]),
                ('raw_new_frequency_metadata','actual_basis_RHS_solves',8),
                ('raw_new_frequency_metadata','exporter_class','CloudShapeBasis'),
                ('raw_new_frequency_metadata','exporter_kind','selectivity_native'),
                ('cached','frequencies_Hz',[9000]),
                ('assembly_metadata','analysis_frequencies_Hz',[5000,5030,9030]),
                ('assembly_metadata','raw_native_metadata_frequencies_Hz',[5000,5030,9000,9030])):
            assembly=copy.deepcopy(self.assembly)
            body=assembly['cached_frequency_metadata']['9000']if target=='cached'else assembly[target]
            body[field]=value
            with self.subTest(target=target,field=field),self.assertRaises(ValueError):
                self.view.validate_frequency_assembly(assembly)

    def test_condition_assembly_must_equal_source_bound_summary(self):
        self.conditions[0]['source_provenance']['frequency_sources']['9000']['basis_folder']='/different/cached/path'
        self.rewrite_condition(0)
        with self.assertRaises(ValueError):self.model()
        self.conditions[0]=self.mid_high_condition(PAIRS[0],self.conditions[0]['id'],self.probes[0])
        self.conditions[0]['source_provenance']['configuration_hash_scope']=''
        self.rewrite_condition(0)
        with self.assertRaises(ValueError):self.model()

    def test_lower_carrier_and_recovery_schemas_are_rejected(self):
        self.summary['schema']='task1-lower-carrier-result-v1';self.write_summary()
        with self.assertRaises(ValueError):self.model()
        self.summary['schema']='task1-mid-high-carrier-result-v1'
        self.registration['schema']='task1-lower-carrier-recovery-preregistration-v1';self.rewrite_registration()
        with self.assertRaises(ValueError):self.model()


if __name__=='__main__':unittest.main()
