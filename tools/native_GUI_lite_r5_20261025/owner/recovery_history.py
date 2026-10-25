"""Specific metadata-only first pre-S failure preservation, import inert."""
import hashlib,json
from pathlib import Path
SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-owner-20261025/source')
OLD_RUN=Path('/dev/shm/task1-native-GUI-lite-20261025-run')
ARCHIVE=SOURCE/'previous-preS-failure-archive.json'
ARCHIVE_SHA='15076e65f426958b5fcff5f96a4c1145189e7424944d7bd30273b9f2c4b7c008'

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Canonical bounded original code/metadata')
 return json.loads(p.read_bytes())
def validate_archive_record(a):
 require(a.get('schema')=='task1-native-GUI-lite-R1-preS-failure-archive-v1'and a.get('status')=='actual_failed_before_source_publication_preserved'and a.get('original_run')==str(OLD_RUN),'Only actual original pre-S failure is preserved')
 require(a.get('original_owner_status')=='failed_preserved'and a.get('actual_phase')=='preparing'and a.get('terminal_UTC')=='2026-10-25T15:39:32.995873+00:00','Exact original terminal phase/status, no completed GUI inference')
 for key in('source_publication_available','result_publication_available','actual_MFG_run','actual_native_byte_reads','actual_GUI_built'):require(a.get(key)is False,'No nonexistent original source/result/test/native/GUI evidence '+key)
 require(a.get('no_original_files_modified')is True and isinstance(a.get('original_metadata_files'),list)and a['original_metadata_files']and isinstance(a.get('original_registered_source_files'),list)and a['original_registered_source_files'],'Complete original code/metadata archive')
 required={'source-publication/result-publication.json','result-publication/result-publication.json','synthetic-test-receipt.json','worker-receipt.json','index.html'}
 require(required.issubset(set(a.get('actual_absent_outputs',[]))),'Original absent source/result/tests/GUI recorded honestly')
 for row in a['original_registered_source_files']:
  raw=row['UTF8'].encode('utf-8');require(len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['SHA256'],'Every original registered source recoverable byte exactly from archive')
 return True

def verify_history(admission,registered_sources):
 descriptor=admission.get('previous_preS_failure',{})
 require(descriptor.get('run')==str(OLD_RUN)and descriptor.get('archive_SHA256')==ARCHIVE_SHA and descriptor.get('source_publication_available')is False and descriptor.get('result_publication_available')is False,'Root explicitly acknowledges exact first pre-S failure, not nonexistent S/R')
 require(digest(ARCHIVE)==ARCHIVE_SHA and registered_sources.get(str(ARCHIVE))==ARCHIVE_SHA,'Immutable fully registered failure archive')
 archive=read(ARCHIVE);validate_archive_record(archive);refs={str(ARCHIVE):ARCHIVE_SHA}
 for row in archive['original_metadata_files']:
  original=Path(row['original_path']);copy=SOURCE/row['archive_source_name'];require(copy.parent==SOURCE,'Flat original metadata alias only')
  require(original.is_file()and original==original.resolve()and not original.is_symlink()and original.stat().st_size==row['bytes']and digest(original)==row['SHA256'],'Original failure metadata remains byte unchanged')
  require(copy.read_bytes()==original.read_bytes()and registered_sources.get(str(copy))==row['SHA256'],'Actual full original bytes included in new source publication')
  refs[str(original)]=row['SHA256'];refs[str(copy)]=row['SHA256']
 for row in archive['original_registered_source_files']:
  p=Path(row['original_path']);require(p.read_bytes()==row['UTF8'].encode()and digest(p)==row['SHA256'],'Original code/source map remains unchanged')
  refs[str(p)]=row['SHA256']
 absent=[str(OLD_RUN/name)for name in archive['actual_absent_outputs']]
 require(all(not Path(p).exists()for p in absent),'An originally absent pre-S output appeared; inspect without fabricating history')
 owner=read(OLD_RUN/'receipt.json');require(owner['status']=='failed_preserved'and owner['failed_phase']=='preparing'and owner['GUI_generated']is False and owner['new_PDE_RHS']==owner['new_Q_loads']==owner['new_angular_evaluations']==0,'Actual first attempt failed before source/tests/native phase')
 bridge_path=SOURCE/'recovery-namespace-bridge.json';bridge=read(bridge_path);require(registered_sources.get(str(bridge_path))==digest(bridge_path),'Root source inventory binds recovery namespace/provenance delta')
 require(bridge.get('frozen_MODEL_unchanged')is True and bridge.get('scientific_algorithms_changed')is False and bridge.get('legacy_mask_publication_ownership_fix')=='first_S/MP_S for masks; original R for raw/scalar/grid','Explicit namespace and source/result provenance correction only')
 for row in bridge['files']:
  require(digest(row['original_path'])==row['original_SHA256']and digest(row['new_path'])==row['new_SHA256']and registered_sources.get(row['new_path'])==row['new_SHA256'],'Full old/new source identities from reviewed bridge')
 refs[str(bridge_path)]=digest(bridge_path)
 return dict(schema='task1-GUI-lite-R2-prior-preS-failure-proof-v1',status='actual_preS_failure_preserved_no_original_publication',archive_SHA256=ARCHIVE_SHA,old_owner_status=owner['status'],old_phase=owner['failed_phase'],old_source_publication_available=False,old_result_publication_available=False,old_tests_run=False,old_native_phase_reached=False,old_GUI_generated=False,original_metadata_and_code_before_SHA_passed=True,bridge_SHA256=digest(bridge_path)),refs,absent
