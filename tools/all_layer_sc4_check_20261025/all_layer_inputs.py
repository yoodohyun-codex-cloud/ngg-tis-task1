"""Pure input derivation for one SC2-to-SC4 adjacency check.

No I/O on import. The sole finite controller supplies exact frozen bytes and
owns preparation, source publication, class pinning, execution and accounting.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path

ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-all-layer-sc4-check-20261025/source')
RUN=Path('/dev/shm/task1-all-layer-sc4-check-20261025-run')
CASE='baseline-square15-sc-eps1100-sc4-xy80'
SCHEMA='task1-whole-layer-sc4-check-native-v1'
COMPARATOR=Path('/dev/shm/task1-all-layer-sensitivity-20261025-run')
COMPARATOR_CASE='baseline-square15-sc-eps1100-xy80'
TEMPLATE=COMPARATOR/'configs'/(COMPARATOR_CASE+'.properties')
MASK=COMPARATOR/'masks'/(COMPARATOR_CASE+'.csv')
TEMPLATE_SHA256='a9d2d08d7e69d3cf1b21e50c1af44510ba416cee95e101c77f5581dcfae1269b'
MASK_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
FREQUENCIES=(3000,3030,9000,9090)
EPS0=8.8541878128e-12
MATERIALS=(('sc',.0002,1100.,1100.),('dermis',.2,10000.,10000.),('fat',.04,1000.,1000.),('muscle',.3,100000.,100000.))

def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def properties(raw):
    require(isinstance(raw,bytes)and len(raw)<128*1024,'Bounded explicit configuration bytes')
    out={}
    for line in raw.decode('utf-8').splitlines():
        if not line.strip()or line.lstrip().startswith('#'):continue
        require('='in line,'Properties assignment required');key,value=line.split('=',1);key=key.strip();value=value.strip()
        require(key and key not in out,'Duplicate property');out[key]=value
    return out
def derive_config(template_raw,mask_raw,run=RUN):
    """Return new bytes and exact two-key diff; do not write or mutate originals."""
    run=Path(run)
    require(run.is_absolute()and run.parent==Path('/dev/shm')and run.name.startswith('task1-all-layer-sc4-check-20261025-run')and '..'not in run.parts,
        'Unique own canonical tmpfs run pathname required')
    require(digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256,'Frozen canonical configuration/mask bytes required')
    old=properties(template_raw)
    require(old['sc.epsilon_r']=='1100'and old['frequencies']=='3000,3030,9000,9090'and old['channels']=='2'and
        old['h_mm']=='0.625'and old['validation.sc_cells']=='2'and old['bulk.counts']=='14,14,40'and old['mask.sha256']==MASK_SHA256,
        'Exact completed SC2 sensitivity source properties required')
    require(template_raw.count(b'validation.sc_cells=2\n')==1,'One SC-cell-count assignment')
    config=template_raw.replace(b'validation.sc_cells=2\n',b'validation.sc_cells=4\n',1)
    before=('mask.path='+old['mask.path']+'\n').encode();after=('mask.path='+str(run/'masks'/(CASE+'.csv'))+'\n').encode()
    require(config.count(before)==1,'One source mask path assignment');config=config.replace(before,after,1)
    proposed=properties(config);changed={key:dict(old=old[key],proposed=proposed[key])for key in old if old[key]!=proposed[key]}
    require(set(changed)=={'validation.sc_cells','mask.path'}and old.keys()==proposed.keys(),'Only SC2to4 plus explicit mask path mapping')
    return dict(case_id=CASE,config_bytes=config,mask_bytes=bytes(mask_raw),config_file=str(run/'configs'/(CASE+'.properties')),
        mask_file=str(run/'masks'/(CASE+'.csv')),config_sha256=digest(config),mask_sha256=digest(mask_raw),
        source_config_sha256=digest(template_raw),source_mask_sha256=digest(mask_raw),config_diff=changed,
        scope='One SC2-to-SC4 adjacency check; unchanged four-layer material hypotheses; not a material calibration or full convergence result',
        material_table=material_table(),material_calibrated=False,new_native_conditions_requested=1,new_native_RHS_requested=8)

def material_table():
    """All four layers/frequencies, explicit missing provenance and no material changes."""
    rows=[]
    for frequency in FREQUENCIES:
        for layer,sigma,old_epsilon,epsilon in MATERIALS:
            imag=2*math.pi*frequency*EPS0*epsilon
            rows.append(dict(layer=layer,frequency_Hz=frequency,old_sigma_S_m=sigma,old_epsilon_r=old_epsilon,
                proposed_sigma_S_m=sigma,proposed_epsilon_r=epsilon,gamma_real_S_m=sigma,gamma_imag_S_m=imag,
                imag_to_real_ratio=imag/sigma,sigma_unit='S/m',epsilon_r_unit='dimensionless',epsilon0_F_m=EPS0,
                source_DOI=None,source_page=None,source_figure=None,measured_or_fit_or_assumed='explicit_legacy_sensitivity_assumption',
                temperature_C=None,recipe=None,interpolation_or_extrapolation='None; frequency-independent sigma/epsilon hypotheses; gamma imaginary part varies with omega',
                uncertainty_or_missing='Separate skin-layer bulk data and exact carrier-specific phantom material tables/fits are unavailable; not measured phantom data',
                changed=False,change_factor_epsilon=1.,
                rationale='Unchanged from the actual SC2 sensitivity; SC-cell count is the only numerical change. None of these material numbers is certified by the cited papers'))
    return dict(schema='task1-four-layer-assumption-material-table-v1',case_id=CASE,rows=rows,
        evidence_backed_four_layer_material_reset='deferred_missing_independent_skin_and_carrier_raw_material_data',
        scalar_sigma_epsilon_dispersion=False,complex_gamma_frequency_dependence=True,
        scenario_single_changed_numeric_key='validation.sc_cells',SC_cells_before=2,SC_cells_after=4,
        comparator_run_id=COMPARATOR.name,comparator_case_id=COMPARATOR_CASE,
        material_calibrated=False,new_PDE_executed=False)
