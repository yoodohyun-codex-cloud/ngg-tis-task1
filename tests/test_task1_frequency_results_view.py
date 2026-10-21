"""Synthetic JSON-only frequency viewer tests; no analysis or CLI rendering."""
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
COHORTS=('cached_original_square_3000_3030_caps', 'fresh_sine_3000_3030_caps')
MODES=('raw_sine_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
       'skin_contact_only', 'legacy_composite_full_skin')
PRIMARY='primary_r5_depth15_20'
SLAB='supplemental_wholeXY_depth15_20'
PAIRS=((3000,3030),(9000,9090))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_condition(value, identifier):
    if isinstance(value,dict):
        if value.get('id')==identifier and 'cohorts' in value:
            return value
        for child in value.values():
            found=find_condition(child,identifier)
            if found is not None:return found
    elif isinstance(value,list):
        for child in value:
            found=find_condition(child,identifier)
            if found is not None:return found
    return None


class SelectParser(HTMLParser):
    def __init__(self):
        super().__init__();self.identifiers=set()

    def handle_starttag(self,tag,attrs):
        if tag=='select':self.identifiers.add(dict(attrs).get('id'))


class FrequencyResultsViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name,path in (('fixture',ROOT/'tests/test_task1_volume_audit_view.py'),
                          ('view',ROOT/'tools/task1_frequency_results_view.py')):
            spec=importlib.util.spec_from_file_location('frequency_view_'+name,path)
            module=importlib.util.module_from_spec(spec)
            sys.modules[spec.name]=module;spec.loader.exec_module(module)
            setattr(cls,name,module)

    def setUp(self):
        baseline=self.fixture.VolumeAuditViewTests('runTest')
        baseline.setUp();self.addCleanup(baseline.doCleanups)
        self.baseline=baseline;self.root=baseline.directory
        baseline.report['cases']=baseline.report['cases'][:1]
        baseline.report['cases'][0]['case_id']='baseline-square15-xy80'
        baseline.write()
        self.baseline_case=baseline.report['cases'][0]
        self.old_gui=self.root/'CLOUD_RESULTS.html';self.old_gui.write_text('<!doctype html><title>prior maps</title>')
        self.plan=self.root/'frequency-preregistration.json'
        self.plan.write_text(json.dumps(dict(schema='task1-frequency-resynthesis-preregistration-v1',
            status='preregistered_not_executed',new_PDE_conditions=0,actual_frequency_pairs=[list(p)for p in PAIRS])))
        self.condition_paths=[];self.probe_paths=[];self.conditions=[];self.probes=[];rows=[]
        for pair in PAIRS:
            identifier=f'sine-{pair[0]}-{pair[1]}-beat{pair[1]-pair[0]}'
            folder=self.root/identifier;folder.mkdir()
            probes=self.probe_fixture(pair)
            probe_path=folder/'probes.json';probe_path.write_text(json.dumps(probes))
            condition=self.condition_fixture(pair,identifier,probes)
            condition_path=folder/'condition.json';condition_path.write_text(json.dumps(condition))
            native=folder/'volume.npz';native.write_bytes(b'opaque native arrays; JSON viewer must not open')
            metrics=folder/'native-volume-metrics.json';metrics.write_text('{"status":"complete"}')
            artifacts={p.name:dict(path=str(p),SHA256=digest(p))for p in (condition_path,probe_path,native,metrics)}
            rows.append(dict(id=identifier,actual_fundamental_Hz=list(pair),beat_frequency_Hz=pair[1]-pair[0],
                             status='calculated_unadopted',artifacts=artifacts))
            self.condition_paths.append(condition_path);self.probe_paths.append(probe_path)
            self.conditions.append(condition);self.probes.append(probes)
        self.summary=dict(schema='task1-frequency-resynthesis-audit-v1',status='calculated_unadopted',
            conditions=rows,new_PDE=0,actual_frequency_pairs=[list(p)for p in PAIRS],
            actual_beat_frequencies_Hz=[30,90],waveform='sine',comparison_cohorts=list(COHORTS),
            holds=['No experimental, physiological or loaded-instrument validation'],
            adopted=False,candidate_adopted=False,numerical_validation_promoted=False,inputs_unchanged=True,
            preregistration=dict(path=str(self.plan),SHA256=digest(self.plan)),
            input_sha256={self.baseline_case['summary_path']:digest(self.baseline_case['summary_path'])})
        self.summary_path=self.root/'frequency-summary.json';self.write_summary()

    def probe_fixture(self,pair):
        rows=[]
        for depth in (5.,10.,15.,20.):
            for name,x,y in (('centre',0.,0.),('x_plus',5.,0.),('x_minus',-5.,0.),
                             ('y_plus',0.,5.),('y_minus',0.,-5.)):
                for axis in ('X','Y'):
                    dx,dy=(2.5,0.)if axis=='X'else(0.,2.5)
                    rows.append(dict(id=f'd{depth:g}-{name}-{axis}',status='complete',
                        depth_from_skin_surface_mm=depth,position=name,axis=axis,centre_mm=[x,y,depth],
                        plus_mm=[x+dx,y+dy,depth],minus_mm=[x-dx,y-dy,depth],
                        plus_centre_pitch_mm=5.,tip_gap_mm=5.,RMS_V=.0125,Vpp_lower_V=.025,
                        Vpp_upper_V=.026,fundamental_fixed_axis_envelope=dict(variation_range_V=.01),
                        spectrum=[dict(frequency_Hz=f,real_V=0.,imaginary_V=-.01)for f in pair]))
        return dict(status='complete',measurements=rows,unloaded_prediction=True,
            instrument_loading_validated=False,actual_fundamental_Hz=list(pair),beat_frequency_Hz=pair[1]-pair[0],
            waveform='sine',actual_source_Vpp_by_output=[1.,1.],
            measurement_grid=dict(depths_mm=[5.,10.,15.,20.],plus_centre_pitch_mm=5.,tip_gap_mm=5.,
                                  centres_per_depth=5,directions_per_centre=2),
            coordinate_system=dict(unit='mm',depth_axis='+z',surface_z_mm=0.),numerical_checks=dict(all_passed=True))

    def condition_fixture(self,pair,identifier,probes):
        cohorts={}
        for cohort in COHORTS:
            modes=copy.deepcopy(self.baseline_case['normalizations'])
            modes['raw_sine_1Vpp']=modes.pop('raw_1Vpp')
            for mode in modes.values():
                scale=mode.pop('source_Vpp_per_output');mode['source_Vpp_by_output']=[scale,scale]
                mode['probe40_unloaded']=[dict(id=row['id'],RMS_V=row['RMS_V'],
                    Vpp_lower_V=row['Vpp_lower_V'],Vpp_upper_V=row['Vpp_upper_V'],
                    fundamental_envelope_variation_V=.01)for row in probes['measurements']]
                mode['regions'][PRIMARY]['maxTIS']['mean']=19.87654321012345 if pair[0]==9000 else 7.125
                mode['carrier_and_balance_regions']={region:{key:copy.deepcopy(stats['RMS'])
                    for key in ('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m',
                                'max_direction_balance','fixed_direction_balance')}
                    for region,stats in mode['regions'].items()}
            cohorts[cohort]=dict(reference_id=self.baseline_case['condition_id']if cohort==COHORTS[0]
                else 'sine-3000-3030-beat30',reference_waveform='square_3h'if cohort==COHORTS[0]else'sine',
                reference_actual_fundamental_Hz=[3000,3030],normalizations=modes,
                cutoff_reference='cached original square3000/3030; same frozen numerical values in every cohort')
        return dict(schema='task1-frequency-resynthesis-condition-v1',status='calculated_unadopted',
            id=identifier,actual_fundamental_Hz=list(pair),beat_frequency_Hz=pair[1]-pair[0],waveform='sine',
            source_provenance=dict(run_id=self.baseline_case['run_id'],case_id=self.baseline_case['case_id'],
                source_summary=self.baseline_case['summary_path'],source_commit='a'*40,configuration_sha256='b'*64,
                circuit=copy.deepcopy(self.baseline_case['circuit'])),source_Vpp_by_output=[1.,1.],cohorts=cohorts,
            electrical_metrics=dict(target20_modulation_V_m=2.,target20_total_E_RMS_V_m=1.),
            new_PDE=0,candidate_adopted=False,numerical_validation_promoted=False,
            instrument_loading_validated=False,C1_status='No newly frequency-matched true electrode-pair control calculated')

    def write_summary(self):
        self.summary_path.write_text(json.dumps(self.summary,ensure_ascii=False))

    def rewrite_condition(self,index):
        path=self.condition_paths[index];path.write_text(json.dumps(self.conditions[index],ensure_ascii=False))
        self.summary['conditions'][index]['artifacts']['condition.json']['SHA256']=digest(path)
        self.write_summary()

    def rewrite_probe(self,index):
        path=self.probe_paths[index];path.write_text(json.dumps(self.probes[index],ensure_ascii=False))
        self.summary['conditions'][index]['artifacts']['probes.json']['SHA256']=digest(path)
        self.write_summary()

    def model(self):
        return self.view.load_model(self.summary_path,self.baseline.path,self.old_gui)

    def test_exact_two_frequency_conditions_and_both_five_mode_cohorts_are_preserved(self):
        model=self.model()
        for condition in self.conditions:
            actual=find_condition(model,condition['id'])
            self.assertIsNotNone(actual)
            self.assertEqual(actual['actual_fundamental_Hz'],condition['actual_fundamental_Hz'])
            self.assertEqual(actual['beat_frequency_Hz'],condition['beat_frequency_Hz'])
            for cohort in COHORTS:
                self.assertEqual(set(actual['cohorts'][cohort]['normalizations']),set(MODES))
                self.assertEqual(actual['cohorts'][cohort]['normalizations'],condition['cohorts'][cohort]['normalizations'])

    def test_original_square_baseline_must_be_present_and_source_bound(self):
        model=self.model();self.assertIn(self.baseline_case['condition_id'],json.dumps(model))
        self.baseline.report['cases']=[];self.baseline.write()
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_missing_baseline_source_hash_binding_is_rejected(self):
        self.summary['input_sha256']={};self.write_summary()
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_native_NPZ_is_never_opened_or_decoded_by_JSON_viewer(self):
        original_open=Path.open
        def guarded(path,*args,**kwargs):
            if Path(path).suffix in ('.npz','.bin','.gz'):
                raise AssertionError('Frequency JSON viewer opened native data')
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):
            model=self.model()
            self.assertIn('9000',json.dumps(model))

    def test_tampered_condition_or_probe_artifact_bytes_are_rejected(self):
        for path in (self.condition_paths[0],self.probe_paths[1]):
            original=path.read_bytes();path.write_bytes(original+b' ')
            with self.subTest(path=path.name),self.assertRaises((ValueError,RuntimeError)):self.model()
            path.write_bytes(original)

    def test_actual_frequency_and_beat_metadata_cannot_relabel_high_carrier_as_low(self):
        original=copy.deepcopy(self.conditions[1])
        for key,value in (('actual_fundamental_Hz',[3000,3030]),('beat_frequency_Hz',30)):
            self.conditions[1]=copy.deepcopy(original);self.conditions[1][key]=value;self.rewrite_condition(1)
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_missing_cohort_mode_or_electrical_metric_is_rejected(self):
        original=copy.deepcopy(self.conditions[0])
        for variant in ('cohort','mode','metric'):
            self.conditions[0]=copy.deepcopy(original);condition=self.conditions[0]
            if variant=='cohort':condition['cohorts'].pop(COHORTS[1])
            elif variant=='mode':condition['cohorts'][COHORTS[0]]['normalizations'].pop('equal_total_power')
            else:condition['cohorts'][COHORTS[0]]['normalizations']['raw_sine_1Vpp']['regions'][PRIMARY].pop('RMS')
            self.rewrite_condition(0)
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_nonfinite_precomputed_statistics_are_rejected_after_valid_SHA_update(self):
        self.conditions[1]['cohorts'][COHORTS[1]]['normalizations']['raw_sine_1Vpp']['regions'][PRIMARY]['maxTIS']['mean']=float('nan')
        self.rewrite_condition(1)
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_physical_four_pads_do_not_allow_four_independent_outputs(self):
        self.conditions[0]['source_provenance']['circuit']['n_outputs']=4;self.rewrite_condition(0)
        with self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_probe_geometry_ids_and_unloaded_scope_are_verified(self):
        original=copy.deepcopy(self.probes[0])
        for variant in ('gap','depth','duplicate','loaded'):
            self.probes[0]=copy.deepcopy(original);probe=self.probes[0]
            if variant=='gap':probe['measurement_grid']['tip_gap_mm']=10.
            elif variant=='depth':probe['measurements'][0]['depth_from_skin_surface_mm']=25.
            elif variant=='duplicate':probe['measurements'][-1]['id']=probe['measurements'][0]['id']
            else:probe['unloaded_prediction']=False
            self.rewrite_probe(0)
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_summary_cannot_claim_new_PDE_adoption_or_unchanged_missing_sources(self):
        original=copy.deepcopy(self.summary)
        for key,value in (('new_PDE',1),('candidate_adopted',True),('inputs_unchanged',False),('status','running')):
            self.summary=copy.deepcopy(original);self.summary[key]=value;self.write_summary()
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):self.model()

    def test_render_keeps_precomputed_values_model_and_offline_selectors(self):
        model=self.model();before=copy.deepcopy(model)
        document=self.view.render_html(model,self.root/'frequency.html')
        self.assertEqual(model,before)
        self.assertIn('19.87654321012345',document)
        self.assertIn(PRIMARY,document);self.assertIn(SLAB,document)
        parser=SelectParser();parser.feed(document)
        self.assertTrue({'cohort-select','roi-select','metric-select','normalization-select'}<=parser.identifiers)
        self.assertNotIn('<script src=',document);self.assertNotIn('fetch(',document)
        self.assertIn('unloaded',document.lower());self.assertIn(self.old_gui.name,document)

    def test_literal_script_terminator_and_Unicode_roundtrip_in_embedded_JSON(self):
        literal='</script><script>literal only</script> 한글 Ω \u2028 👩‍🔬'
        self.summary['holds'].append(literal);self.write_summary()
        model=self.model();document=self.view.render_html(model,self.root/'frequency.html')
        match=re.search(r'<script\b[^>]*type="application/json"[^>]*>(.*?)</script\s*>',document,re.DOTALL)
        self.assertIsNotNone(match)
        restored=json.loads(match.group(1))
        self.assertIn(literal,json.dumps(restored,ensure_ascii=False))
        self.assertNotIn('</script>',match.group(1).lower())


if __name__=='__main__':
    unittest.main()
