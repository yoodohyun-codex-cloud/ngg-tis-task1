"""UNEXECUTED test source for a later separately authorized owner invocation.

No actual datasets, caches, geometry files, or prior numerical results are read.
NumPy is imported only in SyntheticTests.setUpClass. The injected dense solver
is for tiny synthetic algebra, and does not test large-system GMRES convergence.
The independent reference retains every metal potential, two branch currents,
and a Lagrange-multiplier gauge instead of reusing the reduced circuit rows.
"""
import math
import unittest

import floating_cem as model


class PureTests(unittest.TestCase):
    def test_contact_rows_and_uniform_gauge_shift(self):
        phi = [0.2 + 0.1j, -0.3 + 0.2j, 0.1 - 0.4j, 0.4 + 0.3j]
        metal = [0.6 + 0.2j, -0.1 + 0.1j, 0.3 - 0.1j, 0j]
        tissue = [0j] * 4
        pads = cells = list(range(4))
        areas = [1.0, 1.2, 0.8, 1.1]
        z = 4.0 - 1.5j
        surface, rows, q = model.contact_equations(tissue, phi, metal, pads, cells, areas, z)
        self.assertAlmostEqual(rows[0], q[0] + q[1])
        self.assertAlmostEqual(rows[1], (metal[0] - metal[1]) / 50 - q[0])
        self.assertAlmostEqual(rows[2], (metal[2] - metal[3]) / 50 - q[2])
        shift = -0.8 + 1.3j
        shifted = model.contact_equations(tissue, [v + shift for v in phi],
            [v + shift for v in metal], pads, cells, areas, z)
        for expected, actual in zip((surface, rows, q), shifted):
            for a, b in zip(expected, actual):
                self.assertAlmostEqual(a, b)

    def test_signed_capacitive_contact_power_and_total_resistance(self):
        powers = model.signed_powers([0j] * 4, [1 + 0j, 0j, 0j, 0j],
            [0j] * 4, list(range(4)), list(range(4)), [1.0] * 4,
            2.0 - 1.0j, [0.5, 0j])
        self.assertAlmostEqual(powers['contact'], 0.2 - 0.1j)
        self.assertAlmostEqual(powers['current'][0], 0.5 / 50)
        self.assertAlmostEqual(powers['resistor'], 0.5 * 50 * (0.5 / 50) ** 2)
        with self.assertRaises(ValueError):
            model.contact_equations([0j], [0j], [0j] * 4, [0], [0], [1], 1 + 0j, 0)


class SyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np = np

    def setUp(self):
        np = self.np
        self.n = 8
        self.weights = (0.018 + 0.007j, 0.033 + 0.011j, 0.025 + 0.004j)
        self.A, self.Q, self.Y = self.cube_graph(self.weights)
        self.pads = np.asarray([0, 0, 1, 1, 2, 2, 3, 3], dtype=int)
        self.cells = np.asarray([0, 1, 6, 7, 2, 3, 4, 5], dtype=int)
        self.areas = np.asarray([0.8, 1.1, 0.9, 1.3, 0.7, 1.2, 0.95, 1.05])
        self.zA = 12.0 - 3.0j

    def cube_graph(self, weights):
        """Connected graph; positive real edge weights; constant nullspace.

        This is PSD on all nodes and strictly positive on the mean-zero space.
        A strictly positive definite all-node tissue operator would add an
        unphysical ground reference and would invalidate the gauge test.
        Walsh eigenvectors/eigenvalues are analytic, so no eigensolver is used.
        """
        np = self.np
        A = np.zeros((8, 8), dtype=complex)
        for i in range(8):
            for bit, weight in enumerate(weights):
                j = i ^ (1 << bit)
                if i < j:
                    A[i, i] += weight
                    A[j, j] += weight
                    A[i, j] -= weight
                    A[j, i] -= weight
        Q = np.asarray([[(-1.0) ** ((i & k).bit_count()) / math.sqrt(8)
                         for k in range(8)] for i in range(8)])
        Y = np.asarray([2 * sum(weight for bit, weight in enumerate(weights)
                               if k & (1 << bit)) for k in range(8)])
        return A, Q, Y

    def profiles(self):
        np = self.np
        V = np.zeros((8, 2), dtype=complex)
        J = np.zeros((8, 2), dtype=complex)
        V[:, 0] = 1
        J[:, 0] = self.Y
        return dict(Y=self.Y, diagonal=np.diag(self.A), unitV=V, unitJ=J)

    @staticmethod
    def transform(np, Q, values, transpose=False):
        return (Q.T if transpose else Q) @ values

    @staticmethod
    def guard():
        return None

    def linear_operator(self, shape, matvec, dtype):
        class Operator:
            pass
        result = Operator()
        result.shape, result.matvec = shape, matvec
        return result

    def dense_matrix(self, operator):
        np = self.np
        eye = np.eye(operator.shape[1], dtype=complex)
        return np.column_stack([operator.matvec(eye[:, j]) for j in range(eye.shape[1])])

    def tiny_dense_gmres(self, A, rhs, M, callback, callback_type, **options):
        # Interface substitution tests production assembly/residual/power paths;
        # it intentionally makes no statement about iterative convergence.
        np = self.np
        self.assertEqual(callback_type, 'pr_norm')
        self.assertTrue(np.isfinite(M.matvec(rhs)).all())
        dense = self.dense_matrix(A)
        x = np.linalg.solve(dense, rhs)
        callback(float(np.linalg.norm(dense @ x - rhs)))
        return x, 0

    def solve_reduced(self, activepair, pads=None, areas=None):
        return model.solve(self.np, self.Q, self.profiles(),
            self.pads if pads is None else pads, self.cells,
            self.areas if areas is None else areas, self.zA, activepair,
            self.guard, None, transform=self.transform, gmres=self.tiny_dense_gmres,
            linear_operator=self.linear_operator, h_m=1.0)

    def full_mna(self, ideal, *, gauge='metal3', gauge_value=0j,
                 R=50.0, pads=None, areas=None, tissue=None):
        """Independent full passive nodal assembly plus branch-current MNA.

        K u - B I + c lambda=0; B.T u + R I=Vs; c.T u=gauge_value.
        Unlike the reduction, this reference enforces FOUR metal KCL equations.
        The fictitious gauge multiplier must vanish; it is not a ground current.
        """
        np = self.np
        n = self.n
        pads = self.pads if pads is None else pads
        areas = self.areas if areas is None else areas
        K = np.zeros((n + 4, n + 4), dtype=complex)
        K[:n, :n] = self.A if tissue is None else tissue
        for p, i, area in zip(pads, self.cells, areas):
            j, g = n + int(p), area / self.zA
            K[i, i] += g
            K[j, j] += g
            K[i, j] -= g
            K[j, i] -= g
        B = np.zeros((n + 4, 2), dtype=complex)
        B[n + 0, 0], B[n + 1, 0] = 1, -1
        B[n + 2, 1], B[n + 3, 1] = 1, -1
        c = np.zeros(n + 4, dtype=complex)
        if gauge == 'metal3':
            c[n + 3] = 1
        elif gauge == 'mean_all_nodes':
            c[:] = 1 / (n + 4)
        else:
            raise ValueError('Unknown synthetic gauge')
        full = np.zeros((n + 7, n + 7), dtype=complex)
        full[:n + 4, :n + 4] = K
        full[:n + 4, n + 4:n + 6] = -B
        full[n + 4:n + 6, :n + 4] = B.T
        full[n + 4:n + 6, n + 4:n + 6] = R * np.eye(2)
        full[:n + 4, -1] = c
        full[-1, :n + 4] = c
        rhs = np.r_[np.zeros(n + 4, dtype=complex), ideal, complex(gauge_value)]
        x = np.linalg.solve(full, rhs)
        return dict(phi=x[:n], metal=x[n:n + 4], current=x[n + 4:n + 6],
                    gauge_multiplier=x[-1], K=K, B=B)

    def assert_close(self, actual, expected):
        self.np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=2e-13)

    def test_analytic_graph_basis_has_constant_nullspace_and_passivity(self):
        np = self.np
        self.assert_close(self.Q.T @ self.Q, np.eye(8))
        self.assert_close(self.A, (self.Q * self.Y) @ self.Q.T)
        self.assert_close(self.A @ np.ones(8), np.zeros(8))
        self.assertTrue(bool(np.all(self.Y[1:].real > 0)))

    def test_both_basis_reduced_vs_independent_full_mna_power_and_inactive_port(self):
        np = self.np
        for active in (0, 1):
            with self.subTest(active=active):
                result = self.solve_reduced(active)
                ideal = np.zeros(2, dtype=complex)
                ideal[active] = 0.5
                full = self.full_mna(ideal)
                self.assert_close(result['phi_surface'], full['phi'])
                self.assert_close(result['metal'], full['metal'])
                self.assert_close(result['source_current'], full['current'])
                self.assertLess(abs(full['gauge_multiplier']), 1e-13)
                q = np.asarray([complex(v['real'], v['imaginary']) for v in
                    result['proof']['all_pad_outward_tissue_to_metal_current_peak_A']])
                self.assert_close([q[0] + q[1], q[2] + q[3], q.sum()], [0j] * 3)
                self.assert_close(-q[[0, 2]], result['source_current'])
                inactive = 1 - active
                p, m = model.PAIRS[inactive]
                self.assertGreater(abs(result['source_current'][inactive]), 1e-8)
                self.assert_close(result['metal'][p] - result['metal'][m],
                                  -50 * result['source_current'][inactive])
                self.assertTrue(result['proof']['passed'], result['proof'])
                powers = model.signed_powers(self.A @ result['phi_surface'],
                    result['phi_surface'], result['metal'], self.pads, self.cells,
                    self.areas, self.zA, ideal)
                self.assert_close(powers['source'], powers['tissue'] +
                                  powers['contact'] + powers['resistor'])
                for key in ('tissue', 'contact', 'resistor'):
                    self.assertGreaterEqual(complex(powers[key]).real, -1e-14)
                self.assertLess(powers['tissue'].imag, 0)
                self.assertLess(powers['contact'].imag, 0)
                wrong_R = self.full_mna(ideal, R=100.0)
                self.assertGreater(float(np.linalg.norm(full['current'] - wrong_R['current'])), 1e-6)

    def test_two_distinct_gauges_and_complex_uniform_shift(self):
        np = self.np
        base = self.full_mna(np.asarray([0.5, 0j]))
        shift = 0.37 - 0.22j
        shifted = self.full_mna(np.asarray([0.5, 0j]), gauge_value=shift)
        self.assert_close(shifted['phi'], base['phi'] + shift)
        self.assert_close(shifted['metal'], base['metal'] + shift)
        self.assert_close(shifted['current'], base['current'])
        mean = np.mean(np.r_[base['phi'], base['metal']])
        alternative = self.full_mna(np.asarray([0.5, 0j]),
            gauge='mean_all_nodes', gauge_value=shift)
        self.assert_close(alternative['phi'], base['phi'] + shift - mean)
        self.assert_close(alternative['metal'], base['metal'] + shift - mean)
        self.assert_close(alternative['current'], base['current'])
        base_powers = model.signed_powers(self.A @ base['phi'], base['phi'],
            base['metal'], self.pads, self.cells, self.areas, self.zA, [0.5, 0j])
        for result in (base, shifted, alternative):
            self.assertLess(abs(result['gauge_multiplier']), 1e-13)
            powers = model.signed_powers(self.A @ result['phi'], result['phi'],
                result['metal'], self.pads, self.cells, self.areas, self.zA, [0.5, 0j])
            for key in ('source', 'tissue', 'contact', 'resistor'):
                self.assert_close(powers[key], base_powers[key])

    def test_same_frequency_reciprocity_superposition_and_orientation(self):
        np = self.np
        results = [self.solve_reduced(k) for k in (0, 1)]
        Yport = np.column_stack([v['source_current'] / 0.5 for v in results])
        self.assert_close(Yport, Yport.T)  # transpose, never conjugate transpose
        ideal = np.asarray([0.35 + 0.12j, -0.18 + 0.22j])
        full = self.full_mna(ideal)
        self.assert_close(full['current'], Yport @ ideal)
        self.assert_close(full['phi'], sum(results[k]['phi_surface'] * ideal[k] / 0.5
                                          for k in (0, 1)))
        flipped = np.asarray([1 if p == 0 else 0 if p == 1 else p for p in self.pads])
        Yflip = np.column_stack([self.solve_reduced(k, pads=flipped)['source_current'] / 0.5
                                 for k in (0, 1)])
        D = np.diag([-1.0, 1.0])
        self.assert_close(Yflip, D @ Yport @ D)
        exchanged = np.asarray([{0: 2, 1: 3, 2: 0, 3: 1}[int(p)] for p in self.pads])
        Yexchange = np.column_stack([self.solve_reduced(k, pads=exchanged)['source_current'] / 0.5
                                     for k in (0, 1)])
        P = np.asarray([[0, 1], [1, 0]])
        self.assert_close(Yexchange, P @ Yport @ P)

    def test_equal_geometry_and_sources_have_equal_diagonal_port_response(self):
        np = self.np
        self.A, self.Q, self.Y = self.cube_graph((0.025 + 0.006j,) * 3)
        symmetric = np.ones(8)
        Yport = np.column_stack([self.solve_reduced(k, areas=symmetric)['source_current'] / 0.5
                                 for k in (0, 1)])
        self.assert_close(Yport[0, 0], Yport[1, 1])
        self.assert_close(Yport[0, 1], Yport[1, 0])

    def test_ground_leak_fault_is_detectable_and_constant_mode_is_rejected(self):
        np = self.np
        bad = self.A.copy()
        bad[0, 0] += 0.03
        system = model.reduced_system(np, lambda v: bad @ v, np.diag(bad),
            self.pads, self.cells, self.areas, self.zA, self.guard, None)
        op = self.linear_operator((11, 11), system['action'], complex)
        x = np.linalg.solve(self.dense_matrix(op), np.r_[np.zeros(8), 0, 0.5 / 50, 0])
        qpad = system['split'](x)[-1]
        # Pair-1 KCL is an independent gate, not a tautology of the three rows.
        self.assertGreater(abs(qpad[2] + qpad[3]), 1e-8)
        full = self.full_mna(np.asarray([0.5, 0j]), tissue=bad)
        self.assertGreater(abs(full['gauge_multiplier']), 1e-8)
        self.Y = self.Y.copy()
        self.Y[0] = 0.001
        with self.assertRaisesRegex(ValueError, 'Insulated constant mode'):
            self.solve_reduced(0)


if __name__ == '__main__':
    unittest.main()
