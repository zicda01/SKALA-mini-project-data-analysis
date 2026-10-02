"""Guard retrospective split fits and prevent gap filling/false linear knees."""
import unittest
import numpy as np
from src.window_knee_eda import fit_knee,longest_finite_segment,smooth_without_gap_fill,rolling_slope,curve_review_flags

class WindowKneeTests(unittest.TestCase):
    def test_curve_review_preserves_values_and_distinguishes_summary(self):
        q=np.array([-.001,.4,1.05]);original=q.copy()
        self.assertFalse(curve_review_flags(q,1.1))
        self.assertTrue(curve_review_flags(np.array([-84.,.4,306.]),.93))
        np.testing.assert_array_equal(q,original)

    def test_known_continuous_split_and_linear_non_knee(self):
        x=np.arange(0.,301.)
        y=1.1-2e-5*x-4e-4*np.maximum(0,x-150)
        result=fit_knee(x,y,min_span=30)
        self.assertEqual(result['status'],'candidate_passed_heuristic')
        self.assertAlmostEqual(result['candidate_cycle'],150.)
        self.assertAlmostEqual(result['pre_slope'],-2e-5,places=9)
        self.assertAlmostEqual(result['post_slope'],-4.2e-4,places=9)
        result=fit_knee(x,1.1-2e-5*x,min_span=30)
        self.assertEqual(result['status'],'best_split_unconfirmed')
        self.assertEqual(result['relative_sse_improvement'],0.)

    def test_gaps_are_not_joined_smoothed_or_used_by_local_slope(self):
        x=np.array([0.,1.,2.,3.,4.,5.,6.]);y=np.array([1.,2.,np.nan,4.,5.,6.,7.])
        xx,yy=longest_finite_segment(x,y)
        np.testing.assert_array_equal(xx,[3.,4.,5.,6.])
        smoothed=smooth_without_gap_fill(y,3)
        self.assertTrue(np.isnan(smoothed[1:4]).all())
        slope=rolling_slope(x,y,3)
        self.assertTrue(np.isnan(slope[1:4]).all());self.assertAlmostEqual(slope[4],1.)
        xx,yy=longest_finite_segment([0,1,4,5,6],[1,2,3,4,5])
        np.testing.assert_array_equal(xx,[4.,5.,6.])
        self.assertEqual(fit_knee(xx,yy)['status'],'insufficient_record')

if __name__=='__main__':unittest.main()
