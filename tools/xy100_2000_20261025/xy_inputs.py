"""Pure XY refinement input builder; counts/masks evaluated by sole owner only."""
from pathlib import Path
import hashlib,json,math
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-xy100-2000-20261025/source')
RUN=Path('/workspace/task1-xy100-2000-20261025-run-r2')
CASE='baseline-square15-human-sine2000-xy100'
SCHEMA='task1-xy100-2000-native-v1'
COMPARATOR=Path('/workspace/task1-experiment-2000-2010-20261025-run')
COMPARATOR_CASE='baseline-square15-human-sine2000-2010-xy80'
TEMPLATE=COMPARATOR/'configs'/(COMPARATOR_CASE+'.properties')
MASK=COMPARATOR/'masks'/(COMPARATOR_CASE+'.csv')
TEMPLATE_SHA256='61830d8b2abf39a2458666df2b26a0bfb1e585873f3e3002f4e29ba1ab76af13'
MASK_SHA256='7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2'
MATERIAL_INPUT=SOURCE/'material-input.json';CONTACT_INPUT=SOURCE/'contact-receipt.json'
MATERIAL_SHA256='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA256='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
FREQUENCIES=(2000,);LAYERS=('sc','dermis','fat','muscle')
def require(ok,message):
 if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def properties(raw):
 out={}
 for line in raw.decode().splitlines():
  if not line.strip()or line.lstrip().startswith('#'):continue
  require('='in line,'Assignment required');k,v=line.split('=',1);k=k.strip();require(k not in out,'Duplicate property');out[k]=v.strip()
 return out
def verified_materials(raw):
 require(digest(raw)==MATERIAL_SHA256,'Byte-identical actual2000/2010 material receipt required')
 obj=json.loads(raw);rows={}
 for row in obj['rows']:
  require(row['source_verified']is True and row['assignment_type']=='declared_surrogate','Preserve declared source and surrogate scope')
  rows[row['layer'],row['frequency_Hz']]=row
 require(len(rows)==8 and all((l,2000)in rows for l in LAYERS),'Actual old receipt8rows including all2000Hz layers')
 return obj,rows

def refine_mask_and_count():
 """No call at import. Ownerprepare computes count and full-face mask."""
 h=.0005;nx=100;nxy=0
 for j in range(nx):
  for i in range(nx):
   x=-.025+(i+.5)*h;y=-.025+(j+.5)*h
   if x*x+y*y<.025*.025:nxy+=1
 cells=nxy*70;require(0<cells<=800000,'Actual refined cell count within existing native limit')
 lines=['pad,i,j,area_m2'];starts=((15,15),(55,55),(55,15),(15,55));areas=[0.]*4
 for pad,(i0,j0)in enumerate(starts):
  for j in range(j0,j0+30):
   for i in range(i0,i0+30):
    x=-.025+(i+.5)*h;y=-.025+(j+.5)*h;require(x*x+y*y<.025*.025,'Physical square patch must belong to cylinder')
    area=h*h;areas[pad]+=area;lines.append(str(pad)+','+str(i)+','+str(j)+','+format(area,'.17g'))
 require(len(lines)==3601 and all(abs(a/.000225-1)<=1e-12 for a in areas),'Same225mm2 pads on finer full-face mask')
 return ('\n'.join(lines)+'\n').encode(),cells,nxy

def derive_config(template_raw,old_mask_raw,material_raw,run=RUN):
 require(Path(run)==RUN and digest(template_raw)==TEMPLATE_SHA256 and digest(old_mask_raw)==MASK_SHA256,'Exact existing2000Hz coarse operator source')
 material,rows=verified_materials(material_raw);contact_raw=CONTACT_INPUT.read_bytes();require(digest(contact_raw)==CONTACT_SHA256,'Byte-identical actual2k contact receipt; no interpolation/refit')
 contact=json.loads(contact_raw);z=next(r for r in contact['rows']if r['frequency_Hz']==2000)
 old=properties(template_raw);require(old['h_mm']=='0.625'and old['frequencies']=='2000,2010'and old['validation.sc_cells']=='2'and old['bulk.counts']=='14,14,40','Only XY lattice is refined')
 mask,cells,nxy=refine_mask_and_count()
 removed={l+'.'+k+'.2010'for l in LAYERS for k in('sigma','epsilon_r')}|{'z.2010.re','z.2010.im'}
 new={k:v for k,v in old.items()if k not in removed}
 new.update({'h_mm':'0.5','frequencies':'2000','mask.path':str(RUN/'masks'/(CASE+'.csv')),'mask.sha256':digest(mask),
  'material.input_path':str(RUN/'material-input.json'),'contact.input_path':str(RUN/'contact-receipt.json'),'validation.expected_cells':str(cells)})
 require(new['material.input_sha256']==MATERIAL_SHA256 and new['contact.input_sha256']==CONTACT_SHA256,'Unchanged exact material and contact receipts')
 for l in LAYERS:
  require(float(new[l+'.sigma.2000'])==rows[l,2000]['sigma_S_m']and float(new[l+'.epsilon_r.2000'])==rows[l,2000]['epsilon_r'],'No material function reevaluation')
 require(float(new['z.2000.re'])==z['area_real_ohm_m2']and float(new['z.2000.im'])==z['area_imag_ohm_m2'],'No boundary reevaluation or changed effectiveRs/area scaling')
 changed={k:dict(old=old[k],proposed=new[k])for k in old.keys()&new.keys()if old[k]!=new[k]}
 require(set(changed)=={'h_mm','frequencies','mask.path','mask.sha256','material.input_path','contact.input_path'}and set(old)-set(new)==removed and set(new)-set(old)=={'validation.expected_cells'},'Only declared XY/frequency/physical-mask storage mapping changes')
 config=('\n'.join(k+'='+v for k,v in new.items())+'\n').encode()
 return dict(config_bytes=config,mask_bytes=mask,material_bytes=bytes(material_raw),contact_bytes=contact_raw,
  config_file=str(RUN/'configs'/(CASE+'.properties')),mask_file=str(RUN/'masks'/(CASE+'.csv')),config_sha256=digest(config),mask_sha256=digest(mask),
  material_input_sha256=MATERIAL_SHA256,contact_receipt_sha256=CONTACT_SHA256,native_cells=cells,native_XY_columns=nxy,
  config_diff=dict(changed=changed,removed_inactive2010_keys=sorted(removed),added_expected_cells=cells,
   scope='One2000Hz2RHS spatial-discretization diagnostic; no TIS modulation or human validation claimed'),material_table=material)
