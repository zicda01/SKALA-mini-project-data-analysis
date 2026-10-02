"""Protect time-weighted pattern summaries from irregular sampling and gaps."""
import unittest
import numpy as np
from src.report_answer_support import pattern_metrics


class PatternSummaryTests(unittest.TestCase):
    def test_irregular_constant_signal_and_input_preservation(self):
        detail = {'t':np.array([0.,1.,3.,6.]), 'I':np.full(4,2.)}
        before = {key:value.copy() for key,value in detail.items()}
        result = pattern_metrics(detail)
        self.assertEqual(result['positive_duration_native'],6.)
        self.assertEqual(result['mean_positive_I_native'],2.)
        self.assertEqual(result['near_peak_time_share'],1.)
        self.assertEqual(result['late_minus_early_I_native'],0.)
        for key in detail:np.testing.assert_array_equal(before[key],detail[key])

    def test_half_duration_boundary_splits_an_interval(self):
        result = pattern_metrics({'t':np.arange(4,dtype=float),'I':np.array([1.,1.,3.,3.])})
        self.assertAlmostEqual(result['mean_positive_I_native'],2.)
        self.assertAlmostEqual(result['near_peak_time_share'],1/3)
        self.assertAlmostEqual(result['late_minus_early_I_native'],4/3)

    def test_gap_and_state_transitions_are_not_integrated(self):
        result = pattern_metrics({'t':np.array([0.,1.,2.,102.,103.]),'I':np.full(5,2.)})
        self.assertEqual(result['gap_count'],1)
        self.assertEqual(result['excluded_gap_duration_native'],100.)
        self.assertEqual(result['positive_duration_native'],3.)
        result = pattern_metrics({'t':np.arange(4,dtype=float),'I':np.array([-2.,-2.,0.,2.])})
        self.assertEqual(result['positive_duration_native'],0.)
        self.assertTrue(np.isnan(result['mean_positive_I_native']))
        self.assertTrue(np.isnan(result['late_minus_early_I_native']))


if __name__=='__main__':unittest.main()
