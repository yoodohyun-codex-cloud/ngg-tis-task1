"""Child-only operator/file spies. Import is inert and stdlib-only."""
import contextlib,os,sys
from pathlib import Path
from owner_contracts import fixture_path_allowed,element_count,MAX_ELEMENTS,MAX_FIXTURE_FILE_BYTES,MAX_ALL_FIXTURE_BYTES

def install_boundary(stack,current_test,allowed_reads,out,state,guard):
 allowed={str(Path(path).resolve())for path in allowed_reads};out=Path(out).resolve();fixture=out/'synthetic'
 def reject(name):
  state['forbidden_field_calls'].append(name);raise AssertionError('Manufactured-only boundary: '+name)
 def checkpoint():
  guard();total=0;maximum=0
  for p in fixture.rglob('*'):
   if p.is_symlink():continue
   if p.is_file():
    size=p.stat().st_size
    if size>MAX_FIXTURE_FILE_BYTES:reject('oversize_synthetic_fixture')
    total+=size;maximum=max(maximum,size)
  if total>MAX_ALL_FIXTURE_BYTES:reject('aggregate_synthetic_fixture_bytes')
  state['synthetic_IO'].update(total_regular_fixture_bytes=total,maximum_file_bytes=maximum)
 def audit(event,args):
  if event in('subprocess.Popen','os.system','os.posix_spawn','os.fork','os.forkpty','socket.connect','socket.bind'):reject('forbidden_process_or_network_'+event)
  if event!='open'or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  raw=Path(os.fsdecode(args[0]));path=raw.resolve();mode=args[1]if len(args)>1 else None;flags=args[2]if len(args)>2 and type(args[2])is int else 0
  writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))or(isinstance(mode,str)and any(c in mode for c in'wa+x'))
  synthetic=fixture_path_allowed(path,fixture)and raw.absolute()==path
  native=path.suffix in('.npz','.npy','.csv','.f64','.f64le')or'eigen-cache'in path.parts
  research=str(path).startswith('/dev/shm/task1-')or str(path).startswith('/workspace/ngg-tis-task1/')
  active_test=current_test[0]is not None
  active_escape=active_test and((writing and not synthetic)or(not writing and out in path.parents and not synthetic and str(path)not in allowed))
  blocked=active_escape or(native and not synthetic)or(writing and out not in path.parents)or(not writing and research and str(path)not in allowed and out not in path.parents)
  if blocked:state['native_IO_attempts'].append(dict(path=str(path),write=writing));raise AssertionError('Unadmitted/native file IO '+str(path))
  if synthetic:
   if current_test[0]is None:reject('fixture_IO_outside_active_test')
   if path.exists()and(path.is_symlink()or path.stat().st_size>MAX_FIXTURE_FILE_BYTES):reject('noncanonical_or_large_fixture')
   key='write_opens'if writing else'read_opens';state['synthetic_IO'][key]+=1
 sys.addaudithook(audit);state['IO_audit_installed']=True
 from unittest.mock import patch
 import numpy as np
 import streamed_real_q as model
 def record(name):state['manufactured_work_counts'][name]=state['manufactured_work_counts'].get(name,0)+1
 def active():
  if current_test[0]is None or not current_test[0].startswith('test_'):reject('operator_outside_active_test')
  checkpoint()
 def metadata(function):
  def call(manifest,proofs,pins,*args,**kwargs):
   active()
   if type(manifest)is not dict or manifest.get('shape')!=[6,6]or type(manifest.get('chunks'))is not list or not 0<len(manifest['chunks'])<=6:reject('non6x6_or_unbounded_manifest')
   for row in manifest['chunks']:
    path=Path(row.get('path',''))
    # A symlink under synthetic is one explicit negative fixture: the model
    # must reject it before opening, without the owner replacing that test.
    within=path.is_absolute()and fixture in path.parents and fixture in path.resolve().parents
    if not within or not(type(row.get('bytes'))is int and 0<row['bytes']<=288):reject('nonfixture_chunk_descriptor')
   record('metadata_validation_calls');return function(manifest,proofs,pins,*args,**kwargs)
  return call
 stack.enter_context(patch.object(model,'validate_metadata',metadata(model.validate_metadata)))
 original_init=model.StreamedRealQ.__init__
 def init(self,*args,**kwargs):active();record('operator_constructors');return original_init(self,*args,**kwargs)
 stack.enter_context(patch.object(model.StreamedRealQ,'__init__',init))
 original_multiply=model.StreamedRealQ._multiply
 def multiply(self,values,transpose=False):active();record('transpose_attempts'if transpose else'forward_attempts');return original_multiply(self,values,transpose)
 stack.enter_context(patch.object(model.StreamedRealQ,'_multiply',multiply))
 original_slice=model.StreamedRealQ.__getitem__
 def select(self,key):active();record('slice_attempts');return original_slice(self,key)
 stack.enter_context(patch.object(model.StreamedRealQ,'__getitem__',select))
 original_chunk=model.StreamedRealQ._chunk
 @contextlib.contextmanager
 def chunk(self,index):
  active()
  if self.shape!=(6,6)or not fixture_path_allowed(self._rows[index]['path'],fixture):reject('native_chunk_attempt')
  record('chunk_visits_started')
  with original_chunk(self,index)as block:
   if block.size>36:reject('oversize_chunk_array')
   yield block
  record('chunk_visits_completed');checkpoint()
 stack.enter_context(patch.object(model.StreamedRealQ,'_chunk',chunk))
 original_receipt=model.StreamedRealQ.receipt
 def receipt(self):
  active();record('operator_receipts');value=original_receipt(self)
  if len(state['operator_receipts'])>=128:reject('unbounded_operator_receipts')
  state['operator_receipts'].append(value);return value
 stack.enter_context(patch.object(model.StreamedRealQ,'receipt',receipt))
 def forbidden(name):
  def call(*args,**kwargs):return reject(name)
  return call
 for name in('load','save','savez','savez_compressed','fromfile','memmap'):stack.enter_context(patch.object(np,name,forbidden('numpy.'+name)))
 for name in('eig','eigh','eigvals','eigvalsh','solve','inv','svd','lstsq'):stack.enter_context(patch.object(np.linalg,name,forbidden('numpy.linalg.'+name)))
 def count_nested(value):
  if isinstance(value,(list,tuple)):return sum(count_nested(v)for v in value)
  if isinstance(value,np.ndarray):return value.size
  return 1
 original_array=np.array
 def array(value,*args,**kwargs):
  if count_nested(value)>MAX_ELEMENTS:reject('large_numpy.array')
  return original_array(value,*args,**kwargs)
 stack.enter_context(patch.object(np,'array',array))
 for name in('zeros','ones','empty','full'):
  original=getattr(np,name)
  def factory(shape,*args,_original=original,_name=name,**kwargs):
   try:element_count(shape)
   except ValueError:return reject('large_numpy.'+_name)
   return _original(shape,*args,**kwargs)
  stack.enter_context(patch.object(np,name,factory))
 return checkpoint
