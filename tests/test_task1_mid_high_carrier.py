"""Synthetic actual-frequency electrical/configuration/finite-state checks."""
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_mid_high_carrier as lower


class Sampler:
    def __init__(self, grid, geometry): pass
    def stencil(self, point, gamma): return dict(indices=np.array([0]),weights=np.array([1.]))


def electrical_fixture():
    contacts=np.zeros(4,dtype=[('pad',int),('area_m2',float)])
    contacts['pad']=np.arange(4);contacts['area_m2']=1e-6
    basis=dict(f={},grid=np.zeros(1),config={});geometry=dict(gamma_S_m={})
    for f in (5000,5030,9000,9030,3000,3030):
        conductance={5000:.001,5030:.001,9000:.002,9030:.002,3000:.003,3030:.003}[f]
        g,h=conductance,conductance/5
        source=np.array([[g,-h],[-h,g]],complex)
        density=np.array([[g,-h,-(g-h)/2,-(g-h)/2],[-h,g,-(g-h)/2,-(g-h)/2]],complex)/1e-6
        loss=np.zeros((6,2,2),complex);loss[5]=25*source.conj().T@source;loss[0]=.25*source-loss[5]
        field=np.zeros((2,1,3),complex);axis=0 if f in (5000,5030) else 1 if f in (9000,9030) else 2
        amplitude=1 if f in (5000,5030) else 4 if f in (9000,9030) else 7
        field[0,0,axis]=amplitude;field[1,0,axis]=-amplitude
        basis['f'][f]=dict(contacts=contacts.copy(),density=density,source=source,loss=loss,field=field)
        basis['config'][f'z.{f}.re']='0.001';basis['config'][f'z.{f}.im']='-0.002'
        geometry['gamma_S_m'][f]={0:1.+0.j}
    return basis,geometry


def config_fixture():
    return ('sc.sigma=0.0002\nsc.epsilon_r=110000\nh_mm=0.625\nchannels=2\n'
        'frequencies=3000,3030,9000,9090\nvalidation.sc_cells=2\nvalidation.max_cells=800000\n'
        'bulk.counts=14,14,40\nmask.path=/old/mask.csv\nmask.sha256=old\n'
        'pad.0.shape=rectangle\npad.0.x_mm=-10.0\npad.0.represented_area_m2=0.000225\n'
        'z.3000.re=4.407669448241336e-05\nz.3000.im=-9.563561408953766e-05\n'
        'z.3030.re=4.407669448241336e-05\nz.3030.im=-9.563561408953766e-05\n'
        'z.9000.re=0.00004\nz.9000.im=-0.00009\nz.9090.re=0.00004\nz.9090.im=-0.00009\n').encode()


class ElectricalTests(unittest.TestCase):
    def metrics(self,pair,basis=None):
        fixture,geometry=electrical_fixture();basis=fixture if basis is None else basis
        return lower.electrical_for_pair(basis,lower.unit_coefficients(pair),geometry,pair,Sampler,np.eye(3),math.inf)

    def test_actual_pairs_use_their_own_fields_never_relabel_cached_three_k(self):
        self.assertAlmostEqual(self.metrics((5000,5030))['target20_modulation_V_m'],2.)
        self.assertAlmostEqual(self.metrics((9000,9030))['target20_modulation_V_m'],8.)
        self.assertAlmostEqual(self.metrics((3000,3030))['target20_modulation_V_m'],14.)
        self.assertEqual(self.metrics((5000,5030))['actual_fundamental_Hz'],[5000,5030])

    def test_only_two_declared_mid_high_pairs_and_regression_are_accepted(self):
        for pair in ((2000,2010),(5000,9000),(5030,5000),(9000,9090),(5000,5000)):
            with self.subTest(pair=pair),self.assertRaises(ValueError):lower.unit_coefficients(pair)
        for pair in ((5000,5030),(9000,9030),(3000,3030)):
            result=lower.unit_coefficients(pair)
            np.testing.assert_array_equal(result[pair[0]],[-1j,0j]);np.testing.assert_array_equal(result[pair[1]],[0j,-1j])

    def test_inactive_output_remains_loaded_by_fifty_ohm_and_power_is_conserved(self):
        metrics=self.metrics((5000,5030));basis,_=electrical_fixture()
        for row in metrics['source_current_spectrum']:
            current=np.array(row['real_A'])+1j*np.array(row['imaginary_A'])
            metalrow=next(x for x in metrics['loaded_metal_voltage_spectrum']if x['frequency_Hz']==row['frequency_Hz'])
            metal=np.array(metalrow['real_V'])+1j*np.array(metalrow['imaginary_V'])
            source=.5*lower.unit_coefficients((5000,5030))[row['frequency_Hz']]
            np.testing.assert_allclose(metal+50*current,source,rtol=0,atol=1e-15)
            inactive=1 if row['frequency_Hz']==5000 else 0
            self.assertGreater(abs(current[inactive]),0)
        self.assertLess(metrics['driven_max_power_relative_error'],2e-7)
        self.assertLess(metrics['driven_max_current_relative_error'],2e-6)

    def test_wrong_harmonic_coefficients_contact_order_or_energy_fail(self):
        basis,geometry=electrical_fixture();coeff=lower.unit_coefficients((5000,5030));coeff[5000]/=3
        with self.assertRaisesRegex(ValueError,'unit coefficients'):
            lower.electrical_for_pair(basis,coeff,geometry,(5000,5030),Sampler,np.eye(3),math.inf)
        basis,_=electrical_fixture();basis['f'][5030]['contacts']['pad'][0]=3
        with self.assertRaisesRegex(ValueError,'contact identity'):self.metrics((5000,5030),basis)
        basis,_=electrical_fixture();basis['f'][5000]['loss'][0]*=2
        with self.assertRaisesRegex(ValueError,'conservation'):self.metrics((5000,5030),basis)

    def test_current_scalars_are_rms_not_peak_and_all_input_arrays_are_preserved(self):
        basis,geometry=electrical_fixture();before=copy.deepcopy(basis)
        result=self.metrics((5000,5030),basis)
        expected=math.sqrt((.001**2+.0002**2)/2)*1000
        self.assertAlmostEqual(result['source_current_RMS_by_output_mA'][0],expected)
        for f in basis['f']:
            for key in basis['f'][f]:np.testing.assert_array_equal(basis['f'][f][key],before['f'][f][key])

    def test_actual_mid_high_pair_waveforms_reproduce_rms_and_same_beat30_envelopes(self):
        for pair in lower.PAIRS:
            metrics=self.metrics(pair)
            audit=lower.prior.waveform.field_check(dict(id='synthetic',waveform='sine',
                actual_fundamental_Hz=list(pair),metrics=metrics))
            with self.subTest(pair=pair):
                self.assertTrue(audit['passed'])
                self.assertTrue(audit['vector_waveform']['passed'])
                self.assertTrue(audit['winning_direction_fundamental_envelope']['passed'])
                self.assertEqual(audit['winning_direction_fundamental_envelope']['fundamental_frequencies_Hz'],list(pair))
                self.assertAlmostEqual(audit['vector_waveform']['common_period_s'],1/math.gcd(*pair))
                self.assertLess(audit['vector_waveform']['RMS_relative_error'],1e-12)


class RegistrationAndRegressionTests(unittest.TestCase):
    def test_frequency_config_changes_only_frequency_contact_impedance_and_portable_mask(self):
        raw=config_fixture();before=lower.contact.parse_properties(raw)
        rows=[dict(frequency_Hz=f,area_real_ohm_m2=.0002,area_imag_ohm_m2=-.0003)for f in (5000,5030,9030)]
        changed=lower.changed_frequency_config(raw,Path('/new/mask.csv'),'newhash',(5000,5030,9030),rows)
        after=lower.contact.parse_properties(changed)
        for k,v in before.items():
            if k.startswith('z.')or k in ('mask.path','mask.sha256','frequencies'):continue
            self.assertEqual(after[k],v)
        self.assertEqual(after['frequencies'],'5000,5030,9030')
        self.assertNotIn('z.3000.re',after);self.assertEqual(raw,config_fixture())

    def test_regression_keeps_original_lexical_impedance_when_numeric_value_matches(self):
        raw=config_fixture();before=lower.contact.parse_properties(raw)
        rows=[dict(frequency_Hz=f,area_real_ohm_m2=float(before[f'z.{f}.re']),area_imag_ohm_m2=float(before[f'z.{f}.im']))for f in (3000,3030)]
        after=lower.contact.parse_properties(lower.changed_frequency_config(raw,Path('/new/mask.csv'),'same',(3000,3030),rows))
        self.assertEqual(after['z.3000.re'],before['z.3000.re'])
        self.assertEqual(after['z.3030.im'],before['z.3030.im'])

    def test_selected_fit_is_subtracted_once_and_profile_old_fit_is_not_used(self):
        rs=236.5717747232937
        profile=dict(measurement_area_m2=1e-4,selected_fit={'Rs_ohm':999.},points=[
            dict(frequency_Hz=5000,Z_real_ohm=rs+2,Z_imag_ohm=-4),
            dict(frequency_Hz=9030,Z_real_ohm=rs+1,Z_imag_ohm=-2)])
        fit=dict(status='complete',selected_subtraction_passive=True,selected_fit={'Rs_ohm':rs})
        rows=lower.contact.derive_contact_rows(profile,fit,(5000,5030,9030))
        self.assertAlmostEqual(rows[0]['area_real_ohm_m2'],2e-4)
        self.assertAlmostEqual(rows[0]['area_imag_ohm_m2'],-4e-4)
        self.assertAlmostEqual(rows[-1]['area_real_ohm_m2'],1e-4)
        with self.assertRaisesRegex(ValueError,'extrapolation'):
            lower.contact.derive_contact_rows(profile,fit,(999,1030))

    def test_lower_native_job_cannot_start_without_successful_regression(self):
        for status in (None,'failed','running','producer_regression_only'):
            summary={}if status is None else dict(producer_regression={'status':status})
            with self.subTest(status=status),self.assertRaisesRegex(ValueError,'before any lower'):
                lower.require_regression_before_job(summary,lower.MID_HIGH_ID)
        lower.require_regression_before_job({'producer_regression':{'status':'passed'}},lower.MID_HIGH_ID)
        lower.require_regression_before_job({},lower.REGRESSION_ID)

    def test_prepare_admission_preserves_missing_or_insufficient_ledger(self):
        with tempfile.TemporaryDirectory()as temp,mock.patch.object(lower,'ROOT',Path(temp)),mock.patch.object(lower.core,'paths_check'):
            run=Path(temp)/'data-native/cloud-new';run.parent.mkdir()
            ledger=dict(limit_seconds=13800,spent_seconds=12100,runs=[{'prior':'preserved'}]);before=copy.deepcopy(ledger)
            with mock.patch.object(lower.policy,'load_ledger',return_value=ledger), \
                mock.patch.object(lower.policy,'remaining_seconds',return_value=1700), \
                mock.patch.object(lower,'implementation_receipt')as impl,self.assertRaisesRegex(ValueError,'1800s'):
                lower.prepare(run)
            impl.assert_not_called();self.assertEqual(ledger,before);self.assertFalse(run.exists())
            with mock.patch.object(lower.policy,'load_ledger',side_effect=FileNotFoundError('history missing')),self.assertRaises(FileNotFoundError):
                lower.prepare(run)
            self.assertFalse(run.exists())

    def test_attempted_run_is_never_reexecuted_or_reset(self):
        with tempfile.TemporaryDirectory()as temp,mock.patch.object(lower.core,'paths_check'):
            run=Path(temp);(run/'execution-attempt.json').write_text('failure evidence')
            with mock.patch.object(lower.policy,'load_ledger')as ledger,self.assertRaisesRegex(ValueError,'Never retry'):
                lower.execute(run)
            ledger.assert_not_called();self.assertEqual((run/'execution-attempt.json').read_text(),'failure evidence')

    def test_existing_prepared_or_completed_native_plan_is_reused_not_duplicated(self):
        with tempfile.TemporaryDirectory()as temp:
            parent=Path(temp);run=parent/'cloud-old';run.mkdir()
            (run/'preregistration.json').write_text(json.dumps(dict(schema=lower.SCHEMA)))
            for status in ('prepared','running'):
                (run/'controller.json').write_text(json.dumps(dict(status=status)))
                with self.subTest(status=status),self.assertRaisesRegex(ValueError,'never duplicated'):
                    lower.check_existing_frequency_work(parent)
            (run/'controller.json').write_text(json.dumps(dict(status='failed_preserved')))
            lower.check_existing_frequency_work(parent)
            (run/'cases').mkdir();(run/'cases'/(lower.MID_HIGH_ID+'.json')).write_text(json.dumps(dict(status='calculated_unadopted')))
            with self.assertRaisesRegex(ValueError,'never duplicated'):lower.check_existing_frequency_work(parent)

    def test_analysis_assembly_preserves_six_new_rhs_and_cached_two_separately(self):
        basis=dict(f={f:None for f in(5000,5030,9000,9030)},
            metadata=dict(frequencies_Hz=[5000,5030,9030],actual_basis_RHS_solves=6),
            assembly_metadata=dict(actual_new_basis_RHS_solves=6,cached_basis_RHS_reused=2,
                total_analysis_basis_vectors=8,raw_metadata_modified=False),
            frequency_sources={f:dict(kind='reused_cached_native'if f==9000 else'new_native',
                basis_RHS_vectors=2,config_sha256='old9000'if f==9000 else'new3freq')for f in(5000,5030,9000,9030)})
        lower.validate_assembly(basis,dict(config_sha256='new3freq'))
        wrong=copy.deepcopy(basis);wrong['metadata']['frequencies_Hz']=[5000,5030,9000,9030]
        with self.assertRaisesRegex(ValueError,'three actual'):lower.validate_assembly(wrong,dict(config_sha256='new3freq'))
        wrong=copy.deepcopy(basis);wrong['frequency_sources'][9000]['kind']='new_native'
        with self.assertRaisesRegex(ValueError,'relabeled'):lower.validate_assembly(wrong,dict(config_sha256='new3freq'))
        wrong=copy.deepcopy(basis);wrong['assembly_metadata']['actual_new_basis_RHS_solves']=8
        with self.assertRaisesRegex(ValueError,'accounting'):lower.validate_assembly(wrong,dict(config_sha256='new3freq'))


def donor_fixture(root):
    """Opaque native bytes test hash inventory only, never decode fake fields."""
    donor=root/'data-native/cloud-donor';basis=donor/'bases'/lower.REGRESSION_ID;basis.mkdir(parents=True)
    original=root/'tools/java/CloudFrequencyBasis.java';original.parent.mkdir(parents=True);original.write_text('original producer\n')
    config=donor/'configs/regression.properties';config.parent.mkdir();config.write_text('frequencies=3000,3030\n')
    mask=donor/'masks/original.csv';mask.parent.mkdir();mask.write_text('pad,i,j,area_m2\n0,1,1,0.000225\n')
    case=dict(id=lower.REGRESSION_ID,actual_frequencies_Hz=[3000,3030],java_class='CloudFrequencyBasis',
        config_file=str(config),config_sha256=lower.core.sha(config),mask_file=str(mask),mask_sha256=lower.core.sha(mask))
    pre=dict(schema='task1-lower-carrier-preregistration-v1',status='prepared',source_commit=lower.DONOR_SOURCE_COMMIT,
        gates=lower.core.GATES,cases=[case],source_and_input_sha256={str(p):lower.core.sha(p)for p in(original,config,mask)})
    lower.core.write(donor/'preregistration.json',pre);pre_sha=lower.core.sha(donor/'preregistration.json')
    failure=dict(status='failed_preserved',error='ValueError: Exact original full-face square mask required',
        current_case=lower.REGRESSION_ID,phase='loading_native',evidence_preserved=True)
    lower.core.write(donor/'failure.json',failure)
    lower.core.write(donor/'summary.json',dict(status='failed_preserved',source_commit=lower.DONOR_SOURCE_COMMIT,
        registration_sha256=pre_sha,error=failure['error']))
    lower.core.write(donor/'controller.json',dict(status='failed_preserved'))
    for f in (3000,3030):
        for name in(f'field-{f}.bin.gz',f'potential-{f}.bin.gz',f'density-{f}.bin',f'source-{f}.bin',f'loss-{f}.bin',f'contacts-{f}.csv'):
            (basis/name).write_bytes(b'opaque native output for hash-only inventory')
    (basis/'BASIS_COMPLETE').touch();(basis/'grid.csv.gz').write_bytes(b'opaque grid')
    lower.core.write(basis/'validation.json',{k:v/100 for k,v in lower.core.GATES.items()})
    lower.core.write(basis/'mesh-metadata.json',dict(exporter_class='CloudFrequencyBasis',exporter_kind='frequency_native',
        frequencies_Hz=[3000,3030],actual_basis_RHS_solves=4,config_sha256=case['config_sha256']))
    lower.core.write(basis/'basis-progress.json',dict(status='complete',requested_basis_RHS_solves=4,
        completed_basis_RHS_solves=4,last_frequency_Hz=3030,last_basis_channel=1,extra_potential_export_solves=0))
    lower.core.write(basis/'runtime-wrapper.json',dict(runtime_wrapper_class='CloudFrequencyBasis'))
    frozen=donor/'frozen-source/producer.java';frozen.parent.mkdir();frozen.write_bytes(original.read_bytes())
    lower.core.write(donor/'frozen-source-manifest.json',dict(source_commit=lower.DONOR_SOURCE_COMMIT,
        files={str(original):dict(path=str(frozen),sha256=lower.core.sha(frozen))}))
    return donor,pre_sha


class DonorRecoveryTests(unittest.TestCase):
    def inventory(self,root,donor,pre_sha):
        with mock.patch.object(lower,'ROOT',root),mock.patch.object(lower,'DONOR_RUN',donor), \
            mock.patch.object(lower,'DONOR_REGISTRATION_SHA256',pre_sha):
            return lower.donor_inventory(donor)

    def test_exact_failed_consumer_donor_is_pinned_and_reused_without_modification(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);donor,digest=donor_fixture(root)
            before={str(p):p.read_bytes()for p in donor.rglob('*')if p.is_file()}
            with mock.patch.object(lower.native,'load_basis')as loader:
                result=self.inventory(root,donor,digest)
            loader.assert_not_called()
            self.assertEqual(result['actual_reused_RHS_solves'],4)
            self.assertEqual(result['new_regression_RHS_solves'],0)
            self.assertEqual(len(result['native_file_inventory_sha256']),18)
            self.assertEqual({str(p):p.read_bytes()for p in donor.rglob('*')if p.is_file()},before)

    def test_no_second_regression_job_is_registered_or_executable(self):
        self.assertEqual(lower.JOBS,((lower.MID_HIGH_ID,(5000,5030,9030)),))
        self.assertNotIn(lower.REGRESSION_ID,[job[0]for job in lower.JOBS])
        with self.assertRaises(ValueError):lower.require_regression_before_job({},lower.MID_HIGH_ID)

    def test_incomplete_native_export_or_wrong_failed_stage_is_rejected(self):
        for mutation in ('missing_marker','partial_rhs','different_failure','lower_already_attempted'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory()as temp:
                root=Path(temp);donor,digest=donor_fixture(root);basis=donor/'bases'/lower.REGRESSION_ID
                if mutation=='missing_marker':(basis/'BASIS_COMPLETE').unlink()
                elif mutation=='partial_rhs':
                    p=basis/'basis-progress.json';x=lower.core.read(p);x['completed_basis_RHS_solves']=3;lower.core.write(p,x)
                elif mutation=='different_failure':
                    p=donor/'failure.json';x=lower.core.read(p);x['phase']='solving';lower.core.write(p,x)
                else:(donor/'bases'/'lower-1000-1030-2000-2030').mkdir()
                with self.assertRaises(ValueError):self.inventory(root,donor,digest)

    def test_donor_original_registration_java_or_frozen_source_drift_is_rejected(self):
        for mutation in ('registration','java','frozen'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory()as temp:
                root=Path(temp);donor,digest=donor_fixture(root)
                path=donor/'preregistration.json'if mutation=='registration'else root/'tools/java/CloudFrequencyBasis.java'if mutation=='java'else donor/'frozen-source/producer.java'
                path.write_bytes(path.read_bytes()+b' changed')
                with self.assertRaises(ValueError):self.inventory(root,donor,digest)


if __name__=='__main__':unittest.main()
