"""Synthetic fixed-command mesh sensitivities; no native arrays/PDE/preparation."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('original_mesh_sensitivity_tested',ROOT/'tools/task1_original_mesh_sensitivity.py')
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)
PRIMARY=tool.volume.PRIMARY
MODES=tuple(tool.screen.MODES)
REGIONS=('total',PRIMARY,'supplemental_wholeXY_depth15_20','surface_0_5','primary_complement','supplemental_complement')


def config():
    c={'mask.path':'fine-mask','mask.sha256':'fine-hash','h_mm':'0.625','validation.sc_cells':'2','bulk.counts':'14,14,40','sc.sigma':'.0002','z.3000.re':'.00004452'}
    for i,xy in enumerate(((-10,-10),(10,10),(10,-10),(-10,10))):
        for name,value in dict(shape='rectangle',width_mm='15',height_mm='15',rotation_deg='0',analytic_area_mm2='225',
            represented_area_m2='.00022499999999999999',x_mm=str(xy[0]),y_mm=str(xy[1])).items():c[f'pad.{i}.{name}']=value
    return c


def regions():
    result={}
    for index,r in enumerate(REGIONS):
        stats=dict(mean=4.5,p10=4.,p95=18. if r=='surface_0_5' else 23.,volume_m3=(1e-5,1e-7,1e-6,2e-6,9.9e-6,9e-6)[index],
            fixed_baseline_threshold_volume={PRIMARY+'_mean':dict(cutoff_V_m=4.,volume_m3=.8e-7),PRIMARY+'_p10':dict(cutoff_V_m=3.5,volume_m3=1.8e-7)})
        result[r]={metric:copy.deepcopy(stats)for metric in tool.volume.METRICS}
    return result


def fine_modes():
    result={}
    for index,(name,scale)in enumerate(zip(MODES,(1.,.8,1.2,.75,.6))):
        burdens={key:80.+index for key in(*tool.J95_KEYS,*tool.POWER_KEYS)}
        burdens.update(surface_J_RMS_max_A_m2=85.+index,contact_voltage_RMS_max_V=.1,bulk_skin_J_vector_RMS_max_A_m2=95.+index)
        result[name]=dict(amplitude_scale=scale,regions=regions(),normalized_burdens=burdens)
    return result


def new_modes(fine):
    out=tool.fixed_fine_modes(fine)
    for name,row in out.items():row.update(regions=copy.deepcopy(fine[name]['regions']),actual_burdens=copy.deepcopy(fine[name]['normalized_burdens']))
    return out


def baseline():
    r=regions();r[PRIMARY]['maxTIS'].update(mean=4.,p10=3.5)
    for region,p95 in(('surface_0_5',20.),('primary_complement',25.)):
        r[region]['maxTIS']['p95']=p95
        r[region]['maxTIS']['fixed_baseline_threshold_volume'][PRIMARY+'_mean']['volume_m3']=1e-7
        r[region]['maxTIS']['fixed_baseline_threshold_volume'][PRIMARY+'_p10']['volume_m3']=2e-7
    return dict(normalizations={'skin_contact_only':dict(regions=r)})


class OriginalMeshSensitivityTests(unittest.TestCase):
    def test_two_exact_cohorts_fixed_360s8MiB_resources(self):
        self.assertEqual([(r['axis'],r['h_xy_mm'],r['sc_cells'],r['cells'])for r in tool.COHORTS],
            [('SC',.625,4,361728),('XY',1.25,2,88480)])
        self.assertEqual(tool.RESOURCE_CONTRACT['total_seconds'],360)
        self.assertEqual(tool.RESOURCE_CONTRACT['source_load_seconds_each'],30)
        self.assertEqual(tool.RESOURCE_CONTRACT['per_condition_seconds'],120)
        self.assertEqual(tool.RESOURCE_CONTRACT['finalization_seconds'],30)
        self.assertEqual(tool.OUTPUT_BOUND_BYTES,8*1024**2)
        self.assertEqual(tool.RESOURCE_CONTRACT['max_added_bytes'],tool.OUTPUT_BOUND_BYTES)
        self.assertEqual(tool.RESOURCE_CONTRACT['disk_reserve_bytes'],2*tool.GIB)
        self.assertEqual(tool.RESOURCE_CONTRACT['new_PDE'],0)
        self.assertEqual(set(tool.COMPACT_ARTIFACT_FILENAMES),{'condition.json','probes.json','native-volume-metrics.json'})

    def test_sc_only_change_and_byte_identical_mask_alias_permitted(self):
        old=config();new=old.copy();new['validation.sc_cells']='4';before=copy.deepcopy((old,new))
        proof=tool.validate_mesh_config(old,new,'SC');self.assertEqual(proof['changed_properties'],['validation.sc_cells'])
        self.assertEqual((old,new),before)
        new['mask.path']='SC4-copy-of-same-mask';self.assertTrue(tool.validate_mesh_config(old,new,'SC')['physical_rectangles_tissue_contact_circuit_unchanged'])
        for key,value in(('sc.sigma','.002'),('z.3000.re','.2'),('h_mm','1.25'),('mask.sha256','different'),('pad.0.width_mm','14')):
            changed=new.copy();changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):tool.validate_mesh_config(old,changed,'SC')

    def test_xy_only_step_and_new_same_physical_mask_required(self):
        old=config();new=old.copy();new.update({'h_mm':'1.25','mask.path':'coarse-mask','mask.sha256':'coarse-hash'})
        self.assertEqual(tool.validate_mesh_config(old,new,'XY')['changed_properties'],['h_mm','mask.path','mask.sha256'])
        for key,value in(('validation.sc_cells','4'),('bulk.counts','15,15,42'),('pad.1.y_mm','-10'),('pad.3.rotation_deg','5'),('h_mm','2.5')):
            changed=new.copy();changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):tool.validate_mesh_config(old,changed,'XY')
        with self.assertRaises(ValueError):tool.validate_mesh_config(old,new,'bulk')

    def test_exact_complex_selected_coefficients_no_phase_or_global_renormalization(self):
        coefficients={3000:np.array([-.98j,.00245-.0294j]),3030:np.array([-.0098-.0049j,-.9653j]),9000:np.zeros(2,complex),9090:np.zeros(2,complex)}
        c=dict(coefficient_vectors={str(f):dict(real=v.real.tolist(),imaginary=v.imag.tolist())for f,v in coefficients.items()})
        before=copy.deepcopy(c);actual=tool.decode_coefficients(c)
        for f in coefficients:np.testing.assert_array_equal(actual[f],coefficients[f])
        self.assertEqual(c,before);self.assertNotEqual(abs(actual[3000][0]),1.)
        c['coefficient_vectors']['9000']['real'][0]=.001
        with self.assertRaises(ValueError):tool.decode_coefficients(c)

    def test_all5_fine_scales_preserved_with_no_equality_claims(self):
        fine=fine_modes();before=copy.deepcopy(fine);fixed=tool.fixed_fine_modes(fine)
        self.assertEqual(fine,before);self.assertEqual(set(fixed),set(MODES))
        for name,row in fixed.items():
            self.assertEqual(row['amplitude_scale'],fine[name]['amplitude_scale'])
            self.assertEqual(row['fixed_fine_reference_scale'],fine[name]['amplitude_scale'])
            self.assertFalse(row['rematched']);self.assertFalse(row['matches_fine_current_on_new_mesh'])
            self.assertFalse(row['matches_fine_power_on_new_mesh']);self.assertFalse(row['matches_fine_skin_burden_on_new_mesh'])
        fine.pop('equal_total_power')
        with self.assertRaises(ValueError):tool.fixed_fine_modes(fine)

    def test_actual_xy_ROI_volume_difference_reported_not_renormalized(self):
        fine=regions();coarse=copy.deepcopy(fine)
        for r in coarse:
            for metric in tool.volume.METRICS:coarse[r][metric]['volume_m3']*=1.001
        before=copy.deepcopy((fine,coarse));proof=tool.roi_volume_diagnostic(fine,coarse,'XY')
        self.assertFalse(proof['analytic_volume_renormalization']);self.assertFalse(proof['equality_required'])
        self.assertFalse(proof['coarse_volumes_forced_to_fine']);self.assertEqual((fine,coarse),before)
        self.assertAlmostEqual(proof['rows'][0]['relative_change'],.001,places=12)
        with self.assertRaises(ValueError):tool.roi_volume_diagnostic(fine,coarse,'SC')

    def test_SC_volumes_match_without_requiring_same_cell_counts_or_stats(self):
        fine=regions();sc4=copy.deepcopy(fine);sc4[PRIMARY]['maxTIS']['mean']*=.99
        proof=tool.roi_volume_diagnostic(fine,sc4,'SC');self.assertTrue(proof['equality_required'])
        sc4[PRIMARY]['maxTIS']['volume_m3']=float('nan')
        with self.assertRaises(ValueError):tool.roi_volume_diagnostic(fine,sc4,'XY')

    def test_unchanged_diagnostic_pass_never_promotes_convergence_or_closes_oldfailure(self):
        fine=fine_modes();mesh=new_modes(fine);before=copy.deepcopy((fine,mesh))
        for axis in('SC','XY'):
            proof=tool.sensitivity_checks(fine,mesh,baseline(),axis)
            self.assertTrue(proof['all_passed']);self.assertFalse(proof['full_convergence_validated'])
            self.assertFalse(proof['previous_XY_failures_closed']);self.assertEqual(len(proof['checks']),20)
            self.assertEqual(len(proof['screen_status_comparisons']),16)
        self.assertEqual((fine,mesh),before)

    def test_target_1percent_and_offtarget_J95_loss_2percent_both_signs(self):
        for name in('raw_1Vpp','skin_contact_only'):
            for sign in(-1,1):
                fine=fine_modes();mesh=new_modes(fine)
                mesh[name]['regions'][PRIMARY]['maxTIS']['mean']*=1+sign*.011
                self.assertFalse(tool.sensitivity_checks(fine,mesh,baseline(),'SC')['all_passed'])
                for key in(*tool.J95_KEYS,*tool.POWER_KEYS):
                    mesh=new_modes(fine);mesh[name]['actual_burdens'][key]*=1+sign*.021
                    with self.subTest(mode=name,key=key,sign=sign):self.assertFalse(tool.sensitivity_checks(fine,mesh,baseline(),'XY')['all_passed'])
                mesh=new_modes(fine);mesh[name]['regions']['surface_0_5']['maxTIS']['p95']*=1+sign*.021
                self.assertFalse(tool.sensitivity_checks(fine,mesh,baseline(),'XY')['all_passed'])

    def test_original_screen_status_flip_fails_even_tiny_numerical_change(self):
        fine=fine_modes();mesh=new_modes(fine)
        fine['skin_contact_only']['regions'][PRIMARY]['maxTIS']['mean']=4.0002
        mesh['skin_contact_only']['regions'][PRIMARY]['maxTIS']['mean']=3.9998
        proof=tool.sensitivity_checks(fine,mesh,baseline(),'SC')
        self.assertFalse(proof['screen_status_no_flip']);self.assertFalse(proof['all_passed'])

    def test_changed_amplitude_or_silent_rematch_rejected(self):
        fine=fine_modes();mesh=new_modes(fine);mesh['skin_contact_only']['amplitude_scale']*=.999
        with self.assertRaises(ValueError):tool.sensitivity_checks(fine,mesh,baseline(),'SC')
        mesh=new_modes(fine);mesh['skin_contact_only']['rematched']=True
        with self.assertRaises(ValueError):tool.sensitivity_checks(fine,mesh,baseline(),'XY')

    def test_all3_prior_XY_waveform_failures_preserved_without_mutation(self):
        report=dict(status='failed_gates_preserved',comparisons=[dict(axis='XY',waveform=w,passed=False)for w in('square_3h','sine','triangle')])
        before=copy.deepcopy(report);proof=tool.validate_prior_mesh_failures(report)
        self.assertEqual(report,before);self.assertFalse(proof['closed']);self.assertEqual(len(proof['XY_failed_waveforms']),3)
        report['comparisons'][0]['passed']=True
        with self.assertRaises(ValueError):tool.validate_prior_mesh_failures(report)

    def test_compact_recipe_uses_actual_mesh_ROI_archive_and_fine_scales_without_export_claim(self):
        item=dict(path=Path('/synthetic/coarse/summary.json'),summary={'artifacts':{'files':{'volume.npz':{'SHA256':'coarse-weight-hash'}}}})
        cached=dict(item=item,fine_scales={name:float(i+1)for i,name in enumerate(MODES)})
        basis=dict(hashes={'native-E':'Ehash','native-phi':'phihash'},metadata={'config_sha256':'coarse-config'})
        c={f:np.array([-.5j,.02j])if f in(3000,3030)else np.zeros(2,complex)for f in tool.FREQUENCIES}
        with patch.object(tool.view,'sha',return_value='synthetic-sha'):
            recipe=tool.mesh_reconstruction_recipe(basis,c,cached)
        self.assertEqual(recipe['source_ROI_weight_archive']['SHA256'],'coarse-weight-hash')
        self.assertEqual(recipe['frozen_fine_mode_amplitude_scales'],cached['fine_scales'])
        self.assertEqual(recipe['native_input_sha256'],basis['hashes']);self.assertEqual(recipe['native_grid_configuration_sha256'],'coarse-config')
        self.assertFalse(recipe['analytic_volume_renormalization']);self.assertFalse(recipe['new_scalar_archive_written'])
        self.assertFalse(recipe['executable_scalar_export_command_registered']);self.assertFalse(recipe['independent_scalar_export_reproduction_verified'])
        self.assertEqual(len(recipe['frozen_numerical_helpers_sha256']),5)


if __name__=='__main__':unittest.main()
