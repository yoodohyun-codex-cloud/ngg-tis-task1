"""Pure canonical input derivation for one uncalibrated SC-permittivity sensitivity.

No I/O on import. The sole finite controller supplies exact frozen bytes and
owns preparation, source publication, class pinning, execution and accounting.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path

ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-all-layer-sensitivity-20261025/source')
RUN=Path('/dev/shm/task1-all-layer-sensitivity-20261025-run')
CASE='baseline-square15-sc-eps1100-xy80'
SCHEMA='task1-whole-layer-sensitivity-native-v1'
TEMPLATE=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/configs/baseline-square15-xy80.properties'
MASK=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/masks/baseline-square15-h0.625.csv'
TEMPLATE_SHA256='f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b'
MASK_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
FREQUENCIES=(3000,3030,9000,9090)
EPS0=8.8541878128e-12
MATERIALS=(('sc',.0002,110000.,1100.),('dermis',.2,10000.,10000.),('fat',.04,1000.,1000.),('muscle',.3,100000.,100000.))

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
    require(run.is_absolute()and run.parent==Path('/dev/shm')and run.name.startswith('task1-all-layer-sensitivity-20261025-run')and '..'not in run.parts,
        'Unique own canonical tmpfs run pathname required')
    require(digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256,'Frozen canonical configuration/mask bytes required')
    old=properties(template_raw)
    require(old['sc.epsilon_r']=='110000'and old['frequencies']=='3000,3030,9000,9090'and old['channels']=='2'and
        old['h_mm']=='0.625'and old['validation.sc_cells']=='2'and old['bulk.counts']=='14,14,40'and old['mask.sha256']==MASK_SHA256,
        'Exact canonical baseline source properties required')
    config=template_raw.replace(b'sc.epsilon_r=110000\n',b'sc.epsilon_r=1100\n',1)
    before=('mask.path='+old['mask.path']+'\n').encode();after=('mask.path='+str(run/'masks'/(CASE+'.csv'))+'\n').encode()
    require(config.count(before)==1,'One source mask path assignment');config=config.replace(before,after,1)
    proposed=properties(config);changed={key:dict(old=old[key],proposed=proposed[key])for key in old if old[key]!=proposed[key]}
    require(set(changed)=={'sc.epsilon_r','mask.path'}and old.keys()==proposed.keys(),'Only SC-permittivity sensitivity plus explicit mask path mapping')
    return dict(case_id=CASE,config_bytes=config,mask_bytes=bytes(mask_raw),config_file=str(run/'configs'/(CASE+'.properties')),
        mask_file=str(run/'masks'/(CASE+'.csv')),config_sha256=digest(config),mask_sha256=digest(mask_raw),
        source_config_sha256=digest(template_raw),source_mask_sha256=digest(mask_raw),config_diff=changed,
        scope='One four-layer uncalibrated sensitivity condition; not a paper reproduction, material calibration or full convergence result',
        material_table=material_table(),material_calibrated=False,new_native_conditions_requested=1,new_native_RHS_requested=8)

def material_table():
    """All four layers/frequencies, explicit missing provenance and changed factor."""
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
                changed=layer=='sc',change_factor_epsilon=.01 if layer=='sc' else 1.,
                rationale='Predeclared100-fold SC epsilon reduction isolates sensitivity of legacy capacitive dominance; not tuned for a desired spatial gradient' if layer=='sc' else 'Untouched comparator assumption after whole-layer provenance audit; not certified by the cited papers'))
    return dict(schema='task1-four-layer-assumption-material-table-v1',case_id=CASE,rows=rows,
        evidence_backed_four_layer_material_reset='deferred_missing_independent_skin_and_carrier_raw_material_data',
        scalar_sigma_epsilon_dispersion=False,complex_gamma_frequency_dependence=True,
        scenario_single_changed_numeric_key='sc.epsilon_r',material_calibrated=False,new_PDE_executed=False)
