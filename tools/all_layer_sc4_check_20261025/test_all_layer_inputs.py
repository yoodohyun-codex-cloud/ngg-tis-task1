"""Pure source/input contract checks; parent chooses when to execute."""
import unittest
import all_layer_inputs as i

class InputContracts(unittest.TestCase):
    def test_material_rows_are_complete_and_explicitly_assumed(self):
        table=i.material_table();self.assertEqual(len(table['rows']),16)
        for f in i.FREQUENCIES:
            self.assertEqual({r['layer']for r in table['rows']if r['frequency_Hz']==f},{'sc','dermis','fat','muscle'})
        self.assertTrue(all(r['source_DOI']is None and r['temperature_C']is None for r in table['rows']))
        self.assertEqual({r['layer']for r in table['rows']if r['changed']},set())
    def test_sigma_and_other_permittivities_are_not_changed(self):
        for row in i.material_table()['rows']:
            self.assertEqual(row['old_sigma_S_m'],row['proposed_sigma_S_m'])
            self.assertEqual(row['old_epsilon_r'],row['proposed_epsilon_r'])
    def test_sc_ratio_crosses_balance_without_omitting_displacement(self):
        row=next(r for r in i.material_table()['rows']if r['frequency_Hz']==3000 and r['layer']=='sc')
        self.assertAlmostEqual(row['imag_to_real_ratio'],.91794,places=4)
        self.assertGreater(row['gamma_imag_S_m'],0.)
    def test_duplicate_config_properties_rejected(self):
        with self.assertRaises(ValueError):i.properties(b'x=1\nx=2\n')
    def test_changed_source_bytes_rejected_without_running_solver(self):
        with self.assertRaises(ValueError):i.derive_config(b'sc.epsilon_r=110000\n',b'not-the-original-mask')

if __name__=='__main__':unittest.main()
