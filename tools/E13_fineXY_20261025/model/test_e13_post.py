"""Prospective pure scalar/metadata contracts; no arrays or actual inputs."""
import copy,math,unittest
from types import SimpleNamespace
from unittest.mock import patch
import e13_post as post


def manifest():
    return dict(Q_frames_returned=True,GC_before_postprocessing=True,
        **{g:{'E13':{f:dict(proof=dict(actual_new_RHS=int(g=='fine'),passed=True,
            physical_gates=dict(passed=True),passivity_passed=True,frequency_Hz=int(f),driven_output=i))
            for i,f in enumerate(('2000','2010'))}}for g in ('fine','coarse_SC4')})


def records():
    return [dict(candidate_id='synthetic-E13-'+g,physical_geometry_id='synthetic-E13',grid_variant=g,
        metric_evaluations=1,candidate_adopted=False,angular_work=dict(full_field_evaluations=int(g=='XY102-Z97'),
            SC4_only_evaluations=int(g=='XY100-Z97'),repeated_original_bulk_angular_evaluations=0))
        for g in ('XY102-Z97','XY100-Z97')]


def context():
    return dict(fine_B0_record=dict(candidate_id='B0-square15-c10-diagonal-XY102-Z97',
        physical_geometry_id='B0-square15-c10-diagonal',grid_variant='XY102-Z97',candidate_adopted=False,
        metrics=dict(marker='saved full metrics'),angular_work=dict(full_field_evaluations=1)),
        fine_B0_raw_by_frequency={'2000':dict(path='/synthetic/old-2000.npz',SHA256='a'*64),
                                  '2010':dict(path='/synthetic/old-2010.npz',SHA256='b'*64)},
        fine_B0_scalar=dict(path='/synthetic/old-scalars.npz',SHA256='c'*64),
        fine_B0_provenance=dict(published=True,fixture=True))


class E13PostContracts(unittest.TestCase):
    def test_exactly_two_new_fine_rhs_and_no_coarse_or_control_repetition(self):
        result=post.raw_accounting(manifest())
        self.assertEqual(result['actual_new_fine_driven_RHS'],2)
        self.assertEqual(result['actual_new_coarse_driven_RHS'],0)
        self.assertEqual(result['actual_control_RHS_repeated'],0)
    def test_cached_coarse_fallback_or_wrong_carrier_cannot_be_relabelled(self):
        for group,key,value in (('coarse_SC4','actual_new_RHS',1),('fine','actual_new_RHS',True),
                                ('fine','frequency_Hz',2010),('fine','passivity_passed',False)):
            m=manifest();m[group]['E13']['2000']['proof'][key]=value
            with self.assertRaises(ValueError):post.raw_accounting(m)
    def test_Q_frame_return_and_GC_are_required_before_metrics(self):
        for key in ('Q_frames_returned','GC_before_postprocessing'):
            m=manifest();m[key]=False
            with self.assertRaises(ValueError):post.raw_accounting(m)
    def test_one_full_and_one_SC4_scan_do_not_create_a_third_geometry(self):
        result=post.finite_accounting(records())
        self.assertEqual(result['full_angular_evaluations'],1)
        self.assertEqual(result['SC4_only_angular_evaluations'],1)
        self.assertEqual(result['repeated_original_bulk_angular_evaluations'],0)
        self.assertEqual(result['immutable_fine_B0_control_aliases'],1)
        bad=records();bad[1]['physical_geometry_id']='a-new-geometry'
        with self.assertRaises(ValueError):post.finite_accounting(bad)
    def test_hidden_bulk_scan_or_boolean_metric_count_is_rejected(self):
        bad=records();bad[1]['angular_work']['repeated_original_bulk_angular_evaluations']=1
        with self.assertRaises(ValueError):post.finite_accounting(bad)
        bad=records();bad[0]['metric_evaluations']=True
        with self.assertRaises(ValueError):post.finite_accounting(bad)
    def test_four_array_bulk_assembly_does_not_invent_axes_or_duplicate_bulk(self):
        original=dict(path='/synthetic/original.npz',SHA256='a'*64)
        patch=dict(path='/synthetic/SC4.npz',SHA256='b'*64)
        result=post.scalar_assembly_description(original,patch)
        self.assertEqual(result['original_bulk_selection'],dict(start=62880,stop=793860,depth_planes=93))
        self.assertEqual(result['new_SC4_cells'],31440)
        self.assertEqual(result['logical_common97_cells'],762420)
        self.assertEqual(result['scalar_keys_reused'],['AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index'])
        self.assertFalse(result['full_coarse_scalar_archive_written'])
        self.assertFalse(result['original_bulk_angular_scan_repeated'])
        self.assertFalse(result['missing_scalar_values_invented'])
        self.assertEqual(set(result['unavailable_coarse_statistics']),{'X_TIS','Y_TIS','Z_TIS','carrier0_RMS','carrier1_RMS'})
    def test_fine_B0_alias_preserves_full_saved_metadata_and_original_identity(self):
        c=context();before=copy.deepcopy(c);alias=post.fine_B0_alias(c)
        self.assertEqual(c,before);self.assertEqual(alias['metrics'],before['fine_B0_record']['metrics'])
        self.assertEqual(alias['angular_work'],dict(full_field_evaluations=1)) # historical work is not rewritten
        self.assertEqual(alias['new_PDE_RHS'],0);self.assertEqual(alias['new_angular_metric_evaluations'],0)
        self.assertFalse(alias['control_statistics_recomputed'])
        alias['metrics']['marker']='changed alias';self.assertEqual(c,before)
    def test_another_reference_grid_cannot_impersonate_full_fine_B0_alias(self):
        c=context();c['fine_B0_record']['grid_variant']='XY100-Z101'
        with self.assertRaises(ValueError):post.fine_B0_alias(c)
    def test_pairwise_projection_retains_cancelled_complex_vector_variation(self):
        # Two equal-volume fine cells +/-vector: a preaverage would hide the error.
        square=sum(abs(v)**2 for v in (1.+1j,2.,0.))
        result=post.projection_summary(2.,0.,2.*square,2.*square)
        self.assertAlmostEqual(result['pairwise_primary_absolute_L2'],math.sqrt(6.))
        self.assertEqual(result['projected_average_secondary']['status'],'not_run')
    def test_projection_zero_volume_and_original_diagnostic_cutoff_stay_explicit(self):
        self.assertEqual(post.projection_summary(0.,0.,0.,0.)['status'],'not_run_no_common_weighted_volume')
        self.assertFalse(post.relative_diagnostic(100.,102.,.01,'V/m')['passed'])
        self.assertTrue(post.relative_diagnostic(100.,104.,.05,'A/m2')['passed'])
        with self.assertRaises(ValueError):post.projection_summary(1.,1.,1.,-1.)
    def test_missing_axes_are_omitted_from_all_four_normalizations(self):
        linear=('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2')
        power=('SC_power_W','skin_power_W','contact_power_W')
        def cap(reference,candidate,exponent):return (reference/candidate)**(1./exponent)if candidate else None
        helper=SimpleNamespace(LINEAR_BURDENS=linear,POWER_BURDENS=power,_cap=cap,_scaled_electrical=lambda e,s:dict(amplitude_scale=s))
        e={k:1. for k in ('source_Vpp_each','sum_output_current_RMS_A_bookkeeping','source_power_W')+linear+power}
        baseline=dict(electrical={k:2. for k in e})
        stats={k:dict(mean=3.,p10=2.,median=3.,p95=4.,p99=4.,max=5.,std=.5)for k in ('maxTIS','RMS','Jtotal_vector_RMS')}
        summary=dict(electrical=e,regions={r:dict(statistics=copy.deepcopy(stats))for r in ('target','surface_0_5','surface_without_SC','off_target','total')})
        result=post._normalize_available(summary,baseline,helper)
        self.assertEqual(len(result['comparisons']),4)
        for row in result['comparisons'].values():
            self.assertEqual(set(row['absolute_ROI_fields_V_m']['target']),{'maxTIS','RMS'})
            self.assertEqual(row['unavailable_field_statistics'],['X_TIS','Y_TIS','Z_TIS'])
        self.assertFalse(result['missing_field_statistics_invented'])
    def test_minimum_four_ratio_reports_absolute_target_loss(self):
        result=post._ratio4(dict(target_mean=.9,target_P10=.8,target_to_surface=1.2,target_to_offtarget=1.1),
                           dict(target_mean=1.,target_P10=1.,target_to_surface=1.,target_to_offtarget=1.))
        self.assertEqual(result['minimum_four_ratio'],.8)
        self.assertLess(result['four_ratios']['target_mean'],1.)
    def test_partial_contact_fraction_uses_fine_spacing_without_correction(self):
        h=.05/102;area=h*h
        self.assertEqual(post.contact_fraction(area,h),1.)
        self.assertAlmostEqual(post.contact_fraction(area/4,h),.25)
        self.assertLess(post.contact_fraction(area,.0005),1.)
        self.assertEqual(post.contact_fraction(.0005**2,.0005),1.)
        with self.assertRaises(ValueError):post.contact_fraction(area,0.)
    def test_coarse_metric_loader_never_requests_original_bulk_E(self):
        # Shape-only manufactured placeholders test IO selection, not field math.
        calls=[];sc=SimpleNamespace(shape=(31440,3))
        def loader(np,descriptor,keys,guard,deadline):
            calls.append((descriptor['path'],list(keys)))
            result={k:SimpleNamespace(shape=(4,))for k in post.CONTACT_KEYS}
            if descriptor['path']=='SC4':result['E_SC4_peak_V_m']=sc
            else:self.assertNotIn('E_peak_V_m',keys)
            return result
        m=manifest();m['coarse_SC4']['E13']['2000']['raw']={'path':'SC4'}
        c={'coarse_raw':{'E13':{'2000':{'path':'old'}}}}
        np=SimpleNamespace(allclose=lambda a,b,**kwargs:True)
        with patch.object(post,'_load',side_effect=loader):
            raw,_=post._carrier(np,c,m,'XY100-Z97','2000',lambda:None,None,need_bulk=False)
        self.assertIs(raw['E_peak_V_m'],sc)
        self.assertEqual(calls[1][1],list(post.CONTACT_KEYS))
    def test_strict_Pareto_retains_tradeoff_dominance_and_missing_objectives(self):
        def v(a,b,c,d):return dict(target_mean=a,target_P10=b,target_to_surface_mean=c,target_to_offtarget_mean=d)
        result=post.strict_pareto(dict(base=v(1.,1.,1.,1.),dominant=v(2.,2.,2.,2.),tradeoff=v(3.,.5,3.,3.),missing=v(None,4.,4.,4.)))
        self.assertEqual(result['base']['status'],'provisional_dominated')
        self.assertIn('dominant',result['base']['dominated_by'])
        self.assertEqual(result['dominant']['status'],'provisional_nondominated')
        self.assertEqual(result['tradeoff']['status'],'provisional_nondominated')
        self.assertEqual(result['missing']['status'],'not_ranked_missing_objective')
    def test_P10_only_loss_is_disclosed_even_when_mean_and_ratios_improve(self):
        base=dict(target_mean=1.,target_P10=1.,target_to_surface_mean=1.,target_to_offtarget_mean=1.)
        value=dict(target_mean=1.1,target_P10=.9,target_to_surface_mean=1.2,target_to_offtarget_mean=1.3)
        score=post.objective_score(value,base)
        self.assertFalse(score['absolute_target_losses']['target_mean']);self.assertTrue(score['absolute_target_losses']['target_P10'])
        self.assertTrue(score['ratio_only_improvement_with_absolute_loss']);self.assertEqual(score['robust_minimum_four_ratio'],.9)
        self.assertIsNone(post.objective_vector(dict(status='not_available'))['target_mean'])


if __name__=='__main__':unittest.main()
