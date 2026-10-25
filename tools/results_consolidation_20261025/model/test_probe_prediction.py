"""Synthetic analytic unit-test SOURCE; finite owner alone executes it."""
import math
import unittest
import probe_prediction as p


def np_for_test():
    import numpy as np
    return np


def fixture(np,layer_offsets=False):
    xs=np.asarray([-8.5,-7.5,-6.5,-5.5,-4.5,-3.5,-2.5,-1.5,-.5,.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5])
    # Deliberately no same-layer upper bracket for depth5/10.
    depths=[.025,.075,.5,2.,4.,4.8,5.3,7.,9.,9.8,10.4,14.,16.,19.,21.,24.]
    rows=[];values0=[];values1=[]
    a=.3+.2j;b=-.4+.1j;c=.15-.03j
    for z in depths:
        layer=0 if z<.1 else 1 if z<5.1 else 2 if z<10.1 else 3
        for y in xs:
            for x in xs:
                rows.append([x,y,z,layer,1e-9])
                offset=layer*1000. if layer_offsets else 0.
                value=offset+.7+a*x/1000.+b*y/1000.+c*z/1000.
                values0.append(value);values1.append(value*(.5-.2j))
    return np.asarray(rows),np.asarray(values0),np.asarray(values1),a,b,c


class ProbePredictionTests(unittest.TestCase):
    def test_affine_complex_potential_recovers_exact_5mm_tip_difference(self):
        np=np_for_test();grid,v0,v1,a,b,_=fixture(np)
        layout=p._layout(np,grid)
        negative,_,_=p.sample_tip(np,layout,v0,v1,[-2.5,0.,5.])
        positive,_,_=p.sample_tip(np,layout,v0,v1,[2.5,0.,5.])
        np.testing.assert_allclose(positive-negative,[a*.005,a*.005*(.5-.2j)],rtol=1e-10,atol=1e-10)
        negative,_,_=p.sample_tip(np,layout,v0,v1,[5.,-2.5,20.])
        positive,_,_=p.sample_tip(np,layout,v0,v1,[5.,2.5,20.])
        np.testing.assert_allclose(positive-negative,[b*.005,b*.005*(.5-.2j)],rtol=1e-10,atol=1e-10)

    def test_common_mode_cancels_and_nearest_depth_never_crosses_layer(self):
        np=np_for_test();grid,v0,v1,_,_,_=fixture(np,layer_offsets=True)
        common0=np.full(len(grid),3.+2j);common1=np.full(len(grid),-2.+1j)
        layout=p._layout(np,grid)
        low,_,_=p.sample_tip(np,layout,common0,common1,[-2.5,0.,5.])
        high,_,_=p.sample_tip(np,layout,common0,common1,[2.5,0.,5.])
        np.testing.assert_allclose(high-low,0.,rtol=0,atol=1e-10)
        interpolated,nearest,info=p.sample_tip(np,layout,v0,v1,[0.,0.,5.])
        self.assertEqual(info['Z']['layer'],1)
        self.assertEqual(info['Z']['method'],'same_layer_one_sided_linear_extrapolation')
        self.assertTrue(all(.1<z<5.1 for z in info['Z']['sample_depths_mm']))
        self.assertLess(info['nearest_native_xyz_mm'][2],5.1)
        self.assertLess(abs(interpolated[0]-1000.),1.)
        _,_,fat_info=p.sample_tip(np,layout,v0,v1,[0.,0.,10.])
        self.assertEqual(fat_info['Z']['layer'],2)
        self.assertTrue(all(5.1<z<10.1 for z in fat_info['Z']['sample_depths_mm']))

    def test_complete_40_probe_contract_waveform_and_instrument_separation(self):
        np=np_for_test();grid,v0,v1,a,b,_=fixture(np)
        result=p.build(np,grid,v0,v1);summary=result['summary'];arrays=result['arrays']
        self.assertEqual(summary['probe_count'],40)
        self.assertEqual(arrays['probe_differential_phasors_V_peak'].shape,(40,2))
        self.assertEqual(arrays['representative_waveforms_V'].shape,(2,p.SAMPLES))
        for row in summary['probes']:
            self.assertEqual(row['tip_spacing_mm'],5.)
            negative=row['negative_tip_xyz_mm'];positive=row['positive_tip_xyz_mm']
            self.assertAlmostEqual(math.sqrt(sum((x-y)**2 for x,y in zip(positive,negative))),5.)
            self.assertEqual(row['centre_xyz_mm'][2],negative[2])
            self.assertAlmostEqual(row['unloaded']['carrier_RMS_V'],row['unloaded']['carrier_RMS_formula_V'],places=10)
        self.assertFalse(summary['probe_loaded_prediction'])
        self.assertFalse(summary['instruments']['scope_input_connected_directly_in_parallel_with_phantom'])
        self.assertFalse(summary['instruments']['hardware_validation'])

    def test_expired_deadline_does_not_return_partial_probe_table(self):
        np=np_for_test()
        with self.assertRaises(TimeoutError):p.build(np,None,None,None,deadline=0.)


if __name__=='__main__':unittest.main()
