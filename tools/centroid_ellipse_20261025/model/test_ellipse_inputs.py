"""Pure source/proof fixtures; no scientific modules, files, arrays or solves.

These test definitions have not been executed by the source author. The sole
root owner may run them after freezing and publishing the complete source.
"""
import copy
import unittest
from unittest.mock import patch
import ellipse_inputs as subject


def admission_fixture():
    return dict(schema='task1-centroid-ellipse-root-admission-v1',
        status='admitted_finite_centroid_tangent_ellipse',root_review_positive=True,
        sole_NUM_owner=True,maximum_new_driven_RHS=2,new_angular_metric_evaluations=1,
        control_metric_aliases=2,new_eigen_solves=0,physical_pads=4,independent_outputs=2,
        source_high_impedance_Vpp=1.,source_peak_V=.5,source_resistance_ohm=50.,
        source_allocation_amplitudes=[1.,1.],frequencies_Hz=[2000,2010],
        common_depth_layer_counts=[8,19,18,56],physical_evaluation_cells=793860,
        max_physical_evaluation_cells=800000,CPU_limit=4,
        total_RSS_plus_all_owned_tmpfs_bytes=8000000000,candidate_adopted=False,
        source_sha256={'fixture.py':'a'*64},decision_basis='Synthetic contract only',
        fine_review=dict(run=str(subject.FINE_RUN),root_reviewed=True,
            publication_path=str(subject.FINE_RUN/'result-publication/result-publication.json'),
            decision_basis='Synthetic actual-status contract; no execution claimed',
            publication_SHA256='b'*64,publication_commit='c'*40))


def chunk_fixture():
    target='data-native/retained-eigen-cache-20261025/xy100/Q-000.f64'
    chunk=dict(path='/synthetic-cache/Q-000.f64',row_start=0,row_stop=2,
        column_start=0,column_stop=2,dtype='<f8',order='F',bytes=32,SHA256='a'*64)
    manifest=dict(shape=[2,2],dtype='<f8',order='F',remote_verified=False,chunks=[chunk])
    row=dict(SHA256='a'*64,bytes=32,Git_blob_SHA='d'*40,readback_passed=True)
    normalized=dict(status='published_readback_verified',commit=subject.REMOTE_Q_COMMIT,
        original_public_receipt_SHA256=subject.ORIGINAL_Q_RECEIPT_SHA,files={target:row})
    original=dict(schema='task1-retained-cache-public-readback-receipt-v1',
        commit=subject.REMOTE_Q_COMMIT,files=[dict(row,repo_relative_path=target,
        commit=subject.REMOTE_Q_COMMIT)])
    return manifest,normalized,original,target


class InputProofContracts(unittest.TestCase):
    def test_incomplete_admission_rejected_before_metadata_io(self):
        with patch.object(subject,'read_metadata',side_effect=AssertionError('metadata must remain deferred')):
            with self.assertRaises(ValueError):subject.make_spec({})

    def test_only_exact_native_fine_run_can_be_reviewed(self):
        good=admission_fixture()
        self.assertIs(subject.validate_admission(good),good)
        for bad_run in ('/dev/shm/task1-P23-fineXY-synthetic-20261025-run',
                        '/dev/shm/task1-P23-fineXY-synthetic-r2-20261025-run'):
            bad=copy.deepcopy(good);bad['fine_review']['run']=bad_run
            with self.assertRaises(ValueError):subject.validate_admission(bad)
        bad=copy.deepcopy(good)
        bad['fine_review']['publication_path']='/dev/shm/task1-other-run/result-publication/result-publication.json'
        with self.assertRaises(ValueError):subject.validate_admission(bad)

    def test_counts_cannot_change_or_use_boolean_integer_alias(self):
        for key,value in (('maximum_new_driven_RHS',3),('new_eigen_solves',True),
                          ('physical_pads',8),('independent_outputs',4)):
            bad=admission_fixture();bad[key]=value
            with self.assertRaises(ValueError):subject.validate_admission(bad)

    def test_complete_fine_primary_requires_actual_exact_accounting(self):
        primary=dict(status='four_matched97_metric_cases_and_physical_overlap_computed_unadopted',
            actual_new_driven_RHS=3,actual_reused_fine_B0_2000_RHS=1,
            actual_new_metric_evaluations=4,candidate_adopted=False)
        result=subject.validate_fine_outcome('computed_complete',primary,[])
        self.assertFalse(result['fine_numeric_fields_used_in_new_ellipse'])
        for key,value in (('actual_reused_fine_B0_2000_RHS',True),
                          ('actual_new_metric_evaluations',3),('candidate_adopted',True)):
            bad=dict(primary);bad[key]=value
            with self.assertRaises(ValueError):subject.validate_fine_outcome('computed_complete',bad,[])

    def test_published_failure_needs_explicit_missing_fields(self):
        for status in ('failed_preserved','adjacent_fineXY_failed_or_partial_preserved',
                       'P23_fineXY_failed_or_partial_published'):
            result=subject.validate_fine_outcome('failed_preserved',dict(status=status),['fine comparison not completed'])
            self.assertFalse(result['computed_missing_fields_invented'])
            with self.assertRaises(ValueError):subject.validate_fine_outcome('failed_preserved',dict(status=status),[])
        with self.assertRaises(ValueError):
            subject.validate_fine_outcome('failed_preserved',dict(status='synthetic_MMS_passed'),['not native'])

    def test_q_chain_preserves_original_unverified_manifest_flag(self):
        manifest,normalized,original,_=chunk_fixture();before=copy.deepcopy(manifest)
        rows=subject.validate_chunk_receipts(manifest,normalized,original,n=2,grid_name='xy100')
        self.assertEqual(len(rows),1);self.assertTrue(rows[0]['readback_passed'])
        self.assertEqual(manifest,before);self.assertFalse(manifest['remote_verified'])

    def test_actual_fine_diagnostic_metadata_is_copied_without_parameter_transfer(self):
        primary=dict(holds={'full_convergence':False},
                     prospective_adjacent_grid_diagnostics={'synthetic_QA_only':{'passed':False}},
                     diagnostics_not_run={'probe':'not computed'})
        copied=subject.copy_review_diagnostics(primary)
        for key in primary:
            self.assertEqual(copied[key],primary[key]);self.assertIsNot(copied[key],primary[key])
        self.assertFalse(copied['fine_diagnostic_values_used_as_solver_inputs'])
        absent=subject.copy_review_diagnostics({})
        self.assertIsNone(absent['holds']);self.assertIsNone(absent['prospective_adjacent_grid_diagnostics'])
        self.assertFalse(absent['missing_diagnostics_invented'])

    def test_q_chain_rejects_missing_or_inconsistent_remote_proofs(self):
        for alteration in ('missing','SHA','Git_blob','bytes','receipt_binding'):
            manifest,normalized,original,target=chunk_fixture()
            if alteration=='missing':normalized['files'].pop(target)
            elif alteration=='SHA':original['files'][0]['SHA256']='e'*64
            elif alteration=='Git_blob':original['files'][0]['Git_blob_SHA']='f'*40
            elif alteration=='bytes':original['files'][0]['bytes']=16
            else:normalized['original_public_receipt_SHA256']='0'*64
            with self.assertRaises(ValueError):subject.validate_chunk_receipts(manifest,normalized,original,n=2,grid_name='xy100')

    def test_q_chain_rejects_column_gap_or_incomplete_matrix(self):
        for alteration in ('gap','incomplete','order'):
            manifest,normalized,original,_=chunk_fixture()
            if alteration=='gap':manifest['chunks'][0]['column_start']=1
            elif alteration=='incomplete':manifest['chunks'][0]['column_stop']=1
            else:manifest['chunks'][0]['order']='C'
            with self.assertRaises(ValueError):subject.validate_chunk_receipts(manifest,normalized,original,n=2,grid_name='xy100')


if __name__=='__main__':unittest.main()
