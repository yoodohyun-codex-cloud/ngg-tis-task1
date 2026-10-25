"""SOURCE PREPARATION ONLY: a hypothetical two-output floating bipolar CEM.

Import performs no I/O, scientific imports, array construction, or numerical work.
Only an independently authorized numerical owner may call ``solve``. No caller,
admission, cache loading, worker, publication, or hardware control is supplied.
The common-return solver and its results remain a separate baseline.
"""
from __future__ import annotations

import math
import time

PAIRS = ((0, 1), (2, 3))
SOURCE_RESISTANCE_OHM = 50.0  # TOTAL differential resistance per output.
SOURCE_PEAK_V = 0.5  # 1 Vpp high-impedance convention, before the one 50 ohm R.
H_M = 0.0005
MAX_XY = 7860
GMRES = dict(rtol=1e-12, atol=0.0, restart=80, maxiter=40)
LIMITS = dict(
    relative_algebraic_residual=2e-7,
    relative_loaded_current_residual=2e-7,
    relative_all_pad_KCL=2e-6,
    relative_pair_KCL=2e-6,
    relative_output_pad_current=2e-6,
    relative_layer_boundary_power_error=2e-7,
    relative_complex_power_error=2e-7,
    current_absolute_floor_A=1e-12,
    power_absolute_floor_W=1e-12,
    passivity_absolute_floor_W=1e-14,
    passivity_relative_allowance=1e-12,
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check(guard, deadline):
    require(callable(guard), "Owner resource/deadline guard is required")
    guard()
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("Floating CEM owner deadline exceeded")


def pair(value):
    return dict(real=float(value.real), imaginary=float(value.imag))


def _finite(value):
    return math.isfinite(value.real) and math.isfinite(value.imag)


def contact_equations(tissue, phi, metal, pads, cells, areas, zA, R=50.0):
    """Pure reference equations, with all FOUR metal potentials explicit.

    q is positive from tissue into metal. The three reduced rows are in amperes:
    pair-0 KCL; pair-0 differential voltage / R - q0; pair-1 voltage / R - q2.
    Subtract [0, Vs0/R, Vs1/R] to obtain the driven reduced residual. Neither
    this helper nor the circuit contains an earth/common-return connection.
    """
    require(len(phi) == len(tissue) and len(metal) == 4, "Tissue/four-metal ABI")
    require(len(pads) == len(cells) == len(areas), "Contact record ABI")
    require(R > 0 and math.isfinite(R), "Positive total differential resistance")
    require(_finite(zA) and zA.real > 0, "Finite passive specific contact impedance")
    surface = list(tissue)
    qpad = [0j] * 4
    for p, i, area in zip(pads, cells, areas):
        require(p in (0, 1, 2, 3) and 0 <= i < len(phi), "Physical pad/cell index")
        require(area > 0 and math.isfinite(area), "Positive finite patch area")
        q = (area / zA) * (phi[i] - metal[p])
        surface[i] += q
        qpad[p] += q
    rows = [qpad[0] + qpad[1],
            (metal[0] - metal[1]) / R - qpad[0],
            (metal[2] - metal[3]) / R - qpad[2]]
    return surface, rows, qpad


def signed_powers(tissue, phi, metal, pads, cells, areas, zA, ideal, R=50.0):
    """Pure signed peak-phasor power check, independently using circuit current.

    exp(+j omega t): S=.5 V conj(I). Capacitive reactive power is negative.
    ``tissue`` is A phi (outward CEM tissue operator); it must have zero sum.
    """
    require(len(ideal) == 2, "Two differential ideal source phasors")
    _, _, qpad = contact_equations(tissue, phi, metal, pads, cells, areas, zA, R)
    current = [(ideal[k] - (metal[p] - metal[m])) / R
               for k, (p, m) in enumerate(PAIRS)]
    contact = 0j
    for p, i, area in zip(pads, cells, areas):
        drop = phi[i] - metal[p]
        contact += 0.5 * drop * ((area / zA) * drop).conjugate()
    tissue_power = 0.5 * sum(v * j.conjugate() for v, j in zip(phi, tissue))
    resistor = 0.5 * R * sum(abs(v) ** 2 for v in current)
    source = 0.5 * sum(v * j.conjugate() for v, j in zip(ideal, current))
    return dict(source=source, tissue=tissue_power, contact=contact,
                resistor=resistor, current=current, qpad=qpad)


def reduced_system(np, tissue_operator, tissue_diagonal, pads, cells, areas,
                   zA, guard, deadline, R=50.0):
    """Deferred matrix-free n+3 system; V3=0 fixes ONLY a numerical gauge.

    Returned split/action/preconditioner are also usable by small synthetic
    tests. The exact 3x3 metal block preconditions current-scaled metal rows;
    no inverse of the full tissue matrix and no eigensolve is performed here.
    """
    check(guard, deadline)
    n = len(tissue_diagonal)
    require(0 < n <= MAX_XY and R > 0 and math.isfinite(R), "Finite system bounds/R")
    require(_finite(zA) and zA.real > 0, "Passive contact impedance")
    pads = np.asarray(pads)
    cells = np.asarray(cells)
    areas = np.asarray(areas, dtype=float)
    require(pads.ndim == cells.ndim == areas.ndim == 1 and
            len(pads) == len(cells) == len(areas) > 0, "Contact vectors")
    require(np.issubdtype(pads.dtype, np.integer) and
            np.issubdtype(cells.dtype, np.integer), "Integer contact indices")
    require(bool(np.all((pads >= 0) & (pads < 4))) and
            bool(np.all((cells >= 0) & (cells < n))), "Pad/cell bounds")
    require(bool(np.isfinite(areas).all()) and bool(np.all(areas > 0)), "Patch areas")
    require(all(bool(np.any(pads == p)) for p in range(4)), "All four physical pads present")
    require(len(set(zip(pads.tolist(), cells.tolist()))) == len(pads), "Unique pad/cell patches")
    g = areas / zA
    gsum = (np.bincount(cells, weights=g.real, minlength=n) +
            1j * np.bincount(cells, weights=g.imag, minlength=n))
    G = np.asarray([g[pads == p].sum() for p in range(4)], dtype=np.complex128)
    diagonal = np.asarray(tissue_diagonal, dtype=np.complex128) + gsum
    require(bool(np.isfinite(diagonal).all()) and bool(np.all(abs(diagonal) > 1e-30)),
            "Finite nonzero tissue/contact preconditioner diagonal")
    metal_block = np.asarray([[-G[0], -G[1], 0j],
                             [G[0] + 1 / R, -1 / R, 0j],
                             [0j, 0j, G[2] + 1 / R]], dtype=np.complex128)
    metal_inverse = np.linalg.inv(metal_block)  # only a 3x3 preconditioner block
    require(bool(np.isfinite(metal_inverse).all()), "Finite three-metal preconditioner")

    def split(x):
        phi = x[:n]
        metal = np.zeros(4, dtype=np.complex128)
        metal[:3] = x[n:]
        vp = metal[pads]
        q = g * (phi[cells] - vp)
        qsum = np.zeros(n, dtype=np.complex128)
        np.add.at(qsum, cells, q)
        qpad = np.asarray([q[pads == p].sum() for p in range(4)])
        return phi, metal, vp, q, qsum, qpad

    def action(x):
        check(guard, deadline)
        phi, metal, _, _, qsum, qpad = split(x)
        return np.r_[tissue_operator(phi) + qsum,
                     qpad[0] + qpad[1],
                     (metal[0] - metal[1]) / R - qpad[0],
                     (metal[2] - metal[3]) / R - qpad[2]]

    def precondition(x):
        check(guard, deadline)
        return np.r_[x[:n] / diagonal, metal_inverse @ x[n:]]

    return dict(n=n, split=split, action=action, precondition=precondition,
                metal_block=metal_block, g=g, pads=pads, cells=cells, areas=areas)


def solve(np, Q, profiles, pads, cells, areas, zA, activepair, guard, deadline,
          *, transform, gmres, linear_operator, h_m=H_M, settings=None):
    """Deferred owner-only solve; dependencies are explicitly injected.

    ``transform(np,Q,values,transpose=False)`` may be the unchanged frozen
    real/complex transform. ``profiles`` uses the unchanged design_screen
    Y, diagonal, unitV and unitJ ABI. Its V/J/gamma remain available unchanged
    for the caller's original continuous-z field reconstruction. All four
    metal values are returned; callers expecting the old two-metal ABI must
    adapt explicitly. No common-return solution is accepted as a cache hit.
    At 2000 Hz activepair=0; at 2010 Hz activepair=1. Frequency/material/contact
    identity is the caller's responsibility and must be separately recorded.
    """
    check(guard, deadline)
    require(activepair in (0, 1), "Exactly one active differential source")
    require(callable(transform) and callable(gmres) and callable(linear_operator),
            "Inject frozen transform and owner-provided linear algebra")
    n = Q.shape[0]
    require(Q.shape == (n, n) and 0 < n <= MAX_XY and h_m > 0, "Cached real-Q/grid ABI")
    Y = profiles['Y']
    require(Y.shape == (n,) and profiles['diagonal'].shape == (n,), "Modal/diagonal ABI")
    require(Y[0] == 0j and bool(np.isfinite(Y).all()), "Insulated constant mode")
    constant_error = float(np.linalg.norm(Q[:, 0] - Q[0, 0]))
    require(constant_error <= 1e-10, "First frozen Q mode is spatially constant")
    h2 = h_m * h_m

    def tissue(phi):
        check(guard, deadline)
        return h2 * transform(np, Q, Y * transform(np, Q, phi, True))

    system = reduced_system(np, tissue, profiles['diagonal'], pads, cells,
                            areas, zA, guard, deadline)
    constant_defect = float(np.linalg.norm(tissue(np.ones(n, dtype=np.complex128))))
    constant_scale = max(float(np.linalg.norm(profiles['diagonal'])), 1e-30)
    require(constant_defect / constant_scale <= 1e-10, "Tissue gauge/nullspace check")
    R = SOURCE_RESISTANCE_OHM
    ideal = np.zeros(2, dtype=np.complex128)
    ideal[activepair] = SOURCE_PEAK_V
    rhs = np.r_[np.zeros(n, dtype=np.complex128), 0j, ideal / R]
    iterations = []
    matvec_count = 0
    start = time.monotonic()

    def action(x):
        nonlocal matvec_count
        matvec_count += 1
        return system['action'](x)

    def callback(value):
        iterations.append(float(value))
        check(guard, deadline)

    options = dict(GMRES)
    if settings is not None:
        require(set(settings).issubset(GMRES), "Only explicit GMRES settings may vary")
        options.update(settings)
    A = linear_operator((n + 3, n + 3), matvec=action, dtype=np.complex128)
    M = linear_operator((n + 3, n + 3), matvec=system['precondition'], dtype=np.complex128)
    x, info = gmres(A, rhs, M=M, callback=callback, callback_type='pr_norm', **options)
    check(guard, deadline)
    phi, metal, vp, q, qsum, qpad = system['split'](x)
    require(bool(np.isfinite(x).all()), "Finite solved floating iterate")
    tissue_current = tissue(phi)
    differential = metal[[0, 2]] - metal[[1, 3]]
    current = (ideal - differential) / R  # independent circuit-branch current
    port_from_contact = -qpad[[0, 2]]
    terminal_current = np.asarray([current[0], -current[0], current[1], -current[1]])
    pad_residual = qpad + terminal_current
    coeff = transform(np, Q, phi, True)
    unitV, unitJ = profiles['unitV'], profiles['unitJ']
    require(unitV.shape == unitJ.shape and unitV.shape[0] == n and unitV.shape[1] >= 2,
            "Analytic boundary-flux profile ABI")
    Slayer = 0.5 * h2 * np.sum(abs(coeff[:, None]) ** 2 * (
        unitV[:, :-1] * unitJ[:, :-1].conj() -
        unitV[:, 1:] * unitJ[:, 1:].conj()), axis=0)
    Stissue = 0.5 * np.sum(phi * tissue_current.conj())
    Scontact = 0.5 * np.sum((vp - phi[system['cells']]) * (-q).conj())
    Presistor = 0.5 * R * float(np.sum(abs(current) ** 2))
    Ssource = 0.5 * np.sum(ideal * current.conj())
    Ssum = Slayer.sum() + Scontact + Presistor
    floorI = LIMITS['current_absolute_floor_A']
    floorP = LIMITS['power_absolute_floor_W']
    scale = max(float(np.linalg.norm(tissue_current)), float(np.linalg.norm(qsum)),
                float(np.linalg.norm(current)), float(np.linalg.norm(qpad)), floorI)
    pad_scale = np.maximum(np.maximum(abs(qpad), abs(terminal_current)), floorI)
    pair_net = np.asarray([qpad[0] + qpad[1], qpad[2] + qpad[3]])
    pair_scale = np.maximum(np.asarray([abs(qpad[:2]).sum(), abs(qpad[2:]).sum()]), floorI)
    errors = dict(
        relative_algebraic_residual=float(np.linalg.norm(action(x) - rhs) / np.linalg.norm(rhs)),
        relative_loaded_current_residual=float(np.linalg.norm(np.r_[
            tissue_current + qsum, pad_residual]) / scale),
        relative_all_pad_KCL=float(abs(qpad.sum()) / max(float(abs(qpad).sum()), floorI)),
        relative_pair_KCL=float(np.max(abs(pair_net) / pair_scale)),
        relative_output_pad_current=float(np.max(abs(pad_residual) / pad_scale)),
        relative_layer_boundary_power_error=float(abs(Slayer.sum() - Stissue) /
            max(abs(Slayer.sum()), abs(Stissue), floorP)),
        relative_complex_power_error=float(abs(Ssource - Ssum) /
            max(abs(Ssource), abs(Ssum), floorP)))
    gates = {key: bool(math.isfinite(value) and value <= LIMITS[key])
             for key, value in errors.items()}
    gates['passed'] = all(gates.values())
    powers = [complex(v) for v in Slayer] + [complex(Scontact), complex(Presistor)]
    allowance = (LIMITS['passivity_absolute_floor_W'] +
                 LIMITS['passivity_relative_allowance'] * max(abs(v) for v in powers))
    passive = all(_finite(v) and v.real >= -allowance for v in powers)
    proof = dict(
        topology='hypothetical_two_floating_bipolar_outputs_not_hardware_truth',
        gauge='Vmetal3=0 numerical reference only; no ground branch exists',
        pair_pad_indices=[[0, 1], [2, 3]], activepair=int(activepair),
        total_differential_series_resistance_ohm_per_output=R,
        source_peak_V=SOURCE_PEAK_V, source_high_impedance_Vpp=1.0,
        ideal_differential_source_peak_V=[pair(v) for v in ideal],
        inactive_output='zero ideal DIFFERENTIAL voltage through its own floating total50ohm',
        common_return_surface_reused=False, actual_new_RHS=1,
        gmres_info=int(info), iterations=len(iterations), history=iterations,
        matvec_count=matvec_count, wall_seconds=time.monotonic() - start,
        tissue_constant_nullspace_relative_defect=constant_defect / constant_scale,
        residual_errors=errors, physical_gates=gates,
        source_current_peak_A=[pair(v) for v in current],
        source_current_from_contact_peak_A=[pair(v) for v in port_from_contact],
        all_pad_outward_tissue_to_metal_current_peak_A=[pair(v) for v in qpad],
        pair_net_outward_current_peak_A=[pair(v) for v in pair_net],
        source_complex_power_W=pair(Ssource),
        layer_complex_power_W=[pair(v) for v in Slayer],
        tissue_boundary_complex_power_W=pair(Stissue),
        contact_complex_power_W=pair(Scontact), source_resistor_power_W=Presistor,
        passivity_passed=bool(passive), negative_real_power_allowance_W=allowance,
        passed=bool(info == 0 and gates['passed'] and passive),
        reciprocity='requires two basis solves AT ONE SAME frequency/material/contact; not 2000vs2010',
        interpretation='Conditional topology comparison only; existing convergence/material/contact/hardware holds remain')
    return dict(phi_surface=phi, metal=metal, source_current=current,
                source_current_from_contact=port_from_contact, coeff=coeff,
                contact_current=-q, contact_J=-q / system['areas'],
                contact_drop=vp - phi[system['cells']], layer_power=Slayer,
                source_power=Ssource, contact_power=Scontact,
                resistor_power=Presistor, proof=proof)
