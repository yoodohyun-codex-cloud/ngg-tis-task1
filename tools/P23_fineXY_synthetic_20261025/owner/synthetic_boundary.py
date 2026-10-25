"""Finite child-only spies; install only after source/parent authentication.

No scientific imports, data reads, process work or patches occur on import.
The owner passes real test-current identity and its already pinned read paths.
"""
import contextlib,os,sys
from pathlib import Path
def install_boundary(stack,current_test,allowed_reads,out,state):
 # Python audit hooks cover data reads even if a future test bypasses an API spy.
 allowed={str(Path(path).resolve())for path in allowed_reads};out=Path(out).resolve()
 def audit(event,args):
  if event!='open'or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  path=Path(os.fsdecode(args[0])).resolve();mode=args[1]if len(args)>1 else None;flags=args[2]if len(args)>2 and type(args[2])is int else 0;writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))or(isinstance(mode,str)and any(c in mode for c in'wa+x'))
  research=str(path).startswith('/dev/shm/task1-')or str(path).startswith('/workspace/ngg-tis-task1/')
  native=path.suffix in('.npz','.csv','.f64le')or'eigen-cache'in path.parts
  rejected=native or(writing and research and out not in path.parents)or(not writing and research and str(path)not in allowed and out not in path.parents)
  if rejected:state['native_IO_attempts'].append(dict(path=str(path),write=writing));raise AssertionError('Manufactured-only boundary: unregistered research/native file IO '+str(path))
 sys.addaudithook(audit)
 state['IO_audit_installed']=True
 from unittest.mock import Mock,patch
 import numpy as np
 import scipy.sparse.linalg as sparse_linalg
 import fine_screen,fine_inputs,fine_fields,fine_solver,fine_post,cached_metrics,screen_metrics,physical_projector,frozen_layer_dtn_backend,frozen_fourier_v1
 def forbidden(name):
  def call(*args,**kwargs):state['forbidden_field_calls'].append(name);raise AssertionError('Manufactured-only boundary: forbidden native field/input API '+name)
  return call
 def record(name):state['manufactured_work_counts'][name]=state['manufactured_work_counts'].get(name,0)+1
 def tiny(name,function,limit):
  def call(*args,**kwargs):
   if current_test[0]is None or not current_test[0].startswith('test_')or not limit(args,kwargs):return forbidden(name)(*args,**kwargs)
   record(name);return function(*args,**kwargs)
  return call
 # This one negative contract intentionally rejects BEFORE data/inventory work.
 original_make_spec=fine_inputs.make_spec
 def negative_admission_only(*args,**kwargs):
  allowed=current_test[0]=='test_fine_inputs.FineMetadataContracts.test_absent_admission_blocks_before_inventory_or_metadata_reads'
  allowed=allowed and not args and not kwargs and isinstance(fine_inputs.Path.is_file,Mock)and fine_inputs.Path.is_file.return_value is False and isinstance(fine_inputs.source_inventory,Mock)and isinstance(fine_inputs.read_metadata,Mock)
  if not allowed:return forbidden('fine_inputs.make_spec')(*args,**kwargs)
  record('negative_admission_rejection_with_all_data_and_inventory_mocked');return original_make_spec()
 stack.enter_context(patch.object(fine_inputs,'make_spec',negative_admission_only))
 blocked=((fine_screen,('make_spec','required_inputs','build','load','verified_bytes','_cache','_graph','_cache_after','_fine_raw_frame','_coarse_raw_frame','_geometry_frame','archive')),(fine_inputs,('required_inputs','read_metadata','_load_publications','source_inventory','digest')),(fine_fields,('geometry',)),(fine_post,('build','_load','_carrier','_geometry','_archive','_module','_case_scalars','_cross_grid')),(frozen_layer_dtn_backend,('make_spec','required_inputs','build','_metadata','_graph','_graph_records','save_eigenvector_cache')),(frozen_fourier_v1,('make_spec','required_inputs','build')))
 for module,names in blocked:
  for name in names:
   if hasattr(module,name):stack.enter_context(patch.object(module,name,forbidden(module.__name__+'.'+name)))
 # Small explicit fixture matrices/profiles are permitted; native dimensions fail.
 square=lambda a,n:hasattr(a,'shape')and len(a.shape)==2 and a.shape[0]==a.shape[1]and 0<a.shape[0]<=n
 stack.enter_context(patch.object(fine_solver,'solve',tiny('manufactured_CEM_solver_calls',fine_solver.solve,lambda a,k:len(a)>1 and square(a[1],4))))
 stack.enter_context(patch.object(fine_fields,'profiles',tiny('manufactured_modal_profile_calls',fine_fields.profiles,lambda a,k:len(a)>4 and square(a[1],4)and len(a[4])<=4)))
 stack.enter_context(patch.object(fine_fields,'fields',tiny('manufactured_field_constructor_calls',fine_fields.fields,lambda a,k:len(a)>5 and square(a[1],4)and len(a[5])<=4)))
 stack.enter_context(patch.object(screen_metrics,'evaluate',tiny('synthetic_angular_metric_fixture_calls',screen_metrics.evaluate,lambda a,k:len(a)>1 and hasattr(a[1],'shape')and a[1].shape[0]<=64)))
 stack.enter_context(patch.object(cached_metrics,'summarize',tiny('synthetic_cached_metric_fixture_calls',cached_metrics.summarize,lambda a,k:len(a)>1 and hasattr(a[1],'shape')and a[1].shape[0]<=64)))
 stack.enter_context(patch.object(physical_projector,'build_overlap',tiny('synthetic_physical_projection_calls',physical_projector.build_overlap,lambda a,k:len(a)>2 and len(a[0])<=36 and len(a[2])<=36)))
 stack.enter_context(patch.object(np.linalg,'solve',tiny('small_independent_direct_linear_solves',np.linalg.solve,lambda a,k:len(a)>0 and square(a[0],8))))
 stack.enter_context(patch.object(sparse_linalg,'gmres',tiny('small_manufactured_GMRES_calls',sparse_linalg.gmres,lambda a,k:len(a)>0 and square(a[0],6))))
 for name in('load','fromfile','memmap'):stack.enter_context(patch.object(np,name,forbidden('numpy.'+name)))
 for name in('eig','eigh','eigvals','eigvalsh'):stack.enter_context(patch.object(np.linalg,name,forbidden('numpy.linalg.'+name)))
