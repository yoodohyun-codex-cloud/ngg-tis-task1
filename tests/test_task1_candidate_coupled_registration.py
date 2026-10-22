import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import task1_candidate_coupled_registration as registration


def metadata(coupled=False):
    return dict(h_xy_mm=.5, radius_mm=25., total_depth_mm=25.1,
        tissue_boundaries_mm=[0,.1,5.1,10.1,25.1], field_reconstruction='same',
        source_resistance_ohm=50., source_peak_V=.5, channels=2,
        sc_cells=8 if coupled else 2, bulk_layer_counts=[18,18,56] if coupled else [14,14,40],
        cells=786000 if coupled else 550200)


def condition(ident, wave):
    metrics = {name:1. for name in registration.GATE_PERCENT
               if name not in ('roi_mean_TIS_V_m','roi_p10_TIS_V_m','roi_mean_RMS_V_m','target_superficial_p95_ratio')}
    return dict(id=ident+'-'+wave,waveform=wave,actual_fundamental_Hz=[3000,3030],
        phase_deg=[0.,0.],source_Vpp_per_output=1.,metrics=metrics,
        volume_metrics=dict(regions=dict(target=dict(statistics=dict(maxTIS=dict(mean=1.,p10=1.),RMS=dict(mean=1.))),
            surface_0_5=dict(statistics=dict(maxTIS=dict(p95=1.))))))


class CandidateCoupledTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(status='complete',id=registration.TEMPLATE_ID,mesh_metadata=metadata(),
            conditions=[condition(registration.TEMPLATE_ID,w) for w in ('square_3h','sine','triangle_3h')])
        self.new = dict(status='complete',id=registration.CASE_ID,mesh_metadata=metadata(True),
            conditions=[condition(registration.CASE_ID,w) for w in ('square_3h','sine','triangle_3h')])
        self.case = dict(id=registration.CASE_ID,
            candidate_same_xy_reference=dict(postprocess_path='/tmp/candidate-summary.json',postprocess_sha256='pinned'),
            baseline_coupled_reference=dict(case_id='baseline-square15-coupled-xy100-sc8-bulk'))

    def compare(self, new=None):
        with patch.object(registration.core,'sha',return_value='pinned'), patch.object(registration.core,'read',return_value=self.old):
            return registration.compare_candidate_coupled(Path('/tmp/cloud-test'),self.case,new or self.new)

    def test_all36_original_gates_and_no_adoption_promotion(self):
        result = self.compare()
        self.assertTrue(result['all_registered_comparison_gates_passed'])
        self.assertEqual(36,result['gate_count'])
        for key in ('candidate_adopted','matched_burden_evaluated','whole_XY_slab_evaluated',
                    'continuum_convergence_validated','experimental_validation'):
            self.assertFalse(result[key])
        for row in result['waveform_comparisons']:
            self.assertEqual(registration.GATE_PERCENT.keys(),row['changes'].keys())

    def test_contact5percent_failure_is_preserved(self):
        changed = copy.deepcopy(self.new)
        changed['conditions'][0]['metrics']['surface_J_RMS_max_A_m2'] = 1.05001
        result = self.compare(changed)
        self.assertFalse(result['all_registered_comparison_gates_passed'])
        self.assertFalse(result['waveform_comparisons'][0]['changes']['surface_J_RMS_max_A_m2']['passed'])
        self.assertEqual(5.,result['waveform_comparisons'][0]['changes']['surface_J_RMS_max_A_m2']['limit_percent'])

    def test_missing_wave_zero_power_and_changed_phantom_are_rejected(self):
        variants = []
        missing = copy.deepcopy(self.new);missing['conditions'].pop();variants.append(missing)
        zero = copy.deepcopy(self.new);zero['conditions'][0]['metrics']['source_power_W']=0.;variants.append(zero)
        phantom = copy.deepcopy(self.new);phantom['mesh_metadata']['radius_mm']=30.;variants.append(phantom)
        for changed in variants:
            with self.assertRaises(ValueError):self.compare(changed)

    def test_real_template_has400mm2_and_coupled_stays_below_cap(self):
        pool=json.loads((registration.core.HIST/'preregistration.json').read_text())['case_pool']
        template=copy.deepcopy(pool[registration.TEMPLATE_ID])
        registration.validate_candidate_template(template)
        self.assertAlmostEqual(400.,sum(template['expected_pad_areas_m2'])*1e6)
        wrong=copy.deepcopy(template);wrong['expected_pad_areas_m2']=[.000225]*4
        with self.assertRaises(ValueError):registration.validate_candidate_template(wrong)
        template.update(sc_cells=8,bulk_counts=[18,18,56])
        self.assertEqual(786000,registration._mesh(template)['cells'])
        self.assertLessEqual(786000,registration.core.LIMITS['max_cells'])

    def test_config_changes_only_sc_bulk_and_portable_mask_path(self):
        source=registration.core.HIST/'configs'/(registration.TEMPLATE_ID+'.properties')
        before=source.read_bytes()
        changes={'validation.sc_cells':'8','bulk.counts':'18,18,56','mask.path':'/tmp/new-mask.csv'}
        after=registration._changed_config(before,changes)
        a,b=registration._properties(before),registration._properties(after)
        self.assertEqual(set(changes),{key for key in a if a[key]!=b[key]})
        self.assertEqual(before,source.read_bytes())

    def test_same_models_reject_contact_change_but_allow_area_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            a,b=Path(temporary)/'a',Path(temporary)/'b'
            text='sc.sigma=.0002\nz.3000.re=.01\nh_mm=.5\nchannels=2\nfrequencies=3000,3030,9000,9090\n'
            a.write_text(text+'pad.0.width_mm=10\n');b.write_text(text+'pad.0.width_mm=15\n')
            registration.require_same_models({'config_file':str(a)},{'config_file':str(b)})
            b.write_text(text.replace('z.3000.re=.01','z.3000.re=.02'))
            with self.assertRaises(ValueError):registration.require_same_models({'config_file':str(a)},{'config_file':str(b)})


if __name__=='__main__':
    unittest.main()
