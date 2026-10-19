"""Preserve and audit the initial PEDOT EIS and uploaded Prism CV records."""
from pathlib import Path
import argparse,csv,hashlib,json,math,re,shutil,struct
import numpy as np
from update_ngg_eis import read_spectrum, interpolate_complex, SOURCE
from fit_ngg_eis import fit_series_cpe

ROOT=Path(__file__).resolve().parent
FREQUENCIES=(2000,2010,6000,6030)

def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def constrained_fit(f,z):
    """Bound Rs by the lowest measured real Z; never create a negative resistor."""
    mask=f>=1000;w=2*np.pi*f[mask];obs=z[mask];weight=1/abs(obs)
    best=None;bound=float(z.real.min())
    for n in np.linspace(.2,1,1601):
        basis=(1j*w)**(-n)
        design=np.column_stack((np.r_[weight,np.zeros(len(obs))],np.r_[basis.real*weight,basis.imag*weight]))
        target=np.r_[obs.real*weight,obs.imag*weight]
        rs,k=np.linalg.lstsq(design,target,rcond=None)[0]
        rs=float(np.clip(rs,0,bound))
        a=design[:,1];k=max(float(a@(target-design[:,0]*rs)/(a@a)),1e-30)
        residual=design@np.array([rs,k])-target;cost=float(residual@residual)
        if best is None or cost<best[0]:best=(cost,rs,k,float(n))
    cost,rs,k,n=best
    return {'Rs_ohm':rs,'Q_S_s_power_n':1/k,'n':n,'relative_complex_RMS_percent':math.sqrt(cost/len(obs))*100,
            'method':'passivity-constrained Rs+CPE; 1–10 kHz; Rs <= min measured Re(Z)',
            'Rs_upper_bound_ohm':bound,'Rs_at_bound':abs(rs-bound)<1e-8}

def eis_profiles():
    profiles={}
    bare=json.loads((ROOT/'electrode-data/bare-ngg-initial-fit.json').read_text())
    for thickness in (0,10,30,50,100):
        path=SOURCE/f'0 {thickness}.xlsx';points=read_spectrum(path)
        f=np.array([p['frequency_Hz'] for p in points]);z=np.array([complex(p['Z_real_ohm'],p['Z_imag_ohm']) for p in points])
        fit=fit_series_cpe(f,z,1000)
        warnings=[]
        if thickness==0:
            selected=dict(bare['selected_fit']);selected['method']='unchanged previously selected bare NGG Rs+CPE'
        elif fit['subtraction_nonnegative_real_over_full_measured_band']:
            selected=dict(fit);selected['method']='Rs+CPE; 1–10 kHz; passive over measured band'
        else:
            selected=constrained_fit(f,z)
            warnings.append('Unconstrained Rs subtraction is nonpassive; selected constrained Rs is a surrogate requiring Rs sensitivity checks.')
        if selected['n']<.201 or selected['n']>.999:
            warnings.append('CPE exponent is at the search bound; Rs separation is model-sensitive.')
        carriers=[]
        for frequency in FREQUENCIES:
            measured=interpolate_complex(points,frequency)
            re=measured['Z_real_ohm']-selected['Rs_ohm'];im=measured['Z_imag_ohm']
            if re < -1e-9:raise ValueError('Nonpassive electrode boundary')
            carriers.append({'frequency_Hz':frequency,'measured_real_ohm':measured['Z_real_ohm'],
                             'imag_ohm':im,'electrode_real_ohm':max(0,re),'area_real_ohm_m2':max(0,re)*1e-4,
                             'area_imag_ohm_m2':im*1e-4})
        profiles[str(thickness)]={'thickness_nm':thickness,'source_file':str(path.relative_to(ROOT.parent)),
            'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'measurement_area_m2':1e-4,
            'unconstrained_fit':fit,'selected_fit':selected,'warnings':warnings,'carriers':carriers,'points':points}
    return profiles

def prism_columns(path):
    """Recover this Prism binary's typed float records, retaining type/format flags.

    PCFFGRA4 is not PZFX XML. Validate record lengths and preview values rather
    than silently interpreting it with an XML parser. Unknown encodings fail.
    """
    data=Path(path).read_bytes()
    if not data.startswith(b'PCFFGRA4'):raise ValueError('Expected the uploaded PCFFGRA4 binary')
    columns=[]
    for name in ('Potential (V)','Bare NGG','NGG-PEDOT:PSS(50nm)','NGG-PEDOT:PSS(100nm)'):
        token=name.encode();start=0
        while (at:=data.find(token,start))>=0:
            start=at+len(token)
            if data[start:start+3]!=b'\0\x10\0':continue
            length=struct.unpack_from('<I',data,start+3)[0]
            count=struct.unpack_from('<I',data,start+9)[0]
            if not 100<count<100000 or length!=count*12+6:raise ValueError('Unrecognized Prism column layout')
            records=[struct.unpack_from('<IIf',data,start+13+12*i) for i in range(count)]
            if any(kind not in (0,1,5) or not math.isfinite(value) for kind,fmt,value in records):raise ValueError('Unrecognized numeric Prism record')
            columns.append({'name':name,'offset':at,'count':count,'records':records})
    columns.sort(key=lambda c:c['offset'])
    if [c['name'] for c in columns]!=['Potential (V)','Bare NGG','NGG-PEDOT:PSS(50nm)','Potential (V)','Bare NGG','NGG-PEDOT:PSS(100nm)']:
        raise ValueError('Expected exactly two paired CV tables')
    # The binary also stores formatted previews of the first seven values.
    # Check those independent strings against the recovered numeric records.
    previews=[float(m.group().decode('utf-16-le')) for m in re.finditer(rb'(?:[0-9]\x00){1,3}\.\x00(?:[0-9]\x00){5,}',data)]
    for column in columns:
        for kind,fmt,value in column['records'][:7]:
            if not any(math.isclose(value,p,rel_tol=5e-5,abs_tol=5e-7) for p in previews):
                # The 100 nm table has no formatted preview; all X and 50 nm
                # preview-bearing columns still provide independent checks.
                if column['offset']<200000:raise ValueError('Binary CV does not match formatted preview')
    return columns

def cv_profile(path,output):
    columns=prism_columns(path);tables=[]
    for index,thickness in ((0,50),(3,100)):
        xs,bare,coated=columns[index:index+3]
        if len({c['count'] for c in (xs,bare,coated)})!=1:raise ValueError('Paired CV length mismatch')
        rows=[]
        for i,record in enumerate(zip(xs['records'],bare['records'],coated['records'])):
            if any(r[0]==0 for r in record):continue
            rows.append([i]+[r[2] for r in record]+[r[0] for r in record]+[r[1] for r in record])
        values=np.asarray(rows);potential=values[:,1]
        if not (-.81<float(potential.min())<-.79 and .99<float(potential.max())<1.01):raise ValueError('Unexpected CV potential range')
        file=output/f'cv-paired-{thickness}nm.csv'
        with file.open('w',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['index','potential_V','bare_current_A','pedot_current_A','x_record_type','bare_record_type','pedot_record_type','x_format','bare_format','pedot_format']);writer.writerows(rows)
        area=[float(np.sum((np.abs(values[1:,col])+np.abs(values[:-1,col]))/2*np.abs(np.diff(potential)))) for col in (2,3)]
        tables.append({'thickness_nm':thickness,'rows':len(rows),'csv':file.name,
            'potential_range_V':[float(potential.min()),float(potential.max())],
            'bare_current_range_A':[float(values[:,2].min()),float(values[:,2].max())],
            'pedot_current_range_A':[float(values[:,3].min()),float(values[:,3].max())],
            'absolute_integral_I_dV_A_V':{'bare':area[0],'pedot':area[1]},
            'integral_ratio_within_paired_table':area[1]/area[0],
            'data':values[:,:4].tolist(),
            'source_offsets':[c['offset'] for c in (xs,bare,coated)]})
    return {'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'format':'PCFFGRA4 binary with .pzfx extension',
        'recovery':'typed 12-byte numeric records; count/length/type/potential range and cached preview checks',
        'confirmed_units':{'voltage':'V','current':'A','area_cm2':1},'scan_rate_V_s':None,
        'reference_electrode':'Ag/AgCl (user tentative)','counter_electrode':'Pt (user tentative)',
        'warnings':['Scan rate unknown: no CSC or charge-injection limit is computed.',
                    'CV loop area is not stimulation CIC or a verified safe voltage window.',
                    'The two paired tables contain different bare-NGG traces; do not pool them.',
                    'Binary recovery is format-specific, not a vendor-validated Prism XML export. Original bytes and record flags are preserved.'],
        'tables':tables}

def build_inputs(output,cv_source=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    preserved=ROOT/'electrode-data/cv-source/pedot cic.pzfx'
    if cv_source:
        source=Path(cv_source);preserved.parent.mkdir(parents=True,exist_ok=True)
        if preserved.exists() and preserved.read_bytes()!=source.read_bytes():raise ValueError('Preserved CV source already differs')
        if not preserved.exists():shutil.copy2(source,preserved)
    profiles=eis_profiles();dump(output/'eis-profiles.json',profiles)
    cv=cv_profile(preserved,output);dump(output/'cv-profile.json',cv)
    shutil.copy2(preserved,output/'pedot cic.pzfx')
    return profiles,cv

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('--cv-source');args=parser.parse_args()
    profiles,cv=build_inputs(args.output,args.cv_source)
    print(json.dumps({'profiles':{k:{'Rs':v['selected_fit']['Rs_ohm'],'warnings':v['warnings']} for k,v in profiles.items()},
                      'CV':[{k:v for k,v in t.items() if k!='data'} for t in cv['tables']]},ensure_ascii=False,indent=2))
