"""Child-only manufactured I/O gate and bounded constructor wrappers."""
import functools,math,os,sys
from pathlib import Path
from owner_contracts import fixture_elements

def install_io_gate(state,allowed_reads,out):
 allowed={str(Path(p).resolve())for p in allowed_reads};out=Path(out).resolve()
 def audit(event,args):
  if not state['manufactured_phase']:return
  if event in('subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','socket.connect','socket.bind'):
   state['scientific_API_spy_calls'].append(event);raise AssertionError('No process/network in manufactured GUI tests')
  if event!='open'or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  path=Path(os.fsdecode(args[0])).resolve();mode=args[1]if len(args)>1 else None;flags=args[2]if len(args)>2 and type(args[2])is int else 0
  writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))or(isinstance(mode,str)and any(v in mode for v in'wa+x'))
  native=path.suffix.lower()in('.npz','.npy','.csv','.f64','.f64le')or'eigen-cache'in path.parts
  research=str(path).startswith('/dev/shm/task1-')or str(path).startswith('/workspace/ngg-tis-task1/')
  if native or(writing and out not in path.parents)or(not writing and research and str(path)not in allowed and out not in path.parents):
   state['native_IO_attempts'].append(dict(path=str(path),write=writing));raise AssertionError('Native/data I/O forbidden before manufactured PASS')
 sys.addaudithook(audit);state['IO_audit_installed']=True


def install_spies(stack,np,state,modules,current_test):
 from unittest.mock import patch
 def reject(label):state['scientific_API_spy_calls'].append(label);raise AssertionError('Manufactured-only GUI boundary '+label)
 def deny(label):
  def blocked(*args,**kwargs):return reject(label)
  return blocked
 for module,names in modules:
  for name in names:
   if not hasattr(module,name):continue
   original=getattr(module,name)
   if module.__name__=='append_inputs'and name=='make_spec':
    def invalid_admission_guard(*args,_original=original,**kwargs):
     exact=current_test[0]=='test_append_inputs.AppendInputContracts.test_invalid_admission_stops_before_metadata_source_or_native_access'and args==({},)and not kwargs
     if not exact:return reject('append_inputs.make_spec')
     try:value=_original(*args,**kwargs)
     except ValueError:
      state['negative_fixture_counts']['invalid_admission_before_IO']=state['negative_fixture_counts'].get('invalid_admission_before_IO',0)+1
      raise
     return reject('invalid_admission_fixture_unexpectedly_returned')
    stack.enter_context(patch.object(module,name,invalid_admission_guard))
   else:stack.enter_context(patch.object(module,name,deny(module.__name__+'.'+name)))
 for name in('load','save','savez','savez_compressed','fromfile','memmap'):stack.enter_context(patch.object(np,name,deny('numpy.'+name)))
 for name in('eig','eigh','eigvals','eigvalsh','solve','inv','pinv','lstsq','svd'):stack.enter_context(patch.object(np.linalg,name,deny('numpy.linalg.'+name)))
 def count(value):
  if isinstance(value,np.ndarray):return fixture_elements(tuple(int(n)for n in value.shape))
  if isinstance(value,(list,tuple)):
   n=sum(count(v)for v in value)
   if n>65536:return reject('oversize_literal_array')
   return n
  if type(value)in(int,float,complex,bool)or isinstance(value,np.generic):return 1
  return reject('unbounded_array_provider')
 def wrap(label,original):
  @functools.wraps(original)
  def bounded(value,*args,**kwargs):
   try:
    if label in('array','asarray'):n=count(value)
    elif label=='arange':
     vals=(value,)+args
     if not(1<=len(vals)<=3 and all(type(v)in(int,float)and math.isfinite(v)for v in vals)):return reject('unbounded_arange')
     a,b,c=(0,vals[0],1)if len(vals)==1 else(vals[0],vals[1],1)if len(vals)==2 else vals
     if c==0:return reject('zero_arange_step')
     n=fixture_elements(max(0,math.ceil((b-a)/c)))
    else:n=fixture_elements(value)
   except ValueError:return reject('oversize_numpy.'+label)
   if len(state['array_allocations'])>=10000:return reject('unbounded_allocation_events')
   state['array_allocations'].append(dict(constructor=label,elements=n));return original(value,*args,**kwargs)
  return bounded
 for name in('array','asarray','arange','empty','zeros','ones','full'):stack.enter_context(patch.object(np,name,wrap(name,getattr(np,name))))
