"""Pure two-carrier sine preparation; no model fitting or I/O on import."""
from pathlib import Path
import hashlib,json,math
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-experiment-2000-2010-20261025/source')
RUN=Path('/workspace/task1-experiment-2000-2010-20261025-run')
CASE='baseline-square15-human-sine2000-2010-xy80'
SCHEMA='task1-experiment-sine2000-2010-native-v1'
COMPARATOR=Path('/dev/shm/task1-human-tissue-20261025-run')
COMPARATOR_CASE='baseline-square15-human-reference-xy80'
TEMPLATE=COMPARATOR/'configs'/(COMPARATOR_CASE+'.properties')
MASK=COMPARATOR/'masks'/(COMPARATOR_CASE+'.csv')
TEMPLATE_SHA256='8820712d379574c307328096a2b6817da8b59aca9d5be97aa5306668f48633a0'
MASK_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
MATERIAL_INPUT=SOURCE/'material-function-audit.json'
MATERIAL_AUDIT_SHA256='a02360cced49a14c4c2a26d79139e36ba3da2d71aefb71042f7b8ce95a2e6ded'
RAW_EIS=ROOT/'NGG electrode EIS result/1015~1022/0 10.xlsx'
RAW_EIS_SHA256='3ecc99c70db1166fc2137619b6bea9dde468d724ea7bba4c89583e5ca82ac771'
FIT=ROOT/'tis-java/runs/eis-rs-window-analysis-20261019T123730Z/cases/eis010-f0500.json'
POINTS_SHA256='d5788042a0cc67c474f0335bfa0c4be8a51f467f3298538421d60767c15cf144'
FREQUENCIES=(2000,2010);LAYERS=('sc','dermis','fat','muscle');EPS0=8.8541878128e-12

def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def properties(raw):
    out={}
    for line in raw.decode().splitlines():
        if not line.strip()or line.lstrip().startswith('#'):continue
        require('='in line,'Assignment required');k,v=line.split('=',1);k=k.strip();require(k not in out,'Duplicate key');out[k]=v.strip()
    return out

def verified_materials(raw):
    require(digest(raw)==MATERIAL_AUDIT_SHA256,'Exact already-published24row material audit; no material model reevaluation')
    source=json.loads(raw);rows=[dict(r)for r in source['rows']if r['frequency_Hz']in FREQUENCIES]
    require(len(rows)==8 and {(r['layer'],r['frequency_Hz'])for r in rows}=={(l,f)for l in LAYERS for f in FREQUENCIES},'Eight published2kHz carrier material rows required')
    for r in rows:
        require(r['source_verified']is True and r['assignment_type']=='declared_surrogate'and r['sigma_unit']=='S/m'and r['epsilon_r_unit']=='dimensionless','Preserve exact source-verified surrogate assignment and units')
        require(all(math.isfinite(r[k])and r[k]>0 for k in('sigma_S_m','epsilon_r')),'Finite positive existing material rows')
        r['source_frequency_role']=r.get('frequency_role');r['frequency_role']='actual_new_sine_carrier';r['active_PDE_carrier']=True
    return dict(schema='task1-human-tissue-materials-v1',status='source_verified_for_declared_scope',material_version='HREF-MIX-v1',
        scenario='Explicit2000/2010Hz sine common-return experiment-model scenario; actual hardware waveform/topology unverified',
        source_audit_sha256=digest(raw),rows=rows),{(r['layer'],r['frequency_Hz']):r for r in rows}

def contact_receipt():
    # Existing fitted Rs is reused; no refit.500 is the lower FIT WINDOW in Hz,
    # not500ohm. Log-frequency interpolation is repeated at actual new carriers.
    from update_ngg_eis import read_spectrum,interpolate_complex
    raw=RAW_EIS.read_bytes();fit=json.loads(FIT.read_bytes())
    require(digest(raw)==RAW_EIS_SHA256 and fit['status']=='complete'and fit['case_id']=='eis010-f0500'and fit['cutoff_Hz']==500,'Exact nominal10nm/500Hz-window fit/raw evidence')
    points=read_spectrum(RAW_EIS);canonical=digest(json.dumps(points,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    require(len(points)==30 and canonical==POINTS_SHA256 and fit['input']['points_canonical_JSON_sha256']==canonical,'Exact original30 measured points; no migrated-path assumption')
    rs=float(fit['selected_fit']['Rs_ohm']);require(rs==236.5717747232937,'Frozen selected effectiveRs; never confuse500Hz with500ohm')
    rows=[]
    for f in FREQUENCIES:
        p=interpolate_complex(points,f);real=p['Z_real_ohm']-rs;imag=p['Z_imag_ohm'];require(real>=0,'Passive measured-minus-effectiveRs boundary')
        rows.append(dict(frequency_Hz=f,measured_real_ohm=p['Z_real_ohm'],measured_imag_ohm=imag,selected_Rs_ohm=rs,
            area_real_ohm_m2=real*1e-4,area_imag_ohm_m2=imag*1e-4,bracket_frequency_Hz=p['bracket_frequency_Hz'],source_ranges=p['source_ranges'],
            log_frequency_weight=p['log_frequency_weight']))
    return dict(schema='task1-actual-carrier-contact-receipt-v1',coating_nm=10,fit_window_lower_Hz=500,selected_Rs_ohm=rs,
        raw_XLSX_sha256=RAW_EIS_SHA256,points_canonical_JSON_sha256=canonical,fit_file_sha256=digest(FIT.read_bytes()),
        measurement_area_m2=1e-4,Rs_subtractions=1,measurement_area_multiplications=1,division_by_two=False,
        pad_area_scaling='Specific impedance passed once to CEM; actual contact patch areas applied by unchanged ShapeNet',
        raw_reconstruction='Existing frozen stdlib XLSX reader and log-frequency interpolation; no CPE refit/no3kHz impedance reuse',
        PBS_as_human_skin_validated=False,actual_equipment_topology_verified=False,rows=rows)

def derive_config(template_raw,mask_raw,material_raw,run=RUN):
    require(Path(run)==RUN and digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256,'Exact SC2 geometry/circuit/mask source')
    old=properties(template_raw);material,rows=verified_materials(material_raw);contact=contact_receipt()
    material_bytes=(json.dumps(material,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
    contact_bytes=(json.dumps(contact,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
    keep={k:v for k,v in old.items()if not(k.startswith('z.')or any(k.startswith(l+'.sigma.')or k.startswith(l+'.epsilon_r.')for l in LAYERS))}
    keep.update(frequencies='2000,2010',**{'mask.path':str(RUN/'masks'/(CASE+'.csv')),'material.input_path':str(RUN/'material-input.json'),
        'material.input_sha256':digest(material_bytes),'contact.input_path':str(RUN/'contact-receipt.json'),'contact.input_sha256':digest(contact_bytes)})
    for f in FREQUENCIES:
        for l in LAYERS:
            r=rows[l,f];keep[l+'.sigma.'+str(f)]=format(r['sigma_S_m'],'.17g');keep[l+'.epsilon_r.'+str(f)]=format(r['epsilon_r'],'.17g')
    for r in contact['rows']:keep['z.'+str(r['frequency_Hz'])+'.re']=format(r['area_real_ohm_m2'],'.17g');keep['z.'+str(r['frequency_Hz'])+'.im']=format(r['area_imag_ohm_m2'],'.17g')
    config=('\n'.join(k+'='+v for k,v in keep.items())+'\n').encode();new=properties(config)
    unchanged={k:v for k,v in old.items()if k not in {'frequencies','mask.path','material.input_path','material.input_sha256'}and not(k.startswith('z.')or any(k.startswith(l+'.sigma.')or k.startswith(l+'.epsilon_r.')for l in LAYERS))}
    require(all(new[k]==v for k,v in unchanged.items())and new['validation.sc_cells']=='2','Geometry/mesh/circuit preserved; only declared carrier/material/contact/waveform scenario changes')
    return dict(config_bytes=config,mask_bytes=bytes(mask_raw),material_bytes=material_bytes,contact_bytes=contact_bytes,
        config_file=str(RUN/'configs'/(CASE+'.properties')),mask_file=str(RUN/'masks'/(CASE+'.csv')),
        config_sha256=digest(config),mask_sha256=digest(mask_raw),material_input_sha256=digest(material_bytes),contact_receipt_sha256=digest(contact_bytes),
        config_diff=dict(changed={k:dict(old=old.get(k),proposed=new.get(k))for k in set(old)|set(new)if old.get(k)!=new.get(k)},
            scope='SC2samephysicalgeometry; explicit2k/2010sine carrier scenario, actual equipment settings unverified'),
        material_table=material)
