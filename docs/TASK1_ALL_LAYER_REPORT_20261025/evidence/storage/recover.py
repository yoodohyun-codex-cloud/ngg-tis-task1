import sys,os,json,time,hashlib,shutil,subprocess
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_bounded_continuation as bounded
import task1_resource_policy as policy
OUT=Path('/dev/shm/task1-storage-zero-block-20261025');LEDGER=ROOT/'runtime/task1-budget.json';TARGET=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/lib/libjsvml.so')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
 with p.open('x')as f:json.dump(o,f,indent=2)
with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
 start=time.monotonic();ledger=policy.load_ledger(LEDGER);assert policy.remaining_seconds(ledger)>=30
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 before=dict(SHA256=sha(TARGET),bytes=TARGET.stat().st_size,allocated_bytes=TARGET.stat().st_blocks*512,root_free_bytes=shutil.disk_usage(ROOT).free)
 assert before['root_free_bytes']>=2*1024**3
 write(OUT/'preregistration.json',dict(action='Deallocate only all-zero physical blocks; logical bytes/hash remain identical',target=str(TARGET),before=before,cap_seconds=30,source_SHA256=sha(Path(__file__)),new_PDE=0,no_logical_file_deleted=True,original_root_reserve_bytes=2*1024**3))
 error=None
 try:
  subprocess.run(['fallocate','--dig-holes',str(TARGET)],check=True,timeout=20)
  after=dict(SHA256=sha(TARGET),bytes=TARGET.stat().st_size,allocated_bytes=TARGET.stat().st_blocks*512,root_free_bytes=shutil.disk_usage(ROOT).free)
  assert after['SHA256']==before['SHA256']and after['bytes']==before['bytes']and after['root_free_bytes']>=2*1024**3
 except BaseException as e:error=str(e);raise
 finally:
  elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=OUT.name,stage='non_destructive_zero_block_storage_recovery',status='logical_bytes_verified_unchanged'if error is None else'failed_preserved',seconds=elapsed,finished_utc=bounded.now(),error=error))
  raw=json.dumps(ledger,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();assert shutil.disk_usage(ROOT).free>=2*1024**3+len(raw)+8192
  tmp=LEDGER.with_name('task1-budget-zero-block.tmp')
  with tmp.open('xb')as f:f.write(raw)
  os.replace(tmp,LEDGER)
  receipt=dict(status='logical_bytes_verified_unchanged'if error is None else'failed_preserved',before=before,after=after,physical_bytes_recovered=before['allocated_bytes']-after['allocated_bytes'],elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),new_PDE=0,logical_file_deleted=False,installation_changed=False,error=error)
  write(OUT/'receipt.json',receipt);print(json.dumps(receipt))
