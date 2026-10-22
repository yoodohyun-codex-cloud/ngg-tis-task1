"""Pure saved-scalar display contracts; no NPZ/grid load, render or solve."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_coherent_drive_volume_maps as r

BASELINE_ID='baseline-square15-xy80'
CONFIG_SHA='a'*64
DEFINITION='actual full two-tone max-minus-min before50ohm; bounds, not each tone Vpp'


def reference(ratio,phase):
    ident=f'coherent-r{"0p5"if ratio==.5 else"1"}-p{phase:03d}'
    return dict(id=ident,status='calculated_unadopted',mix_ratio=ratio,phase_deg=phase,
        canonical_screen_all_passed=False,artifacts={name:dict(path=f'/tmp/{ident}/{name}',SHA256='b'*64)
                                                  for name in ('condition.json','volume.npz')})


def summary():
    return dict(schema='task1-coherent-drive-scout-v1',status='calculated_unadopted',
        inputs_unchanged=True,new_PDE=0,candidate_adopted=False,full_convergence_validated=False,
        experimentally_validated=False,actual_fundamental_Hz=[3000,3030],beat_frequency_Hz=30,
        conditions=[reference(ratio,phase)for ratio in (.5,1.)for phase in (0,90,180,270)])


def condition(ref,limits):
    raw=np.array([[.9999995,1.],[.9999997,1.]])
    modes={}
    for name,scale in (('raw_1Vpp',1.),('skin_contact_only',2.5)):
        modes[name]=dict(amplitude_scale=scale,baseline_derived_numerical_limits=dict(limits),
            includes_source_power_cap=False,includes_1Vpp_ceiling=False,
            actual_source_Vpp_intervals_V=(raw*scale).tolist(),
            source_Vpp_upper_by_output_V=(raw[:,1]*scale).tolist(),source_Vpp_definition=DEFINITION)
    return dict(schema='task1-coherent-drive-condition-v1',status='calculated_unadopted',id=ref['id'],
        mix_ratio=ref['mix_ratio'],phase_deg=ref['phase_deg'],source_case_id=BASELINE_ID,
        configuration_sha256=CONFIG_SHA,actual_fundamental_Hz=[3000,3030],beat_frequency_Hz=30,
        active_frequencies_Hz=[3000,3030],harmonics_active=False,new_PDE=0,candidate_adopted=False,
        full_convergence_validated=False,experimentally_validated=False,normalizations=modes,
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,source_resistance_ohm=50.,
            pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            return_topology='all_return_pads_ideal_common_GND',uncommanded_frequency_termination='0V through50ohm',
            active_frequencies_by_output_Hz={'0':[3000,3030],'1':[3000,3030]}))


def model():
    cases=[]
    for index,ident in enumerate(('square-control','exclusive-sine-control',
                                 *(ref['id']for ref in summary()['conditions']))):
        values=np.array([100.+10*index,index+1.,2*index+1.])
        if index==9:values[0]=1000.
        arrays={metric:values.copy()for metric in r.base.METRICS}
        arrays['region_target_m3']=np.array([0.,.5,1.])
        arrays['region_total_m3']=np.ones(3);arrays['region_surface_0_5_m3']=np.array([1.,0.,0.])
        case=dict(id=ident,label=ident,arrays=arrays,scales={'raw_1Vpp':1.,'skin_contact_only':3. if index==9 else 1.})
        if index>=2:
            ref=summary()['conditions'][index-2];case.update(mix_ratio=ref['mix_ratio'],phase_deg=ref['phase_deg'])
        cases.append(case)
    return dict(cases=cases)


class CoherentDriveVolumeMapsTests(unittest.TestCase):
    def setUp(self):
        self.limits={key:float(index+1)for index,key in enumerate(sorted(r.base.CAPS))}
        self.reference=reference(.5,0)
        self.condition=condition(self.reference,self.limits)

    def validate(self,value=None,ref=None):
        return r.validate_condition(self.condition if value is None else value,
                                    self.reference if ref is None else ref,BASELINE_ID,CONFIG_SHA,self.limits)

    def test_terminal_eight_reference_summary_preserves_failed_screens_without_adoption(self):
        source=summary();before=copy.deepcopy(source)
        rows=r.validate_summary(source)
        self.assertEqual(8,len(rows));self.assertEqual(source['conditions'],rows)
        self.assertTrue(all(row['canonical_screen_all_passed']is False for row in rows))
        self.assertEqual(before,source)

    def test_summary_rejects_nonterminal_metadata_order_duplicates_ratio_and_phase(self):
        mutations=(lambda s:s.update(status='running'),lambda s:s.update(inputs_unchanged=False),
                   lambda s:s.update(new_PDE=1),lambda s:s.update(candidate_adopted=True),
                   lambda s:s.update(full_convergence_validated=True),
                   lambda s:s.update(actual_fundamental_Hz=[2000,2030]),
                   lambda s:s['conditions'].reverse(),lambda s:s['conditions'].pop(),
                   lambda s:s['conditions'].__setitem__(1,copy.deepcopy(s['conditions'][0])),
                   lambda s:s['conditions'][0].update(mix_ratio=.75),
                   lambda s:s['conditions'][0].update(phase_deg=45))
        for mutate in mutations:
            value=summary();mutate(value)
            with self.assertRaises(ValueError):r.validate_summary(value)

    def test_actual_full_waveform_vpp_intervals_and_saved_skin_scale_are_retained(self):
        before=copy.deepcopy(self.condition);result=self.validate()
        self.assertEqual({'raw_1Vpp':1.,'skin_contact_only':2.5},result['scales'])
        for mode in ('raw_1Vpp','skin_contact_only'):
            self.assertEqual(self.condition['normalizations'][mode]['actual_source_Vpp_intervals_V'],
                             result['source_voltage_intervals'][mode])
        np.testing.assert_allclose([[2.49999875,2.5],[2.49999925,2.5]],
                                   result['source_voltage_intervals']['skin_contact_only'],rtol=0,atol=1e-14)
        self.assertNotEqual([[1.,1.],[1.,1.]],result['source_voltage_intervals']['raw_1Vpp'])
        self.assertEqual(before,self.condition)

    def test_condition_rejects_wrong_config_topology_actual_frequencies_and_vpp_interpretation(self):
        mutations=(lambda c:c.update(configuration_sha256='c'*64),
                   lambda c:c.update(source_case_id='another-case'),lambda c:c.update(phase_deg=90),
                   lambda c:c.update(mix_ratio=1.),lambda c:c.update(status='running'),
                   lambda c:c.update(harmonics_active=True),lambda c:c.update(active_frequencies_Hz=[3000,9000]),
                   lambda c:c['source_circuit'].update(n_outputs=4),
                   lambda c:c['source_circuit']['pad_to_node'].update({'3':'out1'}),
                   lambda c:c['source_circuit'].update(active_frequencies_by_output_Hz={'0':[3000],'1':[3030]}),
                   lambda c:c['normalizations']['raw_1Vpp'].update(amplitude_scale=.9),
                   lambda c:c['normalizations']['skin_contact_only'].update(includes_source_power_cap=True),
                   lambda c:c['normalizations']['skin_contact_only'].update(includes_1Vpp_ceiling=True),
                   lambda c:c['normalizations']['skin_contact_only'].update(source_Vpp_definition='each tone is1Vpp'))
        for mutate in mutations:
            value=copy.deepcopy(self.condition);mutate(value)
            with self.assertRaises(ValueError):self.validate(value)
        for mutate in (lambda c:c['normalizations']['raw_1Vpp']['actual_source_Vpp_intervals_V'][0].__setitem__(1,1.01),
                       lambda c:c['normalizations']['skin_contact_only']['actual_source_Vpp_intervals_V'][0].__setitem__(0,1.),
                       lambda c:c['normalizations']['skin_contact_only'].update(source_Vpp_upper_by_output_V=[1.,1.]),
                       lambda c:c['normalizations']['skin_contact_only']['baseline_derived_numerical_limits'].update(SC_power_W=999.)):
            value=copy.deepcopy(self.condition);mutate(value)
            with self.assertRaises(ValueError):self.validate(value)

    def test_each_panel_repeats_two_controls_and_uses_four_distinct_ordered_phases(self):
        data=model();seen=[]
        for ratio in (.5,1.):
            panel=r.panel_cases(data,ratio)
            self.assertEqual(6,len(panel))
            self.assertEqual([row['id']for row in data['cases'][:2]],[row['id']for row in panel[:2]])
            self.assertEqual([0,90,180,270],[row['phase_deg']for row in panel[2:]])
            self.assertTrue(all(row['mix_ratio']==ratio for row in panel[2:]))
            seen.extend(row['id']for row in panel[2:])
        self.assertEqual(8,len(set(seen)))
        with self.assertRaises(ValueError):r.panel_cases(data,.75)

    def test_color_ranges_use_all_ten_saved_cases_before_panel_selection_and_preserve_arrays(self):
        data=model();before=copy.deepcopy(data)
        panel=r.panel_cases(data,.5)
        self.assertEqual((0.,1000.),r.shared_color_limits(data['cases'],'maxTIS','raw_1Vpp'))
        self.assertEqual((0.,3000.),r.shared_color_limits(data['cases'],'maxTIS','skin_contact_only'))
        self.assertLess(r.shared_color_limits(panel,'maxTIS','raw_1Vpp')[1],1000.)
        self.assertEqual((0.,19.),r.shared_color_limits(data['cases'],'maxTIS','raw_1Vpp',deep_roi=True))
        self.assertEqual((0.,57.),r.shared_color_limits(data['cases'],'maxTIS','skin_contact_only',deep_roi=True))
        for current,original in zip(data['cases'],before['cases']):
            for key in original['arrays']:np.testing.assert_array_equal(original['arrays'][key],current['arrays'][key])
            self.assertEqual(original['scales'],current['scales'])


if __name__=='__main__':
    unittest.main()
