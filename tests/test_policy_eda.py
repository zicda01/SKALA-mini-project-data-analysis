"""Guard detailed-cycle alignment and avoid correlations from tiny groups."""
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.policy_eda import pair_stats,validate_detail,display_with_gap_breaks

class PolicyEDATests(unittest.TestCase):
    def test_small_groups_and_log_scale(self):
        f=pd.DataFrame({'deltaQ_var':10.**np.arange(-5.,0.),'cycle_life':np.arange(5.)+500})
        self.assertEqual(pair_stats(f.iloc[:4])['status'],'insufficient_or_constant')
        s=pair_stats(f);self.assertEqual(s['n'],5);self.assertAlmostEqual(s['pearson_logvar'],1.)
        f.loc[4,'cycle_life']=np.nan
        self.assertEqual(pair_stats(f)['n'],4)

    def test_display_does_not_connect_large_time_gap(self):
        t=np.array([0.,1.,2.,100.,101.]);v=np.array([1.,2.,3.,4.,5.])
        tx,values,gaps=display_with_gap_breaks(t,v)
        self.assertEqual(gaps.tolist(),[3]);self.assertTrue(np.isnan(tx[3]))
        np.testing.assert_array_equal(values[~np.isnan(values)],v)
        np.testing.assert_array_equal(t,[0.,1.,2.,100.,101.])

    def test_detail_content_and_time_mapping(self):
        f=pd.DataFrame({'cycle':[9,10], 'QD':[1.,1.1], 'QC':[1.,1.2]})
        q=SimpleNamespace(cycle_lengths_match_summary=True)
        d={'t':np.array([0.,1.,2.]),'I':np.array([1.,0.,-1.]),'V':np.array([3.,3.5,2.]),
           'Qc':np.array([0.,1.2,1.2]),'Qd':np.array([0.,0.,1.1])}
        self.assertEqual(validate_detail(f,q,d,10),1)
        with self.assertRaisesRegex(ValueError,'Qd maximum'):validate_detail(f,q,d,9)
        bad={**d,'t':np.array([0.,2.,1.])}
        with self.assertRaisesRegex(ValueError,'time decreases'):validate_detail(f,q,bad,10)
        bad={**d,'I':np.array([1.,0.])}
        with self.assertRaisesRegex(ValueError,'lengths'):validate_detail(f,q,bad,10)

if __name__=='__main__':unittest.main()
