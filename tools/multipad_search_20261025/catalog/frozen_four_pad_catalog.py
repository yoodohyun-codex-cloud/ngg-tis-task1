"""Exactly eight owner-derived full-face designs for the cached coarse DtN.
No IO, mask/count calculations, NumPy or scientific work execute on import.
"""
from __future__ import annotations
import hashlib,json,math
from fractions import Fraction
from pathlib import Path
SOURCE=Path('/dev/shm/task1-design-screen-coarse-20261025/source')
U19=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
MATERIAL=U19/'material-input.json';CONTACT=U19/'contact-receipt.json'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
COARSE_CEM=Path('/dev/shm/task1-layer-dtn-cem-20261025-run')
COARSE_CEM_COMMIT='e4c09902bf529b4111c006dd4b4fb6681ca81252'
LAYERS=('sc','dermis','fat','muscle');FREQUENCIES=(2000,2010);EPS0=8.8541878128e-12
EXPECTED_IDS=('B0-square15-c10-diagonal','G1-square12-c10-diagonal','G2-square15-c8-diagonal','G3-square16-c9p5-diagonal','G4-equalarea-rect12p5x18-c9p75x9p5-diagonal','G5-signal200-return250','G6-signal250-return200','G7-square15-c10-adjacent')

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return(json.dumps(obj,allow_nan=False,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def _read(path):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded canonical source/input');return p.read_bytes()
def catalog():
 value=json.loads(_read(SOURCE/'catalog.json'));require(tuple(c['candidate_id']for c in value['candidates'])==EXPECTED_IDS,'Exact frozen first-eight order/definitions');return value

def _material_contact():
 mr=_read(MATERIAL);cr=_read(CONTACT);require(sha(mr)==MATERIAL_SHA and sha(cr)==CONTACT_SHA,'Same executed material/contact bytes, no reevaluation or refit')
 material=json.loads(mr);contact=json.loads(cr);m={(r['layer'],int(r['frequency_Hz'])):r for r in material['rows']};z={int(r['frequency_Hz']):r for r in contact['rows']};gamma={};sigma={};epsilon={};specific={}
 require(contact['Rs_subtractions']==1 and contact['measurement_area_multiplications']==1 and contact['division_by_two']is False,'EffectiveRs/measurementarea applied once, no divide2')
 for frequency in FREQUENCIES:
  gamma[str(frequency)]=[];sigma[str(frequency)]=[];epsilon[str(frequency)]=[]
  for layer in LAYERS:
   r=m[layer,frequency];s=float(r['sigma_S_m']);e=float(r['epsilon_r']);imag=2*math.pi*frequency*EPS0*e
   require(r['assignment_type']=='declared_surrogate'and s>0 and e>0 and math.isfinite(s+e+imag),'Explicit passive declared surrogate row per carrier')
   gamma[str(frequency)].append(dict(real=s,imaginary=imag));sigma[str(frequency)].append(s);epsilon[str(frequency)].append(e)
  r=z[frequency];specific[str(frequency)]=dict(real=float(r['area_real_ohm_m2']),imaginary=float(r['area_imag_ohm_m2']))
 return mr,cr,gamma,sigma,epsilon,specific

def derive_mask(candidate):
 """Root-only exact rectangle/full-pixel partition, h=.5mm, no rescale."""
 h=Fraction(1,2000);R=Fraction(1,40);lines=['pad,i,j,area_m2'];pads=[];covered=set();bounds=[]
 require(len(candidate['pads'])==4,'Four physical pads and two outputs')
 for pad,definition in enumerate(candidate['pads']):
  w,height,cx,cy=(Fraction(str(v))/1000 for v in definition);xl=cx-w/2;xu=cx+w/2;yl=cy-height/2;yu=cy+height/2
  require(w>0 and height>0 and all(x*x+y*y<R*R for x in(xl,xu)for y in(yl,yu)),'Whole physical rectangle inside D50, no circle trimming')
  index=[(x+R)/h for x in(xl,xu,yl,yu)];require(all(v.denominator==1 for v in index),'Every physical rectangle edge must coincide with originalcoarse gridface')
  i0,i1,j0,j1=(int(v)for v in index);require(0<=i0<i1<=100 and 0<=j0<j1<=100,'Exact in-range indices')
  for old in bounds:require(min(xu,old[1])<=max(xl,old[0])or min(yu,old[3])<=max(yl,old[2]),'No electrode overlap')
  bounds.append((xl,xu,yl,yu));total=Fraction(0);count=0
  for j in range(j0,j1):
   for i in range(i0,i1):
    x=-R+(Fraction(i)+Fraction(1,2))*h;y=-R+(Fraction(j)+Fraction(1,2))*h
    require(x*x+y*y<R*R and(i,j)not in covered,'Contact fullface belongs to actual coarsecenter-inside graph and is disjoint');covered.add((i,j));total+=h*h;count+=1;lines.append('%d,%d,%d,%s'%(pad,i,j,format(float(h*h),'.17g')))
  require(total==w*height,'Exact physical pad area, no blanket225mm² assumption')
  pads.append(dict(pad=pad,shape='rectangle',rotation_deg=0,center_mm=[float(cx*1000),float(cy*1000)],width_mm=float(w*1000),height_mm=float(height*1000),analytic_area_m2=float(w*height),represented_area_m2=float(total),exact_area_numerator=total.numerator,exact_area_denominator=total.denominator,patches=count,grid_bounds=[i0,i1,j0,j1],all_fraction_exactly_one=True,node='out'+str(pad)if pad<2 else'GND'))
 raw=('\n'.join(lines)+'\n').encode();receipt=dict(schema='task1-coarse-design-fullface-mask-v1',candidate_id=candidate['candidate_id'],h_mm=.5,nx=100,pad_count=4,independent_outputs=2,pads=pads,mask_sha256=sha(raw),exact_area_proof=True,no_overlap=True,circle_trimmed=False,area_renormalized=False,all_contact_fractions_exactly_one=True)
 return raw,receipt

def required_inputs(output_dir=None):
 refs={str(MATERIAL):MATERIAL_SHA,str(CONTACT):CONTACT_SHA,str(SOURCE/'catalog.json'):sha(_read(SOURCE/'catalog.json')),str(Path(__file__)):sha(_read(Path(__file__)))}
 _material_contact()
 if output_dir is not None:
  spec=make_spec(output_dir);refs.update(spec['input_pins'])
 return refs

def make_spec(output_dir):
 out=Path(output_dir);require(out.is_absolute()and not out.is_symlink(),'Explicit unique root-owned output path');data=catalog();mr,cr,gamma,sigma,epsilon,z=_material_contact();cases=[];pins={str(MATERIAL):MATERIAL_SHA,str(CONTACT):CONTACT_SHA,str(SOURCE/'catalog.json'):sha(_read(SOURCE/'catalog.json'))}
 pins[str(out/'input-material.json')]=MATERIAL_SHA;pins[str(out/'input-contact.json')]=CONTACT_SHA
 for candidate in data['candidates']:
  raw,receipt=derive_mask(candidate);cid=candidate['candidate_id'];mask=out/'masks'/(cid+'.csv');rp=out/'masks'/(cid+'-receipt.json');rr=encoded(receipt);pins[str(mask)]=sha(raw);pins[str(rp)]=sha(rr)
  cases.append(dict(candidate_id=cid,baseline=bool(candidate['baseline']),reuse_baseline_2000=bool(candidate['baseline']),mask_path=str(mask),mask_sha256=sha(raw),mask_receipt_path=str(rp),mask_receipt_sha256=sha(rr),pads=receipt['pads']))
 return dict(schema='task1-coarse-provisional-eight-design-inputs-v1',candidates=cases,source_catalog_path=str(SOURCE/'catalog.json'),source_catalog_sha256=sha(_read(SOURCE/'catalog.json')),
  material_path=str(out/'input-material.json'),material_sha256=MATERIAL_SHA,contact_path=str(out/'input-contact.json'),contact_sha256=CONTACT_SHA,gamma_by_frequency=gamma,sigma_by_frequency=sigma,epsilon_r_by_frequency=epsilon,z_by_frequency=z,layer_order=list(LAYERS),frequencies=list(FREQUENCIES),
  drives={'2000':dict(output=0,source_peak_V=.5,source_Vpp=1.),'2010':dict(output=1,source_peak_V=.5,source_Vpp=1.)},source_resistance_ohm=50.,inactive_output='0V behind50ohm, not open',return_topology='pad2and3 common0V, two outputnodes pad0and1',
  grid=dict(backend='cached_coarse_XY100_DtN_CEM',h_mm=.5,nx=100,nxy=7860,layer_counts=[8,19,18,56],cells=793860,radius_mm=25.,layer_thickness_mm=[.1,5,5,15]),
  baseline_coarse_CEM_run=str(COARSE_CEM),baseline_coarse_CEM_commit=COARSE_CEM_COMMIT,geometry_eigen_cache_run='/dev/shm/task1-layer-dtn-20261025-run',
  minimum_new_RHS_if_baseline2000_verified_reusable=15,maximum_new_RHS=16,RHS_rule='ONLY output0at2000 andoutput1at2010, never automaticallycompute32basisRHS',baseline_field_rule='Reconstruct baseline andallcandidates with the SAMEnew hybridEABI; not claimedidentical toU19nativefullfield',
  common_ROI=dict(radius_mm=5,depth_mm=[15,20],depth_origin='physicaltop,+zdown'),comparison_modes=['fixed1Vpp','same_totalcurrent','same_totalpower','same_surfaceburden'],
  ranking_status='provisional_unadopted',known_contact_XY_interface_and_material_uncertainties_retained=True,independent_outputs=2,physical_pads=4,
  no_new_validation_prerequisite=True,no_new_eigen_work=True,no_local_PC_allocation_or_reservation=True,previous_six_candidate_catalog_preserved_UNRUN=True,no_automatic_geometry_extension=True,no_exhaustive_optimum_claim=True,input_pins=pins)

def prepare_inputs(output_dir):
 """Root before sourcepublication: exclusivecopy/verify full prepared inputs."""
 out=Path(output_dir);require(out.is_absolute()and out.is_dir()and not out.is_symlink(),'Owner-created unique run directory');(out/'masks').mkdir(exist_ok=True);spec=make_spec(out);data=catalog();outputs={out/'input-material.json':_read(MATERIAL),out/'input-contact.json':_read(CONTACT)}
 for candidate in data['candidates']:
  raw,receipt=derive_mask(candidate);cid=candidate['candidate_id'];outputs[out/'masks'/(cid+'.csv')]=raw;outputs[out/'masks'/(cid+'-receipt.json')]=encoded(receipt)
 for path,raw in outputs.items():
  if path.exists():require(_read(path)==raw,'Immutable prepared input differs; preserve evidence')
  else:
   with path.open('xb')as stream:stream.write(raw)
  require(sha(_read(path))==spec['input_pins'][str(path)],'Complete preparedinputSHAreadback')
 cp=out/'catalog-inputs.json';raw=encoded(spec)
 if cp.exists():require(_read(cp)==raw,'Immutable catalog snapshot differs')
 else:
  with cp.open('xb')as stream:stream.write(raw)
 return spec
