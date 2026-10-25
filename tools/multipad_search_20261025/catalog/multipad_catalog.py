"""Proposed4/8/12/16 physical-pad family, exactly two electrical outputs.
No IO, masks, counts, scientific imports or numerical execution on import.
"""
from __future__ import annotations
import hashlib,json,math
from fractions import Fraction
from pathlib import Path
SOURCE=Path('/dev/shm/task1-multipad-extension-20261025/source')
U19=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
MATERIAL=U19/'material-input.json';CONTACT=U19/'contact-receipt.json'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
FOUR_CATALOG_SHA='b5f171982c22bae91a3a8a4aef3c2db7c3aa38176047f8010c0ecce2380c348c'
LAYERS=('sc','dermis','fat','muscle');FREQUENCIES=(2000,2010);EPS0=8.8541878128e-12
IDS=('B0-square15-c10-diagonal','MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return(json.dumps(obj,allow_nan=False,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def _read(path):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded regular source/input');return p.read_bytes()
def catalog():
 value=json.loads(_read(SOURCE/'catalog.json'));require(tuple(c['candidate_id']for c in value['candidates'])==IDS,'Exactly four unadmitted area-matched recipes');return value

def _material_contact():
 mr=_read(MATERIAL);cr=_read(CONTACT);require(sha(mr)==MATERIAL_SHA and sha(cr)==CONTACT_SHA,'Same previously executed material/contact bytes, no refit/reevaluation')
 m={(r['layer'],int(r['frequency_Hz'])):r for r in json.loads(mr)['rows']};contact=json.loads(cr);z={int(r['frequency_Hz']):r for r in contact['rows']};gamma={};sigma={};epsilon={};specific={}
 require(contact['Rs_subtractions']==1 and contact['measurement_area_multiplications']==1 and contact['division_by_two']is False,'Rs and measurementarea once only')
 for f in FREQUENCIES:
  gamma[str(f)]=[];sigma[str(f)]=[];epsilon[str(f)]=[]
  for layer in LAYERS:
   r=m[layer,f];s=float(r['sigma_S_m']);e=float(r['epsilon_r']);imag=2*math.pi*f*EPS0*e;require(r['assignment_type']=='declared_surrogate'and s>0 and e>0 and math.isfinite(s+e+imag),'Explicit declaredsurrogate row perlayer/carrier')
   gamma[str(f)].append(dict(real=s,imaginary=imag));sigma[str(f)].append(s);epsilon[str(f)].append(e)
  specific[str(f)]=dict(real=float(z[f]['area_real_ohm_m2']),imaginary=float(z[f]['area_imag_ohm_m2']))
 return mr,cr,gamma,sigma,epsilon,specific

def physical_pads(candidate):
 data=catalog();pads=[]
 for cluster in data['parent_clusters']:
  for jy,yy in enumerate(candidate['positive_y_intervals_mm']):
   for ix,xx in enumerate(candidate['positive_x_intervals_mm']):
    x0,x1=(Fraction(str(v))/1000 for v in xx);y0,y1=(Fraction(str(v))/1000 for v in yy)
    if cluster['sign_x']<0:x0,x1=-x1,-x0
    if cluster['sign_y']<0:y0,y1=-y1,-y0
    require(x0<x1 and y0<y1,'Positive physical subpad dimensions');pad=len(pads);node=cluster['electrical_node'];require(node in(0,1,-1),'Exactly two electricaloutputs or hardGND')
    pads.append(dict(pad=pad,physical_pad_id=pad,parent_cluster=cluster['parent_cluster'],local_piece_xy=[ix,jy],node_index=node,node=cluster['node_name'],bounds=(x0,x1,y0,y1)))
 require(len(pads)==candidate['physical_pad_count'],'Exact declared physical count; not electrical output count')
 return pads

def derive_mask(candidate):
 h=Fraction(1,2000);R=Fraction(1,40);pads=physical_pads(candidate);lines=['pad,i,j,area_m2'];covered=set();records=[];clusterareas=[Fraction(0)]*4;minimum_squared=None
 for p,pad in enumerate(pads):
  xl,xu,yl,yu=pad['bounds'];require(all(x*x+y*y<R*R for x in(xl,xu)for y in(yl,yu)),'Every physical pad whollyinside fixedD50, no circletrim')
  indices=[(v+R)/h for v in(xl,xu,yl,yu)];require(all(v.denominator==1 for v in indices),'All physical pad edges on the sameh.5mm grid')
  i0,i1,j0,j1=(int(v)for v in indices);total=Fraction(0);count=0
  for other in pads[:p]:
   a,b,c,d=other['bounds'];gx=max(Fraction(0),max(xl,a)-min(xu,b));gy=max(Fraction(0),max(yl,c)-min(yu,d));gap2=gx*gx+gy*gy
   require(gap2>=h*h,'Real at least0.5mm insulating separation between everyphysicalpad, not touching pieces');minimum_squared=gap2 if minimum_squared is None else min(minimum_squared,gap2)
  for j in range(j0,j1):
   for i in range(i0,i1):
    x=-R+(Fraction(i)+Fraction(1,2))*h;y=-R+(Fraction(j)+Fraction(1,2))*h;require(x*x+y*y<R*R and(i,j)not in covered,'Everyfullface actualgraph/disjoint contact');covered.add((i,j));total+=h*h;count+=1;lines.append('%d,%d,%d,%s'%(pad['pad'],i,j,format(float(h*h),'.17g')))
  require(total==(xu-xl)*(yu-yl),'Exact physical subpad area');clusterareas[pad['parent_cluster']]+=total
  records.append(dict(pad=pad['pad'],physical_pad_id=pad['pad'],parent_cluster=pad['parent_cluster'],local_piece_xy=pad['local_piece_xy'],node_index=pad['node_index'],node=pad['node'],shape='rectangle',rotation_deg=0,center_mm=[float((xl+xu)*500),float((yl+yu)*500)],width_mm=float((xu-xl)*1000),height_mm=float((yu-yl)*1000),bounds_mm=[float(v*1000)for v in(xl,xu,yl,yu)],analytic_area_m2=float(total),represented_area_m2=float(total),exact_area_numerator=total.numerator,exact_area_denominator=total.denominator,patches=count,all_fraction_exactly_one=True))
 require(all(a==Fraction(9,40000)for a in clusterareas)and sum(clusterareas)==Fraction(9,10000),'Eachparent225mm²,total900mm² EXACTLY')
 group=[]
 for parent in range(4):
  rows=[r for r in records if r['parent_cluster']==parent];total=sum(r['analytic_area_m2']for r in rows);centroid=[sum(r['analytic_area_m2']*r['center_mm'][axis]for r in rows)/total for axis in range(2)]
  group.append(dict(parent_cluster=parent,electrical_node=rows[0]['node_index'],physical_pad_ids=[r['pad']for r in rows],area_m2=total,area_weighted_centroid_mm=centroid,bounds_mm=[min(r['bounds_mm'][0]for r in rows),max(r['bounds_mm'][1]for r in rows),min(r['bounds_mm'][2]for r in rows),max(r['bounds_mm'][3]for r in rows)]))
 raw=('\n'.join(lines)+'\n').encode();mapping=[r['node_index']for r in records]
 receipt=dict(schema='task1-grouped-multipad-mask-v1',candidate_id=candidate['candidate_id'],physical_pad_count=len(records),independent_outputs=2,physical_pad_to_node=mapping,h_mm=.5,nx=100,pads=records,parent_groups=group,total_contact_area_m2=float(sum(clusterareas)),minimum_physical_gap_mm=math.sqrt(float(minimum_squared))*1000,all_contact_fractions_exactly_one=True,exact_area_proof=True,no_overlap=True,circle_trimmed=False,area_renormalized=False,mask_sha256=sha(raw),single_output_resistor_before_fanout=True,do_not_assume_equal_current_sharing=True,confounds=data_confounds())
 return raw,receipt

def data_confounds():return'Equal900mm² area and commonouter17.5mm bounds; innerextent/centroid/gaps/contactcoverage change. Area-matched segmentation patterns, not isolated causal padcount.'

def required_inputs(output_dir=None):
 _material_contact();frozen=SOURCE/'frozen_four_pad_catalog.py';require(sha(_read(frozen))==FOUR_CATALOG_SHA,'Preserve the activefirst8inputsource byte-exact')
 refs={str(MATERIAL):MATERIAL_SHA,str(CONTACT):CONTACT_SHA,str(SOURCE/'catalog.json'):sha(_read(SOURCE/'catalog.json')),str(Path(__file__)):sha(_read(Path(__file__))),str(frozen):FOUR_CATALOG_SHA}
 if output_dir is not None:refs.update(make_spec(output_dir)['input_pins'])
 return refs

def make_spec(output_dir):
 out=Path(output_dir);require(out.is_absolute()and not out.is_symlink(),'Explicit futureowner output');data=catalog();mr,cr,gamma,sigma,epsilon,z=_material_contact();cases=[];pins={str(MATERIAL):MATERIAL_SHA,str(CONTACT):CONTACT_SHA,str(SOURCE/'catalog.json'):sha(_read(SOURCE/'catalog.json')),str(out/'input-material.json'):MATERIAL_SHA,str(out/'input-contact.json'):CONTACT_SHA}
 for candidate in data['candidates']:
  raw,receipt=derive_mask(candidate);cid=candidate['candidate_id'];mp=out/'masks'/(cid+'.csv');rp=out/'masks'/(cid+'-receipt.json');pins[str(mp)]=sha(raw);pins[str(rp)]=sha(encoded(receipt))
  cases.append(dict(candidate_id=cid,baseline=bool(candidate['baseline']),reuse_baseline_2000=bool(candidate['baseline']),reuse_baseline_2010=bool(candidate['baseline']),reuse_reference_case_id='B0-square15-c10-diagonal'if candidate['baseline']else None,physical_pad_count=receipt['physical_pad_count'],independent_outputs=2,physical_pad_to_node=receipt['physical_pad_to_node'],pads=receipt['pads'],parent_groups=receipt['parent_groups'],mask_path=str(mp),mask_sha256=sha(raw),mask_receipt_path=str(rp),mask_receipt_sha256=sha(encoded(receipt)),total_contact_area_m2=receipt['total_contact_area_m2'],confounds=data_confounds()))
 return dict(schema='task1-proposed-grouped-multipad-inputs-v1',candidates=cases,source_catalog_path=str(SOURCE/'catalog.json'),source_catalog_sha256=sha(_read(SOURCE/'catalog.json')),material_path=str(out/'input-material.json'),material_sha256=MATERIAL_SHA,contact_path=str(out/'input-contact.json'),contact_sha256=CONTACT_SHA,gamma_by_frequency=gamma,sigma_by_frequency=sigma,epsilon_r_by_frequency=epsilon,z_by_frequency=z,layer_order=list(LAYERS),frequencies=list(FREQUENCIES),drives={'2000':dict(output=0,source_peak_V=.5,source_Vpp=1.),'2010':dict(output=1,source_peak_V=.5,source_Vpp=1.)},source_resistance_ohm=50.,inactive_output='0VbehindONE50ohm before fanout',return_topology='All physicalpads assignednode-1 hardcommon0V',independent_outputs=2,physical_pad_counts=[4,8,12,16],output_resistors=2,
  grid=dict(backend='cached_coarse_XY100_DtN_CEM',h_mm=.5,nx=100,nxy=7860,layer_counts=[8,19,18,56],cells=793860,radius_mm=25.,layer_thickness_mm=[.1,5,5,15]),geometry_eigen_cache_run='/dev/shm/task1-layer-dtn-20261025-run',
  first8_reference_run='/dev/shm/task1-design-screen-coarse-20261025-run',baseline_reuse_requires_root_selected_first8_published_raw_SHA_and_identical_ABI=True,maximum_new_RHS_without_reuse=8,new_RHS_if_both_B0_carriers_reused=6,
  common_ROI=dict(radius_mm=5,depth_mm=[15,20],depth_origin='physicaltop,+zdown'),comparison_modes=['fixed1Vpp','same_totalcurrent','same_totalpower','same_surfaceburden'],ranking_status='source_only_next_family_unadmitted',root_finite_selection_after_actual_first8_required=True,
  known_contact_XY_interface_and_material_uncertainties_retained=True,no_new_eigen_work=True,no_local_PC_allocation_or_reservation=True,no_automatic_execution_or_candidate_adoption=True,confounds=data_confounds(),input_pins=pins)

def prepare_inputs(output_dir):
 out=Path(output_dir);require(out.is_absolute()and out.is_dir()and not out.is_symlink(),'Futureowner-created unique run');(out/'masks').mkdir(exist_ok=True);spec=make_spec(out);outputs={out/'input-material.json':_read(MATERIAL),out/'input-contact.json':_read(CONTACT)}
 for candidate in catalog()['candidates']:
  raw,receipt=derive_mask(candidate);cid=candidate['candidate_id'];outputs[out/'masks'/(cid+'.csv')]=raw;outputs[out/'masks'/(cid+'-receipt.json')]=encoded(receipt)
 for path,raw in outputs.items():
  if path.exists():require(_read(path)==raw,'Preserve different/partial prior input, nooverwrite')
  else:
   with path.open('xb')as stream:stream.write(raw)
  require(sha(_read(path))==spec['input_pins'][str(path)],'Complete preparedinputSHAreadback')
 cp=out/'catalog-inputs.json';raw=encoded(spec)
 if cp.exists():require(_read(cp)==raw,'Immutable groupedcatalogsnapshot')
 else:
  with cp.open('xb')as stream:stream.write(raw)
 return spec
