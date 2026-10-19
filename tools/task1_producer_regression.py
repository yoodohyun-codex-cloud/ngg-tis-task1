"""Gate a distinct grouped exporter against the reproduced four-square basis."""
import gzip
import hashlib
from pathlib import Path

import numpy as np


def _raw(folder, name):
    plain = Path(folder)/name
    path = plain if plain.is_file() else plain.with_name(plain.name+'.gz')
    if not path.is_file():
        raise ValueError('Producer comparison missing '+str(path))
    data = gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
    return path, data


def compare_producer(reference, candidate):
    rows=[]
    for frequency in (3000,3030,9000,9090):
        for kind in ('field','potential','density','source','loss'):
            name=f'{kind}-{frequency}.bin'
            pa,ra=_raw(reference,name);pb,rb=_raw(candidate,name)
            a,b=np.frombuffer(ra,'<f8'),np.frombuffer(rb,'<f8')
            if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
                raise ValueError('Producer shape/nonfinite mismatch '+name)
            delta=float(np.max(abs(a-b)))
            scale=float(np.max(abs(a)))
            rows.append(dict(file=name, reference_sha256=hashlib.sha256(ra).hexdigest(),
                candidate_sha256=hashlib.sha256(rb).hexdigest(), decompressed_byte_equal=ra==rb,
                float64_count=len(a), max_absolute_error=delta, max_relative_global_error=delta/max(scale,1e-30),
                passed=delta<=1e-14+1e-8*scale))
    return dict(schema='task1-new-producer-regression-v1',
        status='passed' if all(r['passed'] for r in rows) else 'failed',
        reference_basis=str(Path(reference).resolve()),candidate_basis=str(Path(candidate).resolve()),
        relative_global_norm_tolerance=1e-8, absolute_tolerance=1e-14,
        comparisons=rows, new_physical_designs_in_this_check=0,
        scope='Distinct exporter same four-square physical operator, all peak complex E/phi/density/source/loss arrays',
        independent_solver=False,mesh_convergence_validated=False)
