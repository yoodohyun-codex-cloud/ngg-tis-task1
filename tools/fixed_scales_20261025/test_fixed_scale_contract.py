"""Synthetic contracts only; root owns all actual cached-data execution."""
import base64
import copy
import math
import unittest

import numpy as np

import fixed_scale_contract as fixed


def descriptor(values):
    value=np.asarray(values,dtype='<f4').reshape(1,len(values),3,2)
    return dict(shape=list(value.shape),dtype='<f4',data_base64=base64.b64encode(value.tobytes()).decode())


def half(values):
    return base64.b64encode(np.asarray(values,dtype='<f2').tobytes()).decode()


def fixtures():
    burden=lambda a:dict(surface_J_RMS_max_A_m2=a,bulk_skin_J_vector_RMS_max_A_m2=a/2)
    match=lambda a:dict(amplitude_scale=a,required_source_Vpp=a,burdens=burden(3*a))
    analysis=dict(modes=dict(raw=dict(reference_amplitude_scale=1.,reference_burdens=burden(3.),matches=dict(ROI=match(1.),centre=match(1.5))),
                            skin=dict(reference_amplitude_scale=2.,reference_burdens=burden(6.),matches=dict(ROI=match(3.),centre=match(4.)))))
    # Point0 has orthogonal or phase-shifted terms: triangle5+5=10,
    # independently larger than a same-time cancellation at some phases.
    one=[[3.,4.,0.,0.,0.,0.],[math.nan]*6]
    two=[[-3.,-4.,0.,0.,0.,0.],[math.nan]*6]
    field=dict(schema='task1-native-field-shape-display-v1',analysis=analysis,
               planes=[dict(id='XZ',native_indices=[0,-1],fields=dict(TIS={'3000':descriptor(one),'3030':descriptor(two)},C1={'3000':descriptor(one)}))],
               reference_result_commit='b'*40,display_source_commit='d'*40,source_sha256={})
    source=lambda:dict(RMS=dict(xy=[half([2.,math.nan])],xz=half([2.,math.nan]),yz=half([2.,math.nan])),contactJ=dict(values_b64=half([3.,math.nan])))
    base=dict(analysis=copy.deepcopy(analysis),spatial=dict(TIS=source(),C1=source(),
        regions=dict(TIS=dict(total=dict(max=2.1)),C1=dict(total=dict(max=2.2))),
        grid=dict(x_edges_mm=[-25.,0.,25.],y_edges_mm=[-25.,0.,25.],z_faces_mm=[0.,.1,25.1])))
    return field,base


class FixedScaleContractTests(unittest.TestCase):
    def test_nice_upper_never_rounds_down_and_handles_zero(self):
        for value,expected in ((0.,1.),(.21,.5),(1.,1.),(1.0000000001,2.),(2.1,5.),(50.,50.),(50.000001,100.)):
            self.assertEqual(fixed.nice_upper(value),expected)
        with self.assertRaises(ValueError):fixed.nice_upper(float('nan'))

    def test_extreme_selection_and_phase_independent_bound(self):
        p,b=fixtures();calls=[]
        result=fixed.build_contract(p,b,lambda:calls.append(1))
        self.assertEqual(result['max_amplitude_by_case'],dict(TIS=2.,C1=4.))
        self.assertEqual(result['electric_field']['maximum_declared_upper_bound_V_m'],20.)
        self.assertEqual(result['electric_field']['upper_V_m'],20.)
        self.assertEqual(result['electric_field']['signed_lower_V_m'],-20.)
        self.assertEqual(result['current_density']['upper_A_m2'],20.)
        self.assertGreater(len(calls),3)
        self.assertFalse(result['automatic_rescaling'])

    def test_saved_full_volume_maximum_and_rounded_display_are_included(self):
        p,b=fixtures();b['spatial']['regions']['C1']['total']['max']=25.01
        result=fixed.build_contract(p,b,lambda:None)
        self.assertEqual(result['electric_field']['upper_V_m'],200.)
        p,b=fixtures();b['spatial']['TIS']['RMS']['xz']=half([30.,math.nan])
        result=fixed.build_contract(p,b,lambda:None)
        self.assertEqual(result['electric_field']['upper_V_m'],100.)

    def test_saved_scaled_burdens_are_not_scaled_twice(self):
        p,b=fixtures();p['analysis']['modes']['skin']['matches']['centre']['burdens']['surface_J_RMS_max_A_m2']=49.
        b['analysis']=copy.deepcopy(p['analysis'])
        result=fixed.build_contract(p,b,lambda:None)
        self.assertEqual(result['current_density']['maximum_declared_upper_bound_A_m2'],49.)
        self.assertEqual(result['current_density']['upper_A_m2'],50.)

    def test_nonfinite_interior_and_analysis_mismatch_fail(self):
        p,b=fixtures();p['planes'][0]['fields']['C1']['3000']=descriptor([[math.nan]*6,[math.nan]*6])
        with self.assertRaisesRegex(ValueError,'finite'):fixed.build_contract(p,b,lambda:None)
        p,b=fixtures();b['analysis']['modes']['raw']['reference_amplitude_scale']=9.
        with self.assertRaisesRegex(ValueError,'same analysis'):fixed.build_contract(p,b,lambda:None)

    def test_selection_order_does_not_change_limits_or_coordinates(self):
        p,b=fixtures();a=fixed.build_contract(p,b,lambda:None)
        p['analysis']['modes']=dict(reversed(list(p['analysis']['modes'].items())))
        for mode in p['analysis']['modes'].values():mode['matches']=dict(reversed(list(mode['matches'].items())))
        b['analysis']=copy.deepcopy(p['analysis']);z=fixed.build_contract(p,b,lambda:None)
        self.assertEqual(a['electric_field']['upper_V_m'],z['electric_field']['upper_V_m'])
        self.assertEqual(a['current_density']['upper_A_m2'],z['current_density']['upper_A_m2'])
        self.assertEqual(z['coordinate_ranges_mm'],dict(x_mm=[-25.,25.],y_mm=[-25.,25.],depth_z_mm=[0.,25.1]))


if __name__=='__main__':unittest.main()
