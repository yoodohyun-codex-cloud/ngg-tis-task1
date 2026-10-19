"""Tiny analytic/negative fixtures only; never read an actual source run."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("saved_audit_under_test",Path(__file__).with_name("audit_selectivity_saved_results.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NoResources:
    def check(self):
        pass


def resistor_fixture(channels=2):
    # Independent series circuit: source50ohm + load(100+j40)ohm.
    current = .5/complex(150,40)
    source = [[current if i == j else 0j for j in range(channels)] for i in range(channels)]
    loss = [[[0j for _ in range(channels)] for _ in range(channels)] for _ in range(6)]
    for i in range(channels):
        loss[0][i][i] = .5*abs(current)**2*100
        loss[5][i][i] = .5*abs(current)**2*50
    return {f:(source,loss) for f in m.FREQUENCIES},current


def volume_fixture():
    target=math.pi*5**2*5*1e-9
    total=math.pi*25**2*25.1*1e-9
    slab=total*5/25.1
    volumes=dict(total=total,target=target,surface_0_5=slab,subsurface_5_10=slab,
                 remaining=total-2*slab-target,off_target=total-target)
    regions={}
    totals=[total*d/25.1 for d in (.1,5.,5.,15.)]
    for name,volume in volumes.items():
        statistics={key:dict(min=1.,p10=1.,p50=1.,p95=1.,max=1.,mean=1.,volume_m3=volume,positive_weight_cells=1)
                    for key in ("maxTIS","fixedTIS","RMS","X_TIS","Y_TIS","Z_TIS")}
        if name == "total": tissue=totals
        elif name == "target": tissue=[0.,0.,0.,target]
        elif name == "surface_0_5": tissue=[total*.1/25.1,total*4.9/25.1,0.,0.]
        elif name == "subsurface_5_10": tissue=[0.,total*.1/25.1,total*4.9/25.1,0.]
        elif name == "remaining": tissue=[0.,0.,total*.1/25.1,totals[3]-target]
        else: tissue=[*totals[:3],totals[3]-target]
        regions[name]=dict(statistics=statistics,tissue_volumes_m3={str(i):v for i,v in enumerate(tissue)},high_modulation_volume={})
    ratios={key:{region:dict(target_mean_over_off_p95=1.,target_p10_over_off_p95=1.,target_mean_over_off_max=1.)
                  for region in ("surface_0_5","subsurface_5_10","remaining","off_target")}
            for key in ("maxTIS","fixedTIS","RMS")}
    return dict(status="complete",total_sampled_directions=2074,thresholds={},regions=regions,ratios=ratios,
        geometry=dict(layer_faces_mm=[0.,.1,5.1,10.1,25.1],renormalized_to_analytic_volume=False,
            domain_relative_volume_deviation=0.,domain_relative_volume_tolerance=.01,
            target_relative_volume_deviation=0.,target_relative_volume_tolerance=.001,
            max_relative_partition_roundoff=0.,region_volumes_m3=volumes,
            analytic_cylinder_volume_m3=total,represented_domain_volume_m3=total,
            analytic_target_volume_m3=target,represented_target_volume_m3=target))


class SavedAuditFixtures(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.audit=m.Audit(self.root,NoResources())

    def test_series_circuit_sine_sqrt2_and_power_half_factors(self):
        matrices,current=resistor_fixture()
        result,spectra,loaded,loss=m.independent_circuit(matrices,2,"sine")
        self.assertAlmostEqual(result["max_source_current_RMS_mA"],abs(current)/math.sqrt(2)*1000,places=14)
        self.assertAlmostEqual(result["source_power_W"],.5*current.real,places=18)
        self.assertAlmostEqual(result["SC_power_W"],abs(current)**2*100,places=18)
        self.assertAlmostEqual(result["source_resistor_power_W"],abs(current)**2*50,places=18)
        self.assertAlmostEqual(sum(loss),result["source_power_W"],places=18)
        self.assertAlmostEqual(spectra[3000][0],-1j*current)
        self.assertEqual(spectra[3000][1],0j)
        self.assertAlmostEqual(loaded[3000][0],-.5j-50*(-1j*current))

    def test_square_triangle_harmonics_and_true_C1_carrier(self):
        matrices,current=resistor_fixture(1)
        for wave,factor in (("square_3h",1.25),("triangle_3h",.82)):
            result,spectrum,_,_=m.independent_circuit(matrices,1,wave,3030)
            self.assertEqual(spectrum[3000],[0j])
            self.assertEqual(spectrum[9000],[0j])
            self.assertAlmostEqual(result["source_current_RMS_by_output_mA"][0],abs(current)*math.sqrt(factor/2)*1000,places=14)
            self.assertAlmostEqual(result["source_power_W"],.25*current.real*factor,places=18)
        c=m.coefficients(1,"triangle_3h",3030)
        self.assertEqual(c[9090],[.1j])

    def test_harmonic_phase_is_tripled_not_copied(self):
        c=m.coefficients(2,"square_3h",phases_deg=[30.,-60.])
        self.assertAlmostEqual(c[3000][0],complex(.5,-math.sqrt(3)/2)*m.WAVES["square_3h"][0])
        self.assertAlmostEqual(c[9000][0],m.WAVES["square_3h"][1]+0j)
        self.assertEqual(c[3000][1],0j)
        with self.assertRaises(ValueError):
            m.coefficients(1,"sine",None)

    def test_only_exact_small_matrix_bytes_can_be_decoded(self):
        path=self.root/"source-3000.bin"
        path.write_bytes(struct.pack("<dd",.125,-.25))
        self.assertEqual(m.read_small_matrix(path,1),[.125-.25j])
        path.write_bytes(path.read_bytes()+b"partial")
        with self.assertRaises(ValueError):m.read_small_matrix(path,1)
        forbidden=self.root/"field-3000.bin"
        forbidden.write_bytes(struct.pack("<dd",1.,2.))
        with self.assertRaises(ValueError):m.read_small_matrix(forbidden,1)
        path.write_bytes(struct.pack("<dd",float("nan"),0.))
        with self.assertRaises(ValueError):m.read_small_matrix(path,1)

    def test_SHA_and_nonfinite_metadata_are_rejected(self):
        path=self.root/"metadata.json";path.write_text('{"a":1}')
        pin=m.sha(path)
        self.audit.read(path,pin)
        path.write_text('{"a":2}')
        with self.assertRaises(ValueError):self.audit.read(path,pin)
        path.write_text('{"a":NaN}')
        with self.assertRaises(ValueError):m.Audit(self.root,NoResources()).read(path)

    def test_tiny_nonzero_ratios_have_no_floor_and_zero_mismatch_is_explicit(self):
        self.assertEqual(m.relative_error(2e-40,1e-40),1.)
        self.assertIsNone(m.relative_error(1e-40,0.))
        self.assertEqual(m.relative_error(0.,0.),0.)
        self.audit.compare("tiny_nonzero",2e-40,1e-40)
        self.audit.compare("zero_mismatch",1e-40,0.)
        self.assertFalse(self.audit.checks[0]["passed"])
        self.assertFalse(self.audit.checks[1]["passed"])
        self.assertIsNone(self.audit.checks[1]["relative_error"])
        self.assertTrue(self.audit.checks[1]["zero_reference_mismatch"])
        json.dumps(self.audit.checks,allow_nan=False)

    def test_running_source_is_rejected_before_matrix_access_or_output(self):
        run=self.root/"runs/selectivity-design-fixture"
        run.mkdir(parents=True)
        (run/"controller.json").write_text(json.dumps(dict(status="running",phase="solving")))
        (run/"summary.json").write_text(json.dumps(dict(status="running")))
        output=run/"audit/result.json"
        with patch.object(m,"read_small_matrix",side_effect=AssertionError("must not decode")) as decoder:
            with self.assertRaisesRegex(ValueError,"terminal"):m.audit_run(run,output)
            decoder.assert_not_called()
        self.assertFalse(output.exists())

    def test_terminal_identity_and_existing_output_preservation(self):
        controller=dict(status="interrupted",phase="stopped")
        m.terminal(controller,dict(status="interrupted"))
        with self.assertRaises(ValueError):m.terminal(controller,dict(status="complete"))
        run=self.root/"runs/selectivity-design-fixture";(run/"audit").mkdir(parents=True)
        output=run/"audit/result.json";output.write_bytes(b"original failed audit\n")
        with self.assertRaisesRegex(ValueError,"preserve existing"):m.audit_run(run,output)
        self.assertEqual(output.read_bytes(),b"original failed audit\n")

    def test_coarse_volume_tolerance_and_empty_thresholds_remain_held(self):
        volume=volume_fixture()
        m.volume_checks(self.audit,"synthetic",volume,.01)
        self.assertTrue(all(row["passed"] for row in self.audit.checks))
        self.assertTrue(any("high_modulation_volume" in row["name"] for row in self.audit.held))
        bad=copy.deepcopy(volume);bad["regions"]["target"]["statistics"]["maxTIS"]["p10"]=2.
        other=m.Audit(self.root,NoResources());m.volume_checks(other,"bad",bad,.01)
        self.assertTrue(any(not row["passed"] for row in other.checks))

    def test_scaling_missing_false_or_wrong_primary_not_a_pass(self):
        metrics={key:2. for key in (*m.LINEAR_CHECKS,*m.QUADRATIC_CHECKS)}
        checks={key:dict(passed=True,relative_error=0.,expected=2*(.73 if key in m.LINEAR_CHECKS else .73**2),actual=2*(.73 if key in m.LINEAR_CHECKS else .73**2)) for key in metrics}
        post=dict(id="synthetic",conditions=[dict(waveform="square_3h",actual_fundamental_Hz=[3000,3030],metrics=metrics)],
                  actual_transfer_amplitude_scaling_checks=[dict(actual_carrier_Hz=None,amplitude=.73,source_transfer_re_evaluated=True,new_PDE=0,checks=checks)])
        m.stored_scaling_checks(self.audit,post,2)
        self.assertTrue(all(row["passed"] for row in self.audit.checks))
        post["actual_transfer_amplitude_scaling_checks"][0]["checks"]["SC_power_W"]["passed"]=False
        other=m.Audit(self.root,NoResources());m.stored_scaling_checks(other,post,2)
        self.assertTrue(any(not row["passed"] for row in other.checks))
        post["actual_transfer_amplitude_scaling_checks"]=[]
        other=m.Audit(self.root,NoResources());m.stored_scaling_checks(other,post,2)
        self.assertTrue(any(not row["passed"] for row in other.checks))

    def test_saved_volume_deviation_and_tissue_labels_cannot_hide_tamper(self):
        bad=volume_fixture()
        bad["geometry"]["represented_domain_volume_m3"] *= 2
        other=m.Audit(self.root,NoResources());m.volume_checks(other,"bad-domain",bad,.01)
        self.assertTrue(any(not row["passed"] for row in other.checks))
        bad=volume_fixture()
        target=bad["regions"]["target"]["tissue_volumes_m3"]
        target["0"],target["3"]=target["3"],0.
        other=m.Audit(self.root,NoResources());m.volume_checks(other,"bad-tissue",bad,.01)
        self.assertTrue(any(not row["passed"] for row in other.checks))

    def test_tissue_zero_uses_declared_partition_roundoff_not_ratio_floor(self):
        volume=volume_fixture()
        tissue=volume["regions"]["remaining"]["tissue_volumes_m3"]
        tissue["0"] += 1e-24
        tissue["3"] -= 1e-24
        m.volume_checks(self.audit,"bounded-roundoff",volume,.01)
        self.assertTrue(all(row["passed"] for row in self.audit.checks))

    def test_condition_namespace_cannot_drop_triangle_or_swap_carrier(self):
        conditions=[dict(id="case-"+wave) for wave in m.WAVES]
        m.condition_namespace("case",2,conditions)
        conditions[2]=copy.deepcopy(conditions[1])
        with self.assertRaises(ValueError):m.condition_namespace("case",2,conditions)
        conditions=[dict(id="case-C1-"+str(carrier)+"Hz-"+wave) for carrier in (3000,3030) for wave in m.WAVES]
        m.condition_namespace("case",1,conditions)
        conditions[-1]["id"]="case-C1-3000Hz-triangle_3h"
        with self.assertRaises(ValueError):m.condition_namespace("case",1,conditions)

    def test_probe_ID_coordinates_and_nonempty_native_gate_are_bound(self):
        case=dict(id="fixture",channels=2,postprocess=dict(path=str(self.root/"summary.json")))
        post=dict(id="fixture",input_manifest_sha256="a"*64,postprocessor_sha256="b"*64,validation={"finite":1})
        measurements=[]
        centres={"centre":(0.,0.),"x_plus":(5.,0.),"x_minus":(-5.,0.),"y_plus":(0.,5.),"y_minus":(0.,-5.)}
        for depth in (5.,10.,15.,20.):
            for position,(x,y) in centres.items():
                for axis,(dx,dy) in (("X",(2.5,0.)),("Y",(0.,2.5))):
                    measurements.append(dict(id=f"d{depth:g}-{position}-{axis}",status="complete",position=position,axis=axis,depth_from_skin_surface_mm=depth,
                        centre_mm=[x,y,depth],plus_mm=[x+dx,y+dy,depth],minus_mm=[x-dx,y-dy,depth],tip_gap_mm=5.,plus_centre_pitch_mm=5.))
        gate=dict(passed=True,checked_cell_count=1,checked_cell_indices=[1],unsupported_cell_indices=[],failed_cell_indices=[],
                  checked_cells_by_layer={"3":1},relative_tolerance=2e-10,absolute_tolerance_V_m=1e-10,max_absolute_error_V_m=0.)
        probe=dict(status="complete",expected_waveform_count=40,counts=dict(complete=40,held_data_missing=0,validation_failed=0),measurements=measurements,
            measurement_grid=dict(depths_mm=[5.,10.,15.,20.],plus_centre_pitch_mm=5.,tip_gap_mm=5.,centres_per_depth=5,directions_per_centre=2),
            numerical_checks=dict(all_passed=True,per_frequency={str(f):copy.deepcopy(gate) for f in m.FREQUENCIES}),
            provenance=dict(source_run_id=self.audit.run.name,source_condition_id="fixture",source_candidate_id="fixture-square_3h",input_sha256="a"*64,code_sha256="b"*64,result_sha256=m.digest(post["validation"])))
        conditions=[dict(id="fixture-"+wave,waveform=wave,actual_fundamental_Hz=[3000,3030]) for wave in m.WAVES]
        saved=dict(status="complete",conditions=[dict(id=c["id"],waveform=c["waveform"],probe40=copy.deepcopy(probe)) for c in conditions])
        path=self.root/"probes.json"
        def check(data):
            path.write_text(json.dumps(data))
            post["artifacts"]=dict(files={"probes.json":dict(SHA256=m.sha(path))})
            audit=m.Audit(self.root,NoResources());m.audit_probes(audit,post,case,conditions)
            return audit
        self.assertTrue(all(c["passed"] for c in check(saved).checks))
        bad=copy.deepcopy(saved);row=bad["conditions"][0]["probe40"]["measurements"][0]
        row.update(depth_from_skin_surface_mm=999.,axis="Y",centre_mm=[0.,0.,999.],plus_mm=[0.,2.5,999.],minus_mm=[0.,-2.5,999.])
        self.assertTrue(any(not c["passed"] for c in check(bad).checks))
        bad=copy.deepcopy(saved);bad["conditions"][0]["probe40"]["numerical_checks"]["per_frequency"]={}
        self.assertTrue(any(not c["passed"] for c in check(bad).checks))


if __name__ == "__main__":
    unittest.main()
