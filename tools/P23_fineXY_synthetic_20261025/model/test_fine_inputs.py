"""Unrun pure metadata-contract tests; no actual datasets, masks or Q opened."""
import copy
import unittest
from unittest.mock import patch
import fine_inputs as inputs


def admission_fixture():
    return dict(schema='task1-P23-fineXY-root-admission-v1',
        status='admitted_finite_P23_B0_fineXY', root_review_positive=True, sole_NUM_owner=True,
        maximum_new_driven_RHS=3, reused_B0_2000_RHS=1, automatic_fourth_RHS_fallback=False,
        new_eigen_solves=0, common_depth_layer_counts=[4,19,18,56], CPU_limit=4,
        total_RSS_plus_all_owned_tmpfs_bytes=8000000000, max_physical_evaluation_cells=800000,
        candidate_adopted=False, old_13_of_14_failures_per_basis_preserved=True,
        full_angular_metric_evaluations=2,SC4_only_angular_metric_evaluations=2,
        coarse93_bulk_angular_evaluations=0,duplicate_full_coarse_scalar_archives=False,
        source_peak_V=.5, source_high_impedance_Vpp=1., source_resistance_ohm=50.,
        physical_pairs_common_return=[[0,2],[1,3]], active_frequency_output_assignment=[[2000,0],[2010,1]],
        fine_B0_reuse_failure_blocks_before_new_RHS=True, source_sha256={},
        decision_basis='Synthetic metadata fixture only; not a field admission')


def chunk_fixture():
    chunks, original_files, normalized_files = [], [], {}
    for i, (start, stop) in enumerate(((0,2),(2,4))):
        name='Q-cols-%05d-%05d.f64le'%(start,stop)
        target='data-native/retained-eigen-cache-20261025/xy102/'+name
        row=dict(SHA256=str(i+1)*64, bytes=4*(stop-start)*8,
                 readback_passed=True, Git_blob_SHA=str(i+3)*40)
        normalized_files[target]=row
        original_files.append(dict(row,repo_relative_path=target,commit=inputs.REMOTE_Q_COMMIT))
        chunks.append(dict(path='/synthetic/eigen-cache/'+name,SHA256=row['SHA256'],bytes=row['bytes'],
            row_start=0,row_stop=4,column_start=start,column_stop=stop,dtype='<f8',order='F',remote_verified=False))
    manifest=dict(shape=[4,4],dtype='<f8',order='F',chunks=chunks)
    normalized=dict(status='published_readback_verified',commit=inputs.REMOTE_Q_COMMIT,
        original_public_receipt_SHA256=inputs.ORIGINAL_Q_RECEIPT_SHA,files=normalized_files)
    original=dict(schema='task1-retained-cache-public-readback-receipt-v1',commit=inputs.REMOTE_Q_COMMIT,files=original_files)
    return manifest,normalized,original


class FineMetadataContracts(unittest.TestCase):
    def test_positive_finite_admission_and_no_fourth_rhs_fallback(self):
        fixture=admission_fixture()
        self.assertEqual(inputs.validate_admission(fixture),fixture)
        for key,value in (('maximum_new_driven_RHS',4),('automatic_fourth_RHS_fallback',True),
                ('fine_B0_reuse_failure_blocks_before_new_RHS',False),('new_eigen_solves',1),
                ('common_depth_layer_counts',[8,19,18,56]),('old_13_of_14_failures_per_basis_preserved',False),
                ('active_frequency_output_assignment',[[2000,1],[2010,0]]),
                ('coarse93_bulk_angular_evaluations',2),('duplicate_full_coarse_scalar_archives',True)):
            with self.subTest(key=key),self.assertRaises(ValueError):
                changed=copy.deepcopy(fixture);changed[key]=value;inputs.validate_admission(changed)

    def test_missing_root_review_or_changed_resource_scope_blocks(self):
        for key,value in (('root_review_positive',False),('sole_NUM_owner',False),
                ('CPU_limit',8),('total_RSS_plus_all_owned_tmpfs_bytes',8000000001),
                ('max_physical_evaluation_cells',800001),('reused_B0_2000_RHS',True),
                ('source_peak_V',1.),('source_resistance_ohm',100.)):
            with self.subTest(key=key),self.assertRaises(ValueError):
                changed=admission_fixture();changed[key]=value;inputs.validate_admission(changed)
        with self.assertRaises(ValueError):inputs.validate_admission(None)

    def test_remote_q_full_readback_preserves_historical_manifest_flags(self):
        manifest,normalized,original=chunk_fixture();before=copy.deepcopy(manifest)
        proofs=inputs.validate_chunk_receipts(manifest,normalized,original,n=4,grid_name='xy102')
        self.assertEqual(manifest,before)
        self.assertEqual(len(proofs),2)
        self.assertTrue(all(p['readback_passed']for p in proofs))
        self.assertTrue(all(p['remote_verified']is False for p in manifest['chunks']))

    def test_missing_or_changed_remote_chunk_and_noncontiguous_columns_block(self):
        for change in ('missing','SHA','bytes','original_readback','columns','commit'):
            manifest,normalized,original=chunk_fixture();target=next(iter(normalized['files']))
            if change=='missing':normalized['files'].pop(target)
            elif change=='SHA':normalized['files'][target]['SHA256']='f'*64
            elif change=='bytes':original['files'][0]['bytes']+=1
            elif change=='original_readback':original['files'][0]['readback_passed']=False
            elif change=='columns':manifest['chunks'][1]['column_start']=3
            else:normalized['commit']='e'*40
            with self.subTest(change=change),self.assertRaises(ValueError):
                inputs.validate_chunk_receipts(manifest,normalized,original,n=4,grid_name='xy102')

    def test_absent_admission_blocks_before_inventory_or_metadata_reads(self):
        with patch.object(inputs.Path,'is_file',return_value=False),patch.object(inputs,'source_inventory')as inventory,patch.object(inputs,'read_metadata')as metadata:
            with self.assertRaisesRegex(ValueError,'admission absent'):inputs.make_spec()
            inventory.assert_not_called();metadata.assert_not_called()


if __name__=='__main__':unittest.main()
