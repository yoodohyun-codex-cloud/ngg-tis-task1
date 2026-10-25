"""Metadata-only grouped audit fixtures; no native arrays are decoded."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
import task1_grouped_fine_volume_registration as reg
import task1_grouped_geometry as geometry
import test_task1_return_position_volume_registration as fixtures


class GroupedFineVolumeRegistrationTest(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.ReturnPositionVolumeRegistrationTest(methodName='runTest');fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.fixture=fixture;self.root=fixture.root
        self.output=self.root/'docs/grouped-fine-plan.json';self.write=fixture.write
        for run,ident in reg.CASE_TABLE[1:]:fixture.case_fixture(run,ident)
        self.contracts={}
        common=dict(radius_mm=25.,total_depth_mm=25.1,tissue_boundaries_mm=[0.,.1,5.1,10.1,25.1],
            source_peak_V=.5,source_resistance_ohm=50.,
            field_reconstruction='half_face_flux; top contact term averaged over full cell face h^2')
        for run,ident in reg.CASE_TABLE:
            runpath=self.root/'data-native'/run;prepath=runpath/'preregistration.json'
            pre=json.loads(prepath.read_text());case=next(c for c in pre['cases']if c['id']==ident)
            meta_path=runpath/'bases'/ident/'mesh-metadata.json';meta=json.loads(meta_path.read_text());meta.update(common)
            if (run,ident)!=reg.CASE_TABLE[0]:
                n=reg.COUNTS[list(reg.CASE_IDS).index(ident)];m=n//4;pads=geometry.rectangles(n)
                nodes=[0]*m+[1]*m+[-1]*(2*m)
                circuit=dict(n_pads=n,n_outputs=2,n_return_nodes=1,
                    n_signal_pads=n//2,n_return_pads=n//2,
                    pad_to_node={str(i):'GND'if node<0 else f'out{node}'for i,node in enumerate(nodes)},
                    source_peak_V=.5,source_Vpp_each=1.,source_resistance_ohm=50.,
                    carrier_assignment_Hz=[3000,3030],harmonics_Hz=[9000,9090],source_phase_deg=[0.,0.],
                    return_topology='all_return_pads_ideal_common_GND',exclusive_source_return_pair_assumed=False,
                    inactive_source_at_other_frequencies='0 V through50 ohm')
                case.update(n_pads=n,n_outputs=2,n_return_nodes=1,channels=2,
                    exporter_class='GroupedPadBasis',java_class='GroupedPadBasis',postprocessor='grouped',
                    area_mode='equal_total_area_900mm2',source_coating_nm=10,source_Rs_fit_window_Hz=500,
                    frequencies_Hz=[3000,3030,9000,9090],pad_node_ids=nodes,pads=pads,
                    expected_pad_areas_m2=[900/n*1e-6]*n,
                    control='new_four_rectangle_geometry_control'if n==4 else'physical_strip_count',circuit=circuit)
                cfg=dict(geometry.read_properties(Path(case['config_file'])),channels='2',n_outputs='2',n_pads=str(n),
                    n_return_nodes='1',return_topology='common_GND',frequencies='3000,3030,9000,9090',
                    h_mm='0.625',**{'validation.sc_cells':'2','bulk.counts':'14,14,40',
                    'mask.sha256':case['mask_sha256']})
                cfg.update({f'pad.node.{i}':str(node)for i,node in enumerate(nodes)})
                cfg.update({f'pad.{i}.represented_area_m2':format(900/n*1e-6,'.17g')for i in range(n)})
                for pad in pads:
                    i=pad['pad_id']
                    cfg[f'pad.{i}.shape']=pad['shape']
                    for key in ('width_mm','height_mm','rotation_deg','x_mm','y_mm'):
                        cfg[f'pad.{i}.{key}']=str(pad[key])
                    cfg[f'pad.{i}.analytic_area_mm2']=str(pad['area_mm2'])
                config=Path(case['config_file']);config.write_text(''.join(k+'='+v+'\n'for k,v in cfg.items()))
                case['config_sha256']=reg.sha(config)
                meta.update(exporter_class='GroupedPadBasis',exporter_kind='grouped_native',
                    numerical_base_class='SelectivityShapeBasis',n_pads=n,n_outputs=2,channels=2,
                    n_return_nodes=1,return_topology='common_GND',pad_node_ids=nodes,
                    frequencies_Hz=[3000,3030,9000,9090],config_sha256=case['config_sha256'])
                self.contracts[n]=(copy.deepcopy(case),copy.deepcopy(meta),dict(cfg))
            self.write(meta_path,meta)
            self.write(prepath,pre)
            summary_path=runpath/'postprocess'/ident/'summary.json';summary=json.loads(summary_path.read_text())
            summary['mesh_metadata']=meta;summary['input_sha256'][str(meta_path)]=reg.sha(meta_path)
            self.write(summary_path,summary)
            receipt_path=runpath/'cases'/(ident+'.json');receipt=json.loads(receipt_path.read_text())
            receipt.update(config_sha256=case['config_sha256'],postprocess_sha256=reg.sha(summary_path));self.write(receipt_path,receipt)
        # Shared four-case preregistration changes must update every source-bound audit.
        for run in {run for run,_ in reg.CASE_TABLE}:
            runpath=self.root/'data-native'/run;prepath=runpath/'preregistration.json';pre=json.loads(prepath.read_text())
            for audit in (runpath/'audit').glob('*.json'):
                obj=json.loads(audit.read_text());case=next(c for c in pre['cases']if c['id']==obj['case_id'])
                summary_path=runpath/'postprocess'/case['id']/'summary.json'
                obj.update(registration_sha256=reg.sha(prepath),config_sha256=case['config_sha256'],summary_sha256=reg.sha(summary_path))
                self.write(audit,obj)

    def generate(self):
        with (mock.patch.object(reg,'_committed_sources',return_value=('implementation-commit',{})),
              mock.patch.object(reg.inherited.policy,'load_ledger',return_value=self.fixture.expanded),
              mock.patch.object(reg.inherited.policy,'effective_limit',return_value=13800),
              mock.patch.object(reg.inherited.policy,'remaining_seconds',return_value=7800),
              mock.patch.object(reg.inherited.policy,'policy_refs',return_value={})):
            return reg.make_preregistration(self.output,root=self.root)

    def test_five_rows_have_one_original_baseline_and_never_read_array_bytes(self):
        original=Path.read_bytes
        def guarded(path):
            if path.name=='volume.npz'or path.name.startswith(('grid.','field-','potential-','density-','contacts-','source-','loss-')):
                raise AssertionError('Grouped metadata registration attempted native array byte read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):plan=self.generate()
        self.assertEqual(5,plan['initial_case_count'])
        self.assertEqual([ident for _,ident in reg.CASE_TABLE],[case['case_id']for case in plan['cases']])
        self.assertEqual([4,4,8,12,16],[case['n_pads']for case in plan['cases']])
        self.assertEqual([2]*5,[case['n_outputs']for case in plan['cases']])
        self.assertEqual([plan['cases'][0]['summary']],plan['baseline_summary_paths'])
        self.assertEqual('baseline-square15-xy80',plan['baseline_case_id'])
        self.assertFalse(plan['metadata_registration_scope']['volume_NPZ_decode_or_byte_read'])
        self.assertTrue(all(c['baseline_case_id']==plan['baseline_case_id']for c in plan['cases']))

    def test_each_grouped_contract_accepts_exact_two_output_parent_groups(self):
        for n,(case,meta,config)in self.contracts.items():
            reg._validate_grouped_contract(case,meta,config,n)

    def test_wrong_outputs_common_ground_mapping_frequency_or_exporter_are_rejected(self):
        for field,value in (('n_outputs',8),('n_pads',16),('source_Rs_fit_window_Hz',2000),
                            ('frequencies_Hz',[2000,2010,6000,6030]),('exporter_class','SelectivityShapeBasis')):
            case,meta,config=copy.deepcopy(self.contracts[8]);case[field]=value
            with self.assertRaises(ValueError):reg._validate_grouped_contract(case,meta,config,8)
        for target,key,value in (('meta','return_topology','isolated_returns'),('meta','n_outputs',8),
                                 ('config','pad.node.0','-1'),('config','n_outputs','8')):
            case,meta,config=copy.deepcopy(self.contracts[8]);(meta if target=='meta'else config)[key]=value
            with self.assertRaises(ValueError):reg._validate_grouped_contract(case,meta,config,8)
        case,meta,config=copy.deepcopy(self.contracts[8]);case['circuit']['pad_to_node']['0']='GND'
        with self.assertRaises(ValueError):reg._validate_grouped_contract(case,meta,config,8)

    def test_fixed_total_and_each225mm2_parent_group_are_both_enforced(self):
        case,meta,config=copy.deepcopy(self.contracts[8])
        case['expected_pad_areas_m2']=[area*1.01 for area in case['expected_pad_areas_m2']]
        with self.assertRaises(ValueError):reg._validate_grouped_contract(case,meta,config,8)
        case,meta,config=copy.deepcopy(self.contracts[8]);areas=case['expected_pad_areas_m2']
        areas[0]+=1e-6;areas[2]-=1e-6
        self.assertAlmostEqual(.0009,sum(areas))
        with self.assertRaises(ValueError):reg._validate_grouped_contract(case,meta,config,8)
        case,meta,config=copy.deepcopy(self.contracts[8]);case['pads'][0]['x_mm']+=.625
        with self.assertRaises(ValueError):reg._validate_grouped_contract(case,meta,config,8)

    def test_incompatible_grouped_model_signature_cannot_join_original_baseline(self):
        with mock.patch.object(reg,'_signature',return_value='incompatible-contact-model'):
            with self.assertRaisesRegex(ValueError,'same grid/material/contact/ROI'):self.generate()
        self.assertFalse(self.output.exists())

    def test_missing_receipt_full_skin_mask_pin_or_frozen_evidence_blocks_registration(self):
        run,ident=reg.CASE_TABLE[-1];base=self.root/'data-native'/run
        changes=((base/'cases'/(ident+'.json'),None),
                 (base/'audit'/('full-skin-'+ident+'.json'),None),
                 (base/'masks'/(ident+'.csv'),b'changed contact mask\n'),
                 (base/'frozen-source/tools/frozen.py',b'# changed numerical source\n'))
        for path,replacement in changes:
            saved=path.read_bytes()
            try:
                if replacement is None:path.unlink()
                else:path.write_bytes(replacement)
                with self.assertRaises(ValueError):self.generate()
                self.assertFalse(self.output.exists())
            finally:path.write_bytes(saved)


if __name__=='__main__':
    unittest.main()
