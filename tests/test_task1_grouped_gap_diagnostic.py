"""Synthetic saved-field diagnostics only; never read research native arrays."""
import copy
import gzip
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import numpy as np
import task1_grouped_gap_diagnostic as diagnostic


def grid_fixture():
    grid=np.zeros(4,dtype=[(k,'f8') for k in ('x_mm','y_mm','z_mm','layer','volume_m3')])
    grid['x_mm']=[0,1,2,3];grid['z_mm']=[.025,.075,.3,.6];grid['layer']=[0,0,1,1];grid['volume_m3']=1e-10
    return grid


def config_fixture():
    return {k+suffix:str(value) for k in ('sc','dermis','fat','muscle')
        for suffix,value in (('.sigma',1),('.epsilon_r',2))}


def saved_skin(squared,grid):
    result={}
    for name,mask in [('SC',grid['layer']==0),('dermis',grid['layer']==1),('skin_SC_plus_dermis',grid['layer']<=1)]:
        result[name]={}
        for kind,energy in squared.items():
            values=np.sqrt(energy[mask]);result[name][kind]=dict(J_vector_RMS_max_A_m2=float(max(values)),
                J_vector_RMS_p95_A_m2=float(max(values)))
    return dict(regions=result)


def source_data(values):
    grid=grid_fixture();weights=np.full(4,1e-10);arrays={m:np.array(values,float) for m in diagnostic.volume.METRICS}
    regions={r:weights.copy() for r in ('total',diagnostic.volume.PRIMARY,diagnostic.volume.SLAB,
        'surface_0_5','primary_complement','supplemental_complement')}
    metrics={k:1. for k in diagnostic.view.CAPS};metrics['source_current_RMS_by_output_mA']=[1.,1.]
    condition=dict(id='square',metrics=metrics)
    skin=dict(J_vector_RMS_max_A_m2=1.,J_vector_RMS_p95_A_m2=1.,skin_SC_plus_dermis_power_W=1.)
    item=dict(full_skin={'square':skin},circuit=dict(n_outputs=2),path=Path('/synthetic/summary.json'),
        registration=dict(source_commit='source'),signature='actual-signature',
        summary=dict(id='candidate',mesh_metadata=dict(config_sha256='cfg'),validation={k:0. for k in diagnostic.screen.NATIVE_GATES}))
    return dict(item=item,condition=condition,arrays=arrays,grid=grid,regions=regions,reproduced={})


class GroupedGapDiagnosticTests(unittest.TestCase):
    def test_current_integration_keeps_physical_pads_and_common_return(self):
        contacts=np.zeros(8,dtype=[('pad','i4'),('area_m2','f8')]);contacts['pad']=np.arange(8);contacts['area_m2']=.5
        # 2 pads per source group and 4 shared-GND physical return pads.
        density=np.array([[1,1,.2,.2,-.6,-.6,-.6,-.6],[.3,.3,2,2,-1.15,-1.15,-1.15,-1.15]],complex)
        source=np.array([[1,.3],[.2,2]],complex);coeff=np.array([-1j,0j]);nodes=[0,0,1,1,-1,-1,-1,-1]
        receipt,pads,outputs=diagnostic.currents_from_arrays(density,source,contacts,coeff,nodes)
        self.assertEqual(len(pads),8);self.assertAlmostEqual(receipt['conservation_relative_error'],0.)
        self.assertNotEqual(outputs[1],0.) # Inactive channel still terminated by50ohm.
        metal=receipt['loaded_output_metal_voltage_peak_V'];self.assertAlmostEqual(metal['imaginary'][1],10.)
        self.assertAlmostEqual(sum(pads),0.)

    def test_incorrect_contact_area_or_source_matrix_fails_conservation(self):
        contacts=np.zeros(4,dtype=[('pad','i4'),('area_m2','f8')]);contacts['pad']=np.arange(4);contacts['area_m2']=1.
        density=np.array([[1,0,-.5,-.5],[0,1,-.5,-.5]],complex)
        contacts['area_m2'][0]=.9
        with self.assertRaisesRegex(ValueError,'conservation'):
            diagnostic.currents_from_arrays(density,np.eye(2),contacts,np.array([-1j,0]),[0,1,-1,-1])

    def test_actual_four_square_spectral_lines_not_two_frequency_approximation(self):
        condition=dict(waveform='square_3h',actual_fundamental_Hz=[3000,3030],carrier_group=[0,1],phase_deg=[0.,0.])
        coefficients=diagnostic.waveform.condition_coefficients(condition,dict(channels=2,frequencies_Hz=list(diagnostic.FREQUENCIES)))
        self.assertEqual(set(coefficients),{3000,3030,9000,9090})
        self.assertAlmostEqual(abs(coefficients[9000][0]),1/(2*math.sqrt(2)))
        self.assertEqual(coefficients[9000][1],0.)
        self.assertAlmostEqual(sum(float(np.vdot(c,c).real) for c in coefficients.values()),2.5)

    def test_complex_admittivity_and_all_harmonics_change_total_J(self):
        grid=grid_fixture();field=np.zeros((4,3),complex);field[:,0]=[1,2,3,4]
        cfg=config_fixture();cfg['sc.epsilon_r']='110000'
        low=diagnostic.skin_values_from_field(field,3000,grid,cfg)
        high=diagnostic.skin_values_from_field(field,9000,grid,cfg)
        self.assertGreater(low['total'][0],low['conductive'][0]);self.assertGreater(high['total'][0],low['total'][0])
        np.testing.assert_array_equal(high['conductive'],low['conductive'])

    def test_SC_dermis_hotspot_positions_are_actual_field_cells(self):
        grid=grid_fixture();squared=dict(total=np.array([1.,9.,16.,4.]),conductive=np.array([1.,4.,9.,4.]))
        pad=dict(x_mm=0.,y_mm=0.,width_mm=1.,height_mm=1.)
        result=diagnostic.skin_hotspots(squared,grid,[pad],saved_skin(squared,grid))
        self.assertEqual(result['regions']['SC']['total']['hotspot']['native_cell_index'],1)
        self.assertEqual(result['regions']['dermis']['total']['hotspot']['native_cell_index'],2)
        self.assertEqual(result['regions']['dermis']['total']['hotspot']['center_xyz_mm'],[2.,0.,.3])
        saved=saved_skin(squared,grid);saved['regions']['SC']['total']['J_vector_RMS_max_A_m2']=4.
        with self.assertRaisesRegex(ValueError,'does not reproduce'):
            diagnostic.skin_hotspots(squared,grid,[pad],saved)

    def test_no_saved_field_means_explicit_missing_not_invented_hotspot(self):
        with self.assertRaisesRegex(ValueError,'missing/ambiguous'):
            diagnostic.native_path(dict(input_sha256={}), 'field-3000.bin')

    def test_contact_hotspot_partial_face_and_all_harmonics_voltage_distinct(self):
        contacts=np.zeros(2,dtype=[('pad','i4'),('x_mm','f8'),('y_mm','f8'),('area_m2','f8')])
        contacts['pad']=[0,1];contacts['x_mm']=[0.,2.];contacts['area_m2']=[1e-8,3e-7]
        pads=[dict(x_mm=x,y_mm=0.,width_mm=.1 if x==0 else .6,height_mm=.1 if x==0 else .5) for x in (0.,2.)]
        case=dict(h_xy_mm=.625,pads=pads,pad_node_ids=[0,1])
        # Both fundamental and third harmonic contribute. J and contact V peak at different patches.
        density={3000:np.array([2.,1.]),3030:np.array([0.,1.]),9000:np.array([3.,0.]),9090:np.array([0.,1.])}
        impedance={3000:1.,3030:10.,9000:1.,9090:10.}
        j2=sum(abs(d)**2/2 for d in density.values());v2=sum(abs(d*impedance[f])**2/2 for f,d in density.items())
        saved=dict(surface_J_RMS_max_A_m2=math.sqrt(6.5),surface_J_RMS_p95_A_m2=math.sqrt(1.5),contact_voltage_RMS_max_V=math.sqrt(100.5))
        result=diagnostic.contact_hotspots(j2,v2,contacts,case,saved)
        self.assertEqual(result['normal_J_RMS_max_location']['physical_pad_id'],0)
        self.assertEqual(result['contact_voltage_RMS_max_location']['physical_pad_id'],1)
        self.assertAlmostEqual(result['normal_J_RMS_max_location']['patch_fraction_of_native_face'],1e-8/(.625e-3)**2)
        self.assertGreater(result['metrics']['surface_J_RMS_max_A_m2'],math.sqrt(2.))
        wrong=dict(saved,surface_J_RMS_max_A_m2=math.sqrt(2.))
        with self.assertRaisesRegex(ValueError,'spectral reconstruction'):
            diagnostic.contact_hotspots(j2,v2,contacts,case,wrong)

    def test_fixed_fine_cutoffs_and_caps_applied_to_different_grid_signature(self):
        baseline=source_data([2.,3.,4.,5.]);candidate=source_data([1.,2.,3.,4.]);candidate['item']['signature']='actual-coarse-grid'
        candidate['condition']['metrics']['SC_power_W']=4.
        cutoffs=diagnostic.frozen_cutoffs(baseline)
        with mock.patch.object(diagnostic,'sha',return_value='summaryhash'):
            base_row=diagnostic.normalized_row(baseline,baseline,cutoffs,time.monotonic()+10)
            row=diagnostic.normalized_row(candidate,baseline,cutoffs,time.monotonic()+10)
        self.assertEqual(row['comparison_signature'],'actual-coarse-grid')
        self.assertEqual(row['fixed_fine_baseline_cutoffs_V_m'],cutoffs)
        self.assertEqual(row['normalizations']['skin_contact_only']['amplitude_scale'],.5)
        checks=diagnostic.screen.screen_checks(row,base_row)
        self.assertFalse(checks[0]['passed']);self.assertFalse(checks[1]['passed'])
        self.assertLess(row['normalizations']['skin_contact_only']['regions']['surface_0_5']['maxTIS']['p95'],
            base_row['normalizations']['skin_contact_only']['regions']['surface_0_5']['maxTIS']['p95'])
        self.assertTrue(all(row['normalizations']['skin_contact_only']['normalized_burdens'][k]<=1.+1e-12
            for k in diagnostic.screen.CAP_DEGREES))

    def test_rank_flip_retains_both_mesh_orders_without_adoption(self):
        rows=[]
        for mesh,values in [('coarse',[4,3,2,1]),('fine',[1,2,3,4])]:
            for n,value in zip((4,8,12,16),values):
                rows.append(dict(mesh_label=mesh,n_pads=n,normalizations={mode:dict(regions={diagnostic.volume.PRIMARY:
                    dict(maxTIS=dict(mean=value,p10=value))}) for mode in diagnostic.screen.MODES}))
        result=diagnostic.rank_stability(rows)['skin_contact_only']['mean']
        self.assertEqual(result['coarse'],[4,8,12,16]);self.assertEqual(result['fine'],[16,12,8,4]);self.assertFalse(result['order_identical'])

    def test_bounded_binary_reader_rejects_extra_or_nonfinite_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'field-3000.bin.gz'
            with gzip.open(path,'wb') as stream:stream.write(np.array([1+2j,3+4j],dtype='<c16').tobytes())
            summary=dict(input_sha256={str(path):diagnostic.sha(path)})
            with mock.patch.object(diagnostic,'native_path',return_value=path):
                refs={};a=diagnostic.native_matrix(summary,'field',3000,(2,),refs)
                np.testing.assert_array_equal(a,[1+2j,3+4j]);self.assertEqual(refs[str(path)],summary['input_sha256'][str(path)])
                with self.assertRaisesRegex(ValueError,'byte count'):
                    diagnostic.native_matrix(summary,'field',3000,(1,),{})

    def test_new_output_cannot_overwrite_original_or_partial_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'evidence.json';diagnostic.write(path,dict(failure=True),new=True)
            before=path.read_bytes()
            with self.assertRaises(FileExistsError):diagnostic.write(path,dict(failure=False),new=True)
            self.assertEqual(path.read_bytes(),before)

    def test_failed_attempt_preserves_inputs_and_appends_actual_ledger_cost(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'docs/diagnostic';out.mkdir(parents=True);(root/'runtime').mkdir()
            evidence=root/'saved-native';evidence.write_bytes(b'unchanged original')
            ledger=dict(limit_seconds=13800,spent_seconds=123.,runs=[dict(previous='preserved')])
            baseline=copy.deepcopy(ledger)
            plan=root/'plan.json';plan.write_text('{}')
            with mock.patch.object(diagnostic,'ROOT',root),mock.patch.object(diagnostic.policy,'load_ledger',return_value=ledger),\
                    mock.patch.object(diagnostic.policy,'remaining_seconds',return_value=1000.),\
                    mock.patch.object(diagnostic,'verify_plan',side_effect=ValueError('deliberate hash mismatch')):
                with self.assertRaisesRegex(ValueError,'hash mismatch'):diagnostic.execute(plan,out)
            saved=json.loads((root/'runtime/task1-budget.json').read_text())
            self.assertEqual(saved['runs'][:1],baseline['runs']);self.assertGreater(saved['spent_seconds'],123.)
            self.assertEqual(saved['runs'][-1]['status'],'failed_preserved');self.assertGreater(saved['runs'][-1]['seconds'],0.)
            self.assertTrue((out/'failure.json').exists());self.assertEqual(evidence.read_bytes(),b'unchanged original')
            with mock.patch.object(diagnostic,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'Never retry'):diagnostic.execute(plan,out)


if __name__ == '__main__':unittest.main()
