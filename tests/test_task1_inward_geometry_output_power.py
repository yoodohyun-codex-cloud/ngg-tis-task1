"""Synthetic inward JSON-provenance contracts; no files, native data or runs."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


class InwardGeometryOutputPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('inward_output_power_tested',ROOT/'tools/task1_inward_geometry_output_power.py')
        cls.tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.tool)

    def volume(self):
        return dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',inputs_unchanged=True,
            selected_for_adoption=[],cases=[dict(case_id=case_id,run_id=run_id,adopted=False,
                calculation_status='cached_native_scalar_audit_complete',baseline_summary=str(self.tool.CANONICAL),
                normalizations={mode:{} for mode in self.tool.MODES})for case_id,run_id in zip(self.tool.IDS,self.tool.RUNS)])

    def source(self):
        identifier=self.tool.IDS[2];path=Path('/synthetic/data-native/run/postprocess')/identifier/'summary.json'
        circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,source_resistance_ohm=50,source_peak_V=.5,
            pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'})
        case=dict(id=identifier,config_file='/synthetic/missing-configuration.properties',config_sha256='b'*64,
            mask_sha256='c'*64,circuit=copy.deepcopy(circuit))
        row=dict(case_id=identifier,summary_path=str(path),configuration_sha256='b'*64,circuit=copy.deepcopy(circuit))
        post=dict(id=identifier,status='complete',source_inputs_unchanged=True,mesh_metadata=dict(config_sha256='b'*64),
            input_sha256={case['config_file']:'b'*64})
        pre=dict(source_commit='a'*40,cases=[case],gates=copy.deepcopy(self.tool.core.GATES))
        record=dict(id=identifier,status='complete',postprocess_path=str(path),postprocess_sha256='d'*64,config_sha256='b'*64,
            validation={key:limit for key,limit in self.tool.core.GATES.items()})
        return row,post,pre,record,path,'d'*64

    def test_only_exact_ordered_three_completed_inward_cohorts_and_canonical_baseline_are_accepted(self):
        volume=self.volume();before=copy.deepcopy(volume)
        self.assertEqual(self.tool.IDS,('baseline-square15-xy80','perimeter-shell225-notch-xy80','perimeter-shell225-inward0p625-xy80'))
        self.assertIs(self.tool.validate_volume(volume),volume['cases']);self.assertEqual(volume,before)
        for mutation in('status','changed','adoption','reverse','missing','wrongrun','wrongbaseline','wrongmodes','adoptedrow'):
            bad=self.volume()
            if mutation=='status':bad['status']='running'
            elif mutation=='changed':bad['inputs_unchanged']=False
            elif mutation=='adoption':bad['selected_for_adoption']=[self.tool.IDS[2]]
            elif mutation=='reverse':bad['cases'].reverse()
            elif mutation=='missing':bad['cases'].pop()
            elif mutation=='wrongrun':bad['cases'][2]['run_id']='another-run'
            elif mutation=='wrongbaseline':bad['cases'][2]['baseline_summary']='/other/baseline.json'
            elif mutation=='wrongmodes':bad['cases'][2]['normalizations'].pop('equal_total_power')
            else:bad['cases'][2]['adopted']=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.tool.validate_volume(bad)

    def test_json_source_receipts_require_matching_sha_path_status_config_and_native_gates(self):
        valid=self.source();before=copy.deepcopy(valid)
        self.assertIs(self.tool.validate_source_binding(*valid),valid[2]['cases'][0]);self.assertEqual(valid,before)
        for mutation in('summarysha','recordpath','rowpath','failed','changed','postconfig','caseconfig','configmanifest','duplicatecase','prelimits','residual'):
            args=list(copy.deepcopy(valid));row,post,pre,record=args[:4]
            if mutation=='summarysha':record['postprocess_sha256']='e'*64
            elif mutation=='recordpath':record['postprocess_path']='/other/summary.json'
            elif mutation=='rowpath':row['summary_path']='/other/summary.json'
            elif mutation=='failed':record['status']='error'
            elif mutation=='changed':post['source_inputs_unchanged']=False
            elif mutation=='postconfig':post['mesh_metadata']['config_sha256']='e'*64
            elif mutation=='caseconfig':pre['cases'][0]['config_sha256']='e'*64
            elif mutation=='configmanifest':post['input_sha256'].clear()
            elif mutation=='duplicatecase':pre['cases'].append(copy.deepcopy(pre['cases'][0]))
            elif mutation=='prelimits':pre['gates']['max_power_error']*=2
            else:record['validation']['max_current_error']*=1.01
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.tool.validate_source_binding(*args)

    def test_four_pad_two_output_ground_topology_and_declared_mask_hash_preserve_json_only_scope(self):
        valid=self.source()
        with patch.object(Path,'read_bytes',side_effect=AssertionError('No configuration/mask read')),\
             patch.object(Path,'read_text',side_effect=AssertionError('No configuration/mask read')):
            self.tool.validate_source_binding(*valid)
        self.assertIs(self.tool.audit_condition,self.tool.frozen.audit_condition)
        self.assertIs(self.tool.validate_square_condition,self.tool.frozen.validate_square_condition)
        for mutation in('pads','outputs','ground','resistance','peak','mapping','mask'):
            args=list(copy.deepcopy(valid));row,_,pre,_=args[:4];case=pre['cases'][0]
            if mutation=='mask':case['mask_sha256']='short'
            else:
                key,value={'pads':('n_pads',8),'outputs':('n_outputs',4),'ground':('n_return_nodes',2),
                    'resistance':('source_resistance_ohm',0),'peak':('source_peak_V',1.),
                    'mapping':('pad_to_node',{'0':'out0','1':'out1','2':'out2','3':'GND'})}[mutation]
                case['circuit'][key]=value;row['circuit'][key]=value
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.tool.validate_source_binding(*args)


if __name__=='__main__':unittest.main()
