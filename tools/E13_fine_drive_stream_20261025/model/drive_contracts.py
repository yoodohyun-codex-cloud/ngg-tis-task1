"""Pure protocol checks; import performs no research work or filesystem access."""
import math
from pathlib import Path

FIELD_ATOL=1e-10
ELECTRICAL_ATOL=1e-15
RTOL=2e-7
SAVED_FLOAT_MAPS=('AM_max2074','carrier_RMS','Jtotal_vector_RMS')
UNAVAILABLE_SAVED_FLOAT_MAPS=('AM_x','AM_y','AM_z','carrier0_RMS','carrier1_RMS')

def require(ok,message):
    if not ok:raise ValueError(message)

def fullhex(value,n):
    return type(value)is str and len(value)==n and all(c in '0123456789abcdef' for c in value)

def relative_multipliers(r):
    require(type(r)in(int,float)and math.isfinite(r)and r>0,'Positive finite relative active-current ratio multiplier')
    return min(1.,float(r)),min(1.,1./float(r))

def baseline_close(actual,reference,*,electrical=False):
    return all(type(v)in(int,float)and math.isfinite(v)for v in(actual,reference)) and abs(actual-reference)<=(ELECTRICAL_ATOL if electrical else FIELD_ATOL)+RTOL*abs(reference)

def validate_descriptor(desc,*,expected_commit,expected_target,publication_role,expected_role):
    require(type(desc)is dict and publication_role==expected_role and expected_role in('source','result'),'Exact source/result artifact ownership; no fallback')
    require(fullhex(expected_commit,40)and desc.get('publication_commit')==expected_commit and desc.get('publication_target')==expected_target,'Exact immutable artifact commit and repository target')
    require(fullhex(desc.get('SHA256'),64)and type(desc.get('bytes'))is int and 0<desc['bytes']<80*1024**2 and desc.get('readback_passed')is True,'Actual full SHA/bytes/readback artifact proof')
    p=Path(desc.get('path',''));require(p.is_absolute()and '..'not in p.parts,'Absolute explicit local artifact path; no traversal')
    require(type(expected_target)is str and not expected_target.startswith('/')and '..'not in Path(expected_target).parts,'Safe repository-relative target')
    return desc

def require_baseline_QA(receipt):
    require(type(receipt)is dict and receipt.get('status')=='passed'and receipt.get('baseline_multiplier')==1.,'Original multiplier-one QA must pass before new allocations')
    checks=receipt.get('map_checks');require(type(checks)is dict and set(checks)==set(SAVED_FLOAT_MAPS)and all(type(v)is dict and v.get('passed')is True for v in checks.values()),'Every actually saved Float64 scalar map must agree')
    require(receipt.get('unavailable_saved_float_maps')==list(UNAVAILABLE_SAVED_FLOAT_MAPS),'Five unsaved pixel maps explicitly unavailable for original-reference agreement; never invented')
    for name in('statistics_passed','electrical_passed','source_identity_passed'):
        require(receipt.get(name)is True,'Complete baseline evidence '+name)
    return True
