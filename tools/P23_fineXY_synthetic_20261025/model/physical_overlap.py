"""Exact physical overlap of SHA-authenticated coarse contact-cell unions.

Pure scalar geometry, no filesystem, scientific imports, masks or work on import.
The sole owner authenticates input bytes and actual fine graph identity.
"""
import csv,io,math,operator
from fractions import Fraction as F
def require(ok,message):
 if not ok:raise ValueError(message)
def rectangle_intersection(a,b):
 return max(F(0),min(a[1],b[1])-max(a[0],b[0]))*max(F(0),min(a[3],b[3])-max(a[2],b[2]))
def fraction_record(value):return dict(numerator=value.numerator,denominator=value.denominator)
def _integer(value):
 require(type(value)is not bool,'Boolean is not a native graph index');return operator.index(value)
def remesh_full_cell_union(mask_bytes,nx=102,fine_nodes=None):
 require(type(mask_bytes)is bytes and 0<len(mask_bytes)<8*1024**2 and type(nx)is int and nx==102,'Authenticated bounded coarse CSV bytes and actual XY102 geometry')
 reader=csv.DictReader(io.StringIO(mask_bytes.decode('utf-8')));require(reader.fieldnames==['pad','i','j','area_m2'],'Original full-face coarse mask CSV schema')
 h=F(1,2000);radius=F(1,40);hf=F(1,20*nx);source={};occupied=set();coarse_rectangles=[]
 for row in reader:
  p,i,j=(int(row[key])for key in('pad','i','j'));area=float(row['area_m2']);require(p in(0,1,2,3)and 0<=i<100 and 0<=j<100 and math.isfinite(area)and area==float(h*h),'Typed float serialization must represent the full physical .5mm face, not an alternative fractional geometry')
  require((i,j)not in occupied,'Original physical pad interiors must be disjoint, without duplicate cells');occupied.add((i,j));source.setdefault(p,[]).append((i,j));x0=-radius+i*h;y0=-radius+j*h;rect=(x0,x0+h,y0,y0+h)
  require(all(x*x+y*y<=radius*radius for x in rect[:2]for y in rect[2:]),'Whole original physical contact square inside D50; no circle trimming')
  coarse_rectangles.append((p,i,j,rect))
 require(set(source)=={0,1,2,3},'Exactly four physical pads, fixed electrical mapping handled by caller')
 for p,cells in source.items():require(len(cells)*h*h==F(225,1000000),'Each original published physical pad is exactly225mm2')
 nodes=None
 if fine_nodes is not None:
  nodes=set()
  for pair in fine_nodes:
   require(len(pair)==2,'Actual fine graph index pair');i,j=(_integer(v)for v in pair);require(0<=i<nx and 0<=j<nx,'Actual fine index bounds');cx=-radius+(F(i)+F(1,2))*hf;cy=-radius+(F(j)+F(1,2))*hf;require(cx*cx+cy*cy<radius*radius,'Actual centre-inside-cylinder fine graph');nodes.add((i,j))
 patches={};coverage={};partition_proofs=[]
 for p,ci,cj,rect in coarse_rectangles:
  ix0=max(0,int((rect[0]+radius)//hf));ix1=min(nx-1,int((rect[1]+radius)//hf));iy0=max(0,int((rect[2]+radius)//hf));iy1=min(nx-1,int((rect[3]+radius)//hf));covered=F(0)
  for j in range(iy0,iy1+1):
   for i in range(ix0,ix1+1):
    x=-radius+i*hf;y=-radius+j*hf;area=rectangle_intersection(rect,(x,x+hf,y,y+hf))
    if area==0:continue
    if nodes is not None:require((i,j)in nodes,'Every positive-area physical patch must map to the supplied actual fine graph')
    patches[p,i,j]=patches.get((p,i,j),F(0))+area;coverage[i,j]=coverage.get((i,j),F(0))+area;require(coverage[i,j]<=hf*hf,'Exact sum of physical contact areas exceeds one fine surface face');covered+=area
  require(covered==h*h,'Each original physical square must be partitioned exactly; no lost area, old-index copy or rescale');partition_proofs.append(dict(pad=p,coarse_i=ci,coarse_j=cj,**fraction_record(covered)))
 rows=[];totals={p:F(0)for p in range(4)};float_totals={p:0. for p in range(4)}
 for(p,i,j),area in sorted(patches.items(),key=lambda row:(row[0][0],row[0][2],row[0][1])):
  totals[p]+=area;value=float(area);float_totals[p]+=value;require(0<value<=float(hf*hf)*(1+1e-10),'Positive finite patch area in exported float64')
  rows.append(dict(pad=p,i=i,j=j,area_m2=value,exact_area_m2=fraction_record(area)))
 padproof=[]
 for p,total in sorted(totals.items()):
  require(total==F(225,1000000),'Exact225mm2 pad union retained after remeshing');relative=abs(float_totals[p]-float(total))/float(total);require(relative<=1e-10,'Unchanged exported contact-area relative1e-10 gate')
  padproof.append(dict(pad=p,exact_area_m2=fraction_record(total),physical_area_mm2=225.,exported_float_area_m2=float_totals[p],float_relative_area_error=relative))
 require(sum(totals.values(),F(0))==F(900,1000000),'Total900mm2 exact physical area')
 proof=dict(schema='task1-exact-physical-union-XY102-overlap-v1',nx=nx,fine_h_m=float(hf),coarse_h_m=float(h),physical_pad_count=4,independent_outputs=2,pad_to_node={0:'out0',1:'out1',2:'GND',3:'GND'},one_50ohm_resistor_per_output_before_fanout=True,physical_footprint_changed=False,source_coarse_cell_count=len(occupied),fine_patch_rows=len(rows),pads=padproof,per_source_cell_exact_partitions=partition_proofs,cross_pad_positive_area_overlap=False,physical_contact_inside_D50=True,circle_trimmed=False,area_rescaled=False,coarse_indices_copied_to_fine=False,graph_coverage_verified_against_supplied_nodes=nodes is not None,supplied_graph_identity_authenticated_here=False,graph_coverage_status='positive patches checked against supplied graph nodes'if nodes is not None else'UNVERIFIED: actual fine graph ij/hash binding required before CEM',within_fine_face_area_exact=True,partial_contact_model_sensitivity_preserved=True,full_convergence_or_adoption=False)
 return dict(patches=rows,proof=proof)
