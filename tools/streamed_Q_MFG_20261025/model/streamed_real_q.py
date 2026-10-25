"""Inert column-streamed real-Q operator; NumPy is explicitly injected.

No IO, NumPy import, cache access, arrays, solve or eigen operation occurs on
module import. Root may construct the operator only from its authenticated
original manifest, direct retained-cache proofs and full input SHA map.
"""
from contextlib import contextmanager
import copy,hashlib,json,os,re,stat,time
from pathlib import Path

MAX_CHUNK_BYTES=32*1024**2
MAX_SLICE_COLUMNS=128
MAX_RHS_COLUMNS=16
MAX_OPERATOR_ROWS=8184
MAX_CHUNKS=64
RETAINED_COMMIT='d725ee29ee568ef26a4b7579e9dfc55d23e0681a'

def require(ok,message):
    if not ok:raise ValueError(message)
def fullhex(value,n):
    return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None
def metadata_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def file_identity(path):
    p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical original chunk path, no symlinks')
    s=p.stat();require(stat.S_ISREG(s.st_mode),'Original chunk must be a regular file')
    return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)

def validate_metadata(manifest,proofs,input_sha256,cache_name='xy100'):
    """Pure validation. Remote readback was authenticated by the root owner."""
    require(type(manifest)is dict and type(proofs)is list and type(input_sha256)is dict,'Explicit authenticated manifest/proofs/input pins')
    shape=manifest.get('shape');require(type(shape)is list and len(shape)==2 and all(type(x)is int and 0<x<=MAX_OPERATOR_ROWS for x in shape)and shape[0]==shape[1],'Bounded original square real-Q shape, at most8184 rows')
    require(manifest.get('dtype')=='<f8'and manifest.get('order')=='F','Exact little-endian real float64 Fortran Q ABI')
    require(cache_name in('xy100','xy102'),'Explicit original retained cache name')
    n=shape[0];chunks=manifest.get('chunks');require(type(chunks)is list and 0<len(chunks)<=MAX_CHUNKS and len(chunks)==len(proofs),'Every original chunk has one ordered direct proof, at most64 chunks')
    at=0;paths=set();targets=set();rows=[]
    for row,proof in zip(chunks,proofs):
        require(type(row)is dict and type(proof)is dict,'Original chunk and publication proof objects')
        path=row.get('path');size=row.get('bytes');start=row.get('column_start');stop=row.get('column_stop')
        require(type(path)is str and Path(path).is_absolute()and path not in paths,'Unique absolute original chunk path')
        require(type(start)is int and type(stop)is int and start==at and at<stop<=n and row.get('row_start')==0 and row.get('row_stop')==n,'Ordered disjoint complete original columns')
        require(type(size)is int and size==n*(stop-start)*8 and 0<size<=MAX_CHUNK_BYTES and row.get('dtype')=='<f8'and row.get('order')=='F','Bounded unchanged real-Q chunk ABI')
        expected=row.get('SHA256');require(fullhex(expected,64)and input_sha256.get(path)==expected,'Every local chunk has its exact original input SHA pin')
        target='data-native/retained-eigen-cache-20261025/'+cache_name+'/'+Path(path).name
        require(proof.get('path')==path and proof.get('SHA256')==expected and proof.get('bytes')==size and proof.get('publication_target')==target and target not in targets,'Direct per-chunk publication identity/order')
        require(proof.get('publication_commit')==RETAINED_COMMIT and proof.get('readback_passed')is True and fullhex(proof.get('Git_blob_SHA'),40),'Actual original retained-Q commit/full readback proof')
        rows.append(dict(row));paths.add(path);targets.add(target);at=stop
    require(at==n and sum(row['bytes']for row in rows)==n*n*8,'Every original Q column and byte covered exactly once')
    return n,rows

class _Transpose:
    __array_priority__=10000
    def __init__(self,parent):self._parent=parent
    @property
    def shape(self):return self._parent.shape[::-1]
    @property
    def T(self):return self._parent
    def __matmul__(self,values):return self._parent._multiply(values,transpose=True)
    def __rmatmul__(self,values):raise TypeError('Only Q.T @ explicit real vectors/matrices is supported')
    def __array__(self,dtype=None,copy=None):raise TypeError('Implicit or explicit dense Q conversion is forbidden')
    def __array_ufunc__(self,*args,**kwargs):raise TypeError('Q is a bounded operator, not a NumPy array')
    def __array_function__(self,*args,**kwargs):raise TypeError('Q is a bounded operator, not a NumPy array')

class StreamedRealQ:
    """Read-only real operator with one transient authenticated chunk at a time.

    Supported: shape, T, @ real float64[n] or float64[n,k<=16], and
    Q[:,start:stop] with 0<stop-start<=128. Full-Q materialization, scalar/
    fancy/stepped indexing, implicit conversion and complex Q are forbidden.
    No file handle or chunk buffer is retained between operations.
    """
    __array_priority__=10000
    def __init__(self,np,manifest,remote_proofs,input_sha256,guard,deadline_monotonic=None,cache_name='xy100'):
        require(callable(guard),'Existing authenticated owner guard required')
        self._np=np;self._guard=guard;self._deadline=deadline_monotonic;self._closed=False;self._active=False
        self._manifest=copy.deepcopy(manifest);self._proofs=copy.deepcopy(remote_proofs);self._pins=dict(input_sha256)
        self._n,self._rows=validate_metadata(self._manifest,self._proofs,self._pins,cache_name)
        self._cache_name=cache_name;self._metadata_identity=metadata_sha(dict(manifest=self._manifest,proofs=self._proofs,pins={r['path']:self._pins[r['path']]for r in self._rows}))
        self._check();self._stats={r['path']:file_identity(r['path'])for r in self._rows}
        require(all(self._stats[r['path']][2]==r['bytes']for r in self._rows),'Actual original per-chunk file sizes')
        self._transposed=_Transpose(self)
        self._audit=dict(forward_calls=0,transpose_calls=0,slice_calls=0,
            maximum_live_chunk_bytes=0,maximum_slice_columns=0,maximum_RHS_columns=0,
            loaded_chunk_visits=0,completed_before_after_visits=0,
            chunks={r['path']:dict(SHA256=r['SHA256'],bytes=r['bytes'],publication_target=p['publication_target'],publication_commit=p['publication_commit'],Git_blob_SHA=p['Git_blob_SHA'],before_verified=0,after_verified=0)for r,p in zip(self._rows,self._proofs)})
    @property
    def shape(self):return(self._n,self._n)
    @property
    def dtype(self):return self._np.dtype('<f8')
    @property
    def T(self):return self._transposed
    def __array__(self,dtype=None,copy=None):raise TypeError('Implicit or explicit dense Q conversion is forbidden')
    def __array_ufunc__(self,*args,**kwargs):raise TypeError('Q is a bounded operator, not a NumPy array')
    def __array_function__(self,*args,**kwargs):raise TypeError('Q is a bounded operator, not a NumPy array')
    def __rmatmul__(self,values):raise TypeError('Only Q @ explicit real vectors/matrices is supported')
    def _check(self):
        require(not self._closed,'Streamed Q operator is closed')
        self._guard()
        if self._deadline is not None and time.monotonic()>=self._deadline:raise TimeoutError('Finite streamed-Q owner deadline')
    def _check_metadata(self):
        self._check()
        current=metadata_sha(dict(manifest=self._manifest,proofs=self._proofs,pins={r['path']:self._pins[r['path']]for r in self._rows}))
        require(current==self._metadata_identity,'Frozen original Q manifest/remote proofs/input SHA identity changed')
    def _hash_original(self,path,expected_bytes):
        require(file_identity(path)==self._stats[path],'Original Q file stat changed before after-use SHA')
        h=hashlib.sha256();count=0
        with Path(path).open('rb')as stream:
            require(file_identity(path)==self._stats[path],'Canonical Q path changed while opening after-use stream')
            s=os.fstat(stream.fileno());require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)==self._stats[path],'Same original inode after use')
            for block in iter(lambda:stream.read(1024**2),b''):
                count+=len(block);require(count<=expected_bytes,'Original Q file grew during after-use SHA');h.update(block)
        require(count==expected_bytes and file_identity(path)==self._stats[path],'Exact original Q byte count/stat after use')
        return h.hexdigest()
    @contextmanager
    def _chunk(self,index):
        self._check_metadata();row=self._rows[index];path=row['path'];expected=row['SHA256'];size=row['bytes'];audit=self._audit['chunks'][path]
        require(file_identity(path)==self._stats[path],'Original Q chunk stat changed before read')
        with Path(path).open('rb')as stream:
            s=os.fstat(stream.fileno());require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)==self._stats[path],'Same canonical original chunk inode')
            raw=stream.read(size);extra=stream.read(1)
        require(len(raw)==size and not extra and hashlib.sha256(raw).hexdigest()==expected and file_identity(path)==self._stats[path],'Full original chunk SHA/bytes/stat before numerical use')
        block=self._np.frombuffer(raw,dtype='<f8').reshape((self._n,row['column_stop']-row['column_start']),order='F')
        require(self._np.isfinite(block).all(),'Finite original real Q chunk')
        self._audit['loaded_chunk_visits']+=1;self._audit['maximum_live_chunk_bytes']=max(self._audit['maximum_live_chunk_bytes'],len(raw));audit['before_verified']+=1
        try:yield block
        finally:
            del block,raw
            self._check_metadata();require(self._hash_original(path,size)==expected,'Full original Q file SHA after numerical use')
            audit['after_verified']+=1;self._audit['completed_before_after_visits']+=1
    @contextmanager
    def _operation(self):
        self._check_metadata();require(not self._active,'No concurrent/reentrant operator use; at most one chunk buffer')
        self._active=True
        try:yield
        finally:self._active=False
    def _values(self,values):
        np=self._np
        require(type(values)is np.ndarray and values.dtype==np.dtype('<f8')and values.ndim in(1,2),'Explicit real float64 ndarray only; no input/Q complex copy')
        require(values.shape[0]==self._n and(values.ndim==1 or 1<=values.shape[1]<=MAX_RHS_COLUMNS),'Original Q dimension and bounded RHS columns')
        require(np.isfinite(values).all(),'Finite real RHS values')
        columns=1 if values.ndim==1 else values.shape[1];self._audit['maximum_RHS_columns']=max(self._audit['maximum_RHS_columns'],columns)
        return values
    def __matmul__(self,values):return self._multiply(values,False)
    def _multiply(self,values,transpose=False):
        with self._operation():
            values=self._values(values);np=self._np;result=np.zeros(values.shape,dtype='<f8')
            self._audit['transpose_calls'if transpose else'forward_calls']+=1
            for i,row in enumerate(self._rows):
                a,b=row['column_start'],row['column_stop']
                with self._chunk(i)as block:
                    if transpose:result[a:b]=block.T@values
                    else:result+=block@values[a:b]
                    del block
            require(np.isfinite(result).all(),'Finite bounded streamed transform result')
            return result
    def __getitem__(self,key):
        require(type(key)is tuple and len(key)==2 and type(key[0])is slice and key[0]==slice(None)and type(key[1])is slice,'Only Q[:,start:stop] column slices are supported')
        col=key[1];a,b=col.start,col.stop
        require(type(a)is int and type(b)is int and col.step is None and 0<=a<b<=self._n and b-a<=MAX_SLICE_COLUMNS,'Explicit bounded contiguous <=128-column slice only')
        with self._operation():
            np=self._np;result=np.empty((self._n,b-a),dtype='<f8',order='F');covered=0
            self._audit['slice_calls']+=1;self._audit['maximum_slice_columns']=max(self._audit['maximum_slice_columns'],b-a)
            for i,row in enumerate(self._rows):
                lo=max(a,row['column_start']);hi=min(b,row['column_stop'])
                if lo>=hi:continue
                with self._chunk(i)as block:
                    result[:,lo-a:hi-a]=block[:,lo-row['column_start']:hi-row['column_start']]
                    del block
                covered+=hi-lo
            require(covered==b-a and np.isfinite(result).all(),'Every requested real-Q column copied exactly once')
            result.flags.writeable=False;return result
    def receipt(self):
        require(not self._active,'Receipt only at an operation boundary')
        return dict(schema='task1-streamed-real-Q-operator-receipt-v1',shape=list(self.shape),dtype='<f8',order='F',cache_name=self._cache_name,
            manifest_remote_flags_original=self._manifest.get('remote_verified'),metadata_identity_SHA256=self._metadata_identity,
            maximum_chunk_bytes=MAX_CHUNK_BYTES,maximum_slice_columns=MAX_SLICE_COLUMNS,maximum_RHS_columns=MAX_RHS_COLUMNS,
            whole_Q_loaded=False,complex_Q_materialized=False,originals_modified_by_operator=False,closed=self._closed,
            remote_readback_commit=RETAINED_COMMIT,all_loaded_chunks_before_after_verified=self._audit['loaded_chunk_visits']==self._audit['completed_before_after_visits'],
            audit=copy.deepcopy(self._audit),roundoff_bitwise_identity_claim=False,operator_scope_only=True,
            external_PDE_or_restore_counts_not_inferred=True,operator_invokes_PDE_or_eigen_solver=False,candidate_adopted=False)
    def close(self):
        require(not self._active,'Cannot close an active operation');self._closed=True
    def __enter__(self):self._check_metadata();return self
    def __exit__(self,*exc):self.close();return False
