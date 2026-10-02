"""Meaningful processing invariants with deliberate edge cases."""
import unittest
import numpy as np
import pandas as pd
from src.preprocess import QualityConfig, prepare_summary, cell_diagnostics, representative_cells


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({'batch': ['b'] * 5, 'cell_id': [0] * 5,
                                'cycle': [1., 2., 3., 4., 5.], 'cycle_life': [4.] * 5,
                                'QD': [0., 1.1, 2., .8, np.nan], 'IR': [0., .02, .02, .02, .02],
                                'QC': [0., 1., 1., 1., 1.], 'Tavg': [0., 30., 30., 30., 30.],
                                'Tmax': [0., 35., 35., 35., 35.], 'Tmin': [0., 25., 25., 25., 25.],
                                'chargetime': [0., 10., 10., 10., 10.]})

    def test_preserves_raw_and_low_capacity_and_post_life(self):
        original = self.raw.copy(deep=True)
        p = prepare_summary(self.raw)
        pd.testing.assert_frame_equal(self.raw, original)
        pd.testing.assert_frame_equal(p[original.columns], original)
        self.assertEqual(len(p), 5)
        self.assertTrue(np.isnan(p.QD_analysis.iloc[0]))
        self.assertEqual(p.QD_analysis.iloc[2], 2.)  # heuristic flag only
        self.assertEqual(p.QD_analysis.iloc[3], .8)  # real low capacity retained
        self.assertTrue(p.flag_after_life.iloc[4])
        self.assertTrue(np.isnan(p.IR_analysis.iloc[0]))
        self.assertEqual(p.Tavg.iloc[0], 0.)  # no blanket zero replacement
        c = pd.DataFrame({'batch': ['b'], 'cell_id': [0], 'cycle_life': [4.]})
        d = cell_diagnostics(c, p)
        self.assertEqual(d.first_observed_cycle_le_eol.iloc[0], 4.)
        self.assertEqual(d.crossing_minus_life.iloc[0], 0.)

    def test_opt_in_mask_and_invalid_cycle(self):
        p = prepare_summary(self.raw, QualityConfig(mask_high_qd=True))
        self.assertTrue(np.isnan(p.QD_analysis.iloc[2]))
        self.raw.loc[2, 'cycle'] = 2.
        p = prepare_summary(self.raw)
        self.assertTrue(p.QD_analysis.iloc[1:3].isna().all())

    def test_absent_groups_and_boundary_labels(self):
        c = pd.DataFrame({'batch': ['b'] * 4, 'cell_id': range(4),
                          'cycle_life': [500., 1000., 1100., np.nan]})
        r = representative_cells(c)
        self.assertEqual(set(r.life_group), {'medium (500–1000)', 'long (>1000)'})
        self.assertNotIn(3, r.cell_id.tolist())


if __name__ == '__main__':
    unittest.main()
