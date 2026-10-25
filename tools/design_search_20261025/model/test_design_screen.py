"""Small independent circuit/mask contracts, executed only by the sole owner."""
import hashlib,tempfile,unittest
from pathlib import Path
import design_screen as m

class AdapterContracts(unittest.TestCase):
 def test_physical_top_contact_has_no_extra_SC_half_cell(self):
  area=2.5e-7;za=5.55e-5-1.23e-4j
  self.assertAlmostEqual(abs(m.base.contact_conductance(area,za)-area/za),0.,places=14)

 def test_inactive_output_is_zero_ideal_behind_50_ohm_not_an_open_circuit(self):
  za=.2-.1j;areas=[.001,.001,.001,.001];cells=[0,1,2,3];pads=[0,1,2,3]
  phi=[.3+.1j,.2-.1j,.1+0j,.05+.02j];metal=[.4+.03j,.12-.02j]
  surface,node,qpad=m.base.contact_equations([0j]*4,phi,metal,pads,cells,areas,za,50.)
  # A zero ideal source still contributes metal/R in its node equation.
  self.assertAlmostEqual(abs(node[1]-(metal[1]/50.-qpad[1])),0.,places=14)
  self.assertNotEqual(metal[1]/50.,0j)
  self.assertAlmostEqual(abs(sum(surface)-sum(qpad)),0.,places=14)

 def test_full_face_mask_supports_candidate_specific_pad_areas(self):
  import numpy as np
  with tempfile.TemporaryDirectory(prefix='task1-design-mask-contract-')as directory:
   path=Path(directory)/'mask.csv';raw=('pad,i,j,area_m2\n0,0,0,2.5e-7\n1,2,0,2.5e-7\n2,0,2,2.5e-7\n3,2,2,2.5e-7\n').encode();path.write_bytes(raw)
   candidate=dict(mask_path=str(path),mask_sha256=hashlib.sha256(raw).hexdigest(),pads=[dict(pad=i,analytic_area_m2=2.5e-7)for i in range(4)])
   pads,cells,areas=m._mask(np,candidate,np.asarray([[0,0],[2,0],[0,2],[2,2]]))
   self.assertEqual(len(areas),4);self.assertAlmostEqual(float(areas.sum()),1e-6,places=16)
   self.assertEqual(pads.tolist(),[0,1,2,3]);self.assertEqual(cells.tolist(),[0,1,2,3])

 def test_fraction_column_is_never_accepted_as_absolute_contact_area(self):
  import numpy as np
  with tempfile.TemporaryDirectory(prefix='task1-design-mask-contract-')as directory:
   path=Path(directory)/'mask.csv';raw=b'pad,i,j,area_m2\n0,0,0,1\n';path.write_bytes(raw)
   candidate=dict(mask_path=str(path),mask_sha256=hashlib.sha256(raw).hexdigest(),pads=[])
   with self.assertRaises(ValueError):m._mask(np,candidate,np.asarray([[0,0]]))

 def test_wrong_carrier_output_mapping_fails_before_input_reads(self):
  catalog=dict(frequencies=[2000,2010],candidates=[dict(candidate_id=v)for v in m.EXPECTED_IDS],drives={'2000':dict(output=1,source_peak_V=.5)},gamma_by_frequency={'2000':[{}]*4})
  with self.assertRaises(ValueError):m.make_spec(catalog)

if __name__=='__main__':unittest.main()
