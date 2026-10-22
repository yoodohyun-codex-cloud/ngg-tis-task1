import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from task1_output_power_evidence import output_power_evidence


def fixture():
    # f=3000: output0 ideal2V drives0.01A; passiveoutput1 ideal0V absorbs
    # through its50ohm resistor. f=3030 has quadrature currents: never coherently
    # add0.01+0.02j before applying the distinct-frequency RMS average.
    return dict(source_current_spectrum=[
        dict(frequency_Hz=3000,real_A=[.01,-.002],imaginary_A=[0.,0.]),
        dict(frequency_Hz=3030,real_A=[0.,0.],imaginary_A=[.02,.004])],
        loaded_metal_voltage_spectrum=[
        dict(frequency_Hz=3000,real_V=[1.5,.1],imaginary_V=[0.,0.]),
        dict(frequency_Hz=3030,real_V=[0.,0.],imaginary_V=[2.,-.2])],
        source_power_W=.04,source_resistor_power_W=.013,
        source_current_RMS_by_output_mA=[math.sqrt(.00025)*1000,math.sqrt(.00001)*1000])


class OutputPowerTests(unittest.TestCase):
    def test_signed_passive_absorption_and_per_output_power_balance(self):
        result = output_power_evidence(fixture())
        self.assertAlmostEqual(result['outputs'][0]['ideal_source_power_W'], .04)
        self.assertAlmostEqual(result['outputs'][1]['ideal_source_power_W'], 0.)
        self.assertAlmostEqual(result['outputs'][1]['metal_delivered_power_W'], -.0005)
        self.assertAlmostEqual(result['outputs'][1]['source_resistor_loss_W'], .0005)
        for row in result['outputs']:
            self.assertAlmostEqual(row['ideal_source_power_W'],row['metal_delivered_power_W']+row['source_resistor_loss_W'])

    def test_multifrequency_quadrature_rms_and_power(self):
        result = output_power_evidence(fixture())
        self.assertAlmostEqual(result['outputs'][0]['current_RMS_A'],math.sqrt((.01**2+.02**2)/2))
        self.assertAlmostEqual(result['totals']['metal_delivered_power_W'],.027)
        self.assertAlmostEqual(result['totals']['source_resistor_loss_W'],.013)
        in_phase = fixture()
        in_phase['source_current_spectrum'][1].update(real_A=[.02,.004],imaginary_A=[0.,0.])
        in_phase['loaded_metal_voltage_spectrum'][1].update(real_V=[2.,-.2],imaginary_V=[0.,0.])
        changed = output_power_evidence(in_phase)
        self.assertAlmostEqual(changed['outputs'][0]['current_RMS_A'],result['outputs'][0]['current_RMS_A'])
        self.assertNotAlmostEqual(changed['outputs'][0]['current_RMS_A'],(.01+.02)/math.sqrt(2))

    def test_common_scale_linear_currents_quadratic_signed_powers_no_mutation(self):
        metrics=fixture();original=copy.deepcopy(metrics)
        a=output_power_evidence(metrics);b=output_power_evidence(metrics,amplitude_scale=.3)
        self.assertEqual(metrics,original)
        for before,after in zip(a['outputs'],b['outputs']):
            self.assertAlmostEqual(after['current_RMS_A'],before['current_RMS_A']*.3)
            self.assertAlmostEqual(after['metal_delivered_power_W'],before['metal_delivered_power_W']*.09)
            self.assertAlmostEqual(after['ideal_source_power_W'],before['ideal_source_power_W']*.09)

    def test_frequency_mismatch_duplicate_and_bad_dimensions_rejected(self):
        for mutate in (
            lambda m:m['loaded_metal_voltage_spectrum'][0].update(frequency_Hz=6000),
            lambda m:m['source_current_spectrum'][1].update(frequency_Hz=3000),
            lambda m:m['source_current_spectrum'][0].update(real_A=[.01]),
            lambda m:m.update(source_current_RMS_by_output_mA=[1.])):
            metrics=fixture();mutate(metrics)
            with self.assertRaises((ValueError,TypeError)):output_power_evidence(metrics)

    def test_nonfinite_or_mismatched_saved_evidence_rejected(self):
        for mutate in (
            lambda m:m['source_current_spectrum'][0].update(real_A=[math.nan,0.]),
            lambda m:m.update(source_power_W=.041),
            lambda m:m.update(source_resistor_power_W=math.inf)):
            metrics=fixture();mutate(metrics)
            with self.assertRaises(ValueError):output_power_evidence(metrics)
        with self.assertRaises(ValueError):output_power_evidence(fixture(),amplitude_scale=-1.)


if __name__=='__main__':unittest.main()
