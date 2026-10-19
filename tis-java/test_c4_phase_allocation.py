"""Synthetic C4 algebra/provenance/stage gates; no retained basis is loaded."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import c4_phase_allocation as c4


def fixture():
    contacts=np.zeros(8,dtype=[('pad','f8'),('x_mm','f8'),('y_mm','f8'),('area_m2','f8')])
    contacts['pad']=range(8);contacts['area_m2']=1e-4
    basis={'validation':dict(max_residual=1e-10,max_power_error=1e-10,
        max_current_error=1e-10,channels=4,cells=1),'f':{}}
    for index,f in enumerate(c4.FREQUENCIES):
        source=np.eye(4,dtype=complex)*(.002+index*.0001)+np.full((4,4),.00002)
        density=np.empty((4,8),complex)
        density[:,:4]=source.T/1e-4
        density[:,4:]=-np.sum(source,axis=0)[:,None]/4/1e-4
        target=np.asarray([[1+.1j,.3,0],[.7,.1j,.1],[0,.8,.2j],[.1,.9,.2]],complex)*(1+.07*index)
        basis['f'][f]=dict(target=target,source=source,density=density,
            loss=np.stack([source/24 for _ in range(6)]),contacts=contacts.copy())
    design=dict(channels=4,carrier_Hz=3000,beat_Hz=5,layout='synthetic',size_mm=10,
        xy_mm=[[0,0]]*8,boundary_mode='measured_minus_Rs')
    profile=dict(thickness_nm=50,warnings=[],selected_fit={'Rs_ohm':1},
        points=[dict(frequency_Hz=f,Z_real_ohm=5,Z_imag_ohm=-2,source_range='synthetic') for f in c4.FREQUENCIES])
    bounds=c4._boundaries({'design':design},profile)
    return basis,design,profile,bounds


class C4PhaseAllocationTests(unittest.TestCase):
    def test_exact_grid_and_carrier_gauge_do_not_change_original_globals(self):
        original=c4.old.DIRS.copy();waves=copy.deepcopy(c4.old.WAVES)
        grid=c4.phase_grid()
        self.assertEqual(len(grid),14*64)
        self.assertEqual(sum(g['allocation_family']=='1plus3' for g in grid),4*64)
        self.assertEqual(sum(g['allocation_family']=='2plus2' for g in grid),6*64)
        self.assertEqual(sum(g['allocation_family']=='3plus1' for g in grid),4*64)
        self.assertEqual(len({(g['allocation'],g['phase_index']) for g in grid}),896)
        self.assertEqual(896*3*3,8064)
        for row in grid:
            for carrier in (0,1):self.assertEqual(row['phase_deg'][row['carrier_group'].index(carrier)],0)
        self.assertEqual(len(c4.old.directions(486)),512)
        self.assertEqual(len(c4.old.directions(8192)),8218)
        np.testing.assert_array_equal(original,c4.old.DIRS)
        self.assertEqual(waves,c4.old.WAVES)

    def test_original_summarize_and_new_evaluator_agree_all108_synthetic_rows(self):
        basis,design,profile,boundaries=fixture()
        c4.validate_basis(basis,dict(cells=1,pad_size_mm=10))
        old=c4.old.summarize(basis,design,profile,'synthetic',1.25,seed=3739)
        patterns=c4.old.drive_patterns(4,3739)
        self.assertEqual(len(old),108)
        for index,reference in enumerate(old):
            group,phase=patterns[index//3]
            new=c4.evaluate(basis,boundaries,reference['waveform'],group,phase)
            for key in c4.METRICS:
                with self.subTest(row=index,metric=key):self.assertTrue(c4.strict_match(new[key],reference[key]))

    def test_linear_fields_and_quadratic_power_with_loaded_terminal_currents(self):
        basis,_,_,boundaries=fixture()
        for wave in c4.old.WAVES:
            a=c4.evaluate(basis,boundaries,wave,[0,0,1,1],[0,.4,0,.8])
            b=c4.evaluate(basis,boundaries,wave,[0,0,1,1],[0,.4,0,.8],amplitude=2)
            for key in c4.LINEAR:self.assertAlmostEqual(b[key],2*a[key],delta=1e-12)
            for key in c4.QUADRATIC:self.assertAlmostEqual(b[key],4*a[key],delta=1e-12)
            np.testing.assert_allclose(b['source_current_RMS_by_output_mA'],2*np.array(a['source_current_RMS_by_output_mA']))
            np.testing.assert_allclose(b['source_load_voltage_RMS_by_output_V'],2*np.array(a['source_load_voltage_RMS_by_output_V']))
            self.assertAlmostEqual(sum(a['loss_by_region_W'].values()),a['source_power_W'],delta=1e-12)

    def test_coherent_sum_harmonics_and_per_carrier_global_phase(self):
        basis,_,_,boundaries=fixture();group=[0,0,1,1];phase=np.array([0.,.3,0.,1.1])
        for wave in c4.old.WAVES:
            shifted=phase+np.array([.7,.7,-.4,-.4])
            a=c4.evaluate(basis,boundaries,wave,group,phase)
            b=c4.evaluate(basis,boundaries,wave,group,shifted)
            for key in c4.METRICS:self.assertAlmostEqual(a[key],b[key],delta=1e-11)
        coeff=c4.coefficients('triangle_3h',group,phase)
        self.assertAlmostEqual(abs(coeff[9000][1]),.1)
        self.assertAlmostEqual(abs(coeff[3000][1]),.9)
        self.assertEqual(coeff[3000][2],0)
        self.assertEqual(coeff[3005][0],0)
        expected=-1j*(-.1)*np.exp(3j*phase[1])
        self.assertAlmostEqual(abs(coeff[9000][1]-expected),0)
        basis['f'][3000]['target'][1]=basis['f'][3000]['target'][0]
        target=c4.targets(basis,'sine',group,[0,np.pi,0,0])[3000]
        self.assertLess(np.linalg.norm(target),1e-12)
        incoherent=sum(np.linalg.norm(basis['f'][3000]['target'][i]) for i in (0,1))
        self.assertGreater(incoherent,1)

    def test_exact_dedup_preserves_complements_and_all108_lattice_matches(self):
        key=lambda wave,group,phase:c4.physical_key('basis',wave,group,phase)
        self.assertEqual(key('sine',[0,0,1,1],[0,180,0,180]),key('sine',[0,0,1,1],[360,-180,0,-180]))
        self.assertNotEqual(key('sine',[0,0,1,1],[0,180,0,180]),key('sine',[0,0,1,1],[0,180+1e-12,0,180]))
        self.assertNotEqual(key('sine',[0,0,1,1],[0,0,0,0]),key('sine',[1,1,0,0],[0,0,0,0]))
        old_keys={key(w,g,np.rad2deg(p).tolist()) for g,p in c4.old.drive_patterns(4,3739) for w in c4.old.WAVES}
        new_keys={key(w,r['carrier_group'],r['phase_deg']) for r in c4.phase_grid() for w in c4.old.WAVES}
        self.assertEqual(len(old_keys&new_keys),36)
        self.assertEqual(36*3,108)
        self.assertEqual((2688-36)*3,7956)
        # Cross-allocation matching uses the same actual4-output phase vector,
        # canonicalized under the new carrier's own reference output indices.
        for row in c4.phase_grid():
            for g in itertools.product((0,1),repeat=4):
                if g.count(0)==2:self.assertIn(key('sine',g,row['phase_deg']),new_keys)

    def test_failed_conservation_shapes_and_exact_zero_never_relax(self):
        self.assertFalse(c4.strict_match(1e-30,0))
        self.assertFalse(c4.strict_match(float('nan'),1))
        self.assertTrue(c4.strict_match(0,0))
        basis,_,_,boundaries=fixture()
        broken=copy.deepcopy(basis);broken['f'][3000]['density'][0,0]*=1.02
        with self.assertRaisesRegex(ValueError,'current mismatch'):c4.evaluate(broken,boundaries,'sine',[0,0,1,1],[0]*4)
        broken=copy.deepcopy(basis);broken['f'][3000]['loss']*=1.01
        with self.assertRaisesRegex(ValueError,'power conservation'):c4.evaluate(broken,boundaries,'sine',[0,0,1,1],[0]*4)
        broken=copy.deepcopy(basis);broken['f'][3000]['loss'][0,0,1]+=1j
        with self.assertRaisesRegex(ValueError,'Hermitian'):c4.validate_basis(broken,dict(cells=1,pad_size_mm=10))
        broken=copy.deepcopy(basis);broken['f'][3000]['target'][0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'Nonfinite'):c4.validate_basis(broken,dict(cells=1,pad_size_mm=10))

    def test_high_direction_selection_and_nominal_rank_crossings_are_separate(self):
        rows=[]
        for wave in c4.old.WAVES:
            for family in ('1plus3','2plus2','3plus1'):
                for i,value in enumerate((10.,9.95,9.7)):
                    rows.append(dict(id=wave+family+str(i),waveform=wave,allocation_family=family,
                        metrics_SI={'target20_modulation_V_m':value},
                        direction_sensitivity={'512':value-1,'8218':10.2 if i==1 else value}))
        selected=c4.selected_high_rows(rows)
        self.assertEqual(len(selected),18)
        self.assertTrue(all(not rid.endswith('2') for rid in selected))
        self.assertTrue(c4.rank_crossings(rows))
        self.assertEqual(rows[0]['metrics_SI']['target20_modulation_V_m'],10.)

    def test_hash_stage_and_started_run_guards_without_any_numerics(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name);source=path/'source';source.write_bytes(b'pinned')
            c4.verify_hashes({str(source):hashlib.sha256(b'pinned').hexdigest()})
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Pinned input'):c4.verify_hashes({str(source):hashlib.sha256(b'pinned').hexdigest()})
            (path/'reproduction').mkdir()
            for ident in c4.CASE_IDS:
                c4.old.atomic(path/'reproduction'/(ident+'.json'),dict(status='passed',case_id=ident,original_rows=108,
                    checks=[{'status':'passed'}]*108))
            self.assertEqual(len(c4.require_all_controls(path)),3)
            record=c4.read(path/'reproduction'/('03740.json'));record['status']='failed'
            c4.old.atomic(path/'reproduction'/'03740.json',record)
            with self.assertRaisesRegex(ValueError,'All324'):c4.require_all_controls(path)
            (path/'controller.json').write_text('{"status":"failed"}')
            from contextlib import nullcontext
            with patch.object(c4,'validate_execution',return_value=({},{})),patch.object(c4,'execution_lock',return_value=nullcontext()):
                with self.assertRaisesRegex(ValueError,'no retry'):c4.execute(path)


    def test_relative_parent_cli_and_pinned_baseline_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)
            argv=['python','-u','tis-java/c4_phase_allocation.py','--output',str(output),'--execute']
            self.assertTrue(c4.parent_command_matches(argv,c4.ROOT.parent,output))
            self.assertFalse(c4.parent_command_matches(argv,c4.ROOT.parent,output/'other'))
            self.assertFalse(c4.parent_command_matches(argv+['--worker'],c4.ROOT.parent,output))
            (output/'reproduction').mkdir()
            for ident in c4.CASE_IDS:
                c4.old.atomic(output/'reproduction'/(ident+'.json'),dict(status='passed',case_id=ident,
                    original_rows=108,checks=[{'status':'passed'}]*108))
            with self.assertRaisesRegex(ValueError,'Pinned all324'):c4.require_all_controls(output,require_pin=True)
            c4.old.atomic(output/'all-controls-verification.json',dict(status='passed',original_rows=324,
                per_case_receipt_file_sha256={ident:c4.sha(output/'reproduction'/(ident+'.json')) for ident in c4.CASE_IDS}))
            self.assertEqual(len(c4.require_all_controls(output,require_pin=True)),3)
            p=output/'reproduction'/'03740.json';p.write_text(p.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'receipt changed'):c4.require_all_controls(output,require_pin=True)
            (output/'STOP').touch()
            with self.assertRaises(c4.RequestedStop):c4.check_stop(output)

    def test_cumulative_two_stage_budget_cannot_reset_per_basis(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)
            for name in ('logs','reproduction','cases','derived-target'):(output/name).mkdir()
            spec=dict(case_plan=[{'case_id':ident} for ident in c4.CASE_IDS],input_file_sha256={},holds=[])
            observed=[]
            def guarded(command,log,**limits):
                stage,ident=command[-2:];observed.append((stage,ident,limits['timeout_s']))
                if stage=='reproduce':
                    c4.old.atomic(output/'reproduction'/(ident+'.json'),dict(status='passed',case_id=ident,
                        original_rows=108,checks=[{'status':'passed'}]*108))
                return dict(status='complete',wall_seconds=400 if stage=='reproduce' else 250,peak_rss_bytes=1)
            with patch.object(c4,'validate_execution',return_value=(spec,{'code_file_sha256':{}})), \
                 patch.object(c4,'execution_lock',return_value=nullcontext()), \
                 patch.object(c4.resources,'run_guarded',side_effect=guarded):
                with self.assertRaisesRegex(RuntimeError,'Cumulative basis600'):c4.execute(output)
            self.assertEqual([x[2] for x in observed],[600,600,600,200])
            failed=c4.read(output/'failure.json')
            self.assertEqual(failed['case_elapsed_seconds']['03739'],650)
            self.assertEqual(failed['original_controls_passed'],324)
            self.assertEqual(failed['new_grid_slots_complete'],0)
            self.assertTrue(failed['failed_partial_outputs_preserved'])
            self.assertEqual(failed['new_PDE'],0)


    def test_waveform_peak_normalization_and_source_load_distinction(self):
        theta=np.linspace(0,2*np.pi,65537)
        for wave,(fund,third) in c4.old.WAVES.items():
            source=.5*(fund*np.sin(theta)+third*np.sin(3*theta))
            with self.subTest(wave=wave):
                self.assertAlmostEqual(source.max(),.5,delta=1e-12)
                self.assertAlmostEqual(source.min(),-.5,delta=1e-12)
                self.assertAlmostEqual(source.max()-source.min(),1.,delta=1e-12)
        basis,_,_,boundaries=fixture()
        result=c4.evaluate(basis,boundaries,'sine',[0,0,1,1],[0]*4)
        source_RMS=.5/np.sqrt(2)
        self.assertNotAlmostEqual(result['source_load_voltage_RMS_by_output_V'][0],source_RMS)


if __name__=='__main__': unittest.main()
