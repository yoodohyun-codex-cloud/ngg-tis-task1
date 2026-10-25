# Proposed manufactured Fourier interface benchmark

Status: source-only proposal, not registered or executed. No existing XY source,
run evidence, acceptance threshold, material value or worker is changed.

The question is whether the independent polynomial interface-current diagnostic
can show a large jump even when its input potential is an exact continuous
solution. A second comparison estimates vertical and lateral discretization
error. Neither result alone validates the real cylindrical CEM simulation.

## Domain and fixed inputs

- Manufactured domain: x periodic with period 50 mm, independent of y. Four
  horizontal layers have fixed thickness 0.1/5/5/15 mm and interfaces
  z=0/0.1/5.1/10.1/25.1 mm; z increases downward.
- Frequency is 2000 Hz. Take each complex gamma=sigma+j*omega*epsilon0*epsilon_r
  from the already verified 2000 Hz receipt/config, hash-pinned and reused
  without refitting or evaluation of a different material model.
- For each separate mode m in [1,2,4,8,16], k=2*pi*m/(0.050 m), top potential
  phi(x,0)=cos(k*x) Vpeak, bottom Jz=0. This is a manufactured continuous
  Dirichlet source, not an electrode, CEM, 50-ohm source, hardware, real phantom
  or candidate. No TIS modulation or physiological claim is defined here.
- Grids A=(h=.625 mm,SC2,bulk14/14/40), B=(h=.5 mm,SC2,bulk14/14/40),
  C=(h=.5 mm,SC2,bulk18/18/56). Optional D=(h=.5 mm,SC4,bulk18/18/56)
  requires explicit selection before execution; D isolates SC at the same
  bulk grid as C. No real phantom dimensions are changed.

## Exact solution and signs

Within a layer, phi(x,z)=V(z)*cos(k*x), V''-k^2*V=0, and
J(z)=-gamma*V'(z). For s=[V,J], downward propagation is

P(d)=[[cosh(k*d), -sinh(k*d)/(gamma*k)],
      [-gamma*k*sinh(k*d), cosh(k*d)]],  s(z+d)=P(d)*s(z).

Start at the bottom with [1,0], propagate UPWARD in reverse layer order using
P(-d), and normalize every interface state by the resulting Vtop. Using P(+d)
bottom-up gives the wrong current sign. V and J are continuous at an ideal
interface. Evaluate cell-centre states from the nearest lower interface using
P(-distance); avoid reconstructing a small deep solution by cancellation of two
large terms propagated downward from the top.

Compute exact interface J once. Analytic x-current is -gamma*dphi/dx and is not
needed to reinterpret a normal-current jump. The manufactured problem has no
cylinder perimeter or staircase, so it cannot reproduce or clear a real
periphery-specific error.

## Separating the error sources

For each mode/grid, preserve four distinct data products:

1. Exact continuum solution with k, sampled at actual vertical cell centres.
   Apply two-nearest-point fits on BOTH sides of each interface, and the old
   up-to-three-point diagnostic separately (SC2 upper side remains two points).
   Compare both estimates with the true analytic J and with each other. A jump
   here is diagnostic truncation on exact data, not PDE error.
2. Exact solution with k_fd=2*sin(k*h/2)/h. The difference from product 1
   describes the lateral central-difference symbol, without vertical FVM error.
3. A complex tridiagonal vertical FVM solution using k_fd. Compare centre
   potential and shared interface flux with product 2 to estimate vertical
   discretization error; compare with product 1 to report combined error.
4. Apply the same independent two-point/up-to-three-point fits to product 3.
   Report the diagnostic jump, exact-sample fit bias and actual flux/potential
   error separately. Shared FVM flux is single-valued by construction; it is
   not an independent accuracy certificate.

No fitted correction is subtracted from a real 3D result. No threshold is moved
because an exact-sample fit fails a screening flag.

## Vertical FVM equations (per unit horizontal area)

For adjacent centres i,j, G_ij=1/(dz_i/(2*gamma_i)+dz_j/(2*gamma_j)), units S/m^2.
For each cell, the tridiagonal diagonal is G_up+G_down+gamma_i*dz_i*k_fd^2,
with off-diagonals -G_up/-G_down. The top Dirichlet half-cell has
G_D=2*gamma_0/dz_0, adds G_D to the first diagonal, and RHS=G_D*1 V.
Bottom Neumann zero adds no face conductance or RHS term. Solve in complex128
with a bounded O(Nz) Thomas solver and report residuals. No SciPy installation,
3D native PDE, mesh mask, contact model or circuit solve is required.

## Norms, tests and unchanged screening

- Preserve the existing independent normal-current screening value: spatial
  RMS(up-low)/max(spatial RMS(up),spatial RMS(low),1e-12 A/m^2), with 5% flag.
  Compute sampled spatial RMS over a complete periodic x grid. Report the
  absolute difference and numerator/denominator as well. It remains a
  proposed numerical diagnostic flag, not biological or physical validation.
- Report amplitude/reference errors with explicit units and denominators;
  avoid dividing by vanishing exact J at the insulated bottom. Cell-volume
  weighting applies to centre errors; equal-area weighting applies to faces.
- Before modes run, require analytic tests with 1e-10 relative +1e-10 absolute
  tolerances: interface continuity/propagation inverse, constant-complex-gamma
  solution V=cosh(k*(L-z))/cosh(k*L), a zero-mode insulated constant V=1,J=0,
  a supplementary zero-mode two-Dirichlet layered slab with nonzero constant
  J=1/sum(d/gamma), and small-k continuity. The supplementary slab is a test
  boundary condition, not one of the manufactured reporting modes.
- An exact discrete homogeneous recurrence provides an additional FVM solver
  check distinct from the continuum solution. A small algebraic residual alone
  does not establish discretization accuracy.
- Keep the real-run 1% ROI /5% contact J and voltage /2% power adjacency rules,
  independent 5% flags, and all SC/bulk/edge/contact/material/anatomy holds.
  Manufactured results cannot close these real-model holds.

## Proposed source API and execution boundary

Pure functions, with no IO on import:

- required_inputs() -> SHA map for the verified 2000 Hz receipt/config and the
  exact stored real diagnostic summaries used only for contextual comparison.
- make_spec(material_receipt_bytes, config_bytes, optional_sc4=False) -> JSON
  spec plus receipt hashes; verifies existing gamma only, no refitting.
- run_manufactured(spec, guard, deadline_monotonic) -> {summary, arrays}.
  Calls the finite owner's guard between every mode/grid, has no file writes,
  solver process, Git, lock, ledger or worker creation.
- analytic_contracts() -> explicit test results, run by the owner before data
  evaluation; no research native arrays are needed.

A prospective owner may admit one small finite stage (suggested 10 seconds,
CPU1, existing RAM policy) after inspecting the actual XY result. It must pin
sources/spec/material bytes and record actual wall time/status/next action.
This proposal does not authorize an execution or claim any benchmark outcome.

## Additional analytic audit

A stable independent cross-check can recurse complex admittance upward from
Ybottom=0:

Yupper=(Ylower+gamma*k*tanh(k*d))/(1+Ylower*tanh(k*d)/(gamma*k)).

Preserve complex gamma, check finite nonzero denominators, and recover amplitudes
from stored layer ratios. This is useful alongside the direct bottom-up state
construction; agreement is a check, not an additional physical model.

For a uniform vertical grid of N cells and one constant complex gamma, define
q=k_fd*dz and theta=acosh(1+q^2/2). The exact solution of the stated discrete
recurrence and half-cell Dirichlet/zero-flux boundaries is

V_i = Vtop*cosh(theta*(N-0.5-i))/(cosh(theta*N)*cosh(theta/2)).

This provides a discrete solver test distinct from a continuum approximation.
The k=0 limit is V_i=Vtop. Any future implementation must use stable cosh ratios
when extending the requested mode range; raw matrix products are unnecessary.

Two-point one-sided derivatives at an interface have opposite first-order
curvature biases. For locally uniform centre spacing dz,
upper_fit ~= V'(interface)-dz*V''(interface),
lower_fit ~= V'(interface)+dz*V''(interface), with V''=k^2*V.
After multiplication by the different complex layer gamma, a substantial
estimated J jump can occur on an exactly continuous solution. Each side's error
relative to the exact analytic J must be retained: a small jump could also hide
two biased estimates that cancel. Phase nodes/near-zero currents require
absolute errors and disclosed denominator-floor counts, never ratio-only claims.
