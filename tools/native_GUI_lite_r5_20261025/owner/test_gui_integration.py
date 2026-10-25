"""Tiny synthetic metadata contracts; no actual input context or native I/O."""
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import gui_inputs as inputs
import gui_build as build


class InputContracts(unittest.TestCase):
    def publication(self):
        return dict(status='published_readback_verified',commit='a'*40,files={'data-native/fixture/a.npz':dict(SHA256='b'*64,bytes=1024,readback_passed=True)})

    def test_native_descriptor_authenticates_proof_without_opening_bytes(self):
        with patch.object(Path,'open',side_effect=AssertionError('Native bytes forbidden in preparation')):
            d=inputs.publication_descriptor(self.publication(),'/dev/shm/task1-fixture-does-not-exist/a.npz','data-native/fixture/a.npz','b'*64)
        self.assertEqual(d['SHA256'],'b'*64);self.assertTrue(d['readback_passed'])

    def test_missing_or_failed_direct_proof_rejected(self):
        p=self.publication();p['files']['data-native/fixture/a.npz']['readback_passed']=False
        with self.assertRaises(ValueError):inputs.publication_descriptor(p,'/dev/shm/task1-fixture-does-not-exist/a.npz','data-native/fixture/a.npz')
        with self.assertRaises(ValueError):inputs.publication_descriptor(self.publication(),'/dev/shm/task1-fixture-does-not-exist/a.npz','data-native/fixture/missing.npz')

    def test_S_only_mask_and_R_only_raw_keep_distinct_actual_provenance(self):
        mask_target='data-native/fixture/masks/B0.csv';raw_target='data-native/fixture/rhs/B0-2000-raw.npz'
        source=dict(status='published_readback_verified',commit='a'*40,files={mask_target:dict(SHA256='b'*64,bytes=100,readback_passed=True)})
        result=dict(status='published_readback_verified',commit='c'*40,files={raw_target:dict(SHA256='d'*64,bytes=200,readback_passed=True)})
        pubs={k:v for namespace in('first','MP')for k,v in((namespace+'_S',source),(namespace+'_R',result))}
        with patch.object(Path,'open',side_effect=AssertionError('No native bytes in preparation fixture')):
            for namespace in('first','MP'):
                mask=inputs.publication_descriptor(pubs[inputs.legacy_publication_role(namespace,'mask')],'/dev/shm/task1-fixture-does-not-exist/B0.csv',mask_target,'b'*64)
                raw=inputs.publication_descriptor(pubs[inputs.legacy_publication_role(namespace,'raw')],'/dev/shm/task1-fixture-does-not-exist/B0-2000-raw.npz',raw_target,'d'*64)
                self.assertEqual((mask['publication_commit'],mask['SHA256'],mask['bytes']),('a'*40,'b'*64,100))
                self.assertEqual((raw['publication_commit'],raw['SHA256'],raw['bytes']),('c'*40,'d'*64,200))
                with self.assertRaises(ValueError):inputs.publication_descriptor(result,'/dev/shm/task1-fixture-does-not-exist/B0.csv',mask_target,'b'*64)
                with self.assertRaises(ValueError):inputs.publication_descriptor(source,'/dev/shm/task1-fixture-does-not-exist/B0-2000-raw.npz',raw_target,'d'*64)

    def test_metadata_loader_refuses_native_suffix_before_open(self):
        with patch.object(Path,'is_file',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'open',side_effect=AssertionError('native read')):
            with self.assertRaises(ValueError):inputs.metadata('/dev/shm/task1-fixture-does-not-exist/a.npz','b'*64)

    def test_canonical_admission_independent_of_import_deployment_filename(self):
        owner={'/dev/shm/task1-fixture/source/owner.py':'b'*64};model={'/dev/shm/task1-fixture/source/model.py':'c'*64}
        a=dict(schema='task1-native-GUI-lite-build-root-admission-v1',status='selected_finite_GUI_build',root_authorized=True,safe_boundary_confirmed=True,source_sha256={**model,**owner},model_source_sha256=model,candidate_adopted=False,new_PDE_RHS=0,new_angular_evaluations=0,native_restore_review=dict(status='unavailable',decision_basis='Explicit unavailable fixture'),decision_basis='Fixture source-only identity contract')
        def inventory(root=inputs.SOURCE):return model if root==inputs.MODEL else owner
        with patch.object(inputs,'source_inventory',side_effect=inventory):
            with patch.object(inputs,'__file__','/dev/shm/task1-frozen-snapshot/gui_inputs.py'):self.assertIs(inputs.validate_admission(a),a)
            a['source_sha256']={**owner}
            with self.assertRaises(ValueError):inputs.validate_admission(a)

    def test_selective_top5_reads_only_published_order_not_rank(self):
        text='{\n  "unused600probePayload": {"x":9},\n  "provisional_top5": [\n    "z",\n    "y",\n    "x",\n    "w",\n    "v"\n  ],\n  "other": 2\n}\n'
        with patch.object(Path,'open',return_value=io.StringIO(text)):
            self.assertEqual(inputs._top5_only('/dev/shm/task1-fixture/summary.json'),['z','y','x','w','v'])


class BuildContracts(unittest.TestCase):
    def test_stored_wave_indices_preserve_actual_endpoints_without_interpolation(self):
        indices=build.stored_indices(128);self.assertEqual((len(indices),indices[0],indices[-1]),(64,0,127));self.assertEqual(len(set(indices)),64)
        self.assertEqual(indices,[k*127//63 for k in range(64)])
        with self.assertRaises(ValueError):build.stored_indices(127)

    def test_published_bar_values_never_rescaled_twice(self):
        rows={mode:dict(status='calculated_global_amplitude_rescaling',amplitude_scale=7.,absolute_ROI_fields_V_m={r:dict(maxTIS=dict(mean=2.,p10=1.,p95=3.,max=4.),RMS=dict(mean=.5,p10=.2,p95=.7,max=1.))for r in('target','surface_0_5','off_target','total')},electrical={})for mode in inputs.MODES}
        saved=json.dumps(rows,sort_keys=True);bars=build.bar_values(rows)
        self.assertEqual(bars['target_AM_mean']['same_source_voltage'],2.);self.assertEqual(build.compact_norms(rows)['same_source_voltage']['amplitude_scale'],7.);self.assertEqual(json.dumps(rows,sort_keys=True),saved)

    def test_serialization_failure_cannot_create_empty_output(self):
        with patch.object(Path,'open',side_effect=AssertionError('Must serialize before any open')):
            with self.assertRaises(ValueError):build.new_json('/dev/shm/task1-fixture/a.json',dict(nonfinite=float('nan')))

    def test_arrow_subset_uses_original_signed_vectors(self):
        arrows=[dict(u_V_m=float(i),v_V_m=-float(i))for i in range(9)];display=dict(planes={'AM_max2074':{'xy15':dict(arrows=arrows)},'contact_J':dict(status='unavailable')})
        result=build.subset_display(display);self.assertEqual(result['planes']['AM_max2074']['xy15']['arrows'],[arrows[0],arrows[4],arrows[8]])
        self.assertTrue(result['planes']['AM_max2074']['xy15']['arrow_display_subset']['original_vectors_unchanged'])

if __name__=='__main__':unittest.main()
