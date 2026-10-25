"""Synthetic source fixtures only; sole owner decides when to run them."""
import copy,json,unittest
import u19_inputs as m

def encoded(obj):return json.dumps(obj,separators=(',',':'),allow_nan=False).encode()
def faces():
 result=[];boundaries=(0.,.0001,.0051,.0101,.0251)
 for layer,count in enumerate(m.COUNTS):
  result.extend(boundaries[layer]+(boundaries[layer+1]-boundaries[layer])*j/count for j in range(count))
 return result+[.0251]
def admission_fixture():
 zs=faces();geometry=dict(faces_m=zs,face_table_sha256=m.digest(encoded(zs)),vertical_cells=101,XY_columns=7860,real_equivalent_native_cells=793860)
 spec=dict(schema='task1-fixed-SC8-VS-estimator-spec-v1',modes=[1,2,4,8,16],case_count=15,geometry={'U19':geometry},grids=[dict(id='U19',h_mm=.5,sc_cells=8,bulk_counts=[19,18,56],VS_grading='uniform')])
 review=dict(candidate='U19',true_continuum_error_nonregression=True,physical_error_improvement_review=True,automatic_native_admission=False)
 summary=dict(schema='task1-SC8-VS-estimator-manufactured-result-v1',status='calculated_manufactured_only_unadopted',spec=spec,analytic_contracts={'passed':True},new_real_native_PDE=0,predeclared_native_review=[review])
 sr,rr=encoded(spec),encoded(summary)
 decision=dict(schema='task1-u19-native-root-admission-v1',status='admitted_native_diagnostic',candidate='U19',root_review_positive=True,automatic_native_admission=False,candidate_adopted=False,new_native_conditions=1,maximum_native_RHS=2,mms_spec_sha256=m.digest(sr),mms_summary_sha256=m.digest(rr),mms_result_commit='a'*40,sc8_result_commit='b'*40,decision_basis='Synthetic positive U19 diagnostic decision, not actual admission')
 return sr,rr,decision

class U19Inputs(unittest.TestCase):
 def test_exact_faces_and_preserved_interfaces(self):
  zs=m.validate_faces(faces());self.assertEqual(len(zs),102)
  for index,value in((0,0),(8,.0001),(27,.0051),(45,.0101),(101,.0251)):self.assertAlmostEqual(zs[index],value,places=15)
 def test_bad_geometry_rejected(self):
  for change in('length','boundary','duplicate','nonfinite','nonuniform'):
   zs=faces()
   if change=='length':zs.pop()
   elif change=='boundary':zs[8]=.0002
   elif change=='duplicate':zs[10]=zs[9]
   elif change=='nonfinite':zs[10]=float('nan')
   else:zs[10]+=1e-6
   with self.subTest(change=change),self.assertRaises(ValueError):m.validate_faces(zs)
 def test_positive_synthetic_receipt_is_required(self):
  sr,rr,decision=admission_fixture();out=m.verified_admission(sr,rr,encoded(decision),'c'*40)
  self.assertEqual(out[3],faces())
  for key,value in(('root_review_positive',False),('candidate','G18'),('candidate_adopted',True),('automatic_native_admission',True),('mms_summary_sha256','0'*64),('maximum_native_RHS',4)):
   bad=copy.deepcopy(decision);bad[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):m.verified_admission(sr,rr,encoded(bad),'c'*40)
  with self.assertRaises(ValueError):m.verified_admission(sr,rr,encoded(decision),'PENDING')
 def test_failed_preregistered_MMS_review_rejected(self):
  sr,rr,d=admission_fixture();summary=json.loads(rr);summary['predeclared_native_review'][0]['true_continuum_error_nonregression']=False
  rr=encoded(summary);d['mms_summary_sha256']=m.digest(rr)
  with self.assertRaises(ValueError):m.verified_admission(sr,rr,encoded(d),'c'*40)
 def test_native_source_retains_frozen_science_and_owner_contract(self):
  source=(m.SOURCE/'VS19UniformSingleCarrierBasis.java').read_text()
  self.assertIn('class VSNativeMesh extends Mesh',source)
  self.assertIn('ShapeNet net=new ShapeNet(m,',source)
  self.assertNotIn('new ValidationMesh(.5,8',source)
  self.assertIn('m.n==793860&&m.n<=800000',source)
  self.assertIn('"u19_run.py"',source)
  self.assertIn('root_decision_public_commit',source)
  self.assertIn('worstResidual<=2e-7&&worstPower<=2e-7&&worstCurrent<=2e-6&&worstArea<=1e-10&&worstInterface<=2e-7',source)

if __name__=='__main__':unittest.main()
