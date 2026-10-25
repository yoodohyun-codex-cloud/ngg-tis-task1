"""Synthetic grouped fine-map proof checks; no native data or rendering."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
SPEC = importlib.util.spec_from_file_location('grouped_fine_maps_tested', ROOT/'tools/task1_grouped_fine_volume_maps.py')
MAPS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAPS)


def circuit(n):
    m=n//4
    return dict(n_pads=n,n_outputs=2,n_return_nodes=1,return_topology='all_return_pads_ideal_common_GND',
        source_resistance_ohm=50,source_peak_V=.5,source_Vpp_each=1,carrier_assignment_Hz=[3000,3030],
        inactive_source_at_other_frequencies='0 V through 50 ohm',harmonics_Hz=[9000,9090],
        pad_to_node={str(i):'out0' if i<m else 'out1' if i<2*m else 'GND' for i in range(n)})


class GroupedFineVolumeMapsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.limits={key:float(i+1) for i,key in enumerate(sorted(MAPS.base.CAPS))}
        self.cutoffs={'maxTIS':{'mean':3.,'p10':2.}}
        self.rows=[];self.posts=[];self.records=[]
        for index,(identifier,n) in enumerate(zip(MAPS.IDS,(4,*MAPS.COUNTS))):
            run=MAPS.BASELINE_RUN if index==0 else MAPS.GROUPED_RUN
            source=self.root/run/'postprocess'/identifier/'summary.json'
            mesh=dict(h_xy_mm=.625,sc_cells=2,bulk_layer_counts=[14,14,40],cells=351680,
                radius_mm=25,total_depth_mm=25.1,frequencies_Hz=[3000,3030,9000,9090],
                n_pads=n,n_outputs=2,channels=2,n_return_nodes=1,return_topology='common_GND',
                z_faces_mm=[0.,.1,5.1,10.1,25.1],tissue_boundaries_mm=[0.,.1,5.1,10.1,25.1],config_sha256='b'*64)
            scale=1. if index==0 else 1.+index/10
            condition=dict(id=identifier+'-square_3h',waveform='square_3h',actual_fundamental_Hz=[3000,3030],
                source_Vpp_per_output=1,native_volume_archive='volume.npz')
            row=dict(case_id=identifier,run_id=run,summary_path=str(source),condition_id=condition['id'],
                mesh=mesh,circuit=circuit(n),baseline_summary=str(self.root/MAPS.BASELINE_RUN/'postprocess'/MAPS.BASELINE/'summary.json'),
                fixed_same_grid_baseline_cutoffs_V_m=copy.deepcopy(self.cutoffs),
                adopted=False,calculation_status='cached_native_scalar_audit_complete',source_commit='a'*40,
                configuration_sha256='b'*64,normalizations={
                    'raw_1Vpp':dict(amplitude_scale=1,source_Vpp_per_output=1),
                    'skin_contact_only':dict(amplitude_scale=scale,source_Vpp_per_output=scale,
                        includes_source_power_cap=False,includes_1Vpp_ceiling=False,
                        baseline_derived_numerical_limits=copy.deepcopy(self.limits))})
            self.rows.append(row)
            self.posts.append(dict(status='complete',id=identifier,conditions=[condition]))
            self.records.append(dict(status='complete',id=identifier,postprocess_path=str(source),config_sha256='b'*64))
        self.payload=dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',inputs_unchanged=True,
            new_PDE_solves=0,selected_for_adoption=[],cases=self.rows)

    def validate(self,index=1,row=None,post=None,record=None,original=None,n=None):
        return MAPS.validate_case(self.rows[index] if row is None else row,
            self.posts[index] if post is None else post,self.records[index] if record is None else record,
            self.rows[0] if original is None else original,(4,*MAPS.COUNTS)[index] if n is None else n)

    def test_all_physical_pad_counts_retain_two_outputs_and_common_return(self):
        for n in MAPS.COUNTS:
            counts=MAPS.validate_circuit(circuit(n),n)
            self.assertEqual(counts['physical_pads'],n)
            self.assertEqual(counts['independent_outputs'],2)
            self.assertEqual(counts['pads_on_out0'],n//4)
            self.assertEqual(counts['pads_on_out1'],n//4)
            self.assertEqual(counts['common_GND_return_pads'],n//2)
            self.assertEqual(counts['independent_return_nodes'],1)

    def test_circuit_rejects_more_sources_wrong_termination_and_frequency(self):
        for key,value in (('n_outputs',8),('n_return_nodes',2),('source_resistance_ohm',0),
                ('inactive_source_at_other_frequencies','floating'),('carrier_assignment_Hz',[2000,2010]),
                ('harmonics_Hz',[6000,6030]),('source_peak_V',1.),('source_Vpp_each',2.)):
            bad=circuit(8);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):MAPS.validate_circuit(bad,8)
        bad=circuit(8);bad['pad_to_node']['7']='out1'
        with self.assertRaises(ValueError):MAPS.validate_circuit(bad,8)
        with self.assertRaises(ValueError):MAPS.validate_circuit(circuit(4),6)

    def test_terminal_report_requires_exact_order_and_returns_saved_rows(self):
        self.assertIs(MAPS.terminal_report(self.payload),self.rows)
        for change in ('reversed','missing','duplicate'):
            bad=copy.deepcopy(self.payload)
            if change=='reversed':bad['cases'].reverse()
            elif change=='missing':bad['cases'].pop()
            else:bad['cases'][-1]=copy.deepcopy(bad['cases'][-2])
            with self.subTest(change=change),self.assertRaises(ValueError):MAPS.terminal_report(bad)

    def test_terminal_report_rejects_live_failed_mutated_or_adopted_state(self):
        for key,value in (('schema','other'),('status','running'),('inputs_unchanged',False),
                ('new_PDE_solves',1),('selected_for_adoption',['candidate'])):
            bad=copy.deepcopy(self.payload);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):MAPS.terminal_report(bad)
        for key,value in (('adopted',True),('calculation_status','failed')):
            bad=copy.deepcopy(self.payload);bad['cases'][2][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):MAPS.terminal_report(bad)

    def test_validate_case_all_five_uses_exact_saved_square_and_scale(self):
        for index in range(5):
            before=copy.deepcopy(self.rows[index]);condition,scale=self.validate(index)
            self.assertIs(condition,self.posts[index]['conditions'][0])
            self.assertEqual(scale,self.rows[index]['normalizations']['skin_contact_only']['amplitude_scale'])
            self.assertEqual(self.rows[index],before)

    def test_validate_case_rejects_coarse_or_sc4_mesh(self):
        for key,value in (('h_xy_mm',1.25),('sc_cells',4),('bulk_layer_counts',[18,18,56]),
                ('cells',88480),('radius_mm',30),('total_depth_mm',30),('frequencies_Hz',[3000,3030])):
            row=copy.deepcopy(self.rows[1]);row['mesh'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(row=row)

    def test_validate_case_rejects_wrong_baseline_or_changed_cutoff(self):
        for key,value in (('run_id','coarse-run'),('baseline_summary','/other/baseline.json'),
                ('fixed_same_grid_baseline_cutoffs_V_m',{'different':1})):
            row=copy.deepcopy(self.rows[1]);row[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(row=row)

    def test_validate_case_rejects_incomplete_or_mismatched_receipt(self):
        for key,value in (('status','error'),('id','wrong'),('postprocess_path','/other/summary.json')):
            record=copy.deepcopy(self.records[1]);record[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(record=record)
        for key,value in (('status','running'),('id','wrong')):
            post=copy.deepcopy(self.posts[1]);post[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(post=post)

    def test_validate_case_rejects_config_or_tissue_boundary_identity_changes(self):
        row=copy.deepcopy(self.rows[1]);row['mesh']['config_sha256']='c'*64
        with self.assertRaises(ValueError):self.validate(row=row)
        record=copy.deepcopy(self.records[1]);record['config_sha256']='c'*64
        with self.assertRaises(ValueError):self.validate(record=record)
        row=copy.deepcopy(self.rows[1]);row['configuration_sha256']='c'*64
        with self.assertRaises(ValueError):self.validate(row=row)
        row=copy.deepcopy(self.rows[1]);row['mesh']['tissue_boundaries_mm']=[0.,.2,5.2,10.2,25.2]
        with self.assertRaises(ValueError):self.validate(row=row)

    def test_validate_case_rejects_non_square_archive_alias_and_drive(self):
        for key,value in (('waveform','sine'),('actual_fundamental_Hz',[9000,9090]),
                ('native_volume_archive','other.npz'),('source_Vpp_per_output',.5)):
            post=copy.deepcopy(self.posts[1]);post['conditions'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(post=post)
        for conditions in ([],[copy.deepcopy(self.posts[1]['conditions'][0])]*2):
            post=copy.deepcopy(self.posts[1]);post['conditions']=conditions
            with self.assertRaises(ValueError):self.validate(post=post)

    def test_validate_case_rejects_grouped_outputs_or_topology_metadata(self):
        for key,value in (('n_pads',16),('n_outputs',4),('channels',4),('n_return_nodes',2),('return_topology','isolated')):
            row=copy.deepcopy(self.rows[1]);row['mesh'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(row=row)

    def test_validate_case_uses_saved_eight_skin_caps_without_power_or_ceiling(self):
        for key,value in (('includes_source_power_cap',True),('includes_1Vpp_ceiling',True),
                ('baseline_derived_numerical_limits',dict(self.limits,SC_power_W=1e99))):
            row=copy.deepcopy(self.rows[1]);row['normalizations']['skin_contact_only'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(row=row)
        row=copy.deepcopy(self.rows[1]);row['normalizations']['raw_1Vpp']['amplitude_scale']=.5
        with self.assertRaises(ValueError):self.validate(row=row)
        for value in (0.,-1.,float('nan'),float('inf')):
            row=copy.deepcopy(self.rows[1]);row['normalizations']['skin_contact_only']['amplitude_scale']=value
            with self.subTest(scale=value),self.assertRaises(ValueError):self.validate(row=row)
        row=copy.deepcopy(self.rows[1]);row['normalizations']['skin_contact_only']['source_Vpp_per_output']=1.
        with self.assertRaises(ValueError):self.validate(row=row)

    def test_loader_requires_report_bound_source_sha_before_scalar_or_grid_read(self):
        self.payload['inputs_sha256']={}
        with patch.object(MAPS.base,'bound_json',return_value=self.payload),\
             patch.object(MAPS.base,'load_scalars',side_effect=AssertionError('must not read NPZ')),\
             patch.object(MAPS.np,'loadtxt',side_effect=AssertionError('must not read grid')):
            with self.assertRaisesRegex(ValueError,'source summary SHA'):
                MAPS.load_model(self.root/'audit.json')

    def test_loader_rejects_receipt_postprocess_sha_before_native_reads(self):
        self.payload['inputs_sha256']={row['summary_path']:'d'*64 for row in self.rows}
        record=copy.deepcopy(self.records[0]);record['postprocess_sha256']='e'*64
        def bound(path,pins,expected=None):
            if Path(path).name=='audit.json':return self.payload
            if 'postprocess' in Path(path).parts:
                pins[str(Path(path).resolve())]='d'*64;return self.posts[0]
            return record
        with patch.object(MAPS.base,'bound_json',side_effect=bound),\
             patch.object(MAPS.base,'load_scalars',side_effect=AssertionError('must not read NPZ')),\
             patch.object(MAPS.np,'loadtxt',side_effect=AssertionError('must not read grid')):
            with self.assertRaisesRegex(ValueError,'receipt'):
                MAPS.load_model(self.root/'audit.json')


if __name__=='__main__':unittest.main()
