"""Tiny prospective operator tests; not executed by the source author.

Root alone may run these under its existing finite guard. Synthetic Q is
at most9x9 (81 real values); no native path/Q/eigen/PDE is accessed. Small
newly created synthetic chunk files are preserved, including on failure.
"""
import copy,hashlib,os,tempfile,unittest
from pathlib import Path
from streamed_real_q import StreamedRealQ,RETAINED_COMMIT,validate_metadata

class StreamedOperatorFixtures(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.np=np;base=Path(os.environ.get('TASK1_STREAMED_Q_SYNTHETIC_DIR',''))
        expected=Path('/dev/shm/task1-streamed-Q-MFG-20261025-run/synthetic')
        if base!=expected or not base.is_dir()or base.is_symlink()or base!=base.resolve():
            raise ValueError('Sole MFG owner must supply its exact canonical new OUT/synthetic directory')
        self.root=Path(tempfile.mkdtemp(prefix='test-',dir=base))
        self.Q=np.array([[1.,2.,-3.,4.,0.,-1.],[-2.,3.,5.,0.,1.,2.],
                         [4.,-1.,0.,2.,-3.,5.],[1.,0.,2.,-4.,3.,-2.],
                         [-3.,2.,1.,5.,-1.,4.],[2.,-5.,3.,1.,4.,0.]],dtype='<f8',order='F')/7.
        self.manifest,self.proofs,self.pins=self.prepare(self.Q,(0,2,3,6))
    def prepare(self,Q,faces):
        rows=[];proofs=[];pins={};n=Q.shape[0]
        for i,(a,b)in enumerate(zip(faces[:-1],faces[1:])):
            path=self.root/('synthetic-Q-'+str(len(list(self.root.iterdir())))+'-'+str(i)+'.f64')
            raw=Q[:,a:b].tobytes(order='F')
            with path.open('xb')as stream:stream.write(raw)
            sha=hashlib.sha256(raw).hexdigest();row=dict(path=str(path),SHA256=sha,bytes=len(raw),row_start=0,row_stop=n,column_start=a,column_stop=b,dtype='<f8',order='F');rows.append(row);pins[str(path)]=sha
            proofs.append(dict(path=str(path),SHA256=sha,bytes=len(raw),publication_target='data-native/retained-eigen-cache-20261025/xy100/'+path.name,publication_commit=RETAINED_COMMIT,Git_blob_SHA='a'*40,readback_passed=True))
        return dict(shape=[n,n],dtype='<f8',order='F',remote_verified=False,chunks=rows),proofs,pins
    def operator(self):return StreamedRealQ(self.np,self.manifest,self.proofs,self.pins,lambda:None)
    def bounded_equal(self,actual,reference,Q,values,transpose=False):
        np=self.np;matrix=Q.T if transpose else Q
        # Conservative two-algorithm dot-product roundoff bound, scaled by
        # absolute products rather than a cancelling/near-zero result.
        scale=np.abs(matrix)@np.abs(values)
        bound=32*np.finfo(np.float64).eps*Q.shape[0]*scale
        self.assertTrue(np.all(np.abs(actual-reference)<=bound+np.finfo(np.float64).tiny))
    def test_forward_and_transpose_vectors_match_trusted_dense_reference(self):
        np=self.np;x=np.array([1.,-3.,.5,2.,-1.,4.],dtype='<f8')
        with self.operator()as q:
            self.bounded_equal(q@x,self.Q@x,self.Q,x)
            self.bounded_equal(q.T@x,self.Q.T@x,self.Q,x,True)
            self.assertIs(q.T.T,q);self.assertEqual(q.shape,self.Q.shape)
            audit=q.receipt();self.assertTrue(audit['all_loaded_chunks_before_after_verified']);self.assertFalse(audit['whole_Q_loaded'])
    def test_bounded_multiple_real_rhs_and_strided_complex_views(self):
        np=self.np;z=np.array([[1+2j,2-3j],[-3+1j,1+.5j],[4-2j,-2+3j],[1+0j,5+1j],[2+4j,-1-1j],[-2+3j,3-2j]],dtype=np.complex128)
        with self.operator()as q:
            for x in(z.real,z.imag):
                self.bounded_equal(q@x,self.Q@x,self.Q,x)
                self.bounded_equal(q.T@x,self.Q.T@x,self.Q,x,True)
            actual=q@z.real+1j*(q@z.imag);reference=self.Q@z
            self.assertTrue(np.allclose(actual,reference,rtol=2e-14,atol=2e-14))
    def test_cross_chunk_column_slice_matches_original_exact_values(self):
        np=self.np
        with self.operator()as q:
            selected=q[:,1:5];self.assertTrue(np.array_equal(selected,self.Q[:,1:5]));self.assertFalse(selected.flags.writeable)
            self.assertEqual(q.receipt()['audit']['maximum_slice_columns'],4)
    def test_cancelling_high_dynamic_range_dot_has_absolute_product_bound(self):
        np=self.np;Q=np.array([[1e15,1.,-1e15,2.,-2.,1.],[1.,-1.,2.,-2.,3.,-3.],[-1e15,2.,1e15,-2.,1.,1.],[.25,-.5,.75,-1.,1.25,-1.5],[1.,2.,3.,4.,5.,6.],[-6.,-5.,-4.,-3.,-2.,-1.]],dtype='<f8',order='F');m,p,s=self.prepare(Q,(0,1,3,6));x=np.ones(6,dtype='<f8')
        with StreamedRealQ(np,m,p,s,lambda:None)as q:
            self.bounded_equal(q@x,Q@x,Q,x);self.bounded_equal(q.T@x,Q.T@x,Q,x,True)
    def test_native_complex_Q_or_implicit_dense_conversion_is_forbidden(self):
        np=self.np
        with self.operator()as q:
            for target in(q,q.T):
                with self.assertRaises(TypeError):np.asarray(target)
                with self.assertRaises(TypeError):np.array(target,dtype=np.complex128)
            with self.assertRaises(TypeError):np.zeros(6,dtype='<f8')@q
    def test_unsupported_index_or_rhs_is_rejected(self):
        np=self.np
        with self.operator()as q:
            for index in((0,0),(slice(None),slice(None)),(slice(None),slice(0,3,2)),(slice(None),[0,1]),(slice(None),slice(True,3))):
                with self.assertRaises(ValueError):q[index]
            for x in([1.]*6,np.ones(6,dtype=np.float32),np.ones(6,dtype=np.complex128),np.ones((6,17),dtype='<f8'),np.ones(5,dtype='<f8')):
                with self.assertRaises(ValueError):q@x
    def test_bad_or_missing_remote_proof_never_loads_native_Q(self):
        for key,value in(('readback_passed',False),('publication_commit','0'*40),('Git_blob_SHA','short'),('SHA256','f'*64)):
            bad=copy.deepcopy(self.proofs);bad[0][key]=value
            with self.assertRaises(ValueError):validate_metadata(self.manifest,bad,self.pins)
    def test_wrong_column_order_gap_or_dtype_is_rejected(self):
        for mutation in('reverse','gap','complex'):
            m=copy.deepcopy(self.manifest);p=copy.deepcopy(self.proofs)
            if mutation=='reverse':m['chunks'].reverse();p.reverse()
            elif mutation=='gap':m['chunks'][1]['column_start']+=1
            else:m['dtype']='<c16'
            with self.assertRaises(ValueError):validate_metadata(m,p,self.pins)
    def test_full_buffer_SHA_detects_corruption_before_numerical_use(self):
        path=Path(self.manifest['chunks'][0]['path'])
        with path.open('r+b')as stream:stream.write(b'corrupt!')
        with self.operator()as q:
            with self.assertRaises(ValueError):q@self.np.ones(6,dtype='<f8')
            self.assertEqual(q.receipt()['audit']['loaded_chunk_visits'],0)
    def test_stat_change_and_symlink_rejected(self):
        q=self.operator();path=Path(self.manifest['chunks'][0]['path'])
        with path.open('ab')as stream:stream.write(b'x')
        with self.assertRaises(ValueError):q@self.np.ones(6,dtype='<f8')
        q.close()
        original=Path(self.manifest['chunks'][1]['path']);link=self.root/'synthetic-link.f64';link.symlink_to(original)
        m=copy.deepcopy(self.manifest);p=copy.deepcopy(self.proofs);pins=dict(self.pins);m['chunks'][1]['path']=str(link);p[1]['path']=str(link);p[1]['publication_target']='data-native/retained-eigen-cache-20261025/xy100/'+link.name;pins[str(link)]=m['chunks'][1]['SHA256']
        with self.assertRaises(ValueError):StreamedRealQ(self.np,m,p,pins,lambda:None)
    def test_no_reentrant_use_or_use_after_close(self):
        q=self.operator()
        with q._operation():
            with self.assertRaises(ValueError):q@self.np.ones(6,dtype='<f8')
        q.close()
        with self.assertRaises(ValueError):q@self.np.ones(6,dtype='<f8')
    def test_original_manifest_flags_and_metadata_are_not_rewritten(self):
        before=copy.deepcopy(self.manifest)
        with self.operator()as q:q@self.np.ones(6,dtype='<f8')
        self.assertEqual(self.manifest,before);self.assertFalse(self.manifest['remote_verified'])

if __name__=='__main__':unittest.main()
