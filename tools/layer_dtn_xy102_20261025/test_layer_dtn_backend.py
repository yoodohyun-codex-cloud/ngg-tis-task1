"""Pure small meaningful contracts, no NumPy/SciPy/eigen/CEM imports or IO."""
import math,unittest
import layer_dtn_backend as d
class Contracts(unittest.TestCase):
 def test_passive_homogeneous_and_zero(self):
  g=.2+.03j;t=[.0001,.005,.005,.015]
  self.assertEqual(d.modal_admittance(0,[g]*4,t),0j)
  for k in(1e-7,125.,5700.):
   self.assertLess(abs(d.modal_admittance(k,[g]*4,t)-g*k*math.tanh(k*sum(t))),1e-10+1e-10*abs(g*k))
 def test_stable_profile_versus_independent_transfer(self):
  gamma=[.003+.02j,.2+.04j,.04+.005j,.3+.07j];t=[.0001,.005,.005,.015];zs=[0.,.00005,.0001,.002,.0051,.01,.0251]
  for k in(0.,125.,5700.):
   v,j=d.stable_profile(k,gamma,t,zs);ev,ej,_=d.f.exact_profile(k,gamma,t,zs)
   for a,b in zip(v,ev):self.assertLess(abs(a-b),1e-10+1e-10*abs(b))
   for a,b in zip(j,ej):self.assertLess(abs(a-b),1e-10+1e-10*abs(b))
 def test_negative_and_extra_zero_eigenvalues_rejected(self):
  with self.assertRaises(ValueError):d.eigenvalue_policy([-1.,1.,2.],100.,0.)
  with self.assertRaises(ValueError):d.eigenvalue_policy([0.,0.,2.],100.,0.)
  with self.assertRaises(ValueError):d.eigenvalue_policy([0.,1.,2.],100.,.1)
 def test_only_proven_zero_is_clipped(self):
  vals,proof=d.eigenvalue_policy([-1e-12,1.,2.],100.,0.)
  self.assertEqual(vals,[0.,1.,2.]);self.assertTrue(proof['clipped_only_proven_constant_zero'])

class ProposedGraphContracts(unittest.TestCase):
 def test_preserved_physical_thickness_and_sampling_scope(self):
  self.assertEqual(d.PLAN['physical_layers_m'],[.0001,.005,.005,.015])
  self.assertEqual(d.PLAN['nx'],102)
  self.assertEqual(d.PLAN['evaluation_SC_cells'],4)
  self.assertEqual(d.PLAN['evaluation_planes'],97)
 def test_physical_evaluation_cap_is_not_dense_entry_count(self):
  result=d.register_counts(10,12)
  self.assertEqual(result['evaluation_cells'],970)
  self.assertEqual(result['dense_real_matrix_entries'],100)
  with self.assertRaises(ValueError):d.register_counts(10000,12000)
 def test_small_graph_stencil_has_no_wraparound(self):
  xy,ij,edges,degree=d._graph_records(4)
  for a,b in edges:
   self.assertEqual(abs(ij[a][0]-ij[b][0])+abs(ij[a][1]-ij[b][1]),1)
  self.assertEqual(sum(degree),2*len(edges))
  self.assertEqual(len(set(ij)),len(xy))

if __name__=='__main__':unittest.main()
