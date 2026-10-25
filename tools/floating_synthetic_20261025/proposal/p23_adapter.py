"""Pure pad-number adapter; scientific operations are explicitly deferred.

Physical source assignments stay out0@2000 on pad0, out1@2010 on pad1.
The original frozen floating core pairs solver pads (0,1) and (2,3); the
involutive permutation below makes these PHYSICAL pairs (0,2) and (1,3).
No geometry, patch ordering, waveform amplitude, impedance or field is changed.
"""
from __future__ import annotations
import copy

PHYSICAL_PAIRS = ((0, 2), (1, 3))
PHYSICAL_TO_SOLVER = (0, 2, 1, 3)
SOLVER_TO_PHYSICAL = (0, 2, 1, 3)
TOPOLOGY = 'Hypothetical two isolated bipolar outputs: physical(0+,2-),(1+,3-); total50ohm/output; no earth branch'


def floating_geometry(original):
    result = copy.deepcopy(original)
    result['original_common_return_node_metadata'] = [
        dict(pad=p['pad'], node=p.get('node'), node_index=p.get('node_index'))
        for p in result['pads']]
    nodes = {0: ('out0+', 0, '+'), 2: ('out0-', 0, '-'),
             1: ('out1+', 1, '+'), 3: ('out1-', 1, '-')}
    for pad in result['pads']:
        pad['node'], pad['output_index'], pad['polarity'] = nodes[pad['pad']]
        pad['node_index'] = pad['pad']  # four independent equipotential metals
    result['power_topology'] = TOPOLOGY
    result['actual_hardware_wiring_claimed'] = False
    result['physical_mask_changed'] = False
    return result


def solve(np, Q, profiles, pads, cells, areas, zA, active_output, guard, deadline,
          *, floating_solver, transform, gmres, linear_operator):
    """Return physical pad order while preserving original source-output order."""
    physical = np.asarray(pads)
    if not np.issubdtype(physical.dtype, np.integer) or not bool(np.all((physical >= 0) & (physical < 4))):
        raise ValueError('Exact four physical pad IDs required before permutation')
    permutation = np.asarray(PHYSICAL_TO_SOLVER, dtype=int)
    mapped = permutation[physical]
    result = floating_solver(np, Q, profiles, mapped, cells, areas, zA,
        active_output, guard, deadline, transform=transform, gmres=gmres,
        linear_operator=linear_operator)
    result = dict(result)
    result['metal'] = result['metal'][np.asarray(SOLVER_TO_PHYSICAL)].copy()
    proof = copy.deepcopy(result['proof'])
    proof['solver_pair_pad_indices'] = proof['pair_pad_indices']
    proof['pair_pad_indices'] = [list(v) for v in PHYSICAL_PAIRS]
    proof['physical_to_solver_pad_permutation'] = list(PHYSICAL_TO_SOLVER)
    proof['driven_output'] = int(active_output)
    proof['topology'] = TOPOLOGY
    proof['actual_hardware_wiring_claimed'] = False
    proof['source_output_order_preserved'] = True
    qkey = 'all_pad_outward_tissue_to_metal_current_peak_A'
    solver_q = proof[qkey]
    proof['solver_order_outward_tissue_to_metal_current_peak_A'] = solver_q
    proof[qkey] = [solver_q[k] for k in SOLVER_TO_PHYSICAL]
    proof['contact_patch_order_preserved'] = True
    proof['metal_archive_order'] = 'physical pads0,1,2,3; pad3=0 PURE GAUGE'
    result['proof'] = proof
    return result


def correct_metric_metadata(result):
    """Correct only frozen common-return descriptive labels after evaluation.

    The frozen arithmetic is topology independent once given actual E/current/
    power. Its historical hard-coded common-ground label must never escape
    into this hypothetical floating result. Scalars/fields are unchanged.
    """
    result['summary']['return_topology'] = TOPOLOGY
    result['summary']['actual_hardware_wiring_claimed'] = False
    result['summary']['electrical']['return_topology'] = TOPOLOGY
    return result
