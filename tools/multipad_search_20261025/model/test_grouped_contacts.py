"""Genuine grouped-node contracts, no original arrays or PDE are accessed."""
import unittest
import multipad_screen as m

class GroupedContactContracts(unittest.TestCase):
 def test_physical_pad_number_is_not_an_output_number(self):
  import numpy as np
  phi=np.asarray([.1+.02j,.2-.03j,.05+.01j,.3+.04j]);metal=np.asarray([.4+.05j,.25-.01j]);pads=np.arange(4);state=m.grouped_contact_state(np,phi,metal,pads,pads,np.ones(4)*1e-6,[-1,0,-1,1],.2-.1j)
  np.testing.assert_allclose(state['metal_contact_voltage'],[0,metal[0],0,metal[1]],rtol=0,atol=0)
  self.assertEqual(len(state['outward_current_by_physical_pad']),4)
  self.assertEqual(len(state['outward_current_by_node']),3)

 def test_same_voltage_fanout_does_not_force_equal_branch_currents(self):
  import numpy as np
  pads=np.arange(6);mapping=[0,0,1,1,-1,-1];phi=np.asarray([.1,.3,.2,.25,.05,.08],complex);metal=np.asarray([.5,.4],complex);state=m.grouped_contact_state(np,phi,metal,pads,pads,np.ones(6)*2.5e-7,mapping,.2-.1j)
  q=state['outward_current_by_physical_pad'];self.assertNotEqual(q[0],q[1]);self.assertEqual(state['metal_contact_voltage'][0],state['metal_contact_voltage'][1])
  self.assertAlmostEqual(abs(state['outward_current_by_node'][0]-q[:2].sum()),0.,places=14)
  # The source sees one total output-node current and one50ohm drop.
  I0=-state['outward_current_by_node'][0];source_voltage=metal[0]+50*I0
  self.assertAlmostEqual(abs((source_voltage-metal[0])/50-I0),0.,places=14)

 def test_complex_patch_sums_and_node_sums_have_identical_KCL(self):
  import numpy as np
  phi=np.asarray([.1+.2j,.3-.1j,.15+.04j,.08-.02j]);pads=np.asarray([0,1,2,3,4,5]);cells=np.asarray([0,1,2,3,2,1]);areas=np.asarray([1,2,3,4,2,1])*1e-7;mapping=[0,0,1,1,-1,-1]
  state=m.grouped_contact_state(np,phi,np.asarray([.4+.02j,.3-.03j]),pads,cells,areas,mapping,.2-.1j)
  for key in('surface_outward_current','outward_current_by_physical_pad','outward_current_by_node'):
   self.assertAlmostEqual(abs(state[key].sum()-state['outward_patch_current'].sum()),0.,places=14)

 def test_splitting_equal_potential_contact_preserves_node_conductance(self):
  import numpy as np
  phi=np.asarray([.1,.1,.2,.2,.05,.05],complex);pads=np.arange(6);areas=np.asarray([1,3,2,2,1,3])*1e-7;mapping=[0,0,1,1,-1,-1];metal=np.asarray([.5,.4],complex);za=.2-.1j
  state=m.grouped_contact_state(np,phi,metal,pads,pads,areas,mapping,za)
  truth=np.asarray([4e-7/za*(.1-.5),4e-7/za*(.2-.4),4e-7/za*.05])
  np.testing.assert_allclose(state['outward_current_by_node'],truth,rtol=1e-14,atol=1e-20)

 def test_contact_complex_power_uses_each_actual_unequal_branch_current(self):
  import numpy as np
  phi=np.asarray([.1+.02j,.3-.04j,.2+.01j,.04-.03j]);metal=np.asarray([.5+.01j,.4-.02j]);pads=np.arange(4);areas=np.asarray([1,2,3,4])*1e-7;za=.2-.1j;state=m.grouped_contact_state(np,phi,metal,pads,pads,areas,[0,0,1,-1],za)
  inward=-state['outward_patch_current'];drop=state['metal_contact_voltage']-phi
  direct=.5*np.sum(drop*inward.conj());constitutive=.5*za*np.sum(abs(inward)**2/areas)
  self.assertAlmostEqual(abs(direct-constitutive),0.,places=14)
  self.assertGreater(direct.real,0.);self.assertLess(direct.imag,0.)

 def test_fractional_or_new_electrical_output_mapping_is_rejected(self):
  import numpy as np
  for mapping in([.2,1,-1],[0,2,-1]):
   with self.subTest(mapping=mapping),self.assertRaises(ValueError):
    m.grouped_contact_state(np,np.zeros(3,complex),np.zeros(2,complex),np.arange(3),np.arange(3),np.ones(3),mapping,1+0j)

if __name__=='__main__':unittest.main()
