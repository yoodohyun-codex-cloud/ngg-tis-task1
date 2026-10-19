"""3k input/failure integration regressions; no Java compile or phantom PDE.

Only synthetic temporary outputs are written. Original preparation, source and
2k results are read-only. Every process-launch API is blocked except an explicit
mock of the already guarded analytic/compiler interface.
"""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import mesh_validation as common
import mesh_validation_3k as validation


PIN = '81a92c5be563cbe47d1bfd57768ec5e069454549e331867046efd062773d7833'
ORDERED_CONFIGS = (
    ('baseline-reference','8f2d861323fac74366ce3c0aa56ae8f5f8138e92ba4acb2453c56c12fcc9f23a'),
    ('baseline-leader','96c0e2f2f3daf699ca18d6e3a50b8fdf5c6f61e50fbec11f0b1affe1e6da2534'),
    ('sc4-reference','2b05326ca3b5698bcd0959967fd1bcdb67492a6f518b5cff6e614c975665e63a'),
    ('sc4-leader','3ba420b9b350edecb67cee8205ed2c69248a31e53d241bb49edaba48a043f689'),
    ('sc8-reference','3271fa0bb095b093eba4464a8481adf261958edfec47de9035440f1e94c5e1ce'),
    ('sc8-leader','b0dc51e30e5c5e0b9c8b59fe48811942f051353ac538b2d6c8475fb9477eca79'),
    ('xy100-reference','af1b56c1ff0d815aa2e371257574ea079f48f447aaaf7e2460aaf92c88f9f95f'),
    ('xy100-leader','0e869df2542fc9cc0adb247d93a054ec82cf238a75f6b94f75a97ca38cd5695c'),
    ('xy120-reference','538a7177a98f6dfa2a9dd6600eec78c2a608c060b99c568ebc0d024a7a8d8876'),
    ('xy120-leader','cb40ff029bf7479b517b0fc17d12117ae0747eabec2c1bd019b87aa54b8fbb68'),
)


def raw_metrics():
    values=dict(target20_modulation_V_m=3.94,target20_total_E_RMS_V_m=2.07,
        surface_J_RMS_max_A_m2=21.4,surface_J_RMS_p95_A_m2=12.,
        contact_voltage_RMS_max_V=.032,SC_power_W=1.8e-6,contact_power_W=25e-6,
        source_power_W=.00108,max_source_current_RMS_mA=1.3)
    return [dict(values,waveform=wave,carrier_group=[0,1],phase_deg=[0.,0.],
        carrier_Hz=3000,beat_Hz=30,target20_at_baseline_burden_V_m=999.)
        for wave in common.WAVEFORMS]


class ThreeKTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads(validation.PREPARATION.read_text())
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        for name in ('Popen','run','call','check_call','check_output'):
            self.stack.enter_context(mock.patch.object(validation.subprocess,name,
                side_effect=AssertionError('No subprocess/Java/PDE in3k regression: '+name)))

    def test_original_preparation_and_ten_ordered_config_hashes_are_exact(self):
        self.assertEqual(hashlib.sha256(validation.PREPARATION.read_bytes()).hexdigest(),PIN)
        self.assertEqual(validation.PREPARATION_SHA,PIN)
        original=deepcopy(self.spec)
        plan=validation.validate_spec(self.spec)
        self.assertEqual(tuple((c['id'],c['config_sha256']) for c in plan),ORDERED_CONFIGS)
        self.assertEqual([c['cells'] for c in plan],
                         [351680,351680,361728,361728,381824,381824,550200,550200,791280,791280])
        self.assertEqual(self.spec,original)
        for c in plan:
            self.assertEqual(hashlib.sha256(c['config_text'].encode()).hexdigest(),c['config_sha256'])
            p=common.parse_properties(c['config_text'])
            self.assertEqual(p['frequencies'],'3000,3030,9000,9090')
            self.assertEqual(p['validation.sc_cells'],str(c['sc_cells']))
            self.assertEqual(p['validation.max_cells'],'800000')
            self.assertEqual([c['sc_cells'],14,14,40],c['layer_counts'])

    def test_3k_spec_does_not_mutate_2k_globals_or_accept_in_old_guard(self):
        names=('FREQUENCIES','BASELINE_IDS','DESIGNS','THRESHOLDS','RESOURCE_LIMITS')
        before={n:deepcopy(getattr(common,n)) for n in names}
        for _ in range(2):validation.validate_spec(deepcopy(self.spec))
        with self.assertRaisesRegex(ValueError,'baseline candidates'):
            common.validate_preregistration(deepcopy(self.spec))
        old=json.loads((common.ROOT/'runs/leader-validation-20261017T190056Z/preregistration.json').read_text())
        common.validate_preregistration(old)
        self.assertEqual({n:getattr(common,n) for n in names},before)
        self.assertEqual(common.FREQUENCIES,(2000,2010,6000,6030))
        self.assertEqual(validation.FREQUENCIES,(3000,3030,9000,9090))

    def test_resource_and_per_metric_tolerances_cannot_change(self):
        for section in ('resource_limits','solver_validation_limits','convergence_relative_limits'):
            for key,value in self.spec[section].items():
                if key=='on_limit':continue
                changed=deepcopy(self.spec)
                changed[section][key]=value*1.1 if isinstance(value,(int,float)) else 'changed'
                with self.subTest(section=section,key=key),self.assertRaises(ValueError):
                    validation.validate_spec(changed)
        changed=deepcopy(self.spec);changed['baseline_reproduction_relative_tolerance']=3e-7
        with self.assertRaises(ValueError):validation.validate_spec(changed)

    def test_case_order_mesh_freq_and_bytes_are_not_interchangeable(self):
        mutations=[lambda s:s['case_plan'].reverse(),
            lambda s:s['case_plan'].pop(),
            lambda s:s['case_plan'][0].update(frequencies_Hz=[2000,2010,6000,6030]),
            lambda s:s['case_plan'][0].update(config_sha256='0'*64),
            lambda s:s['case_plan'][1].update(config_sha256=s['case_plan'][0]['config_sha256']),
            lambda s:s['case_plan'][0].update(cells=351681),
            lambda s:s['case_plan'][6].update(h_xy_mm=.625),
            lambda s:s['mesh_plan'].update(bulk_z_counts=[17,17,50]),
            lambda s:s['source_conditions'].update(carrier_Hz=[2000,2010]),
            lambda s:s['baseline_cases'].update(leader='03522-1')]
        for mutate in mutations:
            changed=deepcopy(self.spec);mutate(changed)
            with self.subTest(mutation=mutations.index(mutate)),self.assertRaises(ValueError):
                validation.validate_spec(changed)

    def test_material_source_contact_and_waveform_changes_are_rejected(self):
        paths=[('source_conditions','materials_SI','sc.sigma'),
               ('source_conditions','source_R_ohm'),('source_conditions','source_Vpp_each_output'),
               ('source_conditions','phase_deg'),('source_conditions','phasor'),
               ('source_conditions','boundary_mode'),('source_conditions','coating_nm'),
               ('designs','leader','size_mm'),('waveform_comparisons','coefficient_by_waveform','square_3h','third_harmonic')]
        for path in paths:
            changed=deepcopy(self.spec);target=changed
            for key in path[:-1]:target=target[key]
            old=target[path[-1]]
            target[path[-1]]=(old*1.1 if old else 1) if isinstance(old,(int,float)) else [0,90] if isinstance(old,list) else 'changed'
            with self.subTest(path=path),self.assertRaises(ValueError):validation.validate_spec(changed)
        changed=deepcopy(self.spec)
        c=changed['case_plan'][0]
        c['config_text']=c['config_text'].replace('sc.sigma=0.0002','sc.sigma=0.0003')
        c['config_sha256']=hashlib.sha256(c['config_text'].encode()).hexdigest()
        with self.assertRaises(ValueError):validation.validate_spec(changed)

    @staticmethod
    def completed_xy100_cases():
        numerical={k if k!='max_relative_electrode_area_error' else 'max_area_relative_error':v
                   for k,v in validation.NUMERICAL.items()}
        return [dict(id='xy100-'+geometry,status='complete',postprocess={'status':'complete'},
                     validation=deepcopy(numerical),resources=dict(status='complete',
                         case_wall_seconds=600,peak_rss_bytes=3*validation.GIB))
                for geometry in ('reference','leader')]

    def test_xy120_requires_both_unique_completed_validated_xy100_cases(self):
        cases=self.completed_xy100_cases();original=deepcopy(cases)
        validation.ensure_xy120_dependencies(cases)
        self.assertEqual(cases,original)
        variations=[lambda c:c.pop(),lambda c:c.append(deepcopy(c[0])),
            lambda c:c[0].update(status='running'),
            lambda c:c[1].update(postprocess={'status':'failed'}),
            lambda c:c[1]['resources'].update(status='case_timeout'),
            lambda c:c[0]['resources'].update(case_wall_seconds=600.001),
            lambda c:c[0]['resources'].update(peak_rss_bytes=3*validation.GIB+1)]
        for mutate in variations:
            changed=deepcopy(cases);mutate(changed)
            with self.subTest(variation=variations.index(mutate)),self.assertRaises(ValueError):
                validation.ensure_xy120_dependencies(changed)
        for key,limit in cases[0]['validation'].items():
            for invalid in [limit*1.01,-limit,float('nan'),float('inf')]:
                changed=deepcopy(cases);changed[0]['validation'][key]=invalid
                with self.subTest(metric=key,value=invalid),self.assertRaises(ValueError):
                    validation.ensure_xy120_dependencies(changed)

    def test_prepared_manifest_cannot_change_plan_inputs_actions_or_guard_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,output,manifest,_=self.prepared_fixture(tmp)
            with mock.patch.object(validation,'ROOT',root):
                validation.validate_execution_manifest(manifest)
                variations=[lambda m:m.update(status='preparation_failed'),
                    lambda m:m.update(output_run=str(root/'other/leader-validation-3k-synthetic')),
                    lambda m:m['plan'].reverse(),
                    lambda m:m['plan'][0].update(execution_action='reuse_verified_complete_basis'),
                    lambda m:m['plan'][0].update(config_file='/older/other.properties'),
                    lambda m:m['plan'][1].update(execution_action='new_private_solve'),
                    lambda m:m['plan'][0].update(frequencies_Hz=[2000,2010,6000,6030]),
                    lambda m:m['plan'][0].update(cells=800001),
                    lambda m:m.update(classes='/older/classes'),
                    lambda m:m.update(baseline_basis_dir='/other/cache'),
                    lambda m:m.update(baseline_native_dir='/other/native'),
                    lambda m:m['resource_limits'].update(per_case_wall_seconds=601),
                    lambda m:m['numerical_gates'].update(max_residual=1e-6),
                    lambda m:m['guard_hashes'].pop(str(root/'Validation3kBasis.java'))]
                for mutate in variations:
                    changed=deepcopy(manifest);mutate(changed)
                    with self.subTest(variation=variations.index(mutate)),self.assertRaises(ValueError):
                        validation.validate_execution_manifest(changed)
                # A changed private config is rejected by byte SHA, independently of a same path.
                config=Path(manifest['plan'][0]['config_file']);saved=config.read_bytes()
                config.write_bytes(saved+b'\nchanged.synthetic=1\n')
                with self.assertRaises(ValueError):validation.validate_execution_manifest(manifest)
                config.write_bytes(saved)
                validation.validate_execution_manifest(manifest)

    def test_mesh_metadata_has_actual_independent_z_faces(self):
        for c in self.spec['case_plan']:
            metadata=validation.mesh_metadata(dict(c,config_file='/synthetic/'+c['id']),dict(output_run='/synthetic/newrun',guard_hashes={}))
            self.assertEqual(len(metadata['z_faces_mm']),sum(c['layer_counts'])+1)
            self.assertAlmostEqual(metadata['z_faces_mm'][-1],25.1)
            for z in [0.,.1,5.1,10.1,25.1]:
                self.assertTrue(any(abs(v-z)<1e-10 for v in metadata['z_faces_mm']))
            self.assertEqual(metadata['layer_counts'],c['layer_counts'])
            self.assertEqual(metadata['exporter_kind'],'validation_native')
            self.assertEqual(metadata['config_sha256'],c['config_sha256'])

    def test_command_uses_private_class_and_unchanged_resource_flags(self):
        command=validation.java_command({'java':'/installed/java','classes':'/new/private/classes'})
        self.assertEqual(command,['/installed/java','-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1',
                                  '-cp','/new/private/classes','Validation3kBasis'])
        self.assertNotIn('ValidationBasis',command)

    def test_startticks_matches_actual_current_process_identity(self):
        raw=Path('/proc/self/stat').read_text()
        expected=int(raw[raw.rfind(')')+2:].split()[19])
        self.assertEqual(validation.startticks(os.getpid()),expected)
        self.assertGreater(expected,0)

    def test_only_original_3k_leader_raw_metrics_are_reproduced(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source';(source/'cases').mkdir(parents=True)
            cached=p/'cached';new=p/'new';cached.mkdir();new.mkdir()
            (cached/'grid.csv').write_text('synthetic same grid\n');(new/'grid.csv').write_text('synthetic same grid\n')
            old=raw_metrics()
            # The original2k-normalized fields must not govern a new3k reference.
            for row in old:row['target20_at_baseline_burden_V_m']=1.
            (source/'cases/03542.json').write_text(json.dumps({'candidates':old}))
            manifest=dict(baseline_basis_dir=str(cached),source_run=str(source))
            result=validation.reproduction(raw_metrics(),manifest,new)
            self.assertEqual(result['source_candidate'],'03542-1')
            self.assertEqual(result['status'],'passed')
            self.assertFalse((source/'cases/02342.json').exists())
            changed=raw_metrics();changed[0]['surface_J_RMS_max_A_m2']*=1.01
            with self.assertRaises(ValueError):validation.reproduction(changed,manifest,new)
            (new/'grid.csv').write_text('different grid')
            with self.assertRaisesRegex(ValueError,'grid'):validation.reproduction(raw_metrics(),manifest,new)

    def prepared_fixture(self, tmp):
        root=Path(tmp)/'private-root';root.mkdir()
        (root/'runs').mkdir()
        for name in set(validation.SOURCES+validation.DEPENDENCIES):
            (root/name).write_text('synthetic guard fixture '+name+'\n')
        jdk=root/'jdk';jdk.mkdir()
        for n in ['javac','java']:(jdk/n).write_text('never executed')
        actual_source=Path(self.spec['source_run'])
        profile=Path(self.spec['source_conditions']['EIS']['profile_file'])
        source_case=json.loads((actual_source/'cases/03542.json').read_text())
        baseline=actual_source/'bases'/source_case['candidates'][1]['basis_id']
        native=root/'runs/depth-probe-20261017T200912Z/bases/tis-03542-1'
        output=root/'runs/leader-validation-3k-synthetic'
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(validation,'ROOT',root))
            stack.enter_context(mock.patch.object(validation,'audit_sources',return_value=(actual_source,profile,baseline,native,[])))
            stack.enter_context(mock.patch.object(validation.shutil,'which',return_value=str(jdk/'javac')))
            runner=stack.enter_context(mock.patch.object(common,'run_guarded',return_value={'status':'complete','returncode':0}))
            stack.enter_context(mock.patch.object(common,'diagnostic_lock',return_value=nullcontext()))
            manifest=validation.prepare(output)
        return root,output,manifest,runner

    def test_prepare_only_compiler_and_analytic_commands_are_mocked(self):
        before=deepcopy(common.FREQUENCIES)
        with tempfile.TemporaryDirectory() as tmp:
            root,output,manifest,runner=self.prepared_fixture(tmp)
            self.assertEqual(manifest['status'],'prepared')
            self.assertEqual(len(manifest['plan']),10)
            self.assertEqual(runner.call_count,2)
            calls=[c.args[0] for c in runner.call_args_list]
            self.assertTrue(calls[0][0].endswith('/javac'))
            self.assertEqual(calls[1][-1],'--selftest')
            self.assertFalse(any(str(output/'bases') in ' '.join(c) for c in calls))
            self.assertEqual(manifest['plan'][1]['execution_action'],'reuse_verified_complete_basis')
            self.assertEqual(sum(c['execution_action']=='new_private_solve' for c in manifest['plan']),9)
            self.assertTrue(all(c['id']!='baseline-reference' or c['execution_action']=='new_private_solve' for c in manifest['plan']))
            self.assertEqual(common.FREQUENCIES,before)

    def test_failed_or_partial_execution_is_preserved_without_launch(self):
        for status in ['running','stopped','interrupted','postprocessing_failed']:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as tmp:
                root,output,manifest,_=self.prepared_fixture(tmp)
                saved=json.dumps({'status':status,'synthetic_failure':True})
                (output/'summary.json').write_text(saved)
                with mock.patch.object(validation,'ROOT',root),mock.patch.object(common,'diagnostic_lock',return_value=nullcontext()),mock.patch.object(common,'run_guarded') as run:
                    with self.assertRaisesRegex(ValueError,'Previous execution'):
                        validation.execute(manifest)
                    run.assert_not_called()
                self.assertEqual((output/'summary.json').read_text(),saved)

    def test_complete_execution_is_reused_without_new_solve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,output,manifest,_=self.prepared_fixture(tmp)
            saved={'status':'complete','cases':[],'synthetic_existing_result':True}
            (output/'summary.json').write_text(json.dumps(saved))
            with mock.patch.object(validation,'ROOT',root),mock.patch.object(common,'diagnostic_lock',return_value=nullcontext()),mock.patch.object(common,'run_guarded') as run:
                self.assertEqual(validation.execute(manifest),saved)
                run.assert_not_called()

    def test_postprocessing_failure_keeps_complete_basis_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,output,manifest,_=self.prepared_fixture(tmp)
            folder=output/'bases/baseline-reference'
            def synthetic_guarded_producer(command, *args, **kwargs):
                self.assertEqual(command[-1],str(folder))
                folder.mkdir()
                (folder/'BASIS_COMPLETE').write_text('synthetic-complete\n')
                (folder/'validation.json').write_text(json.dumps({'cells':351680}))
                return dict(status='complete',peak_rss_bytes=1,wall_seconds=.01)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validation,'ROOT',root))
                stack.enter_context(mock.patch.object(common,'diagnostic_lock',return_value=nullcontext()))
                stack.enter_context(mock.patch.object(validation.signal,'signal',return_value=None))
                stack.enter_context(mock.patch.object(validation.signal,'setitimer'))
                stack.enter_context(mock.patch.object(common,'available_disk_bytes',return_value=20*validation.GIB))
                runner=stack.enter_context(mock.patch.object(common,'run_guarded',side_effect=synthetic_guarded_producer))
                stack.enter_context(mock.patch.object(common,'check_numerical_gates',return_value=[.000225]*4))
                stack.enter_context(mock.patch.object(validation,'load_basis',return_value=object()))
                stack.enter_context(mock.patch.object(validation,'summarize',return_value=raw_metrics()))
                stack.enter_context(mock.patch('validation_3k_postprocess.analyze_case',side_effect=RuntimeError('synthetic-postprocess-failure')))
                with self.assertRaisesRegex(RuntimeError,'synthetic-postprocess-failure'):
                    validation.execute(manifest)
                self.assertEqual(runner.call_count,1)
                summary=json.loads((output/'summary.json').read_text())
                self.assertEqual(summary['status'],'postprocessing_failed')
                self.assertEqual(summary['failed_case'],'baseline-reference')
                case=json.loads((output/'cases/baseline-reference.json').read_text())
                self.assertEqual(case['status'],'complete')
                self.assertEqual(case['postprocess']['status'],'failed')
                retained={str(p):p.read_bytes() for p in folder.iterdir()}
                with self.assertRaisesRegex(ValueError,'Previous execution'):
                    validation.execute(manifest)
                self.assertEqual(runner.call_count,1)
                self.assertEqual({str(p):p.read_bytes() for p in folder.iterdir()},retained)

    def test_partial_basis_is_not_overwritten_or_solved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,output,manifest,_=self.prepared_fixture(tmp)
            partial=output/'bases/baseline-reference';partial.mkdir();(partial/'failure.txt').write_text('preserve')
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(validation,'ROOT',root))
                stack.enter_context(mock.patch.object(common,'diagnostic_lock',return_value=nullcontext()))
                stack.enter_context(mock.patch.object(validation.signal,'signal',return_value=None))
                timer=stack.enter_context(mock.patch.object(validation.signal,'setitimer'))
                run=stack.enter_context(mock.patch.object(common,'run_guarded'))
                with self.assertRaisesRegex(ValueError,'Partial basis'):
                    validation.execute(manifest)
                run.assert_not_called()
            self.assertEqual((partial/'failure.txt').read_text(),'preserve')
            summary=json.loads((output/'summary.json').read_text())
            self.assertEqual(summary['status'],'stopped')
            self.assertEqual(summary['failed_case'],'baseline-reference')


if __name__=='__main__':unittest.main()
