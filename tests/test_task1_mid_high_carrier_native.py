"""Synthetic mid/high-frequency readback fixtures; no actual native arrays."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests'))
import task1_mid_high_carrier_native as r
from test_task1_lower_carrier_native import make_fixture,write_array,write_json

MID_HIGH=(5000,5030,9030)
ANALYSIS_FREQUENCIES=(5000,5030,9000,9030)
ORIGINAL=ROOT/'tis-java/runs/selectivity-design-20261019T155933Z/masks/baseline-square15-h0.625.csv'
ORIGINAL_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
EPS0=8.8541878128e-12


def fixture(root,frequencies=MID_HIGH):
    result=make_fixture(root,frequencies)
    if frequencies==MID_HIGH:
        result['metadata'].update(exporter_class='CloudFrequencyMidHighBasis',exporter_kind='mid_high_frequency_native')
        config=Path(result['case']['config_file'])
        config.write_text(config.read_text()+'z.9000.re=0.00004\nz.9000.im=-0.00009\n')
        digest=hashlib.sha256(config.read_bytes()).hexdigest()
        result['case']['config_sha256']=result['metadata']['config_sha256']=digest
        write_json(result['folder']/'mesh-metadata.json',result['metadata'])
        path=result['folder']/'runtime-wrapper.json';wrapper=json.loads(path.read_text())
        wrapper['runtime_wrapper_class']='CloudFrequencyMidHighBasis';write_json(path,wrapper)
        result['case'].update(exporter_class='CloudFrequencyMidHighBasis',java_class='CloudFrequencyMidHighBasis')
    return result


def legacy_cache(root,wrong_contact=False):
    run=Path(root)/'cached-run';oldroot=run/'bases';oldroot.mkdir(parents=True)
    old=make_fixture(oldroot,(3000,3030,9000,9090))
    oldcase=copy.deepcopy(old['case']);oldcase.update(id=old['folder'].name,
        exporter_class='SelectivityShapeBasis',java_class='CloudShapeBasis')
    metadata=copy.deepcopy(old['metadata']);metadata['exporter_class']='SelectivityShapeBasis'
    metadata.pop('exporter_kind')
    if wrong_contact:
        config=Path(oldcase['config_file'])
        config.write_text(config.read_text().replace('z.9000.re=0.00004','z.9000.re=0.00005'))
        oldcase['config_sha256']=metadata['config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest()
    write_json(old['folder']/'mesh-metadata.json',metadata)
    write_json(run/'preregistration.json',dict(cases=[oldcase]))
    (run/'cases').mkdir();(run/'postprocess').mkdir()
    summary=run/'postprocess'/'summary.json';write_json(summary,dict(status='complete'))
    write_json(run/'cases'/(oldcase['id']+'.json'),dict(status='complete',validation=old['validation'],
        postprocess_path=str(summary),postprocess_sha256=hashlib.sha256(summary.read_bytes()).hexdigest()))
    # Prove that assembly does not reopen unrelated cached spectral arrays.
    for f in (3000,3030,9090):
        for path in old['folder'].glob(f'*-{f}.*'):path.unlink()
    return old


class MidHighCarrierNativeTests(unittest.TestCase):
    def load(self,data):
        return r.load_basis(data['folder'],data['case'],time.monotonic()+120.)

    def test_actual_three_frequency_bundle_gamma_and_six_rhs_are_preserved(self):
        with tempfile.TemporaryDirectory()as temporary:
            data=fixture(temporary);basis=self.load(data)
            self.assertEqual(set(MID_HIGH),set(basis['f']))
            self.assertEqual('CloudFrequencyMidHighBasis',basis['metadata']['exporter_class'])
            self.assertEqual('mid_high_frequency_native',basis['metadata']['exporter_kind'])
            self.assertEqual(6,basis['metadata']['actual_basis_RHS_solves'])
            self.assertEqual(0,basis['metadata']['extra_potential_export_solves'])
            self.assertFalse((data['folder']/'field-9000.bin.gz').exists())
            geometry,volume=r.geometry(basis,data['case'])
            self.assertEqual(set(MID_HIGH),set(geometry['gamma_S_m']))
            for f in MID_HIGH:
                self.assertEqual((2,4,3),basis['f'][f]['field'].shape)
                self.assertEqual((2,4),basis['f'][f]['potential'].shape)
                self.assertEqual((2,2304),basis['f'][f]['density'].shape)
                for layer,sigma,epsilon in ((0,.0002,110000.),(1,.2,10000.),(2,.04,1000.),(3,.3,100000.)):
                    gamma=geometry['gamma_S_m'][f][layer]
                    self.assertAlmostEqual(sigma,gamma.real)
                    self.assertAlmostEqual(2*math.pi*f*EPS0*epsilon,gamma.imag,places=13)
            progress=json.loads((data['folder']/'basis-progress.json').read_text())
            self.assertEqual(9030,progress['last_frequency_Hz'])
            self.assertEqual(6,progress['completed_basis_RHS_solves'])

    def test_original_three_khz_donor_remains_accepted_without_relabeling(self):
        with tempfile.TemporaryDirectory()as temporary:
            data=fixture(temporary,(3000,3030));basis=self.load(data)
            self.assertEqual({3000,3030},set(basis['f']))
            self.assertEqual('CloudFrequencyBasis',basis['metadata']['exporter_class'])
            self.assertEqual('frequency_native',basis['metadata']['exporter_kind'])
            self.assertEqual(4,basis['metadata']['actual_basis_RHS_solves'])
            geometry,_=r.geometry(basis,data['case'])
            self.assertEqual({3000,3030},set(geometry['gamma_S_m']))

    def test_old_lower_bundle_and_disguised_exporter_or_wrong_kind_are_rejected(self):
        for frequencies in ((1000,1030,2000,2030),ANALYSIS_FREQUENCIES):
            with tempfile.TemporaryDirectory()as temporary:
                data=fixture(temporary,frequencies)
                data['metadata'].update(exporter_class='CloudFrequencyMidHighBasis',exporter_kind='mid_high_frequency_native')
                write_json(data['folder']/'mesh-metadata.json',data['metadata'])
                with self.assertRaises(ValueError):self.load(data)
        for mutation in (dict(exporter_class='CloudFrequencyBasis',exporter_kind='frequency_native'),
                         dict(exporter_kind='frequency_recovery_native'),
                         dict(exporter_class='CloudFrequencyRecoveryBasis')):
            with tempfile.TemporaryDirectory()as temporary:
                data=fixture(temporary);data['metadata'].update(mutation)
                write_json(data['folder']/'mesh-metadata.json',data['metadata'])
                with self.assertRaises(ValueError):self.load(data)

    def test_extra_or_fabricated_rhs_and_incomplete_progress_are_rejected(self):
        for mutation in (dict(actual_basis_RHS_solves=8),dict(actual_basis_RHS_solves=10),
                         dict(extra_potential_export_solves=1),dict(potential_export_basis_vectors=8)):
            with tempfile.TemporaryDirectory()as temporary:
                data=fixture(temporary);data['metadata'].update(mutation)
                write_json(data['folder']/'mesh-metadata.json',data['metadata'])
                with self.assertRaises(ValueError):self.load(data)
        with tempfile.TemporaryDirectory()as temporary:
            data=fixture(temporary);path=data['folder']/'basis-progress.json'
            progress=json.loads(path.read_text());progress['completed_basis_RHS_solves']=4;write_json(path,progress)
            with self.assertRaises(ValueError):self.load(data)

    def test_released_one_ulp_full_face_mask_remains_unchanged_and_accepted(self):
        before=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
        self.assertEqual(ORIGINAL_SHA256,before)
        rows=np.genfromtxt(ORIGINAL,delimiter=',',names=True)
        self.assertTrue(np.any(rows['area_m2']==3.9062499999999997e-7))
        receipt=r._validate_full_face_mask(rows)
        self.assertEqual(2304,receipt['contact_count'])
        self.assertEqual(4*np.finfo(float).eps,receipt['full_face_relative_tolerance'])
        self.assertEqual(0.,receipt['full_face_absolute_tolerance'])
        self.assertEqual(before,hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())

    def test_native_loss_hermitian_and_coherent_common_gnd_guards_still_apply(self):
        for kind in ('loss','current'):
            with tempfile.TemporaryDirectory()as temporary:
                data=fixture(temporary)
                if kind=='loss':
                    loss=data['loss'].copy();loss[0,0,1]=1e-6j
                    write_array(data['folder'],'loss',5000,loss)
                else:
                    density=data['density'].copy()
                    returns=np.array([pad>=2 for pad,_,_,_ in data['rows']])
                    density[0,returns]*=-1
                    write_array(data['folder'],'density',5000,density)
                with self.assertRaises(ValueError):self.load(data)

    def test_cached9000_assembly_preserves_raw_metadata_and_uses_only_that_cached_line(self):
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary);newroot=root/'new';newroot.mkdir()
            data=fixture(newroot);basis=self.load(data);raw_metadata=copy.deepcopy(basis['metadata'])
            cached=legacy_cache(root)
            assembled=r.assemble_with_cached_9000(basis,cached['folder'],time.monotonic()+120.)
            self.assertEqual(set(ANALYSIS_FREQUENCIES),set(assembled['f']))
            self.assertEqual(list(ANALYSIS_FREQUENCIES),assembled['analysis_frequencies_Hz'])
            self.assertEqual(raw_metadata,basis['metadata'])
            self.assertEqual(raw_metadata,assembled['metadata'])
            self.assertEqual(list(MID_HIGH),assembled['metadata']['frequencies_Hz'])
            self.assertEqual(6,assembled['metadata']['actual_basis_RHS_solves'])
            self.assertIn(9000,assembled['frequency_sources'])
            self.assertEqual(6,assembled['assembly_metadata']['actual_new_basis_RHS_solves'])
            self.assertEqual(2,assembled['assembly_metadata']['cached_basis_RHS_reused'])
            self.assertEqual(8,assembled['assembly_metadata']['total_analysis_basis_vectors'])
            self.assertEqual('explicit_frequency_native_and_cached9000_assembly',assembled['assembly_metadata']['source'])
            self.assertTrue(assembled['cached_frequency_metadata'])
            geometry,_=r.geometry(assembled,data['case'])
            self.assertEqual(set(ANALYSIS_FREQUENCIES),set(geometry['gamma_S_m']))
            self.assertAlmostEqual(2*math.pi*9000*EPS0*110000,
                                   geometry['gamma_S_m'][9000][0].imag,places=13)

    def test_cached9000_contact_model_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary);newroot=root/'new';newroot.mkdir()
            data=fixture(newroot);basis=self.load(data)
            cached=legacy_cache(root,wrong_contact=True)
            with self.assertRaises(ValueError):
                r.assemble_with_cached_9000(basis,cached['folder'],time.monotonic()+120.)


if __name__=='__main__':
    unittest.main()
