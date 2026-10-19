"""Pure synthetic checks; no source native cache reads, PDE, or execution.

Preserves the 25 analytic checks from the first implementation and adds exact
reference-scope/hash rejection and failure-status fixtures.
"""
from pathlib import Path
import gzip
import hashlib
import json
import math
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import selectivity_postprocess as m
from layered_probe_analysis import LayeredPotentialSampler,DEFAULT_LAYERS,ProbeDataMissing,waveform_statistics


def preserved_synthetic_contracts():
    checks=[]
    def check(name,value):
        if not value:raise AssertionError(name)
        checks.append(name)
    C=m._coefficients(2,'square_3h')
    check('two_source_sine_coefficients', np.allclose(m._coefficients(2,'sine')[3000],[-1j,0]) and not np.any(m._coefficients(2,'sine')[9000]))
    check('actual_C1_second_carrier', not np.any(m._coefficients(1,'square_3h',3030)[3000]) and np.allclose(m._coefficients(1,'square_3h',3030)[3030],[-1j*m.WAVES['square_3h'][0]]))
    check('triangle_third_sign',np.allclose(m._coefficients(2,'triangle_3h')[9000],[.1j,0]))
    with tempfile.TemporaryDirectory() as temporary:
     p=Path(temporary);a=np.arange(12,dtype=float).reshape(2,3,2);raw=a.tobytes();(p/'a.gz').write_bytes(gzip.compress(raw));loaded=m._array(p/'a.gz',(2,3),time.monotonic()+30)
     check('gzip_little_endian_exact',np.array_equal(loaded.view('<f8').reshape(a.shape),a))
     for name,blob in [('truncated',raw[:-1]),('trailing',raw+b'x'),('nonfinite',np.full(12,np.nan).tobytes())]:
      (p/name).write_bytes(blob)
      try:m._array(p/name,(2,3),time.monotonic()+30)
      except ValueError:check(name+'_rejected',True)
      else:raise AssertionError(name)
     output=p/'failed'
     try:m.process_case(p/'absent',{'id':'deadline-only'},output,time.monotonic()-1)
     except m.PostprocessDeadlineExceeded:pass
     failure=(output/'failure.json').read_bytes()
     check('deadline_partial_failure_receipt',json.loads(failure)['partial_artifacts_preserved'])
     try:m.process_case(p/'absent',{'id':'deadline-only'},output,time.monotonic()+30)
     except FileExistsError:check('existing_partial_retry_rejected', (output/'failure.json').read_bytes()==failure)
     else:raise AssertionError('retry')
    faces=[0,.1,5.1,10.1,17.6,25.1];zs=(np.array(faces[:-1])+faces[1:])/2
    rows=[(x,y,z,l) for z,l in zip(zs,[0,1,2,3,3]) for y in [-1,0,1] for x in [-1,0,1]]
    grid=np.array(rows,dtype=[('x_mm','f8'),('y_mm','f8'),('z_mm','f8'),('layer','i4')])
    geometry=dict(coordinate_system=dict(unit='mm',surface_z_mm=0,depth_axis='+z'),radius_mm=25,layers=[dict(l) for l in DEFAULT_LAYERS],z_faces_mm=faces,field_reconstruction=m.FIELD_RECONSTRUCTION,basis_normalization=m.NORMALIZATION)
    gammas={i:complex(1+i,.2+i*.1) for i in range(4)}
    geometry['gamma_S_m']={f:gammas for f in m.FREQUENCIES}
    sampler=LayeredPotentialSampler(grid,geometry)
    ex,ey,J=2+1j,3-.5j,4+.7j
    phi=[]
    for row in grid:
     z=row['z_mm'];integral=sum(max(0,min(z,l['z_max_mm'])-l['z_min_mm'])/1000/gammas[l['id']] for l in DEFAULT_LAYERS if z>l['z_min_mm'])
     phi.append(-ex*row['x_mm']/1000-ey*row['y_mm']/1000-J*integral)
    phi=np.asarray(phi)[None,:]
    for z,label in [(5.,1),(5.05,1),(5.15,2),(10.,2),(20.,3)]:
     observed=m._phi_gradient(sampler,phi,[0,0,z],gammas,1.25)
     check('layer_phi_gradient_'+str(z),np.allclose(observed,[ex,ey,J/gammas[label]],atol=1e-11,rtol=1e-11))
    try:m._phi_gradient(sampler,phi,[0,0,5.1],gammas,1.25)
    except ProbeDataMissing:check('exact_interface_gradient_held',True)
    else:raise AssertionError('interface')
    contacts=np.array([(0,1e-4),(1,1e-4),(2,1e-4),(3,1e-4)],dtype=[('pad','i4'),('area_m2','f8')])
    field=np.zeros((2,len(grid),3),complex);field[0,:,0]=1;field[1,:,0:2]=1
    source=np.eye(2)*.001
    loss=np.zeros((6,2,2),complex);loss[0]=np.eye(2)*.0001;loss[4]=np.eye(2)*.0001;loss[5]=np.eye(2)*.00005
    density=np.array([[10,0,-10,0],[0,10,0,-10]],complex)
    basis=dict(grid=grid,config={f'z.{f}.{part}':str(value) for f in m.FREQUENCIES for part,value in [('re',.001),('im',-.002)]},f={f:dict(field=field,density=density,source=source,loss=loss,contacts=contacts) for f in m.FREQUENCIES})
    metric=m._electrical(basis,C,geometry,time.monotonic()+30)
    check('driven_power_conservation_and_absolute_value',abs(metric['source_power_W']-.000625)<1e-14 and metric['driven_max_power_relative_error']<1e-12)
    check('driven_current_and_weighted_J95',abs(metric['surface_J_RMS_max_A_m2']-math.sqrt(62.5))<1e-12 and metric['surface_J_RMS_p95_A_m2']==metric['surface_J_RMS_max_A_m2'])
    check('centre_RMS_and_2074_TIS',abs(metric['target20_total_E_RMS_V_m']-math.sqrt(1.875))<1e-12 and abs(metric['target20_modulation_V_m']-2*m.WAVES['square_3h'][0])<1e-12)
    probe=waveform_statistics(m.FREQUENCIES,[.005+.001j,.004-.001j,.001,.0007],m.FUNDAMENTALS);probe['status']='complete'
    changed=m._probe_variation({'measurements':[probe]},'triangle_3h',time.monotonic()+30)['measurements'][0]
    check('native_probe_exact_waveform_reuse',abs(changed['spectrum'][2]['real_V']-(-.001*.1/m.WAVES['square_3h'][1]))<1e-15 and 'time_plot' not in changed)
    # Native half-face phi/E algebra, including adjacent material interfaces.
    faces=[0,.05,.1];ids=[0,0]
    for tissue,(lo,hi,count) in enumerate([(0.1,5.1,3),(5.1,10.1,3),(10.1,25.1,6)],1):
     faces.extend(np.linspace(lo,hi,count+1)[1:].tolist());ids.extend([tissue]*count)
    zs=(np.array(faces[:-1])+faces[1:])/2
    rows=[(x,y,z,l) for z,l in zip(zs,ids) for y in np.linspace(-10,10,9) for x in np.linspace(-10,10,9)]
    g=np.array(rows,dtype=[('x_mm','f8'),('y_mm','f8'),('z_mm','f8'),('layer','i4')]);geo=dict(geometry,z_faces_mm=faces)
    s=LayeredPotentialSampler(g,geo);native_phi=np.zeros((2,len(g)),complex);native_E=np.zeros((2,len(g),3),complex)
    for at,row in enumerate(g):
     z=row['z_mm'];integral=sum(max(0,min(z,l['z_max_mm'])-l['z_min_mm'])/1000/gammas[l['id']] for l in DEFAULT_LAYERS if z>l['z_min_mm'])
     for ch,(ex,ey,jz) in enumerate([(2+.1j,0,1+.2j),(0,3-.2j,2+.3j)]):
      native_phi[ch,at]=-ex*row['x_mm']/1000-ey*row['y_mm']/1000-jz*integral
      native_E[ch,at]=[ex,ey,jz/gammas[int(row['layer'])]]
    nodes=[]
    for k in range(1,len(zs)-1):
     for j in range(1,8):
      for i in range(1,8):nodes.append(int(s.lookup[k,j,i]))
    gate=s.phi_e_consistency(native_phi,native_E,nodes,gammas)
    check('native_bulk_phi_E_algebra_interfaces',gate['passed'] and gate['interface_adjacent_cell_count']>0)
    broken=native_E.copy();broken[0,nodes[0],0]+=.001
    check('native_phi_E_mismatch_rejected',not s.phi_e_consistency(native_phi,broken,nodes,gammas)['passed'])
    from layered_probe_analysis import evaluate_layered_probe
    probe=evaluate_layered_probe(g,{f:native_phi for f in m.FREQUENCIES},{f:native_E for f in m.FREQUENCIES},geo,C,
     provenance=dict(source_run_id='synthetic-only',source_condition_id='synthetic',source_candidate_id='synthetic',input_sha256='0'*64,code_sha256='1'*64,result_sha256='2'*64),fundamental_frequencies_Hz=m.FUNDAMENTALS)
    check('synthetic_native_40_probe_all_axes_gate',probe['status']=='complete' and probe['counts']['complete']==40)
    # Derived wave must remove primary-only tissue statistics, never relabel them.
    weights={k:np.array([1.,2.]) for k in ('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    statistics={k:dict(statistics={},tissue_statistics={'0':{'RMS':{'mean':123}}},high_modulation_volume={}) for k in weights}
    primary=dict(metrics=dict(regions=statistics,thresholds={},ratios={k:{} for k in ('maxTIS','fixedTIS','RMS')}),region_weights_m3=weights,scalars={k:np.array([1.,2.]) for k in ('maxTIS','fixedTIS','X_TIS','Y_TIS','Z_TIS')})
    spectra={f:np.full((2,3),(.1+.2j) if f in m.FUNDAMENTALS else 0,complex) for f in m.FREQUENCIES}
    derived=m._derive_volume(primary,spectra,'sine',time.monotonic()+30)
    check('derived_wave_tissue_statistics_explicitly_omitted',all('tissue_statistics' not in v for v in derived['regions'].values()) and 'tissue_statistics' in primary['metrics']['regions']['total'])
    check('derived_wave_actual_harmonic_RMS_and_activefreqs',abs(derived['regions']['target']['statistics']['RMS']['mean']-math.sqrt(.15))<1e-12 and derived['frequencies_Hz']==list(m.FUNDAMENTALS))
    with tempfile.TemporaryDirectory() as temporary:
     p=Path(temporary)/'p';p.write_bytes(b'original');before=m._sha(p,time.monotonic()+30);p.write_bytes(b'mutated');check('source_SHA_mutation_detectable',m._sha(p,time.monotonic()+30)!=before)
    return checks


def exact_reference_case():
    return dict(id='reference-best1-final',existing_reference=True,expected_source_exporter='RsWindowTisBasis',
        config_file=str(m._REFERENCE_RUN/'configs'/(m._REFERENCE_ID+'.properties')),
        source_original_case=str(m._REFERENCE_RUN/'cases'/(m._REFERENCE_ID+'.json')),
        existing_reference_pins=dict(
            source_case_path=str(m._REFERENCE_RUN/'cases'/(m._REFERENCE_ID+'.json')),
            source_case_sha256=m._REFERENCE_CASE_SHA,
            source_postprocess_path=str(m._REFERENCE_RUN/'postprocess'/(m._REFERENCE_ID+'.json.gz')),
            source_postprocess_sha256=m._REFERENCE_POST_SHA,config_sha256=m._REFERENCE_CONFIG_SHA,
            basis_input_sha256={}))


class SyntheticPostprocessTests(unittest.TestCase):
    def test_preserved_25_analytic_checks(self):
        checks=preserved_synthetic_contracts()
        self.assertEqual(len(checks),25)

    def test_unapproved_exporter_rejected_before_source_read(self):
        case=exact_reference_case();case['expected_source_exporter']='OtherClass'
        with patch.object(m,'_sha',side_effect=AssertionError('source must not be read')):
            with self.assertRaisesRegex(ValueError,'restricted'):
                m._reference_guard(m._REFERENCE_RUN/'bases'/m._REFERENCE_ID,case,time.monotonic()+1)

    def test_unapproved_case_namespace_rejected_before_source_read(self):
        case=exact_reference_case();case['id']='any-historical-case'
        with patch.object(m,'_sha',side_effect=AssertionError('source must not be read')):
            with self.assertRaisesRegex(ValueError,'restricted'):
                m._reference_guard(m._REFERENCE_RUN/'bases'/m._REFERENCE_ID,case,time.monotonic()+1)

    def test_unapproved_source_case_path_rejected_before_source_read(self):
        case=exact_reference_case();case['source_original_case']='/tmp/unapproved-source.json'
        with patch.object(m,'_sha',side_effect=AssertionError('source must not be read')):
            with self.assertRaisesRegex(ValueError,'restricted'):
                m._reference_guard(m._REFERENCE_RUN/'bases'/m._REFERENCE_ID,case,time.monotonic()+1)

    def test_wrong_config_pin_rejected_before_source_read(self):
        case=exact_reference_case();case['existing_reference_pins']['config_sha256']='0'*64
        with patch.object(m,'_sha',side_effect=AssertionError('source must not be read')):
            with self.assertRaisesRegex(ValueError,'pin mismatch'):
                m._reference_guard(m._REFERENCE_RUN/'bases'/m._REFERENCE_ID,case,time.monotonic()+1)

    def test_wrong_postprocess_pin_rejected_before_source_read(self):
        case=exact_reference_case();case['existing_reference_pins']['source_postprocess_sha256']='0'*64
        with patch.object(m,'_sha',side_effect=AssertionError('source must not be read')):
            with self.assertRaisesRegex(ValueError,'pin mismatch'):
                m._reference_guard(m._REFERENCE_RUN/'bases'/m._REFERENCE_ID,case,time.monotonic()+1)

    def test_original_source_byte_mutation_rejected(self):
        case=exact_reference_case()
        with patch.object(m,'_sha',return_value='0'*64):
            with self.assertRaisesRegex(ValueError,'source bytes changed'):
                m._reference_guard(m._REFERENCE_RUN/'bases'/m._REFERENCE_ID,case,time.monotonic()+1)

    def test_existing_reference_false_does_not_expand_guard(self):
        with patch.object(m,'_sha',side_effect=AssertionError('source must not be read')):
            self.assertIsNone(m._reference_guard(Path('/tmp/unapproved'),{},time.monotonic()+1))

    def test_controlled_interrupted_status_preserved(self):
        class Interrupted(Exception):status='interrupted'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(m,'_load_basis',side_effect=Interrupted('user control')):
                with self.assertRaises(Interrupted):
                    m.process_case(root/'source',dict(id='synthetic'),root/'out',time.monotonic()+5)
            failure=json.loads((root/'out/failure.json').read_text())
            self.assertEqual(failure['status'],'interrupted')

    def test_timeout_status_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(m,'_load_basis',side_effect=TimeoutError('bounded')):
                with self.assertRaises(TimeoutError):
                    m.process_case(root/'source',dict(id='synthetic'),root/'out',time.monotonic()+5)
            failure=json.loads((root/'out/failure.json').read_text())
            self.assertEqual(failure['status'],'postprocessing_timeout')


if __name__=='__main__':
    unittest.main()
