"""Pure evaluation of separately verified primary model functions; no I/O on import.

All assignments are declared surrogates. This model combines human forearm
conductivity/skin references and mixed-source permittivity, not direct human
thoracoabdominal measurements or a validated anatomic or physiological model.
"""
import math,cmath
EPS0=8.8541878128e-12
FREQUENCIES=(2000,2010,3000,3030,9000,9090)
ACTUAL=(3000,3030,9000,9090)

def require(ok,message):
 if not ok:raise ValueError(message)

def polynomial(coefficients,x):
 value=0.
 for c in coefficients:value=value*x+c
 independent=math.fsum(c*x**(len(coefficients)-i-1)for i,c in enumerate(coefficients))
 require(abs(value-independent)<1e-10,'Independent polynomial evaluation')
 return value

def skin_value(row,f):
 n=math.log10(f)
 return 10**polynomial(row['sigma_log10_coefficients_descending'],n),10**polynomial(row['epsilon_r_log10_coefficients_descending'],n)

def real_conductivity(row,f):
 w=2*math.pi*f;tau=row['tau_us']*1e-6;power=1-row['alpha'];u=(w*tau)**power;c=math.cos(math.pi*power/2)
 value=row['sigma_inf_S_m']+(row['sigma_DC_S_m']-row['sigma_inf_S_m'])*(1+u*c)/(1+2*u*c+u*u)
 independent=(row['sigma_inf_S_m']+(row['sigma_DC_S_m']-row['sigma_inf_S_m'])/(1+(1j*w*tau)**power)).real
 require(math.isclose(value,independent,rel_tol=1e-14,abs_tol=1e-15),'Kangasmaa real algebra/complex evaluation crosscheck')
 require(min(row['sigma_DC_S_m'],row['sigma_inf_S_m'])<=value<=max(row['sigma_DC_S_m'],row['sigma_inf_S_m']),'Passive fitted real conductivity bounds')
 return value

def gabriel_epsilon(row,f):
 factors={'ps':1e-12,'ns':1e-9,'us':1e-6,'ms':1e-3};w=2*math.pi*f
 terms=[d/(1+(1j*w*t*factors[unit])**(1-a))for d,t,unit,a in zip(row['delta_epsilon'],row['tau_original'],row['tau_units'],row['alpha'])]
 dispersion=row['epsilon_infinity']+sum(terms)
 full=dispersion+row['sigma_i_S_m']/(1j*w*EPS0)
 require(math.isclose(full.real,dispersion.real,rel_tol=1e-15),'Ionic term excluded from real permittivity')
 # Only real epsilon is transferred. Neither Gabriel conductive loss nor
 # Kangasmaa imaginary conductivity is added to the hybrid conductivity.
 return float(dispersion.real)

def build(skin,kang,gabriel):
 primary=skin['preferred_unambiguous_skin_proxy'];params=kang['Table3'];g=gabriel['original_Table1_parameters']
 require(primary['valid_frequency_Hz']==[1000,1000000]and kang['Equation10']['permittivity_from_imaginary_part_validated']is False,'Verified source scopes')
 all_rows=[];diagnostics=[]
 limitations={
 'sc':'Human saline-conditioned forearm inverse-model SC transferred to fixed100um geometry; not intact thoracoabdominal SC. Source baseSC14um is not copied as geometry.',
 'dermis':'VS means living epidermis+dermis with SC excluded. Assigned ONLY to5mm dermis slot as equivalent-layer proxy; not isolated measured dermis. No whole-skin duplication.',
 'fat':'Human right-forearm real conductivity combined with Gabriel generic mixed-source not-infiltrated-fat real permittivity; not a co-measured human thoracoabdominal complex spectrum. Fat fit tau/alpha weakly identified.',
 'muscle':'Human forearm muscle/tendon real conductivity tensor components reduced to trace/3 scalar, combined with mixed-source generic muscle epsilon. No resolved fiber direction, abdominal-wall/intercostal/diaphragm-specific material, or posterior interpretation of trace average.'}
 sources={
 'sc':('Tsai2018_SC','10.2478/joeb-2018-0006, originalPDF printedp36 Eq89-90'),
 'dermis':('Tsai2018_VS_dermis_slot_proxy','10.2478/joeb-2018-0006, originalPDF printedp36 Eq91-92'),
 'fat':('Kangasmaa2025_real_fat__Gabriel1996III_epsilon_fat_not_infiltrated','10.1002/bem.22541 Eq10/Table3 p11;10.1088/0031-9155/41/11/003 Eq4/Table1 p2291'),
 'muscle':('Kangasmaa2025_real_tensor_trace_proxy__Gabriel1996III_epsilon_muscle','10.1002/bem.22541 Eq10/Table3 p11;10.1088/0031-9155/41/11/003 Eq4/Table1 p2291')}
 for f in FREQUENCIES:
  sc=skin_value(primary['SC'],f);vs=skin_value(primary['VS'],f)
  perpendicular=real_conductivity(params['lateral_perpendicular_muscle'],f);parallel=real_conductivity(params['longitudinal_parallel_muscle'],f)
  trace=(parallel+2*perpendicular)/3
  require(perpendicular<=trace<=parallel,'Declared tensor trace surrogate bounds')
  fat_sigma=real_conductivity(params['subcutaneous_fat'],f)
  values={'sc':sc,'dermis':vs,'fat':(fat_sigma,gabriel_epsilon(g['fat_not_infiltrated'],f)),'muscle':(trace,gabriel_epsilon(g['skeletal_muscle_generic'],f))}
  for layer,(sigma,epsilon)in values.items():
   require(math.isfinite(sigma)and sigma>0 and math.isfinite(epsilon)and epsilon>0,'Finite positive passive scalar material')
   biological_human=layer in('sc','dermis');source_id,location=sources[layer]
   all_rows.append(dict(layer=layer,frequency_Hz=f,sigma_S_m=sigma,epsilon_r=epsilon,sigma_unit='S/m',epsilon_r_unit='dimensionless',
    gamma_real_S_m=sigma,gamma_imag_S_m=2*math.pi*f*EPS0*epsilon,gamma_unit='S/m',epsilon0_F_m=EPS0,
    source_verified=True,source_id=source_id,source_location=location,assignment_type='declared_surrogate',limitation=limitations[layer],
    material_version='HREF-MIX-v1',human_thoracoabdominal_direct_measurement=False,
    conductivity_species='human',conductivity_condition='in-vivo inverse model; not isolated excised-tissue direct measurement',
    conductivity_site='volar forearm'if biological_human else'right forearm',
    permittivity_species='human_inverse_model'if biological_human else'mixed_source_generic_reference_not_verified_human_kHz',
    permittivity_condition='in-vivo saline-conditioned inverse skin model'if biological_human else'mixed in-vivo/ex-vivo/postmortem literature; stronger Gabriel confidence above1MHz',
    tissue_definition='SC'if layer=='sc'else'VS=LE+DE, SC excluded'if layer=='dermis'else'subcutaneous-fat proxy'if layer=='fat'else'pooled forearm muscle/tendon conductivity with generic skeletal-muscle permittivity',
    conductivity_frequency_valid_Hz=[1000,1000000]if biological_human else[100,1000000],
    permittivity_model_domain_Hz=[1000,1000000]if biological_human else[10,100000000000],
    kHz_human_permittivity_verified=biological_human,temperature_C=None,
    temperature_limitation='Source measurement temperature not independently specified'if biological_human else'Kangasmaa individual skin/room readings, no single37C; Gabriel experimental body-temperature examples do not define all literature fits',
    hydration='0.9percentNaCl saline1minute'if biological_human else'no hydration correction transferred from source',
    isotropy='original scalar skin model'if biological_human else'scalar generic proxy'if layer=='fat'else'mathematical trace/3 of fitted anisotropic conductivity; no fiber map',
    numerical_uncertainty_interval=None,uncertainty='No carrier-specific joint source interval transcribed; site transfer, inverse-model, hydration/temperature and cross-source uncertainty remain. Never average marginal CrI endpoints.',
    source_conductivity_parameters='Tsai2018 direct log10(sigma) polynomial, not reciprocal resistivity'if biological_human else'Kangasmaa Eq10 real part only',
    source_permittivity_parameters='Tsai2018 separate SC/VS log10(epsilon_r) polynomial'if biological_human else'Gabriel1996III journal-rounded Table1 real epsilon only; no Kangasmaa imaginary-to-epsilon inference',
    active_PDE_carrier=f in ACTUAL,frequency_role='historical_initial_not_recomputed'if f in(2000,2010)else'fundamental'if f in(3000,3030)else'third_harmonic',
    muscle_sigma_parallel_S_m=parallel if layer=='muscle'else None,muscle_sigma_perpendicular_S_m=perpendicular if layer=='muscle'else None))
  diagnostics.append(dict(frequency_Hz=f,real_fit_closed_form_vs_complex_real_passed=True,muscle_trace_formula='(sigma_parallel+2*sigma_perpendicular)/3',
   muscle_parallel_S_m=parallel,muscle_perpendicular_S_m=perpendicular,muscle_trace_S_m=trace,
   Gabriel_epsilon_only=True,Gabriel_conductive_loss_added=False,Kangasmaa_imaginary_to_epsilon=False))
 # An audit of the rejected literal2019 indexing uses log values only, avoiding
 # overflow. Matching the visual curve by reversing coefficients is NOT adopted.
 rejected=skin['distinct_dermis_candidate_not_used_literal']['dermis_coefficients_table_row_j0_to_j5']
 ambiguity=[]
 for f in(1000,1000000):
  n=math.log10(f)
  ambiguity.append(dict(frequency_Hz=f,literal_2019_log10_rho_Ohm_m=math.fsum(c*n**j for j,c in enumerate(rejected['c'])),literal_2019_log10_epsilon_r=math.fsum(c*n**j for j,c in enumerate(rejected['d'])),
    note='Literal equation/table index convention compared to source stated endpoint ranges; no coefficient reversal adopted'))
 receipt=dict(schema='task1-human-tissue-materials-v1',status='source_verified_for_declared_scope',material_version='HREF-MIX-v1',
  model_label='human-forearm references with explicit viable-skin, isotropic-trace and mixed-source-permittivity substitutes',
  rows=[r for r in all_rows if r['active_PDE_carrier']],all_assignments_declared_surrogates=True,
  fixed_geometry=dict(diameter_mm=50,layer_slots_mm=[.1,5,5,15]),actual_carrier_Hz=list(ACTUAL),initial_experiment_Hz=[2000,2010],
  initial_experiment_recomputed=False,anatomical_model=False,material_calibrated=False,physiological_or_experimental_validation=False,
  no_whole_skin_duplication=True,SC_source_independent_from_VS_proxy=True,original2013_full_parameter_pages_independently_verified=False,
  source2018_PDF_formulas_independently_verified=True,Tsai2019_DE_table_not_used=True,Kangasmaa_imaginary_part_not_used=True,
  Gabriel_sigma_i_not_added=True,hybrid_co_measured_causal_spectrum_validated=False,
  muscle_fiber_resolved=False,abdominal_wall_intercostal_diaphragm_distinct_and_not_measured_here=True,
  citation_files=['evidence-skin.json','evidence-skin-fit-review.json','evidence-gabriel.json','evidence-kangasmaa.json','evidence-regional-gaps.json'])
 return dict(receipt=receipt,audit=dict(schema='task1-material-function-audit-v1',rows=all_rows,independent_evaluations=diagnostics,
  rejected2019_literal_index_audit=ambiguity,original2018_epsilon0_typo_not_used=True,standard_epsilon0_F_m=EPS0,uncertainty_intervals_not_fabricated=True))
