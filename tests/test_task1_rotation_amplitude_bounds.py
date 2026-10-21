"""Synthetic theorem and power identities only; no real cached scalar evaluation."""
import copy
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_rotation_amplitude_bounds as bounds


def weighted_mean(values,weights): return sum(v*w for v,w in zip(values,weights))/sum(weights)


def weighted_p95(values,weights):
    running=0.;total=sum(weights)
    for value,weight in sorted(zip(values,weights)):
        running+=weight
        if running>=.95*total:return value
    raise AssertionError('positive weights required')


def coefficients(v):
    result={}
    for f in bounds.FREQUENCIES:
        j=0 if f in (3000,9000) else 1
        amplitude=(3 if f in (3000,3030) else 1)/(2*math.sqrt(2))
        imaginary=[0.,0.];imaginary[j]=-amplitude*v[j]
        result[str(f)]=dict(real=[0.,0.],imaginary=imaginary)
    return result


def losses(v,balance_error=0.):
    units={3000:[2e-6,3e-5,1e-6,4e-5,1e-6,5e-5],3030:[3e-6,2e-5,2e-6,5e-5,2e-6,4e-5],
           9000:[1e-6,1e-5,1e-6,2e-5,1e-6,3e-5],9090:[2e-6,2e-5,1e-6,1e-5,1e-6,2e-5]}
    rows=[];totals=[0.]*6
    for f in bounds.FREQUENCIES:
        j=0 if f in (3000,9000) else 1
        values=[p*v[j]**2 for p in units[f]]
        totals=[a+b for a,b in zip(totals,values)]
        source=sum(values)*(1+balance_error)
        rows.append(dict(frequency_Hz=f,layer_contact_resistor_losses_W=values,source_power_W=source,
            power_balance_relative_error=abs(sum(values)-source)/max(abs(source),1e-20)))
    return dict(per_frequency=rows,metrics=dict(SC_power_W=totals[0],contact_power_W=totals[4],skin_SC_plus_dermis_power_W=totals[0]+totals[1]),
        actual_active_harmonics_included=True,no_extra_peak_RMS_factor_applied=True)


class TheoremTests(unittest.TestCase):
    def test_pointwise_sampled_direction_metric_is_monotone_and_homogeneous(self):
        rng=random.Random(13)
        cells=[[(rng.uniform(.01,10),rng.uniform(.01,10)) for _ in range(8)] for _ in range(20)]
        weights=[rng.uniform(.01,2) for _ in cells]
        def metric(a,b):return [max(2*min(a*x,b*y) for x,y in directions) for directions in cells]
        for t in (.5,.55,.7,.9,1.):
            values,low,high=metric(t,1),metric(.5,1),metric(1,1)
            self.assertTrue(all(a<=(t/.5)*b+1e-12 for a,b in zip(values,low)))
            self.assertTrue(all(a+1e-12>=(t/1.)*b for a,b in zip(values,high)))
            target=weighted_mean(values,weights);surface=weighted_p95(values,weights)
            ratio_lower=.5*weighted_p95(high,weights)/weighted_mean(low,weights)
            self.assertGreaterEqual(surface/target+1e-12,ratio_lower)
            for common in (.03,1.,8.,100.):
                changed=metric(common*t,common)
                self.assertAlmostEqual(weighted_mean(changed,weights),common*target,places=10)
                self.assertAlmostEqual(weighted_p95(changed,weights),common*surface,places=10)

    def test_outer_power_constant_output_bounds_hold_for_arbitrary_common_amplitude(self):
        variable_power,constant_power=3.,5.
        for common in (.01,.5,2.,25.):
            for t in (.001,.1,.49):
                actual=common**2*(t*t*variable_power+constant_power)
                self.assertGreaterEqual(actual,common**2*constant_power)
                cap=7.
                if actual<=cap:self.assertLessEqual(common,math.sqrt(cap/constant_power))

    def unit_bounds(self,value=1.):
        return [{k:dict(lower_W=value,upper_W=value) for k in bounds.POWER_CAPS} for _ in range(2)]

    def test_both_inner_and_outer_branches_exclude_entire_positive_family(self):
        result=bounds.family_bounds(4.,24.,50.,[3.,3.],{k:1. for k in bounds.POWER_CAPS},self.unit_bounds())
        self.assertTrue(result['overall_proof_passed'])
        self.assertEqual(result['conclusion'],'excluded_fixed_discrete_positive_amplitude_family')
        self.assertEqual([b['constant_output'] for b in result['branches']],[1,0])
        for branch in result['branches']:
            self.assertTrue(branch['inner']['excluded']);self.assertTrue(branch['outer']['excluded'])
            self.assertIn('arbitrary positive',branch['common_A'])
        self.assertEqual(result['zero_amplitude_endpoints']['basic_two_carrier_maxTIS'],0)

    def test_any_unproved_interval_stays_inconclusive(self):
        for equal,halves,caps in [(10.,[3.,3.],1.),(50.,[3.,3.],100.),(50.,[3.,8.],1.)]:
            result=bounds.family_bounds(4.,24.,equal,halves,{k:caps for k in bounds.POWER_CAPS},self.unit_bounds())
            self.assertFalse(result['overall_proof_passed'])
            self.assertEqual(result['conclusion'],'inconclusive')

    def test_unresolved_constant_power_or_near_ratio_margin_cannot_force_proof(self):
        result=bounds.family_bounds(4.,24.,36.,[3.,3.],{k:1. for k in bounds.POWER_CAPS},self.unit_bounds())
        self.assertFalse(result['overall_proof_passed'])
        self.assertTrue(all(not b['inner']['excluded'] for b in result['branches']))
        result=bounds.family_bounds(4.,24.,50.,[3.,3.],{k:1. for k in bounds.POWER_CAPS},self.unit_bounds(0.))
        self.assertFalse(result['overall_proof_passed'])
        self.assertTrue(all(b['outer']['common_A_upper'] is None for b in result['branches']))

    def test_existing_screen_tolerance_is_preserved_and_bounds_are_outward(self):
        result=bounds.family_bounds(4.,24.,50.,[3.,3.],{k:1. for k in bounds.POWER_CAPS},self.unit_bounds())
        self.assertLess(result['baseline_mean_required_lower_V_m'],4.-bounds.screen.tolerance(4.))
        self.assertGreater(result['baseline_surface_p95_allowed_upper_V_m'],24.+bounds.screen.tolerance(24.))
        for branch in result['branches']:
            self.assertLess(branch['inner']['surface_over_target_lower_bound'],.5*50./3.)
            self.assertGreater(branch['outer']['target_mean_upper_V_m'],3.)


class PowerProofTests(unittest.TestCase):
    def samples(self):
        vectors=[[1.,1.],*[v for _,v in bounds.CONDITIONS]]
        return [dict(id=str(i),source_Vpp_by_output=v,losses=losses(v)) for i,v in enumerate(vectors)]

    def test_source_unit_power_uses_actual_vpp_squared_without_extra_half(self):
        recovered=bounds.unit_power_contributions(losses([.5,1.]),[.5,1.])
        self.assertAlmostEqual(recovered[0]['SC_power_W'],3e-6,places=18)
        self.assertAlmostEqual(recovered[1]['SC_power_W'],5e-6,places=18)
        self.assertAlmostEqual(recovered[0]['contact_power_W'],2e-6,places=18)
        self.assertAlmostEqual(recovered[1]['skin_SC_plus_dermis_power_W'],45e-6,places=18)
        units,proof=bounds.crosscheck_unit_powers(self.samples())
        self.assertEqual(len(proof),6);self.assertTrue(all(r['passed'] for r in proof))
        self.assertLess(units[0]['SC_power_W']['lower_W'],3e-6)

    def test_inherited_native_power_gate_is_distinct_from_tight_scaling_identity(self):
        # Existing solver errors around3e-10 must not be rejected by a new1e-10
        # source-vs-loss gate. Exact drive scaling is still checked more tightly.
        result=bounds.unit_power_contributions(losses([.5,1.],3.348e-10),[.5,1.])
        self.assertGreater(result[0]['SC_power_W'],0.)
        with self.assertRaisesRegex(ValueError,'power-conservation'):
            bounds.unit_power_contributions(losses([.5,1.],1e-6),[.5,1.])
        samples=self.samples();samples[1]['losses']['per_frequency'][0]['layer_contact_resistor_losses_W'][0]+=1e-9
        samples[1]['losses']['per_frequency'][0]['source_power_W']+=1e-9
        samples[1]['losses']['metrics']['SC_power_W']+=1e-9
        samples[1]['losses']['metrics']['skin_SC_plus_dermis_power_W']+=1e-9
        with self.assertRaisesRegex(ValueError,'unit compartment power changed'):
            bounds.crosscheck_unit_powers(samples)

    def test_cached_total_power_fallback_checks_real_totals_without_inventing_unit_split(self):
        samples=self.samples();samples[0]=dict(id='cached',source_Vpp_by_output=[1.,1.],cached_total_powers=losses([1.,1.])['metrics'])
        _,proof=bounds.crosscheck_unit_powers(samples)
        totals=[p for p in proof if p['output_index'] is None]
        self.assertEqual(len(totals),3)
        samples[0]['cached_total_powers']['SC_power_W']+=1e-8
        with self.assertRaisesRegex(ValueError,'cached1/1 compartment total'):
            bounds.crosscheck_unit_powers(samples)

    def test_wrong_coefficients_frequency_assignment_passivity_or_missing_harmonic_are_rejected(self):
        v=[.5,1.];c=coefficients(v);bounds.exclusive_square_coefficients(c,v)
        c['3000']['imaginary'][1]=.1
        with self.assertRaisesRegex(ValueError,'exclusive square3h'):bounds.exclusive_square_coefficients(c,v)
        for mutation in ('missing','negative','extra-half'):
            obj=losses(v)
            if mutation=='missing':obj['per_frequency'].pop()
            elif mutation=='negative':obj['per_frequency'][0]['layer_contact_resistor_losses_W'][0]=-1e-6
            else:obj['no_extra_peak_RMS_factor_applied']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):bounds.unit_power_contributions(obj,v)


class JSONBoundaryTests(unittest.TestCase):
    def test_non_json_or_native_array_paths_are_never_opened(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); p=root/'field-3000.bin';p.write_bytes(b'not an allowed JSON source')
            with mock.patch.object(bounds,'ROOT',root),mock.patch.object(bounds.core,'sha') as sha:
                with self.assertRaisesRegex(ValueError,'Only canonical bounded JSON'):bounds.json_source(p,{})
                sha.assert_not_called()

    def test_actual_cli_failure_fixture_saves_evidence_and_preserves_budget_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'docs').mkdir();(root/'runtime').mkdir()
            out=root/'docs/new';plan=root/'docs/plan.json';plan.write_text('{}')
            ledger=dict(limit_seconds=13800,spent_seconds=123.,runs=[dict(stage='prior')])
            argv=['bounds','--preregistration',str(plan),'--output',str(out)]
            with mock.patch.object(bounds,'ROOT',root),mock.patch.object(sys,'argv',argv),mock.patch.object(bounds.os,'sched_setaffinity'), \
                 mock.patch.object(bounds.policy,'load_ledger',return_value=copy.deepcopy(ledger)),mock.patch.object(bounds.policy,'remaining_seconds',return_value=100), \
                 mock.patch.object(bounds,'verify_plan',side_effect=ValueError('synthetic JSON drift')),mock.patch.object(bounds,'execute') as execute:
                with self.assertRaisesRegex(ValueError,'synthetic JSON drift'):bounds.main()
                execute.assert_not_called()
            receipt=bounds.core.read(out/'failure.json');after=bounds.core.read(root/'runtime/task1-budget.json')
            self.assertTrue(receipt['partial_evidence_preserved']);self.assertFalse(receipt['automatic_retry'])
            self.assertEqual(after['runs'][0],ledger['runs'][0]);self.assertGreater(after['spent_seconds'],123.)
            self.assertEqual(after['runs'][-1]['status'],'failed_preserved')


if __name__=='__main__':unittest.main()
