import sys,os,json,time,hashlib,shutil,subprocess,fcntl
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_bounded_continuation as bounded
import task1_resource_policy as policy
OUT=Path('/dev/shm/task1-storage-zero-block-20261025');LEDGER=ROOT/'runtime/task1-budget.json'
ORIGINAL=ROOT/'runtime/backups/cloud-baseline-20261019T185900Z.tar';CACHE=ROOT/'runtime/downloaded/git-cloud-baseline-20261019T185900Z.tar'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def write(p,o):
 with p.open('x')as f:json.dump(o,f,indent=2)
with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
 start=time.monotonic();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});ledger=policy.load_ledger(LEDGER);assert policy.remaining_seconds(ledger)>=90
 h=sha(ORIGINAL);assert h==sha(CACHE)=='443a713e6cedb177dec3309a45a8251e7ef6e57b6bf25e296510accf520e63d4'
 before=shutil.disk_usage(ROOT).free;original_inode=ORIGINAL.stat().st_ino;cached_inode=CACHE.stat().st_ino
 write(OUT/'restore-plan.json',dict(method='Try exact copy-on-write cloning; if unsupported preserve cache bytes in tmpfs, then atomically share verified immutable backup inode at unchanged cache pathname',SHA256=h,bytes=ORIGINAL.stat().st_size,root_original=str(ORIGINAL),cache_path=str(CACHE),source_SHA256=sha(Path(__file__)),PDE=0,original_backup_unchanged=True,filename_deletion_requested=False))
 method=None;clone_error=None
 try:
  with ORIGINAL.open('rb')as src,CACHE.open('r+b')as dst:fcntl.ioctl(dst.fileno(),0x40049409,src.fileno())
  method='copy_on_write_reflink_existing_identical_cache'
 except OSError as error:
  clone_error=str(error);saved=OUT/'cache-original.tar'
  with CACHE.open('rb')as src,saved.open('xb')as dst:shutil.copyfileobj(src,dst,1024**2)
  assert sha(saved)==h
  temporary=CACHE.with_name(CACHE.name+'.verified-shared-inode');os.link(ORIGINAL,temporary);assert sha(temporary)==h
  os.replace(temporary,CACHE);method='immutable_backup_and_cache_share_inode; byte-identical cache_original_also_preserved_in_tmpfs'
 assert sha(ORIGINAL)==sha(CACHE)==h and ORIGINAL.stat().st_ino==original_inode
 after=shutil.disk_usage(ROOT).free;assert after>=2*1024**3+LEDGER.stat().st_size+16384
 # Failed earlier allocation attempt had no final clock receipt; charge its full30s cap conservatively.
 elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed+30
 ledger['runs'].extend([dict(run_id=OUT.name,stage='zero_block_allocation_attempt',status='failed_overlay_copy_up_preserved_hash_no_logical_data_change',seconds=30,finished_utc=bounded.now(),cost='full30second_cap_charged_conservatively_missing_final_clock_receipt'),dict(run_id=OUT.name,stage='restore_root_reserve_by_verified_duplicate_cache',status='completed_hash_verified',seconds=elapsed,finished_utc=bounded.now())])
 raw=json.dumps(ledger,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();assert after>=2*1024**3+len(raw)+8192
 temporary=LEDGER.with_name('task1-budget-reserve-recovered.tmp')
 with temporary.open('xb')as f:f.write(raw)
 os.replace(temporary,LEDGER)
 receipt=dict(status='root_reserve_restored_original_bytes_verified',method=method,clone_error=clone_error,SHA256=h,bytes=ORIGINAL.stat().st_size,root_free_before=before,root_free_after=shutil.disk_usage(ROOT).free,original_inode=original_inode,cache_inode_before=cached_inode,cache_inode_after=CACHE.stat().st_ino,logical_filenames_preserved=True,original_archive_preserved=True,cache_original_also_preserved_in_tmpfs=(OUT/'cache-original.tar').exists(),write_alias_warning='Shared immutable archive/cache inode: future modifications prohibited under frozen-original rule'if method.startswith('immutable')else None,elapsed_seconds=elapsed,previous_failed_stage_charge_seconds=30,remaining_approved_seconds=policy.remaining_seconds(ledger),new_PDE=0,Windows_saved=False)
 write(OUT/'restore-receipt.json',receipt);print(json.dumps(receipt))
