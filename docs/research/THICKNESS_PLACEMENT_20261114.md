# TIS thickness and placement comparison — 2026-11-14

**Status: blocked before implementation/execution; new PDE 0, numerical rescaling 0, workers created 0.** This is a bounded experiment design and source audit, not simulation results or an executable restoration bundle.

The new task varies dermis and fat thickness, fixes SC at 0.1 mm and the phantom diameter at 50 mm, and compares voltage compensation with placement compensation in the same 15–20 mm volume. It does not replace the existing baseline, raw data, failures, GUI pointers or Task 2 work.

## Environment and repository evidence

| Check | Actual observation | Consequence |
|---|---|---|
| Selected execution environment | The platform reported failure querying executor configuration capabilities. The subsequent environment-status API changed from starting to running, but the command provider returned `No usable execution environment is available. Wait for an environment to become available before using this tool.` | No requested shell command executed. Filesystem, installed solver, CPU/RAM, runtime ledgers and locks remain uninspected. Control-plane running is not executor readiness. |
| Original computation filesystem | Not accessible through the command provider in this task | No claim that this environment, another checkout, or the public restart package is the original compute filesystem. No local-path or raw-basis restoration was performed. |
| Existing numerical owner | Current live PID/startticks and both ownership locks cannot be inspected | Worker state **unknown**, not idle. No replacement worker, stop signal, lock removal or duplicate solve. |
| GitHub provider | Read operations succeeded; PR2 head `95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98` | Public evidence can be inspected and this separate plan can be versioned. This does not establish compute access. |
| Other work | Open PR1 review head f44ac2d; PR3 GUI head 0d3039b. Branches isolated-pairs-local and windows-owner-adapter diverge from PR2; best1-pair-source is behind it | Do not overwrite or merge these branches. Floating isolated pairs are a different circuit from this common-return comparison. |
| Latest compute report | [E13 drive report](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/docs/TASK1_CONTACT_EDGE_20261025/E13-fine-drive-stream-root-review.md) is dated October 25. Its next E11 condition was not run: predicted aggregate memory 8,300,885,378 B for numerical work / 8,410,885,378 B for publication exceeded 8,000,000,000 B | Historical admission forecast, not a current measurement or an observed OOM. It cannot establish current free memory or whether a different bounded case fits. |
| Operational policies | [AGENTS](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/AGENTS.md), [execution-policy helper](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tools/task1_execution_policy.py) record CPU up to 4, aggregate owned RSS + all task-owned tmpfs at most 8,000,000,000 B, Java heap 2 GiB, 800,000 cells, one owner/solve, finite watchdogs. Later recorded policy removes the cumulative-time ceiling and old storage-reserve guards | This task changes no resource policy. Actual effective limits must be verified in the original environment. The operational runtime policy/approval paths returned GitHub 404; do not fabricate their bytes from documentation. |
| Migration | [manifest](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/MIGRATION_MANIFEST.json) remains a bootstrap inventory; later published native manifests cover additional specific runs | Repository access is not proof of whole-history raw restoration or Windows saving. Preserve all originals. |

Read sources include README, AGENTS, CODEX_START_PROMPT, RESEARCH_LOOP, MIGRATION and the migration manifest, PAD_COUNT_DESIGN_CONTRACT, PR2 discussion, current index and the latest E13 report. The older README/index/PR body is not used to override the later policy or to infer a live worker.

The exact executor failure is the current action blocker. This is **not** an automatic-approval rejection, a request for new compute resources, or a reason to change credentials/security. No COMSOL installation/license/runtime was verified; no COMSOL action was attempted.

## Explicit reference cohort

The initial reference proposed here is the **documented original 2000/2010 Hz bare-NGG exploratory model**, with four **10 × 10 mm** pads (100 mm² each, 400 mm² total), because these frequencies and pad dimensions are present together in [model-inputs](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/model-inputs.json), [NggSweep](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/NggSweep.java) and [TisSweep](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/TisSweep.java). This is a newly named comparison cohort; its reference values must be calculated with the new volume metric and bound configuration. It is not a claim to reproduce a historically selected winner.

Do not silently substitute the later 225 mm²-per-pad B0/P23/E13 or 3000/3030/9000/9090 Hz square-wave cohorts. Their results remain separate, immutable historical comparators. No previous 3 kHz or E13 mean is copied as the target for this new 2 kHz cohort.

Reference layout L0 is the existing TisSweep layout `a12.5_b12.5_p1`:

| Pad | Centre (x,y) mm | Connection |
|---|---|---|
| 0 | (−12.5,−12.5) | output 0 |
| 1 | (+12.5,+12.5) | output 1 |
| 2 | (+12.5,−12.5) | common GND |
| 3 | (−12.5,+12.5) | common GND |

There are two independent outputs and one common return node, not four sources. Each output has 50 Ω series resistance. At 2000 Hz drive output 0 only; at 2010 Hz drive output 1 only. The inactive source is 0 V behind its 50 Ω termination. Use zero-DC sinusoids, the original equal phase convention, peak phasors exp(+jωt), and **1 Vpp high-Z command per active output = 0.5 Vpeak before 50 Ω**. Loaded metal/tissue/contact voltages and all currents are solved quantities. Beat frequency is 10 Hz; no third harmonics are included.

### Material/contact control

For this separately labelled historical-control cohort, [simulation.properties](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/simulation.properties) supplies the following **uncalibrated assumptions**, held constant across all thickness/placement cases:

| Layer | σ (S/m) | εr |
|---|---:|---:|
| SC | 0.0002 | 110000 |
| dermis | 0.2 | 10000 |
| fat | 0.04 | 1000 |
| muscle | 0.3 | 100000 |

This retains a controlled mathematical comparison; it does **not** overturn the existing paper/material audit or certify these values. In particular the Anand phantom data do not validate the fat .04/1000 pair, and independent SC/dermis carrier values remain unvalidated. The later mixed-material/E13 family is not silently relabelled as this historical control. No layer property is adjusted to make a preferred gradient or target value.

Use γ(f)=σ+j2πfε0εr in SI units. Constant σ/εr across the two tones is an explicit model limitation, not measured dielectric dispersion. Keep conduction current σE and total current γE separate.

The [initial bare-NGG properties](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/electrode-data/bare-ngg-initial.properties) and NggSweep define measured complex PBS EIS minus fitted Rs, then multiply by the measured 0.0001 m² **once**. The area-specific interface values are:

| Hz | Re(Zarea), Ω m² | Im(Zarea), Ω m² |
|---|---:|---:|
| 2000 | 0.0010246703091681638 | −0.0022333986363121724 |
| 2010 | 0.0010212321657819615 | −0.0022243456968300194 |

Rs≈213.279972 Ω is an EIS fit subtraction, not the generator's 50 Ω. These are nominal PBS-derived interface assumptions, not validated dry NGG skin contact. Freeze input file bytes/hash and effective numbers before execution; do not infer bulk tissue values from electrode EIS.

## Thickness and target geometry

Vary one layer at a time by ±1 mm around 5 mm. These are synthetic ±20% sensitivities, **not human thickness distributions**. Muscle stays 15 mm; the lower boundary therefore moves. Side and bottom insulation remain explicit assumptions.

| Case | SC / dermis / fat / muscle, mm | Muscle starts at z, mm | Bottom z, mm | Fixed z15–20 ROI relative to muscle top, mm |
|---|---|---:|---:|---|
| T0 | 0.1 / 5 / 5 / 15 | 10.1 | 25.1 | 4.9–9.9 |
| D4 | 0.1 / 4 / 5 / 15 | 9.1 | 24.1 | 5.9–10.9 |
| D6 | 0.1 / 6 / 5 / 15 | 11.1 | 26.1 | 3.9–8.9 |
| F4 | 0.1 / 5 / 4 / 15 | 9.1 | 24.1 | 5.9–10.9 |
| F6 | 0.1 / 5 / 6 / 15 | 11.1 | 26.1 | 3.9–8.9 |

The primary region remains **r≤5 mm, absolute z15–20 mm measured from the top SC surface**. It lies entirely in muscle for these five cases, but its depth below muscle and distance from the bottom change. Report that movement and the finite-bottom confound. Do not move the primary ROI with a layer boundary or hold total depth fixed by silently changing muscle thickness.

Use exact physical ROI/cell overlap weights; the ideal target volume is 125π mm³. Report represented volume, tissue fractions and quadrature error. Material-relative auxiliary regions may be added with explicit labels, but cannot replace the fixed-depth comparison.

## A–D comparisons and matching rule

Use M(x)=max over the same ordered 2074 real unit directions of **2 min(|u·E2000(x)|, |u·E2010(x)|)**. Preserve the original 26 lattice + 2048 Fibonacci direction construction and its hash. This is a sampled directional maximum (a lower bound on the continuum angular maximum), not recruitment. Report fixed x/y/z TIS separately and carrier RMS as sqrt((||E2000||²+||E2010||²)/2).

Let μ0 and q0 be the volume-weighted mean and P10 of T0/L0 at the reference command. Use stable inverse volume-weighted ECDF for P10. Values are currently **null/not_run**.

| Comparison | New fields needed after admission | Input/placement treatment |
|---|---|---|
| A: thickness only | T0,D4,D6,F4,F6 at L0 | Identical 1/1 Vpp, phase, contacts, materials and four pad areas |
| B: voltage compensation | Reuse each A case's exact complex solution | Positive common amplitude kμ=μ0/μ. Scale φ,E,J and source currents by kμ, complex/real power by kμ². No new PDE. Also report q0/q separately; never claim both match from matching mean alone. |
| C: placement only | At the single altered-thickness case with largest absolute fractional mean departure in A, evaluate L1 and L2 below | Same 1/1 Vpp and contact area. Tie-break D4,D6,F4,F6. Selection concerns model sensitivity, not an optimum. |
| D: placement + voltage | Reuse the two C solutions | Apply the same common-amplitude matching and report residual P10/spatial errors and all burdens. No extra PDE. |

L1 uses centres (±10,±10) mm with the same diagonal signal/return mapping as L0; L2 uses (±7.5,±7.5) mm with that mapping. All pads remain axis-aligned 10 mm squares. Minimum edge gaps are 15/10/5 mm for L0/L1/L2; all corners lie within radius25 mm. Verify clipped cell/contact intersections analytically before assembling. The two new placements explore a small inward-spacing family only. Failure does not establish that no placement can match.

Provisional numerical matching criterion, registered before results: both |μ/μ0−1| and |P10/q0−1| ≤1%, plus common-physical-ROI map relative L2 difference ≤5%. These are comparison tolerances, not biological thresholds or proof of numerical convergence. Compute map error with conservative physical overlap across grids, not equal array indices. μ0/q0≤0, non-finite values or missing overlap produce `not_matchable` with reason, never an infinite voltage. Report actual signed errors even if a row passes.

Always separate (i) raw equal command, (ii) common voltage rescaling, (iii) equal real source power, (iv) equal sum of output RMS currents **bookkeeping**, and (v) simultaneous reference-relative burden limits. The latter uses this cohort's T0/L0 values, not a 900 mm² later cohort's caps: skin vector Jmax/J95, contact-normal Jmax/J95, maximum contact voltage, SC power, contact power and source real power. These eight quantities are model-comparison ceilings, not safety limits. A target match that exceeds any ceiling remains explicitly burden-increased.

Per-frequency complex pad/source currents, the complex sum of return-pad currents before RMS, loaded voltages, signed VI*/2 power, each layer/contact/50 Ω loss, surface0–5 mm and target-complement mean/P95/max and high-modulation volume must accompany target mean/P10/CV/maps. Sum of RMS output currents is not the net common-ground current. Preserve negative signed power where applicable; do not clip it.

## Solver changes and finite admission

Static inspection found hard-coded layer thicknesses in [TisSweep.Mesh](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/TisSweep.java) and [SelectivityShapeBasis.ValidationMesh](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tis-java/SelectivityShapeBasis.java). ValidationMesh also whitelists bulk counts, while its exporter hard-codes total depth25.1 and boundaries0/.1/5.1/10.1/25.1. **A properties-file edit alone cannot implement this experiment.** Do not run NggSweep.main: it launches its old54-case sweep.

Required new isolated implementation, **not implemented/tested here**:
- One parameterized isotropic mesh/boundary builder using thickness arrays, derived z edges, layer masks, volumes, total depth and metadata consistently. No changes to frozen originals.
- Exact contact intersection areas and consistent potential/complex E/J reconstruction, including partial contacts, displacement current and moving material interfaces.
- The 2000/2010 actual-drive coupled source circuit, with two actual RHS per geometry (one per tone). No assumption that old all-frequency basis files can be reused across changed thickness.
- Lossless complex128/Float64 native φ/E/J, grid/volumes/ROI weights, config/material/contact/source manifests and source hashes. No Float16-only quantitative export.

Proposed exploratory grid: hXY=.625 mm, SC4 cells, bulk dz≤.3125 mm with counts ceil(thickness/.3125). T0 uses4/16/16/48; 6 mm cases use20 cells in the varied layer. This differs from historical grids and must have a new identity. No baseline target number is borrowed from a different grid.

First admit **only T0** after preflight and synthetic checks. If gates fail, preserve failure and stop dependent comparisons. If they pass, the planned finite scope is A's five cases plus C's two placements, at most7 primary geometries/14 actual RHS. B/D are separately counted linear rescaling. Up to two paired hXY=.5 mm checks (T0 and the selected changed-thickness case; same SC/bulk partition) give a total ceiling of9 geometries/18 RHS. All must remain below800000 cells; compute exact counts rather than rely on nominal estimates. No Cartesian sweep and no automatic third placement.

Each stage has a finite watchdog fixed before execution: preparation/synthetic checks120s, each two-tone geometry600s, each full-volume metric stage300s, each preservation/publication stage360s. A timeout is a preserved failure, not permission to extend the budget or relaunch. Aggregate live RSS+all owned tmpfs, source/input hashes, both owner locks and actual available storage/transport must be rechecked before each stage. This plan neither reinstates obsolete reserve guards nor expands current limits; actual I/O failure blocks completion.

Required validations before any scientific comparison:
1. Geometry/units/layer-boundary/ROI overlap and pad-area/no-overlap tests, including all five thickness cases. Old baseline geometry equivalence; no ignored thickness property.
2. Independent homogeneous affine and layered complex slab cases; analytic current/power and z-interface gradients. Separate shared-flux algebra checks from independent interface accuracy.
3. Original source/50 Ω/inactive-output/area scaling and synthetic two-tone envelope checks; single carrier, collinear equal amplitudes and phase-bearing vectors.
4. Actual residual≤2e−7, real-power error≤2e−7, current error≤2e−6, area error≤1e−10 and shared-face current error≤2e−7, with raw maxima and thresholds.
5. Independent potential-only one-sided tangential E/normal total J diagnostics at all moving interfaces, all/interior/periphery regions, plus side/bottom treatment. Do not invent a passing threshold after seeing results.
6. Paired-grid mean/P10, maps, J/contactV/powers and extrema coordinates. Retain all existing SC/XY/edge/contact failures. A two-level comparison cannot certify full convergence; significant mesh movement relative to matching tolerances prevents a robust matching claim.

## Required output and current status

Use a new uniquely named run and separate source branch. Never overwrite historical files or current.json. Each actual run needs environment/owner identity, PID+startticks, lock proof, source/config/mask/material/contact hashes, command, UTC start/end/exit, resource maxima and native artifact locations. Bind model parameters and exact arrays before execution; unavailable values remain null. Common-scale unclipped maps must show units/colorbar and actual ranges; optional layer zooms remain labelled. Geometry-only illustrations are not calculated field maps.

| Stage | Current status |
|---|---|
| Public-source and branch inventory | completed, limited to GitHub provider |
| Original filesystem / live worker / dual locks / current resources | blocked, not inspected |
| Source implementation and synthetic tests | not_run |
| T0 new reference and A thickness PDEs | not_run |
| B/D numerical rescaling | not_run |
| C placement PDEs | not_run |
| Grid/interface numerical validation | not_run |
| Native restore, new field maps, Windows save | not_run |
| Draft scientific plan | prepared; not an execution receipt |
| Physiological/clinical/activation/safety validity | not established; outside this electrical comparison |

Resume requires a usable command connection to the intended computation environment and verification of its existing owner, operational policies, retained inputs and effective resource headroom. No installation, COMSOL activation, credentials/security change, deletion, paid compute, resource expansion, main merge, or alteration of Task 2 is authorized or performed by this plan.
