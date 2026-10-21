"""Synthetic JSON-viewer contract tests; no PDE, native decode or real rendering."""
from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODES = ('raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
         'skin_contact_only', 'legacy_composite_full_skin')
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
PRIMARY = 'primary_r5_depth15_20'
SLAB = 'supplemental_wholeXY_depth15_20'
REGIONS = ('total', PRIMARY, SLAB, 'surface_0_5', 'primary_complement', 'supplemental_complement')
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2', 'contact_voltage_RMS_max_V',
           'SC_power_W', 'contact_power_W', 'source_power_W', 'bulk_skin_J_vector_RMS_max_A_m2',
           'bulk_skin_J_vector_RMS_p95_A_m2', 'skin_SC_plus_dermis_power_W')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unwrap(value):
    if 'cases' in value:
        return value
    for key in ('report', 'audit', 'data'):
        if isinstance(value.get(key), dict) and 'cases' in value[key]:
            return value[key]
    raise AssertionError('Validated report must expose the original audit cases')


class SelectParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.select_ids = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'select':
            self.select_ids.add(dict(attrs).get('id'))


def stats(scale, metric, region):
    factor = {'maxTIS': 1., 'fixedTIS': .5, 'RMS': .75}[metric]
    mean = 3.333333*scale*factor
    volume = {PRIMARY: 4e-7, SLAB: 1e-5, 'total': 5e-5,
              'surface_0_5': 1e-5, 'primary_complement': 4.96e-5,
              'supplemental_complement': 4e-5}[region]
    return dict(min=1.*scale*factor, max=10.*scale*factor, mean=mean,
        p10=2.*scale*factor, p50=3.*scale*factor, p90=7.*scale*factor,
        p95=8.*scale*factor, p99=9.*scale*factor, std=scale*factor,
        CV=1/3.333333, p10_over_mean=2/3.333333, volume_m3=volume,
        positive_weight_cells=4, maximum_scope='native cell-constant represented samples; not continuum maximum',
        hotspot=dict(native_cell_index=3, center_xyz_mm=[1., 2., .025],
            layer_index=0, layer='stratum_corneum', tied_native_cell_count=1,
            position_scope='center of a cell with positive fractional region overlap; may lie outside ROI boundary'),
        fixed_baseline_threshold_volume={
            key: dict(cutoff_V_m=cutoff, volume_m3=volume/2, region_volume_fraction=.5,
                comparison='scaled native scalar >= frozen raw same-grid baseline cutoff',
                quantity='high_field_RMS' if metric == 'RMS' else 'high_fundamental_TIS_modulation',
                interpretation='electrical numerical comparison; not biological activation or safety')
            for key, cutoff in {PRIMARY+'_mean': 3., PRIMARY+'_p10': 2.,
                                SLAB+'_mean': 3.5, SLAB+'_p10': 2.5}.items()})


class VolumeAuditViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('volume_view_test_target', ROOT/'tools/task1_volume_audit_view.py')
        cls.view = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.view
        spec.loader.exec_module(cls.view)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.inputs = {}
        self.summary_paths = {}
        for name in ('baseline', 'candidate'):
            p = self.directory/(name+'-summary.json')
            p.write_text(json.dumps(dict(status='complete', id=name)))
            self.inputs[str(p)] = digest(p)
            self.summary_paths[name] = p
        self.probe = self.directory/'probes.json'
        self.probe.write_text(json.dumps(dict(status='complete', unloaded_prediction=True)))
        self.inputs[str(self.probe)] = digest(self.probe)
        self.native = self.directory/'volume.npz'
        self.native.write_bytes(b'opaque native archive fixture; do not open in JSON viewer')
        self.inputs[str(self.native)] = digest(self.native)
        self.plan = self.directory/'preregistration.json'
        self.plan.write_text(json.dumps(dict(schema='task1-volume-selectivity-audit-preregistration-v1',
            status='preregistered_not_executed', new_PDE_conditions=0)))
        self.inputs[str(self.plan)] = digest(self.plan)
        self.report = dict(schema='task1-volume-selectivity-v1', status='calculated_unadopted',
            feedback_id='T1-F010-S1-GH6297472037', source_comment_id=6297472037,
            source_sha256='d'*64, implementation_git_commit='a'*40,
            implementation_file_SHA256='d'*64, new_PDE_solves=0,
            preregistration=dict(path=str(self.plan),SHA256=digest(self.plan),verified_before_and_after=True),
            selected_for_adoption=[], inputs_sha256=self.inputs, inputs_unchanged=True,
            scope=dict(primary_ROI='central r<=5mm, depth15..20mm unchanged',
                supplemental_ROI='whole native modeled XY cross-section, depth15..20mm; separately reported',
                coordinates='x,y horizontal; z positive depth from top, all positions mm',
                weights='saved fractional primary ROI and h^2 dz native full-cell volume; exact face-clipped slab',
                whole_XY_geometry='center-in-disk FVM square cells; staircase wall, not exact cylinder clipping; no volume renormalization',
                quantiles='stable inverse volume-weighted ECDF, searchsorted side=left; native cell steps/ties retained; no interpolation',
                metrics=dict(maxTIS='fundamentals only, maximum over2074 sampled directions; lower bound to continuous direction maximum',
                    fixedTIS='fundamentals only along (1/sqrt(2),1/sqrt(2),0)',
                    RMS='total vector electric-field RMS including all4 stored square_3h spectral lines; not modulation'),
                omitted='X/Y/Z directional scalar fields not cached; sine/triangle RMS not available in this archive',
                current_sum='sum of each physical output RMS including all harmonics/passive-frequency currents; bookkeeping, not common-GND return current',
                skin_contact_only='eight skin/contact burden caps, no source-power cap and no1Vpp ceiling; may exceed1Vpp numerically',
                legacy_composite_full_skin='same eight caps plus source-power cap and1Vpp ceiling',
                equal_current_and_power='no1Vpp ceiling; only named denominator is equalized',
                limits='frozen raw same-grid baseline numerical burdens and scalar cutoffs; not human safety/activation limits'),
            cases=[self.case('baseline',4), self.case('candidate',8)])
        self.path = self.directory/'audit.json'
        self.write()

    def case(self, name, pads):
        modes = {}
        factors = dict(zip(MODES, (1., .8, .7, 1.2, .6))) if name == 'candidate' else {mode:1. for mode in MODES}
        for mode, scale in factors.items():
            modes[mode] = dict(amplitude_scale=scale, source_Vpp_per_output=scale,
                baseline_derived_numerical_limits={key:1. for key in BURDENS},
                normalized_burdens={key:scale**(2 if key.endswith('_W') else 1) for key in BURDENS},
                sum_source_output_RMS_mA=2*scale, source_output_RMS_by_output_mA=[scale,scale],
                active_skin_contact_caps=['surface_J_RMS_p95_A_m2'] if mode == 'skin_contact_only' else [],
                includes_source_power_cap=mode=='legacy_composite_full_skin',
                includes_1Vpp_ceiling=mode=='legacy_composite_full_skin', may_require_more_than_1Vpp=scale>1,
                interpretation='numerical normalization only; baseline limits are not human safety limits',
                regions={region:{metric:stats(scale,metric,region) for metric in METRICS} for region in REGIONS})
        return dict(case_id=name, design_id='baseline-square15' if name=='baseline' else 'test-candidate',
            run_id='synthetic-run', condition_id=name+'-square_3h', summary_path=str(self.summary_paths[name]),
            comparison_signature='signature-A', baseline_summary=str(self.summary_paths['baseline']),
            source_commit='a'*40, configuration_sha256='b'*64, physical_model_version='c'*64,
            circuit=dict(n_pads=pads,n_outputs=2,n_return_nodes=1,return_topology='all_return_pads_ideal_common_GND',
                source_Vpp_each=1.,source_peak_V=.5,source_resistance_ohm=50.,
                inactive_source_at_other_frequencies='0 V through 50 ohm',
                carrier_assignment_Hz=[3000,3030],pad_to_node={str(i):'out0' if i==0 else 'out1' if i==1 else 'GND' for i in range(pads)}),
            mesh=dict(radius_mm=25.,total_depth_mm=25.1,h_xy_mm=1.25,sc_cells=2,bulk_layer_counts=[14,14,40],
                cells=4,tissue_boundaries_mm=[0.,.1,5.1,10.1,25.1],frequencies_Hz=[3000,3030,9000,9090]),
            primary_ROI_reproduction={metric:dict(mean=3.333333,p10=2.,passed=True) for metric in METRICS},
            fixed_same_grid_baseline_cutoffs_V_m={metric:{PRIMARY+'_mean':3.,PRIMARY+'_p10':2.,SLAB+'_mean':3.5,SLAB+'_p10':2.5} for metric in METRICS},
            represented_geometry={region:dict(represented_volume_m3=stats(1.,'maxTIS',region)['volume_m3'],
                analytic_ideal_volume_m3=stats(1.,'maxTIS',region)['volume_m3'],represented_minus_analytic_percent=0.) for region in REGIONS},
            normalizations=modes,raw_probe_artifact_reference=dict(path=str(self.probe),SHA256=digest(self.probe),
                scope='raw unloaded probe predictions only; no newly reconstructed or loaded Vpp'),
            adopted=False,calculation_status='cached_native_scalar_audit_complete',
            numerical_validation_status='primary_statistics_reproduced_only; mesh/convergence gates unchanged',
            experimental_validation_status='not_established')

    def write(self):
        self.path.write_text(json.dumps(self.report))

    def validated(self):
        return self.view.validate_audit(self.path, verify_sources=True)

    def test_valid_report_preserves_five_normalizations_three_metrics_and_two_ROIs(self):
        validated = self.validated()
        data = unwrap(validated)
        self.assertEqual(set(data['cases'][1]['normalizations']),set(MODES))
        for mode in MODES:
            self.assertEqual(set(data['cases'][1]['normalizations'][mode]['regions'][PRIMARY]),set(METRICS))
            self.assertIn(SLAB,data['cases'][1]['normalizations'][mode]['regions'])
        self.assertEqual(data['cases'][1]['normalizations']['skin_contact_only']['source_Vpp_per_output'],1.2)

    def test_wrong_schema_noncomplete_audit_or_PDE_claim_is_rejected(self):
        for field,value in [('schema','other'),('status','running'),('inputs_unchanged',False),('new_PDE_solves',1),('selected_for_adoption',['candidate'])]:
            with self.subTest(field=field):
                original=self.report[field];self.report[field]=value;self.write()
                with self.assertRaises((ValueError,RuntimeError)):self.validated()
                self.report[field]=original

    def test_preregistered_source_and_verification_receipt_are_required(self):
        self.report['preregistration']['verified_before_and_after']=False
        self.write()
        with self.assertRaises((ValueError,RuntimeError)):self.validated()
        self.report['preregistration']['verified_before_and_after']=True
        self.write()
        self.plan.write_text('{"changed":true}')
        with self.assertRaises((ValueError,RuntimeError)):self.validated()

    def test_source_JSON_hash_tamper_is_rejected(self):
        self.probe.write_text('{"status":"changed"}')
        with self.assertRaises((ValueError,RuntimeError)):self.validated()

    def test_nonfinite_precomputed_statistic_is_rejected(self):
        self.report['cases'][1]['normalizations']['raw_1Vpp']['regions'][PRIMARY]['maxTIS']['mean']=float('nan')
        self.write()
        with self.assertRaises((ValueError,RuntimeError)):self.validated()

    def test_missing_or_renamed_normalization_is_rejected(self):
        for name in MODES:
            with self.subTest(mode=name):
                data=copy.deepcopy(self.report);data['cases'][1]['normalizations'].pop(name)
                self.path.write_text(json.dumps(data))
                with self.assertRaises((ValueError,RuntimeError)):self.validated()

    def test_missing_metric_or_primary_ROI_is_rejected(self):
        for field in ('metric','ROI'):
            with self.subTest(field=field):
                data=copy.deepcopy(self.report)
                if field=='metric':data['cases'][1]['normalizations']['raw_1Vpp']['regions'][PRIMARY].pop('RMS')
                else:data['cases'][1]['normalizations']['raw_1Vpp']['regions'].pop(PRIMARY)
                self.path.write_text(json.dumps(data))
                with self.assertRaises((ValueError,RuntimeError)):self.validated()

    def test_view_never_reads_native_npz_or_imports_scientific_solver(self):
        real_open=Path.open
        def safe_open(path,*args,**kwargs):
            if Path(path).suffix=='.npz':raise AssertionError('JSON viewer opened native NPZ')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',safe_open):
            validated=self.validated()
            model=self.view.build_model([validated])
            self.assertIn('candidate',json.dumps(model))

    def test_identical_duplicate_case_is_deduplicated_but_conflict_rejected(self):
        validated=self.validated()
        cases=self.view.collect_cases([validated,validated])
        self.assertEqual(len(cases),2)
        other=copy.deepcopy(validated)
        unwrap(other)['cases'][1]['normalizations']['raw_1Vpp']['regions'][PRIMARY]['maxTIS']['mean']+=.1
        with self.assertRaises((ValueError,RuntimeError)):self.view.collect_cases([validated,other])

    def test_model_and_offline_HTML_keep_source_values_not_rescaled_again(self):
        model=self.view.build_model([self.validated()])
        before=copy.deepcopy(model)
        output=self.directory/'volume-view.html'
        document=self.view.render_html(model,output,self.directory/'CLOUD_RESULTS.html')
        self.assertEqual(model,before)
        self.assertIn(PRIMARY,document);self.assertIn(SLAB,document)
        for metric in METRICS:self.assertIn(metric,document)
        for mode in MODES:self.assertIn(mode,document)
        self.assertIn('candidate',document);self.assertIn('baseline',document)
        self.assertNotIn('<script src=',document)
        self.assertNotIn('fetch(',document)
        self.assertIn('unloaded',document.lower())
        parser=SelectParser();parser.feed(document)
        self.assertTrue({'roi-select','metric-select','normalization-select'}<=parser.select_ids)

    def test_validated_report_records_native_declaration_separately_from_verified_small_inputs(self):
        validated=self.validated()
        self.assertEqual(validated['native_inputs_declared_not_opened'][str(self.native)],digest(self.native))
        self.assertNotIn(str(self.native),validated['verified_small_inputs'])
        self.assertEqual(validated['verified_small_inputs'][str(self.probe)],digest(self.probe))
        self.assertEqual(validated['SHA256'],digest(self.path))
        self.assertEqual(Path(validated['path']),self.path.resolve())

    def test_build_model_is_independent_of_later_fixture_mutation(self):
        validated=self.validated()
        model=self.view.build_model([validated])
        saved=copy.deepcopy(model)
        unwrap(validated)['cases'][1]['normalizations']['raw_1Vpp']['regions'][PRIMARY]['maxTIS']['mean']=999.
        self.assertEqual(model,saved)

    def test_missing_same_grid_baseline_produces_explicit_hold(self):
        self.report['cases']=self.report['cases'][1:]
        self.write()
        model=self.view.build_model([self.validated()])
        self.assertTrue(model['holds'])
        candidate=next(case for case in model['cases'] if case['case_id']=='candidate')
        self.assertFalse(candidate['baseline_present'])

    def test_wrong_baseline_output_count_cannot_be_a_same_grid_control(self):
        self.report['cases'][0]['circuit']['n_outputs']=4
        self.write()
        try:
            model=self.view.build_model([self.validated()])
        except (ValueError,RuntimeError):
            return
        self.assertTrue(model['holds'])
        self.assertFalse(next(case for case in model['cases'] if case['case_id']=='candidate')['baseline_present'])

    def test_embedded_JSON_script_terminator_and_Unicode_roundtrip_exactly(self):
        model=self.view.build_model([self.validated()])
        literal='</script><script>literal only</script> 한글 Ω ≤5mm \u2028 👩‍🔬'
        model['definitions']['roundtrip_literal']=literal
        document=self.view.render_html(model,self.directory/'view.html',self.directory/'maps.html')
        match=re.search(r'<script\b[^>]*type="application/json"[^>]*>(.*?)</script\s*>',document,re.DOTALL)
        self.assertIsNotNone(match,'Offline report must contain an application/json data script')
        embedded=json.loads(match.group(1))
        self.assertEqual(embedded['definitions'],model['definitions'])
        self.assertEqual(embedded['definitions']['roundtrip_literal'],literal)
        self.assertNotIn('</script>',match.group(1).lower())

    def test_changed_fixed_layer_boundary_is_rejected(self):
        case=copy.deepcopy(self.report['cases'][0])
        self.view.check_case(case)
        case['mesh']['tissue_boundaries_mm']=[0.,.2,5.1,10.1,25.1]
        with self.assertRaises((ValueError,RuntimeError)):
            self.view.check_case(case)


if __name__=='__main__':unittest.main()
