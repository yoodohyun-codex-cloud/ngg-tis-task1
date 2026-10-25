"""Independent analytic unit-test SOURCE; caller owns any eventual execution.

No native files, reference outputs or research arrays are read. Tests use only
small manufactured inputs and fixed 1e-10 absolute/relative tolerances. A passed
test does not validate the cylindrical electrode/contact/material model.
"""
import cmath
import math
import unittest

import fourier_benchmark as f


ABS_TOL=1e-10
REL_TOL=1e-10
THICKNESSES=(.0001,.005,.005,.015)
GAMMA=(.002+.01j,.2+.002j,.04+.0002j,.3+.02j)


def centres_and_faces(counts):
    """Small independent physical z grid; no production grid helper reused."""
    faces=[0.]
    layerids=[]
    for layer,(thickness,count)in enumerate(zip(THICKNESSES,counts)):
        start=faces[-1]
        faces.extend(start+thickness*(i+1)/count for i in range(count))
        layerids.extend([layer]*count)
    centres=[(a+b)/2 for a,b in zip(faces[:-1],faces[1:])]
    return faces,layerids,centres


class FourierBenchmarkAnalyticTests(unittest.TestCase):
    def assertComplexClose(self,actual,expected):
        self.assertLessEqual(abs(actual-expected),ABS_TOL+REL_TOL*abs(expected))

    def assertComplexSequenceClose(self,actual,expected):
        self.assertEqual(len(actual),len(expected))
        for i,(value,reference)in enumerate(zip(actual,expected)):
            with self.subTest(index=i):self.assertComplexClose(value,reference)

    def test_zero_mode_insulated_layered_profile_is_constant(self):
        _,_,zs=centres_and_faces((2,3,3,4))
        values,currents,states=f.exact_profile(0.,GAMMA,THICKNESSES,zs)
        self.assertComplexSequenceClose(values,[1.+0j]*len(zs))
        self.assertComplexSequenceClose(currents,[0j]*len(zs))
        self.assertEqual(len(states),5)
        for value,current in states:
            self.assertComplexClose(value,1.+0j)
            self.assertComplexClose(current,0j)

    def test_zero_mode_two_dirichlet_slab_has_nonzero_constant_current(self):
        # Supplementary analytic boundary condition: Vtop=1, Vbottom=0.
        # It is distinct from exact_profile's manufactured insulated bottom.
        current=1./sum(d/g for d,g in zip(THICKNESSES,GAMMA))
        self.assertGreater(abs(current),1e-12)
        state=(1.+0j,current)
        consumed=0j
        for gamma,thickness in zip(GAMMA,THICKNESSES):
            state=f.transfer_state(state,0.,gamma,thickness)
            consumed+=thickness/gamma
            self.assertComplexClose(state[0],1.-current*consumed)
            self.assertComplexClose(state[1],current)
        self.assertComplexClose(state[0],0j)
        for gamma,thickness in reversed(list(zip(GAMMA,THICKNESSES))):
            state=f.transfer_state(state,0.,gamma,-thickness)
        self.assertComplexClose(state[0],1.+0j)
        self.assertComplexClose(state[1],current)

    def test_homogeneous_cosh_profile_has_correct_top_current_sign(self):
        k=2.*math.pi*2./.050
        gamma=.2+.03j;length=sum(THICKNESSES)
        _,_,zs=centres_and_faces((2,3,3,4))
        values,currents,states=f.exact_profile(k,[gamma]*4,THICKNESSES,zs)
        expected_v=[math.cosh(k*(length-z))/math.cosh(k*length)for z in zs]
        expected_j=[gamma*k*math.sinh(k*(length-z))/math.cosh(k*length)for z in zs]
        self.assertComplexSequenceClose(values,expected_v)
        self.assertComplexSequenceClose(currents,expected_j)
        self.assertComplexClose(states[0][0],1.+0j)
        self.assertComplexClose(states[-1][1],0j)
        self.assertGreater((states[0][1]/gamma).real,0.)
        self.assertComplexClose(states[0][1],gamma*k*math.tanh(k*length))

    def test_layered_interface_states_propagate_downward_and_invert(self):
        k=2.*math.pi/.050
        _,_,zs=centres_and_faces((2,3,3,4))
        _,_,states=f.exact_profile(k,GAMMA,THICKNESSES,zs)
        for layer,(gamma,d)in enumerate(zip(GAMMA,THICKNESSES)):
            upper=states[layer];lower=states[layer+1]
            # Independently spell out the downward transfer sign convention.
            c=math.cosh(k*d);s=math.sinh(k*d)
            expected=(c*upper[0]-s*upper[1]/(gamma*k),
                      -gamma*k*s*upper[0]+c*upper[1])
            self.assertComplexSequenceClose(lower,expected)
            self.assertComplexSequenceClose(f.transfer_state(lower,k,gamma,-d),upper)

    def test_small_k_limit_agrees_with_insulated_zero_mode(self):
        _,_,zs=centres_and_faces((2,3,3,4))
        values,currents,_=f.exact_profile(1e-6,GAMMA,THICKNESSES,zs)
        self.assertComplexSequenceClose(values,[1.+0j]*len(zs))
        self.assertComplexSequenceClose(currents,[0j]*len(zs))

    def test_fvm_zero_mode_respects_dirichlet_and_insulated_bottom(self):
        faces,layerids,zs=centres_and_faces((2,3,3,4))
        values=f.solve_fvm(0.,GAMMA,faces,layerids)
        self.assertComplexSequenceClose(values,[1.+0j]*len(zs))

    def test_fvm_homogeneous_exact_discrete_recurrence(self):
        # Exact DISCRETE solution for half-cell Dirichlet and zero bottom flux.
        # This is not the continuum cosh solution and tolerances do not absorb
        # discretization error.
        n=8;dz=.001;kfd=87.;gamma=.2+.03j
        faces=[i*dz for i in range(n+1)]
        layers=[i//2 for i in range(n)]
        values=f.solve_fvm(kfd,[gamma]*4,faces,layers)
        theta=math.acosh(1.+(kfd*dz)**2/2.)
        denominator=math.cosh(theta*n)*math.cosh(theta/2.)
        reference=[math.cosh(theta*(n-.5-i))/denominator for i in range(n)]
        self.assertComplexSequenceClose(values,reference)
        q2=(kfd*dz)**2
        self.assertComplexClose((3.+q2)*values[0]-values[1],2.)
        self.assertComplexClose((1.+q2)*values[-1]-values[-2],0.)
        for i in range(1,n-1):
            self.assertComplexClose((2.+q2)*values[i]-values[i-1]-values[i+1],0.)
        self.assertGreater(values[0].real,0.)
        self.assertLess(values[0].real,1.)

    def test_fvm_layered_flux_balance_with_independent_complex_harmonic_faces(self):
        faces,layerids,zs=centres_and_faces((2,3,3,4))
        kfd=71.;values=f.solve_fvm(kfd,GAMMA,faces,layerids)
        widths=[b-a for a,b in zip(faces[:-1],faces[1:])]
        conductance=[1./(widths[i]/(2.*GAMMA[layerids[i]])+
                           widths[i+1]/(2.*GAMMA[layerids[i+1]]))
                     for i in range(len(values)-1)]
        for i,value in enumerate(values):
            up=(2.*GAMMA[layerids[0]]/widths[0]*(value-1.)if i==0 else
                conductance[i-1]*(value-values[i-1]))
            down=(conductance[i]*(value-values[i+1])if i+1<len(values)else 0j)
            lateral=GAMMA[layerids[i]]*widths[i]*kfd*kfd*value
            scale=max(abs(up),abs(down),abs(lateral),1.)
            self.assertLessEqual(abs(up+down+lateral),ABS_TOL+REL_TOL*scale)

    def test_exact_sample_polyfit_jump_is_truncation_not_physical_discontinuity(self):
        # All four gamma values equal: both exact V and exact J are continuous.
        # Deliberately sample exact curved potential on a coarse vertical grid.
        # The common two-point derivative extrapolation is biased on each side.
        gamma=.2+.03j;k=200.;counts=(2,4,4,4)
        _,_,zs=centres_and_faces(counts)
        values,_,states=f.exact_profile(k,[gamma]*4,THICKNESSES,zs)
        boundary=counts[0]+counts[1]  # z=5.1 mm, equal cell spacing on both sides.
        upper_derivative=(values[boundary-1]-values[boundary-2])/(zs[boundary-1]-zs[boundary-2])
        lower_derivative=(values[boundary+1]-values[boundary])/(zs[boundary+1]-zs[boundary])
        upper_j=-gamma*upper_derivative;lower_j=-gamma*lower_derivative
        exact_j=states[2][1]
        self.assertGreater((upper_j/gamma).real,(exact_j/gamma).real)
        self.assertGreater((exact_j/gamma).real,(lower_j/gamma).real)
        self.assertGreater(abs(upper_j-lower_j),1e-8)
        # Independent cosh reference establishes exact current at the boundary.
        depth=sum(THICKNESSES[:2]);length=sum(THICKNESSES)
        reference_j=gamma*k*math.sinh(k*(length-depth))/math.cosh(k*length)
        self.assertComplexClose(exact_j,reference_j)


if __name__=='__main__':unittest.main()
