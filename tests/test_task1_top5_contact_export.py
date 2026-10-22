"""Synthetic contact-current metrics only; no catalogue, native files or CLI."""
import copy
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_top5_contact_export as r


class Top5ContactExportTest(unittest.TestCase):
    def test_same_frequency_outputs_sum_coherently_before_rms_squaring(self):
        patch=np.array([1.,2.,3.,4.])
        density=np.stack((patch,patch)).astype(complex)
        first=r.contact_rms({3000:density},{3000:np.array([1.,0.],complex)})
        inphase=r.contact_rms({3000:density},{3000:np.array([1.,1.],complex)})
        cancelled=r.contact_rms({3000:density},{3000:np.array([1j,-1j])})
        np.testing.assert_allclose(first,patch/np.sqrt(2),rtol=1e-14,atol=0)
        np.testing.assert_allclose(inphase,2*first,rtol=1e-14,atol=0)
        np.testing.assert_array_equal(cancelled,np.zeros(4))
        # Summing individual output powers would falsely predict nonzero JRMS.
        self.assertTrue(np.all(np.sqrt(np.sum(abs(density)**2,axis=0)/2)>cancelled))

    def test_distinct_frequencies_add_rms_power_after_each_coherent_sum(self):
        a=np.array([1.,2.,0.,4.]);b=np.array([0.,2.,3.,0.])
        densities={3000:np.stack((a,np.zeros(4))).astype(complex),3030:np.stack((np.zeros(4),b)).astype(complex)}
        coefficients={3000:np.array([1j,0j]),3030:np.array([0j,-1j])}
        before=copy.deepcopy((densities,coefficients))
        result=r.contact_rms(densities,coefficients)
        np.testing.assert_allclose(result,np.sqrt((a*a+b*b)/2),rtol=1e-14,atol=0)
        self.assertEqual((4,),result.shape)
        for actual,old in zip((densities,coefficients),before):
            for f in actual:np.testing.assert_array_equal(actual[f],old[f])

    def test_weighted_nearest_cdf_p95_uses_physical_area_and_inclusive_exact_cutoff(self):
        self.assertEqual(2.,r.weighted_p95(np.array([1.,2.,100.]),np.array([94.,1.,5.])))
        self.assertEqual(1.,r.weighted_p95(np.array([1.,100.]),np.array([95.,5.])))
        self.assertEqual(5.,r.weighted_p95(np.array([5.,1.,5.,8.]),np.array([2.,92.,1.,5.])))
        values=np.array([100.,2.,1.]);areas=np.array([5.,1.,94.]);before=(values.copy(),areas.copy())
        self.assertEqual(2.,r.weighted_p95(values,areas))
        np.testing.assert_array_equal(values,before[0]);np.testing.assert_array_equal(areas,before[1])
        self.assertEqual(2.,r.weighted_p95(values,areas*1e-6))

    def test_coefficient_decoder_preserves_complex_signs_alias_and_explicit_zero_frequencies(self):
        frequencies=(3000,3030,9000,9090)
        source={'3000':dict(real=[1.,-2.],imaginary=[-.5,.25]),'3030':dict(real=[0.,3.],imag=[2.,-4.])}
        before=copy.deepcopy(source);result=r.decode_coefficients(source,frequencies)
        self.assertEqual(set(frequencies),set(result))
        np.testing.assert_array_equal(result[3000],[1-.5j,-2+.25j])
        np.testing.assert_array_equal(result[3030],[2j,3-4j])
        np.testing.assert_array_equal(result[9000],[0j,0j]);np.testing.assert_array_equal(result[9090],[0j,0j])
        self.assertEqual(before,source)
        for invalid in ({'9999':dict(real=[0.,0.],imaginary=[0.,0.])},
            {'3000':dict(real=[1.,2.],imag=[0.,0.],imaginary=[0.,0.])},
            {'3000':dict(real=[1.],imaginary=[0.,0.])},
            {'3000':dict(real=[1.,float('nan')],imaginary=[0.,0.])}):
            with self.subTest(invalid=invalid),self.assertRaises((ValueError,TypeError)):
                r.decode_coefficients(invalid,frequencies)

    def test_metric_shape_frequency_and_finite_guards_reject_invalid_arrays(self):
        good=np.ones((2,4),complex);coeff=np.array([1.,0.],complex)
        for density,coefficient in (({3000:good},{3030:coeff}),({3000:good[:1]},{3000:coeff}),
            ({3000:good},{3000:np.ones(3)}),({3000:np.full((2,4),np.nan+0j)},{3000:coeff}),
            ({3000:good},{3000:np.array([1.,np.inf])}),
            ({3000:good,3030:np.ones((2,3),complex)},{3000:coeff,3030:coeff})):
            with self.subTest(density_shapes={f:v.shape for f,v in density.items()}),self.assertRaises((ValueError,TypeError)):
                r.contact_rms(density,coefficient)
        for values,areas in (([],[]),([1.,2.],[1.]),([1.,float('nan')],[1.,1.]),
            ([1.,2.],[1.,-1.]),([1.,2.],[0.,0.]),([1.,2.],[1.,float('inf')])):
            with self.subTest(values=values,areas=areas),self.assertRaises((ValueError,TypeError)):
                r.weighted_p95(np.asarray(values),np.asarray(areas))

    def test_contact_geometry_checks_full_area_grid_centres_unique_patch_ids_and_fixed_disk(self):
        rows=[(0,-.5,-.5,1e-6),(1,.5,.5,1e-6),(2,.5,-.5,1e-6),(3,-.5,.5,1e-6)]
        before=copy.deepcopy(rows);receipt=r.validate_contacts(rows,1.,n_pads=4)
        self.assertEqual(4,receipt['n_patches']);self.assertEqual(4,len(receipt['pad_areas_m2']))
        np.testing.assert_allclose(receipt['pad_areas_m2'],[1e-6]*4,rtol=1e-14,atol=0)
        self.assertAlmostEqual(4e-6,receipt['total_area_m2'],places=16);self.assertEqual(before,rows)
        invalids=[rows+[rows[0]],rows[:-1],[(4,*rows[0][1:]),*rows[1:]],
            [(0,0.,-.5,1e-6),*rows[1:]],[(0,25.5,-.5,1e-6),*rows[1:]],
            [(0,-.5,-.5,1.01e-6),*rows[1:]],[(0,-.5,-.5,0.),*rows[1:]],
            [(0,float('nan'),-.5,1e-6),*rows[1:]],[(0,-.5,-.5,float('inf')),*rows[1:]]]
        for invalid in invalids:
            with self.subTest(rows=invalid),self.assertRaises((ValueError,TypeError)):r.validate_contacts(invalid,1.,n_pads=4)

    def test_native_recipe_uses_frozen_peak_basis_and_harmonic_phase_without_extra_half_scale(self):
        source="WAVES = {'square_3h': (3/(2*math.sqrt(2)), 1/(2*math.sqrt(2))), 'sine': (1,0), 'triangle_3h': (.9,-.1)}"
        frequencies=(3000,3030,9000,9090)
        condition=dict(waveform='square_3h',carrier_group=[0,1],actual_fundamental_Hz=[3000,3030],
            source_Vpp_per_output=1.,phase_deg=[0.,0.])
        for waveform,a1,a3 in [('square_3h',3/(2*math.sqrt(2)),1/(2*math.sqrt(2))),
            ('sine',1.,0.),('triangle_3h',.9,-.1)]:
            with self.subTest(waveform=waveform):
                actual=r._native_coefficients({**condition,'waveform':waveform},frequencies,source)
                np.testing.assert_allclose(actual[3000],[-1j*a1,0j],rtol=1e-14,atol=1e-16)
                np.testing.assert_allclose(actual[3030],[0j,-1j*a1],rtol=1e-14,atol=1e-16)
                np.testing.assert_allclose(actual[9000],[-1j*a3,0j],rtol=1e-14,atol=1e-16)
                np.testing.assert_allclose(actual[9090],[0j,-1j*a3],rtol=1e-14,atol=1e-16)
                self.assertAlmostEqual(a1,abs(actual[3000][0]),places=14)
        rotated=r._native_coefficients({**condition,'phase_deg':[30.,0.]},frequencies,source)
        self.assertAlmostEqual(1/(2*math.sqrt(2)),rotated[9000][0].real,places=14)
        self.assertAlmostEqual(0.,rotated[9000][0].imag,places=14)
        np.testing.assert_allclose(rotated[3000][0],-1j*3/(2*math.sqrt(2))*np.exp(1j*math.pi/6),rtol=1e-14,atol=1e-16)

    def test_raw_and_all_five_saved_mode_regressions_must_pass_without_replacing_saved_metrics(self):
        values=np.array([1.,2.,3.,4.]);areas=np.ones(4)
        keys=('surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2')
        raw={k:4. for k in keys}
        scales={'raw_1Vpp':1.,'equal_total_source_output_RMS_sum':1.25,'equal_total_power':1.5,
            'skin_contact_only':2.,'legacy_composite_full_skin':.5}
        modes={name:dict(amplitude_scale=scale,normalized_burdens={k:4.*scale for k in keys})for name,scale in scales.items()}
        before=copy.deepcopy((raw,modes,scales))
        aggregate,checks=r.regression_checks(values,areas,raw,modes,scales)
        self.assertEqual(raw,aggregate);self.assertEqual(12,len(checks));self.assertTrue(all(c['passed']for c in checks))
        self.assertEqual([8.,8.],[c['actual_A_m2']for c in checks if c['mode']=='skin_contact_only'])
        self.assertEqual(before,(raw,modes,scales))
        for error in('raw','skin_saved','skin_scale'):
            badraw,badmodes,badscales=copy.deepcopy((raw,modes,scales))
            if error=='raw':badraw[keys[0]]+=.01
            elif error=='skin_saved':badmodes['skin_contact_only']['normalized_burdens'][keys[1]]+=.01
            else:badscales['skin_contact_only']=1.
            with self.subTest(error=error),self.assertRaises(ValueError):
                r.regression_checks(values,areas,badraw,badmodes,badscales)


if __name__=='__main__':unittest.main()
