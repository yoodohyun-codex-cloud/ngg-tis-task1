"""Small synthetic contracts only: no native files, Matplotlib or render call."""
import ast
import copy
import importlib.util
import inspect
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


class RoundedContactMapsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rounded_contact_maps_tested',ROOT/'tools/task1_rounded_contact_maps.py')
        cls.maps=importlib.util.module_from_spec(spec)
        with patch.object(Path,'read_text',side_effect=AssertionError('No research input read at import')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('No research input read at import')):
            spec.loader.exec_module(cls.maps)

    def fixture(self):
        vectors={'3000':{'real':[0.,-.02],'imaginary':[-1.,-.01]},'3030':{'real':[-.01,0.],'imaginary':[-.015,-1.]}}
        vectors.update({str(f):{'real':[0.,0.],'imaginary':[0.,0.]}for f in(9000,9090)})
        waveform={'source_Vpp_intervals_V':[[.995,.996],[.999,1.]]}
        five=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
        scales=(1.,1.05,1.02,1.1,1.)
        rows=[]
        for index,ident in enumerate(self.maps.NATIVE_IDS):
            modes={m:dict(amplitude_scale=a,historical_SC2_mode_id=m,normalization_scope='frozen_SC2_amplitude_no_SC4_rematch',
                SC4_skin_caps_rematched=False,matches_SC2_current_on_SC4=False,matches_SC2_power_on_SC4=False,
                actual_source_Vpp_intervals_V=[[a,a],[a,a]])for m,a in zip(five,scales)}
            row=dict(schema='task1-rounded-sc4-sensitivity-condition-v1'if index==0 else'task1-rounded-contact-sensitivity-condition-v1',
                status='calculated_unadopted',candidate_adopted=False,source_case_id=ident,source_geometry_unchanged=True,
                same_source_coefficients_and_whole_Vpp=True,selected_SC2_condition_id=self.maps.SELECTED,coefficient_vectors=copy.deepcopy(vectors),
                active_frequencies_Hz=[3000,3030],harmonics_active=False,source_waveform=copy.deepcopy(waveform),fixed_SC2_amplitude_modes=modes,
                source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,source_resistance_ohm=50,return_topology='all_return_pads_ideal_common_GND',
                    pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'}))
            if index:row.update(complex_specific_contact_impedance_factor=self.maps.FACTORS[index],contact_configuration_contract=dict(
                complex_specific_contact_impedance_factor=self.maps.FACTORS[index],additional_Rs_subtraction=False,contact_area_rescaling=False,SC_cells=4))
            rows.append(row)
        selected=dict(condition_id=self.maps.SELECTED,raw_coefficient_vectors=vectors,raw_source_Vpp_intervals_V=waveform['source_Vpp_intervals_V'],SC2_skin8_amplitude_scale=1.1)
        return rows,selected

    def test_terminal_two_contact_factors_not_a_new_pass_threshold(self):
        value=dict(schema='task1-rounded-contact-sensitivity-v1',status='calculated_unadopted',inputs_unchanged=True,candidate_adopted=False,
            new_PDE=0,nominal_SC4_result_reused_without_recalculation=True,nominal_SC4_native_array_decode=False,
            relative_change_acceptance_threshold=None,conditions=[dict(native_contact_case_id=i,complex_specific_contact_impedance_factor=f,status='calculated_unadopted')
                for i,f in zip(self.maps.NATIVE_IDS[1:],self.maps.FACTORS[1:])])
        before=copy.deepcopy(value);self.maps.validate_summary(value);self.assertEqual(value,before)
        for key,bad in [('status','running'),('inputs_unchanged',False),('candidate_adopted',True),('new_PDE',2),('relative_change_acceptance_threshold',.02)]:
            changed=copy.deepcopy(value);changed[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):self.maps.validate_summary(changed)
        changed=copy.deepcopy(value);changed['conditions'].reverse()
        with self.assertRaises(ValueError):self.maps.validate_summary(changed)

    def test_three_exact_frozen_command_modes_not_contact_rematched(self):
        rows,selected=self.fixture();before=copy.deepcopy(rows)
        self.assertEqual(self.maps.validate_conditions(rows,selected),[{'raw_1Vpp':1.,'skin_contact_only':1.1}]*3);self.assertEqual(rows,before)
        for kind in ('rematch','current_equality','power_equality','skin_amplitude','other_mode','source_voltage','coefficient','source_count','mask_geometry','factor','Rs','area'):
            changed=copy.deepcopy(rows);row=changed[1]
            if kind=='rematch':row['fixed_SC2_amplitude_modes']['skin_contact_only']['SC4_skin_caps_rematched']=True
            elif kind=='current_equality':row['fixed_SC2_amplitude_modes']['raw_1Vpp']['matches_SC2_current_on_SC4']=True
            elif kind=='power_equality':row['fixed_SC2_amplitude_modes']['equal_total_power']['matches_SC2_power_on_SC4']=True
            elif kind=='skin_amplitude':row['fixed_SC2_amplitude_modes']['skin_contact_only']['amplitude_scale']=.9
            elif kind=='other_mode':row['fixed_SC2_amplitude_modes']['equal_total_power']['amplitude_scale']=1.03
            elif kind=='source_voltage':row['source_waveform']['source_Vpp_intervals_V'][0][0]=.5
            elif kind=='coefficient':row['coefficient_vectors']['3000']['real'][0]=.01
            elif kind=='source_count':row['source_circuit']['n_outputs']=4
            elif kind=='mask_geometry':row['source_geometry_unchanged']=False
            elif kind=='factor':row['complex_specific_contact_impedance_factor']=.75
            elif kind=='Rs':row['contact_configuration_contract']['additional_Rs_subtraction']=True
            else:row['contact_configuration_contract']['contact_area_rescaling']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.maps.validate_conditions(changed,selected)

    def test_identically_mutated_selected_and_nominal_harmonic_command_is_rejected(self):
        rows,selected=self.fixture();selected['raw_coefficient_vectors']['9000']['real'][0]=.1
        for row in rows:row['coefficient_vectors']['9000']['real'][0]=.1
        with self.assertRaisesRegex(ValueError,'zero harmonics'):self.maps.validate_conditions(rows,selected)

    def test_fixed_sc4_mesh_rejects_sc2_bigger_phantom_or_grid(self):
        meta=dict(cells=361728,h_xy_mm=.625,radius_mm=25.,total_depth_mm=25.1,channels=2,sc_cells=4,bulk_layer_counts=[14,14,40],
            frequencies_Hz=[3000,3030,9000,9090],tissue_boundaries_mm=[0,.1,5.1,10.1,25.1])
        self.maps.validate_grid_contract(meta)
        for k,v in [('sc_cells',2),('cells',351680),('radius_mm',30),('h_xy_mm',.5),('bulk_layer_counts',[14,14,50])]:
            bad=copy.deepcopy(meta);bad[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):self.maps.validate_grid_contract(bad)

    def test_config_only_complex_specific_Z_changes_all_frequency_parts(self):
        before={'validation.sc_cells':'4','mask.sha256':'abc','mask.path':'old','source.R':'50','radius':'25'}
        before.update({f'z.{f}.{p}':str(2. if p=='re'else-.5)for f in(3000,3030,9000,9090)for p in('re','im')})
        after={k:(str(float(v)*.5)if k.startswith('z.')else v)for k,v in before.items()};after['mask.path']='new'
        self.maps.validate_config_contrast(before,after,.5)
        for key,value in [('source.R','75'),('mask.sha256','other'),('validation.sc_cells','2'),('z.9090.im','-.5')]:
            bad=dict(after);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.maps.validate_config_contrast(before,bad,.5)

    def test_common_ranges_use_three_columns_and_saved_frozen_amplitude(self):
        cases=[dict(arrays=dict(maxTIS=np.array(v),fixedTIS=np.array(v)*.5,RMS=np.array(v)*2,region_target_m3=np.array([0.,1.])),
            scales={'raw_1Vpp':1.,'skin_contact_only':1.1})for v in([100.,2.],[50.,4.],[200.,3.])]
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','raw_1Vpp'),(0.,200.))
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','skin_contact_only',True),(0.,4.4))
        self.assertEqual(self.maps.shared_color_limits(cases,'fixedTIS','raw_1Vpp'),(0.,100.))
        self.assertEqual(self.maps.shared_color_limits(cases,'RMS','raw_1Vpp'),(0.,400.))

    def test_native_slice_never_relabels_it_as_twenty_mm_probe(self):
        grid=np.array([(x,y,z)for z in(.5,17.4125)for y in(-.3125,.3125)for x in(-.3125,.3125)])
        # Exact native faces are supplied for this synthetic two-layer grid.
        grid[:,2]=np.repeat([.5,17.4125],4)
        result=self.maps.native_slices(grid,dict(cells=8,h_xy_mm=.625,z_faces_mm=[0.,1.,33.825]),np.arange(1.,9.))
        self.assertEqual(result['xy_actual_depth_mm'],17.4125);np.testing.assert_array_equal(result['xy'],[[5.,6.],[7.,8.]])
        self.assertNotEqual(result['xy_actual_depth_mm'],20.)

    def test_nonterminal_summary_stops_before_any_array_or_grid_read(self):
        with patch.object(self.maps.base,'bound_json',return_value={'schema':'task1-rounded-contact-sensitivity-v1','status':'running'}),\
             patch.object(self.maps.base,'load_scalars',side_effect=AssertionError('No scalar read')),\
             patch.object(self.maps.np,'loadtxt',side_effect=AssertionError('No grid read')):
            with self.assertRaises(ValueError):self.maps.load_model('/future/summary.json')

    def test_renderer_source_has_twelve_combinations_true_fatband_and_no_bbox_drawing(self):
        source=inspect.getsource(self.maps.render_model);tree=ast.parse(source)
        self.assertEqual(len(self.maps.MODES)*len(self.maps.METRICS)*2,12)
        self.assertIn('Polygon(p[\'polygon_mm\']',source);self.assertNotIn("p['bounding_box_mm']",source)
        self.assertIn("plt.subplots(2,3",source);self.assertIn("shared_cases=3",source)
        spans=[c for c in ast.walk(tree)if isinstance(c,ast.Call)and isinstance(c.func,ast.Attribute)and c.func.attr=='axhspan']
        self.assertTrue(any([ast.literal_eval(a)for a in c.args[:2]]==[5.1,10.1]for c in spans))
        self.assertIn('no_E_phi_decode=True',source);self.assertEqual(self.maps.MAX_OUTPUT_BYTES,32*1024**2)

if __name__=='__main__':unittest.main()
