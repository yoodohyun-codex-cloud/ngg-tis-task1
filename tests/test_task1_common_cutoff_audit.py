"""Synthetic-only common-threshold tests; no native data or PDE execution."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_common_cutoff_audit as audit
import task1_volume_selectivity as volume


class CommonThresholdTests(unittest.TestCase):
    def test_inclusive_threshold_and_fractional_volume_not_cell_count(self):
        result=audit.summarize([1.,2.,4.],[.1,.2,.7],1.,{'cut':2.},volume)
        self.assertAlmostEqual(result['common_cutoff_volumes']['cut']['volume_m3'],.9)
        self.assertNotAlmostEqual(result['common_cutoff_volumes']['cut']['fraction'],2/3)
        self.assertEqual(result['common_cutoff_volumes']['cut']['comparison'],'>=')

    def test_amplitude_before_classification_threshold_stays_fixed(self):
        cutoffs={'cut':2.}
        raw=audit.summarize([1.,2.,4.],[.1,.2,.7],1.,cutoffs,volume)
        matched=audit.summarize([1.,2.,4.],[.1,.2,.7],.5,cutoffs,volume)
        self.assertAlmostEqual(raw['common_cutoff_volumes']['cut']['volume_m3'],.9)
        self.assertAlmostEqual(matched['common_cutoff_volumes']['cut']['volume_m3'],.7)
        self.assertEqual(matched['common_cutoff_volumes']['cut']['cutoff_V_m'],2.)
        self.assertEqual(cutoffs,{'cut':2.})
        self.assertAlmostEqual(matched['mean'],raw['mean']/2)

    def test_own_model_scale_retained_no_nominal_recalculation(self):
        case=dict(own_model_amplitude_scales=dict(raw_1Vpp=1.,skin_contact_only=.922),own_baseline_summary='Rs2000baseline')
        row=dict(normalizations={'raw_1Vpp':{'amplitude_scale':1.},'skin_contact_only':{'amplitude_scale':.922}},baseline_summary='Rs2000baseline')
        self.assertEqual(audit.own_scales(case,row)['skin_contact_only'],.922)
        row['normalizations']['skin_contact_only']['amplitude_scale']=.921
        with self.assertRaisesRegex(ValueError,'immutable normalization'):
            audit.own_scales(case,row)
        row['normalizations']['skin_contact_only']['amplitude_scale']=.922
        row['baseline_summary']='nominal500baseline'
        with self.assertRaisesRegex(ValueError,'Cross-model normalization'):
            audit.own_scales(case,row)

    def test_same_grid_and_six_roi_weights_exact_guard(self):
        data=dict(grid=np.array([(1.,2.)],dtype=[('x','<f8'),('y','<f8')]),
            regions={name:np.array([.5],dtype='<f8') for name in audit.REGIONS})
        reference=audit.require_same_geometry(None,data)
        self.assertIs(audit.require_same_geometry(reference,data),reference)
        data['regions'][audit.REGIONS[-1]][0]+=.0000000001
        with self.assertRaisesRegex(ValueError,'fractional ROI weights differ'):
            audit.require_same_geometry(reference,data)
        data['regions'][audit.REGIONS[-1]][0]=.5
        data['grid']['x'][0]=1.1
        with self.assertRaisesRegex(ValueError,'source grids'):
            audit.require_same_geometry(reference,data)

    def test_zero_weight_high_value_does_not_set_maximum(self):
        result=audit.summarize([999.,2.,4.],[0.,.25,.75],1.,{'cut':4.},volume)
        self.assertEqual(result['maximum'],4.)
        self.assertEqual(result['common_cutoff_volumes']['cut']['volume_m3'],.75)


class PreregistrationTests(unittest.TestCase):
    def fixture(self, root):
        paths=[]
        cutoff={region+'_'+stat:float(i+1) for i,(region,stat) in enumerate(
            (r,s) for r in audit.REGIONS[1:3] for s in ('mean','p10'))}
        for model in range(2):
            rows=[];pins={}
            for index,ident in enumerate(audit.CASE_IDS[model*2:model*2+2]):
                path=root/ident/'summary.json';path.parent.mkdir()
                value=dict(id=ident,status='complete',artifacts={'files':{'volume.npz':{'SHA256':str(model+1)*64}}})
                path.write_text(json.dumps(value));archive=path.parent/'volume.npz'
                # No archive exists: make_preregistration must read only manifests.
                pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
                pins[str(archive)]=str(model+1)*64
                rows.append(dict(case_id=ident,summary_path=str(path),baseline_summary=str(root/audit.CASE_IDS[model*2]/'summary.json'),
                    comparison_signature=str(model),fixed_same_grid_baseline_cutoffs_V_m={'maxTIS':dict(cutoff)},
                    normalizations={'raw_1Vpp':{'amplitude_scale':1.},'skin_contact_only':{'amplitude_scale':1. if index==0 else .92+model*.001}}))
            path=root/f'report-{model}.json'
            path.write_text(json.dumps(dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',
                new_PDE_solves=0,inputs_unchanged=True,cases=rows,inputs_sha256=pins)))
            paths.append(path)
        return paths

    def test_metadata_preregistration_never_reads_npz_and_retains_two_own_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);reports=self.fixture(root)
            with patch.object(audit,'source_files',return_value=[]):
                plan=audit.make_preregistration(reports)
            self.assertEqual([c['case_id'] for c in plan['cases']],list(audit.CASE_IDS))
            self.assertEqual(plan['cases'][1]['own_model_amplitude_scales']['skin_contact_only'],.92)
            self.assertAlmostEqual(plan['cases'][3]['own_model_amplitude_scales']['skin_contact_only'],.921)
            self.assertEqual(len(plan['common_cutoffs_V_m']),4)
            self.assertFalse(any(Path(c['volume_npz']).exists() for c in plan['cases']))

    def test_changed_summary_and_npz_manifest_identity_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);reports=self.fixture(root)
            summary=root/audit.CASE_IDS[0]/'summary.json'
            value=json.loads(summary.read_text());value['artifacts']['files']['volume.npz']['SHA256']='f'*64
            summary.write_text(json.dumps(value))
            with patch.object(audit,'source_files',return_value=[]),self.assertRaisesRegex(ValueError,'source-summary SHA'):
                audit.make_preregistration(reports)
            report=json.loads(reports[0].read_text());report['inputs_sha256'][str(summary)]=audit.sha(summary)
            reports[0].write_text(json.dumps(report))
            with patch.object(audit,'source_files',return_value=[]),self.assertRaisesRegex(ValueError,'NPZ manifest'):
                audit.make_preregistration(reports)


if __name__=='__main__':unittest.main()
