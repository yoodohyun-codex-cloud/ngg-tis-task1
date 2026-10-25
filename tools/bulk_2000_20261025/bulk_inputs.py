"""Pure bulk refinement input builder; counts/masks evaluated by sole owner only."""
from pathlib import Path
import hashlib,json,math
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-bulk-2000-20261025/source')
RUN=Path('/dev/shm/task1-bulk-2000-20261025-run')
CASE='baseline-square15-human-sine2000-bulk18-18-56-xy100'
SCHEMA='task1-bulk-2000-native-v1'
COMPARATOR=Path('/workspace/task1-xy100-2000-20261025-run-r2')
COMPARATOR_CASE='baseline-square15-human-sine2000-xy100'
TEMPLATE=COMPARATOR/'configs'/(COMPARATOR_CASE+'.properties')
MASK=COMPARATOR/'masks'/(COMPARATOR_CASE+'.csv')
TEMPLATE_SHA256='0a0caf4e625789060abf76e84f26708dea86c25520754593428b4a1c06374617'
MASK_SHA256='884d3bc2537bc88d87a82bffcd735a197c48afda02485573ec27b80469b688ca'
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

def bulk_cell_count():
 """No call at import. Soleownerprepare counts unchangedXY columns."""
 h=.0005;nx=100;nxy=0
 for j in range(nx):
  for i in range(nx):
   x=-.025+(i+.5)*h;y=-.025+(j+.5)*h
   if x*x+y*y<.025*.025:nxy+=1
 cells=nxy*(2+18+18+56);require(0<cells<=800000,'Actual refinedbulk count within original800k cap')
 return cells,nxy

def derive_config(template_raw,mask_raw,material_raw,run=RUN):
 require(Path(run)==RUN and digest(template_raw)==TEMPLATE_SHA256 and digest(mask_raw)==MASK_SHA256,'Exact completedXY100 coarsebulk configuration and physical pad mask')
 material,rows=verified_materials(material_raw);contact_raw=CONTACT_INPUT.read_bytes();require(digest(contact_raw)==CONTACT_SHA256,'Exact unchanged actual2000Hz contact receipt')
 contact=json.loads(contact_raw);z=next(r for r in contact['rows']if r['frequency_Hz']==2000)
 old=properties(template_raw);require(old['h_mm']=='0.5'and old['frequencies']=='2000'and old['validation.sc_cells']=='2'and old['bulk.counts']=='14,14,40','Onlybulk18/18/56refinement on sameXY/SC')
 cells,nxy=bulk_cell_count();new=dict(old)
 new.update({'bulk.counts':'18,18,56','validation.expected_cells':str(cells),'mask.path':str(RUN/'masks'/(CASE+'.csv')),
  'material.input_path':str(RUN/'material-input.json'),'contact.input_path':str(RUN/'contact-receipt.json')})
 require(new['material.input_sha256']==MATERIAL_SHA256 and new['contact.input_sha256']==CONTACT_SHA256,'Unchanged material and contact receipt hashes')
 for l in LAYERS:
  require(float(new[l+'.sigma.2000'])==rows[l,2000]['sigma_S_m']and float(new[l+'.epsilon_r.2000'])==rows[l,2000]['epsilon_r'],'No material reevaluation')
 require(float(new['z.2000.re'])==z['area_real_ohm_m2']and float(new['z.2000.im'])==z['area_imag_ohm_m2'],'No contact reevaluation')
 changed={k:dict(old=old[k],proposed=new[k])for k in old if old[k]!=new[k]}
 require(old.keys()==new.keys()and set(changed)=={'bulk.counts','validation.expected_cells','mask.path','material.input_path','contact.input_path'},'Onlybulkcounts/expectedN/storage mappings change')
 config=('\n'.join(k+'='+v for k,v in new.items())+'\n').encode()
 return dict(config_bytes=config,mask_bytes=bytes(mask_raw),material_bytes=bytes(material_raw),contact_bytes=contact_raw,
  config_file=str(RUN/'configs'/(CASE+'.properties')),mask_file=str(RUN/'masks'/(CASE+'.csv')),config_sha256=digest(config),mask_sha256=MASK_SHA256,
  material_input_sha256=MATERIAL_SHA256,contact_receipt_sha256=CONTACT_SHA256,native_cells=cells,native_XY_columns=nxy,
  config_diff=dict(changed=changed,scope='One same2000Hz bulk14/14/40to18/18/56 numerical diagnostic; no human/TIS validation'),material_table=material)
