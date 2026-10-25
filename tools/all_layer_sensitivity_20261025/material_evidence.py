"""Whole-layer provenance audit and a separately labelled numerical sensitivity.

No I/O on import. Literature context does not provide measured values for this
phantom; absent carrier-specific values are deliberately null.
"""
import hashlib,math
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1')
EPS0=8.8541878128e-12
DOI_SKIN='10.1016/j.sna.2022.113513'
DOI_BULK='10.1016/j.msec.2018.11.080'
SPEC='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/d719c43e668c8b7ba98dc5f43512d6f722c8ba99/docs/reviews/TASK1_FAT_VALIDATION_REQUEST_20261024.md'
LAYERS=(('sc',.0002,110000.,1100.),('dermis',.2,10000.,10000.),('fat',.04,1000.,1000.),('muscle',.3,100000.,100000.))
FREQUENCIES=(2000,2010,3000,3030,9000,9090)

def required_inputs():
    # Code/config/metadata hashes only, no research-module import or array decode.
    paths=[ROOT/'tis-java/model-inputs.json',ROOT/'tis-java/TisSweep.java',ROOT/'tis-java/SelectivityShapeBasis.java',ROOT/'ELECTRODE_DATA_PROVENANCE.md']
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths if p.is_file()}

def build():
    rows=[]
    for frequency in FREQUENCIES:
        for layer,sigma,epsilon,new_epsilon in LAYERS:
            rows.append(dict(layer=layer,frequency_Hz=frequency,frequency_role='historical_initial_not_recomputed'if frequency in(2000,2010)else'actual_baseline_fundamental'if frequency in(3000,3030)else'actual_baseline_third_harmonic',
                old_sigma_S_m=sigma,old_epsilon_r=epsilon,proposed_literature_calibrated_sigma_S_m=None,proposed_literature_calibrated_epsilon_r=None,
                sensitivity_sigma_S_m=sigma,sensitivity_epsilon_r=new_epsilon,used_by_first_new_solve=frequency in(3000,3030,9000,9090),
                sigma_unit='S/m',epsilon_r_unit='dimensionless',epsilon0_unit='F/m',gamma_unit='S/m',
                old_gamma_S_m=dict(real=sigma,imaginary=2*math.pi*frequency*EPS0*epsilon),sensitivity_gamma_S_m=dict(real=sigma,imaginary=2*math.pi*frequency*EPS0*new_epsilon),
                numeric_origin='SHA-pinned legacy canonical model hypotheses; not measured phantom data',
                contextual_DOI=DOI_SKIN if layer in('sc','dermis')else DOI_BULK,
                source_section_figure='Goyal sections2.1/2.2/3.1,Figure2'if layer in('sc','dermis')else'Anand methods2.1.1-2.2; Figures10/11 only as prior-review graphical evidence',
                measured_or_fit_or_assumed='assumed_sensitivity',actual_fabrication_batch_confirmed=False,measurement_temperature_C=None,
                recipe_matched_to_actual_phantom=False,interpolation_or_extrapolation='No interpolation. Sigma/epsilon constant hypotheses at all frequencies; omega term only. Not a fitted material dispersion.',
                statistical_uncertainty_interval=None,missing='Independent layer bulk complex measurement/validated material dispersion fit at actual frequencies, batch/recipe/temperature and measurement corrections',
                sensitivity_change='SC epsilon multiplied by0.01'if layer=='sc'else'Numeric comparator hypothesis retained after explicit provenance review'))
    skin=dict(DOI=DOI_SKIN,primary_read_URL='https://pmc.ncbi.nlm.nih.gov/articles/PMC9053740/?pdf=1',
        title='A biomimetic skin phantom for characterizing wearable electrodes in the low-frequency regime',year=2022,
        independent_read_scope='Primary full HTML methods/results/captions; PDF page numbering not independently verified in this environment',
        upper_layer='SC surrogate: PDMS with carbon black and barium titanate; composition/porosity dependent, not undoped PDMS',
        lower_layer='PVA-c equivalent of remaining epidermis+dermis+hypodermis; not an independent dermis layer',
        total_two_layer_thickness_mm=5.,SC_measured_thickness_um=dict(mean=99.,SD=3.),
        measurement=dict(frequency_range_Hz=[1,1000],voltage_RMS_V=.025,electrodes='two dry stainless-steel,9cm2 each',instrument='Reference600',
            includes_electrode_phantom_interface=True,individual_layer_sigma_epsilon_table=False,actual_measurement_temperature_C=None),
        temperature_caution='22C is reported thaw/storage condition, not established measurement temperature',
        rejected_inferences=['Total two-layer5mm is not dermis5mm','Whole electrode+phantom Z is not unique layer bulk sigma/epsilon','1MOhm/10nF targets and undoped-PDMS epsilon cannot specify the mixed SC bulk','3k/3030/9k/9090 and historical2k/2010 exceed the tested1-1000Hz band'])
    bulk=dict(DOI=DOI_BULK,year=2019,primary_URL='https://www.sciencedirect.com/science/article/abs/pii/S092849311832472X',PubMed='https://pubmed.ncbi.nlm.nih.gov/30606559/',
        title='Tissue phantoms to mimic the dielectric properties of human forearm section for multi-frequency bioimpedance analysis at low frequencies',
        independent_read_scope='Primary publisher text cache/methods and PubMed;2019PDF/curve assets HTTP403; exact curve values not independently digitized',
        individual_material_measurement=dict(instrument='Keysight E4980A with coaxial immersion-depth method',actual_frequency_range_Hz=[1000,2000000],log_frequency_points=50,instrument_hardware_range_Hz=[20,2000000],
            stabilization='at least6h or overnight',temperature='room temperature; exact C not reported',raw_frequency_material_table_available=False,individual_material_fit_coefficients_available=False),
        whole_forearm_measurement=dict(instrument='Quadra',measured_frequency_range_Hz=[1000,349000],frequency_points=15,fit='Cole extrapolation to2MHz; not an individual fat/muscle material fit'),
        fat_recipe_context='5percent agar plus0.05percent saline; final mass-fraction inference is not a reported exact table',
        muscle_reported_wt_percent=dict(water=75.4,NaCl=.03,agar=3.77,gelatine=1.88,propylene_glycol=18.72),muscle_reported_sum_wt_percent=99.80,recipe_renormalized=False,
        target_vs_measurement='Fabricated phantom curves differ from Gabriel tissue target curves; neither is a measurement of this project phantom',
        previous_review_graphical_observations=dict(source_review_commit='d719c43e668c8b7ba98dc5f43512d6f722c8ba99',fat_conductivity_whole_figure_approx_S_m=[.013,.025],
            muscle_epsilon_near_2kHz_graph_approx=[370000,400000],muscle_epsilon_near_3kHz_graph_approx=[320000,360000],
            independently_digitized_here=False,usable_as_exact_carrier_input=False,usable_as_statistical_confidence_interval=False),
        author_2017_thesis_context=dict(URL='https://openrepository.aut.ac.nz/items/a6206973-b898-4e00-ac49-cc41d9470fbc/full',
            PDF_SHA256='3ccb6516ff504e7ce15e87897b20a1aa109e9e5315fbca172e2dfec9651c5638',independently_read=True,equivalent_to_2019_dataset=False,
            limitations='Fat plot datasets/ranges differ within thesis; some permittivity frequency-axis labels are ambiguous. Do not silently reinterpret units or substitute as2019 carrier calibration.'))
    ratio_old=2*math.pi*3000*EPS0*110000/.0002;ratio_new=ratio_old*.01
    return dict(schema='task1-whole-layer-material-evidence-v1',feedback_id='T1-F004/F001/F002/F006/F007/F010:FAT-20261024',reviewed_spec_commit='d719c43e668c8b7ba98dc5f43512d6f722c8ba99',spec_URL=SPEC,
        directive_received=True,evidence_backed_four_layer_material_reset='blocked_missing_independent_skin_bulk_and_actual_frequency_material_tables_or_fits',
        independent_SC_dermis_input_limit_reported_before_new_PDE=True,all_four_layers_audited=True,all_numeric_materials_changed=False,
        first_new_PDE_scope='One explicit four-layer assumption-sensitivity condition, authorized by specification section5.4; not a calibrated material reset or paper reproduction',
        sensitivity=dict(changed_numeric_key='sc.epsilon_r',old=110000,new=1100,factor=.01,other_sigma_epsilon_values_unchanged=True,
            rationale='Isolate the uncalibrated SC capacitive term by a declared100fold change; at3kHz Im(gamma)/Re(gamma) moves91.7936 to0.917936, crossing order-one balance. No desired color gradient or target-field value was used to choose the scenario.',
            SC_3kHz_Im_gamma_over_Re_gamma_old=ratio_old,SC_3kHz_Im_gamma_over_Re_gamma_sensitivity=ratio_new,parameter_uncertainty_distribution_claimed=False),
        fixed_model=dict(diameter_mm=50,thicknesses_mm=[.1,5,5,15],pads=4,independent_outputs=2,return_topology='two common-GND return pads',source_resistance_ohm=50,source='1Vpp highZ before50ohm; peak complex basis0.5V; +jomega_t'),
        frequency_properties=dict(calibrated_sigma_epsilon_dispersion_available=False,gamma_formula='sigma+j2pi*f*epsilon0*epsilon_r',gamma_omega_dependence_is_not_material_dispersion_fit=True),
        rows=rows,Goyal2022=skin,Anand2019=bulk,NGG_PBS_EIS_scope='Electrode interface specific impedance, not layer bulk sigma/epsilon and not validated dry skin contact',
        missing_data_priority=['Independent SC and dermis bulk complex spectra/validated fits with geometry and interface de-embedding','Material-specific50frequency tables or calibratedR/C+conversion/fit coefficients for2019 fat/muscle','Actual batch/recipe/concentration units,temperature,hydration/aging correspondence','FEM/FVM spatial convergence and independent interface tests; separate from material calibration'],
        separate_validation_rows=['material_provenance','actual_config_to_gamma_and_units','complex_envelope_formula','native_discrete_residual_power_KCL','independent_potential_gradient_interfaces','mesh_convergence','publication_readback','Windows_storage'],
        new_PDE_executed=False,material_calibrated=False,full_convergence_validated=False,experimentally_validated=False,Windows_storage_verified=False,paper_PDFs_or_images_for_publication=False)
