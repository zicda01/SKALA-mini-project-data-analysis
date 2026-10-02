"""Sensitivity calculations must use actual cycle coordinates and valid pairs."""
import unittest
import numpy as np
import pandas as pd
from src.quality_eda import qd_features, correlation, temperature_review

class QualityEDATests(unittest.TestCase):
    def test_slope_uses_cycle_numbers_across_missing_observation(self):
        frame=pd.DataFrame({'cell_id':[0]*6,'cycle':[10,11,12,20,21,22],
                            'QD_analysis':[1.0,1.002,np.nan,1.02,1.022,1.024]})
        original=frame.copy(deep=True)
        result=qd_features(frame).iloc[0]
        self.assertAlmostEqual(result.QD_slope,.002)
        self.assertEqual(result.n_QD,5)
        pd.testing.assert_frame_equal(frame,original)

    def test_pairwise_correlation_and_review_not_blanket_exclusion(self):
        frame=pd.DataFrame({'x':[1,2,3,4,np.inf], 'y':[1,np.nan,3,4,5]})
        n,r=correlation(frame,'x','y');self.assertEqual(n,3);self.assertAlmostEqual(r,1.)
        n,r=correlation(frame.iloc[:2],'x','y');self.assertEqual(n,1);self.assertTrue(np.isnan(r))
        t=pd.DataFrame({'mean_Tmax':[35,400,20,np.nan], 'mean_Tmin':[30,-270,25,np.nan]})
        self.assertEqual(temperature_review(t).tolist(),[False,True,True,False])

if __name__=='__main__':unittest.main()
