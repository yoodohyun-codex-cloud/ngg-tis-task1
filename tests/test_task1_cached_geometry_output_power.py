"""Synthetic saved-output power contracts; no native arrays or research runs."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')


def metrics_fixture():
    first=3/(2*math.sqrt(2));third=1/(2*math.sqrt(2));currents=[];metals=[]
    for frequency in(3000,3030,9000,9090):
        amplitude=first if frequency in(3000,3030)else third;active=0 if frequency in(3000,9000)else 1
        current=[.00005*amplitude,.00005*amplitude];current[active]=-.0005*amplitude
        metal=[-50.*value for value in current];metal[active]+=-.5*amplitude
        currents.append(dict(frequency_Hz=frequency,real_A=[0.,0.],imaginary_A=current))
        metals.append(dict(frequency_Hz=frequency,real_V=[0.,0.],imaginary_V=metal))
    return dict(source_current_spectrum=currents,loaded_metal_voltage_spectrum=metals,
        source_power_W=.0003125,source_resistor_power_W=.00001578125,tissue_contact_power_W=.00029671875,
        source_current_RMS_by_output_mA=[math.sqrt(.1578125),math.sqrt(.1578125)],
        driven_max_current_relative_error=1e-8,driven_max_power_relative_error=1e-8)


def modes_fixture(metrics):
    return {name:dict(amplitude_scale=scale,source_Vpp_per_output=scale,
        source_output_RMS_by_output_mA=[value*scale for value in metrics['source_current_RMS_by_output_mA']],
        normalized_burdens=dict(source_power_W=metrics['source_power_W']*scale**2))
        for name,scale in zip(MODES,(1.,.75,2.,1.2,.6))}


def square_fixture():
    return dict(waveform='square_3h',actual_fundamental_Hz=[3000,3030],phase_deg=[0.,0.],
        source_Vpp_per_output=1.,metrics=metrics_fixture())


class CachedGeometryOutputPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('cached_geometry_output_power_tested',ROOT/'tools/task1_cached_geometry_output_power.py')
        cls.tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.tool)

    def test_passive_output_negative_tone_power_is_preserved_and_balances_sources(self):
        condition=square_fixture();metrics=self.tool.validate_square_condition(condition);before=copy.deepcopy(metrics)
        report=self.tool.audit_condition(metrics,modes_fixture(metrics))
        raw=report['normalizations']['raw_1Vpp']['signed_per_output_power_evidence']
        self.assertEqual(metrics,before)
        self.assertTrue(raw['requires_output_power_absorption'])
        self.assertFalse(raw['requires_source_power_absorption'])
        self.assertFalse(raw['hardware_absorption_and_compliance_validated'])
        self.assertLess(raw['outputs'][1]['spectrum'][0]['metal_delivered_power_W'],0.)
        self.assertAlmostEqual(raw['outputs'][1]['spectrum'][0]['ideal_source_power_W'],0.,places=18)
        self.assertAlmostEqual(raw['totals']['ideal_source_power_W'],metrics['source_power_W'],places=16)
        for output in raw['outputs']:
            self.assertAlmostEqual(output['ideal_source_power_W'],output['metal_delivered_power_W']+output['source_resistor_loss_W'],places=16)

    def test_five_saved_modes_scale_actual_output_voltage_current_linearly_and_signed_power_quadratically(self):
        metrics=metrics_fixture();modes=modes_fixture(metrics);before=copy.deepcopy((metrics,modes))
        report=self.tool.audit_condition(metrics,modes);self.assertEqual(set(report['normalizations']),set(MODES))
        raw=report['normalizations']['raw_1Vpp']['signed_per_output_power_evidence']
        for name,mode in report['normalizations'].items():
            scale=modes[name]['amplitude_scale'];evidence=mode['signed_per_output_power_evidence']
            self.assertEqual(mode['source_Vpp_by_output'],[scale,scale])
            for old,new in zip(raw['outputs'],evidence['outputs']):
                self.assertAlmostEqual(new['current_RMS_mA'],old['current_RMS_mA']*scale,places=15)
                for key in('ideal_source_power_W','metal_delivered_power_W','source_resistor_loss_W'):
                    self.assertAlmostEqual(new[key],old[key]*scale**2,places=16)
            self.assertAlmostEqual(evidence['totals']['ideal_source_power_W'],metrics['source_power_W']*scale**2,places=16)
        self.assertEqual((metrics,modes),before)

    def test_saved_power_disagreement_and_native_conservation_gate_failures_are_rejected(self):
        condition=square_fixture()
        for key,value in(('driven_max_current_relative_error',2.1e-6),('driven_max_power_relative_error',2.1e-7)):
            bad=copy.deepcopy(condition);bad['metrics'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.tool.validate_square_condition(bad)
        for key,value in(('source_power_W',.0004),('source_resistor_power_W',.00002),('tissue_contact_power_W',.0001)):
            metrics=metrics_fixture();metrics[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.tool.audit_condition(metrics,modes_fixture(metrics))
        at_limit=square_fixture();at_limit['metrics'].update(driven_max_current_relative_error=2e-6,driven_max_power_relative_error=2e-7)
        self.tool.validate_square_condition(at_limit)

    def test_wrong_native_wave_phase_drive_or_frequency_rows_cannot_be_relabelled_square(self):
        for key,value in(('waveform','sine'),('actual_fundamental_Hz',[9000,9090]),('phase_deg',[90.,0.]),('source_Vpp_per_output',.5)):
            condition=square_fixture();condition[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.tool.validate_square_condition(condition)
        for mutation in('missing','duplicate','other_frequency','swapped_carriers','reversed_third'):
            condition=square_fixture();rows=condition['metrics']['source_current_spectrum']
            if mutation=='missing':rows.pop()
            elif mutation=='duplicate':rows[1]['frequency_Hz']=3000
            elif mutation=='other_frequency':rows[0]['frequency_Hz']=2000
            elif mutation=='swapped_carriers':
                for name in('source_current_spectrum','loaded_metal_voltage_spectrum'):
                    condition['metrics'][name][0]['frequency_Hz']=3030
                    condition['metrics'][name][1]['frequency_Hz']=3000
            else:
                for name in('source_current_spectrum','loaded_metal_voltage_spectrum'):
                    for key in condition['metrics'][name][2]:
                        if key!='frequency_Hz':condition['metrics'][name][2][key]=[-value for value in condition['metrics'][name][2][key]]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.tool.validate_square_condition(condition)

    def test_saved_scaled_current_power_or_mode_contract_mismatch_is_rejected(self):
        for mutation in('current','power','missing','zero','nan','raw','voltage'):
            metrics=metrics_fixture();modes=modes_fixture(metrics);mode=modes['skin_contact_only']
            if mutation=='current':mode['source_output_RMS_by_output_mA'][0]+=.1
            elif mutation=='power':mode['normalized_burdens']['source_power_W']+=.0001
            elif mutation=='missing':modes.pop('equal_total_power')
            elif mutation=='zero':mode['amplitude_scale']=0.
            elif mutation=='nan':mode['amplitude_scale']=float('nan')
            elif mutation=='raw':modes['raw_1Vpp'].update(amplitude_scale=.5,source_Vpp_per_output=.5)
            else:mode['source_Vpp_per_output']=.2
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.tool.audit_condition(metrics,modes)


if __name__=='__main__':unittest.main()
