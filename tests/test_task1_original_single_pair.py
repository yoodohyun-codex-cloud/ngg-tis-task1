"""Synthetic latest fine TIS/C1 linkage; no native arrays, PDE or preparation."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('original_single_pair_tested',ROOT/'tools/task1_original_single_pair.py')
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)


def probes():
    return dict(status='complete',measurements=[dict(id=f'{d}-{p}-{a}',RMS_V=.01,Vpp_lower_V=.02,Vpp_upper_V=.020000001,
        fundamental_fixed_axis_envelope=dict(variation_range_V=0.),axis=a,depth_from_skin_surface_mm=d,position=p,tip_gap_mm=5.)
        for d in(5,10,15,20)for p in('centre','x_plus','x_minus','y_plus','y_minus')for a in('X','Y')])


def metrics():
    current=.001-.0005j;ideal=-.5j;loaded=ideal-50*current
    return dict(source_current_spectrum=[dict(frequency_Hz=f,real_A=[current.real if f==3000 else 0.],imaginary_A=[current.imag if f==3000 else 0.])for f in(3000,3030)],
        loaded_metal_voltage_spectrum=[dict(frequency_Hz=f,real_V=[loaded.real if f==3000 else 0.],imaginary_V=[loaded.imag if f==3000 else 0.])for f in(3000,3030)],
        source_power_W=.5*(ideal*current.conjugate()).real,source_resistor_power_W=25*abs(current)**2,
        source_current_RMS_by_output_mA=[abs(current)/math.sqrt(2)*1000])


def aliases_fixture():
    unit=dict(case_id=tool.C1,source_run_id=tool.RUN,raw_source_Vpp=1.,frequency_Hz=3000)
    case=dict(config_sha256='canonical-config',circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1))
    rows=[]
    for mode in tool.MODES:
        rows.append(dict(id=tool.REFERENCE_IDS[0]+'--'+mode,reference_id=tool.REFERENCE_IDS[0],
            reference_condition_id='baseline-square15-xy80-square_3h',reference_source_case_id='baseline-square15-xy80',
            reference_source_run_id=tool.RUN,reference_source_commit='canonical-commit',reference_configuration_sha256='canonical-config',reference_circuit=case['circuit'],
            matches={key:dict(required_source_Vpp=1.5,unloaded_probe40=[dict(id=str(i))for i in range(40)])for key in('centre20_E_RMS','ROI_energy_RMS')}))
    cache=dict(schema='task1-rounded-single-pair-rms-v1',status='calculated_unadopted',inputs_unchanged=True,new_PDE=0,native_array_decode=False,
        single_stimulation=copy.deepcopy(unit),targets=rows)
    return cache,unit,case


class OriginalSinglePairTests(unittest.TestCase):
    def test_latest_nominalSC2_reference_and4MiB120seconds_scope(self):
        self.assertEqual(tool.REFERENCE_IDS,('original-SC2-square3h','original-SC2-refine-3e018f8a317a'))
        self.assertEqual(tool.OPT_ID,'original-refine-3e018f8a317a')
        self.assertEqual(tool.MODES,('raw','skin_contact_only'))
        self.assertEqual(tool.OUTPUT_BOUND_BYTES,4*1024**2)

    def test_full_ROI_energy_RMS_uses_population_second_moment_not_mean(self):
        stat=dict(mean=2.5,std=math.sqrt(.75),volume_m3=1e-7)
        self.assertAlmostEqual(tool.energy_rms_from_statistics(stat),math.sqrt(7),places=14)
        self.assertNotEqual(tool.energy_rms_from_statistics(stat),stat['mean'])
        for bad in(dict(mean=-1.,std=1.,volume_m3=1.),dict(mean=1.,std=float('nan'),volume_m3=1.),dict(mean=1.,std=0.,volume_m3=0.)):
            with self.assertRaises(ValueError):tool.energy_rms_from_statistics(bad)

    def test_C1_source_RMS_from_actual_highZ_phasor_preserves_loaded_voltage_separation(self):
        m=metrics();before=copy.deepcopy(m);proof=tool.source_voltage_evidence(m)
        self.assertAlmostEqual(proof['unit_source_RMS_voltage_V'],1/(2*math.sqrt(2)),places=14)
        self.assertEqual(proof['unit_source_Vpp_V'],1.);self.assertEqual(proof['unit_source_peak_V'],.5)
        active=proof['spectrum'][0];self.assertAlmostEqual(active['ideal_source_peak_real_V'],0.,places=14)
        self.assertAlmostEqual(active['ideal_source_peak_imaginary_V'],-.5,places=14);self.assertEqual(m,before)
        self.assertNotEqual(m['loaded_metal_voltage_spectrum'][0]['imaginary_V'][0],-.5)

    def test_C1_source_voltage_rejects_wrong_frequency_two_outputs_or_wrong_peak(self):
        for change in('frequency','output','peak','duplicate'):
            m=metrics()
            if change=='frequency':m['loaded_metal_voltage_spectrum'][1]['real_V'][0]=.01
            elif change=='output':m['source_current_spectrum'][0]['real_A'].append(0.)
            elif change=='peak':m['loaded_metal_voltage_spectrum'][0]['imaginary_V'][0]*=.9
            else:m['source_current_spectrum'].append(copy.deepcopy(m['source_current_spectrum'][0]))
            with self.subTest(change=change),self.assertRaises(ValueError):tool.source_voltage_evidence(m)

    def test_existing_baseline4matches_are_exact_immutable_aliases_not_new_scaling(self):
        fixture=aliases_fixture();before=copy.deepcopy(fixture)
        with patch.object(tool,'target_matches',side_effect=AssertionError('must not recompute aliases')):
            rows=tool.baseline_aliases(*fixture,'canonical-commit')
        self.assertEqual(rows,fixture[0]['targets']);self.assertEqual(len(rows),2)
        self.assertEqual(sum(len(r['matches'])for r in rows),4);self.assertEqual(fixture,before)
        rows[0]['matches']['centre20_E_RMS']['required_source_Vpp']=999
        self.assertEqual(fixture,before)

    def test_alias_cache_wrong_unit_source_config_commit_or_scope_rejected(self):
        for change in('unit','config','commit','circuit','SC4','probes'):
            cache,unit,case=aliases_fixture()
            if change=='unit':cache['single_stimulation']['raw_source_Vpp']=2.
            elif change=='config':cache['targets'][0]['reference_configuration_sha256']='wrong'
            elif change=='commit':cache['targets'][0]['reference_source_commit']='wrong'
            elif change=='circuit':cache['targets'][0]['reference_circuit']=dict(n_pads=4,n_outputs=4,n_return_nodes=1)
            elif change=='SC4':cache['targets'][0]['reference_source_case_id']='baseline-square15-sc4'
            else:cache['targets'][0]['matches']['ROI_energy_RMS']['unloaded_probe40'].pop()
            with self.subTest(change=change),self.assertRaises(ValueError):tool.baseline_aliases(cache,unit,case,'canonical-commit')

    def test_grid_decimal_formats_equal_without_allowing_physical_drift(self):
        a={'h_mm':'.625','validation.sc_cells':'2','bulk.counts':'14,14,40'};b=dict(a,h_mm='0.625')
        self.assertTrue(tool.same_sc2_grid(a,b))
        for key,value in(('h_mm','1.25'),('h_mm','0.625000001'),('validation.sc_cells','4'),('bulk.counts','14,14,41')):
            bad=dict(b);bad[key]=value;self.assertFalse(tool.same_sc2_grid(a,bad))

    def test_point_and_ROI_matches_have_distinct_voltage_and_quadratic_losses(self):
        b=dict(source_power_W=.1,contact_power_W=.02,contact_voltage_RMS_max_V=.03,source_current_RMS_mA=2.)
        before=copy.deepcopy(b);p=probes();saved=copy.deepcopy(p)
        matched=tool.target_matches(6.,8.,2.,4.,b,p)
        for key,scale in(('centre20_E_RMS',3.),('ROI_energy_RMS',2.)):
            row=matched[key];self.assertEqual(row['required_source_Vpp'],scale)
            self.assertAlmostEqual(row['burdens']['source_power_W'],.1*scale**2)
            self.assertAlmostEqual(row['burdens']['source_current_RMS_mA'],2.*scale)
            self.assertAlmostEqual(row['burdens']['contact_voltage_RMS_max_V'],.03*scale)
            self.assertEqual(len(row['unloaded_probe40']),40);self.assertIn('zero temporal envelope variation',row['single_frequency_modulation_definition'])
        self.assertEqual(b,before);self.assertEqual(p,saved)

    def test_footprints_include_return_450versus900mm2_oneversustwooutputs(self):
        a=tool.reference_footprint([225e-6]*2,dict(n_pads=2,n_outputs=1,n_return_nodes=1))
        b=tool.reference_footprint([225e-6]*4,dict(n_pads=4,n_outputs=2,n_return_nodes=1))
        self.assertAlmostEqual(a['total_contact_area_mm2'],450.);self.assertAlmostEqual(b['total_contact_area_mm2'],900.)
        self.assertEqual(a['physical_pads'],2);self.assertEqual(a['independent_outputs'],1)
        self.assertEqual(b['physical_pads'],4);self.assertEqual(b['independent_outputs'],2)

    def test_execution_computes_only4new_matches_and_reuses_baseline4_unchanged(self):
        cache,_,_=aliases_fixture();raw=metrics();p=probes()
        unit=dict(raw_centre20_E_RMS_V_m=1.,raw_ROI_energy_RMS_V_m=2.,raw_burdens=dict(source_power_W=.1,source_current_RMS_mA=1.),
            probe=p,saved_electrical_metrics=raw,source_voltage_evidence=tool.source_voltage_evidence(raw))
        modes={mode:dict(amplitude_scale=scale,regions={tool.rounded.volume.PRIMARY:dict(RMS=dict(mean=3*scale,std=scale,volume_m3=1e-7))},
            normalized_burdens=dict(source_power_W=.2*scale**2))for mode,scale in(('raw',1.),('skin_contact_only',.8))}
        reference=dict(id=tool.REFERENCE_IDS[1],condition_id=tool.OPT_ID,source_run_id=tool.RUN,source_case_id='baseline-square15-xy80',
            source_commit='fine-commit',configuration_sha256='fine-config',circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1),
            waveform='optimized_two_tone_sine',frequencies_Hz=[3000,3030],electrical_metrics=dict(target20_total_E_RMS_V_m=2.),
            source_intervals_V=[[.99,1],[.98,.99]],normalized_modes=modes,condition_path='/synthetic/condition.json',condition_SHA256='synthetic')
        plan=dict(single_unit=unit,references=[reference],baseline_alias_targets=cache['targets'],baseline_alias_source=dict(path='/synthetic/old.json',SHA256='old',reused_matches=4),
            output_directory='/synthetic/current-run',cohort_footprints={},cohort_scope='nominalPBS SC2',root_selection_decision={},feedback_context={},holds=[])
        before=copy.deepcopy(plan)
        with patch.object(tool,'target_matches',wraps=tool.target_matches)as calls:result=tool.execute(plan)
        self.assertEqual(calls.call_count,2);self.assertEqual(result['new_matches'],4);self.assertEqual(result['reused_baseline_matches'],4)
        self.assertEqual(result['total_matches'],8);self.assertEqual(len(result['targets']),4)
        self.assertEqual(result['baseline_alias_targets'],cache['targets']);self.assertEqual(plan,before)
        self.assertFalse(result['same_field_RMS_implies_same_modulation_or_activation']);self.assertFalse(result['native_array_decode'])
        for row in result['new_targets']:
            for match in row['matches'].values():
                self.assertAlmostEqual(match['source_voltage_RMS_V'],match['required_source_Vpp']/(2*math.sqrt(2)),places=13)
                self.assertEqual(len(match['unloaded_probe40']),40)
    def test_native_TIS_and_comparison_run_provenance_remain_distinct(self):
        runs=tool.comparison_run_provenance('/synthetic/cloud-original-single-pair-unique')
        self.assertEqual(runs,dict(native_basis_run_id='cloud-mesh-c1-20261019T190000Z',
            source_tis_calculation_run_id='cloud-original-drive-refinement-20261021T222000Z',
            comparison_run_id='cloud-original-single-pair-unique'))
        self.assertEqual(len(set(runs.values())),3)
        self.assertNotIn('source_calculation_run_id',runs)
        self.assertNotIn('source_run_id',runs)


if __name__=='__main__':unittest.main()
