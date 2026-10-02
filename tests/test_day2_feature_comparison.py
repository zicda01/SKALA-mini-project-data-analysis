"""Verify descriptor replacement is real and masking comparisons use the same cells."""
import unittest
import numpy as np
import pandas as pd
from src.day2_linear_comparison import evaluate
from src.day2_feature_comparison import FEATURE_SETS, configurations, paired_fold_deltas


class FeatureComparisonTests(unittest.TestCase):
    def setUp(self):
        self.dev=pd.DataFrame({'batch':['batch1']*10,'cell_id':range(10),
            'barcode_key':[f'cell-{i}' for i in range(10)],'protocol_key':[f'protocol-{i//2}' for i in range(10)],
            'partition':['development']*10,'cv_valid_fold':np.repeat(range(1,6),2),
            'log10_deltaQ_var':np.linspace(-5,-3,10),
            'deltaQ_min':-np.linspace(.02,.07,10)**2,
            'QD_slope_masked':np.linspace(-.0002,.0001,10)**2,
            'QD_slope_retained':np.linspace(-.0002,.0001,10)**2,
            'cycle_life':[1200.,1100.,1000.,950.,850.,800.,700.,600.,550.,500.]})

    def test_minimum_model_really_uses_minimum_not_variance(self):
        cfg=[x for x in configurations() if x['config_id']=='ols_minimum_only']
        original=self.dev.copy(deep=True)
        _,scores,pred,coefs,_=evaluate(self.dev,cfg,FEATURE_SETS)
        self.assertEqual(set(coefs.feature),{'deltaQ_min'})
        train=self.dev[self.dev.cv_valid_fold.ne(1)]
        valid=self.dev[self.dev.cv_valid_fold.eq(1)]
        slope,intercept=np.polyfit(train.deltaQ_min,train.cycle_life,1)
        np.testing.assert_allclose(pred.loc[pred.fold.eq(1),'predicted_life'],valid.deltaQ_min*slope+intercept)
        pd.testing.assert_frame_equal(self.dev,original)

    def test_identical_slope_values_give_identical_masking_predictions(self):
        _,scores,pred,_,_=evaluate(self.dev,list(configurations()),FEATURE_SETS)
        delta=paired_fold_deltas(scores)
        np.testing.assert_allclose(delta.loc[delta.comparison.ne('descriptor_replacement'),'alternative_minus_base_pp'],0.,atol=1e-12)
        self.assertEqual(len(delta),45)
        self.assertFalse(pred.duplicated(['config_id','barcode_key']).any())

    def test_invalid_descriptor_and_target_feature_are_rejected(self):
        bad=self.dev.copy();bad.loc[0,'deltaQ_min']=np.nan
        cfg=[x for x in configurations() if x['config_id']=='ols_minimum_only']
        with self.assertRaisesRegex(ValueError,'Invalid'):evaluate(bad,cfg,FEATURE_SETS)
        with self.assertRaisesRegex(ValueError,'target-containing'):
            evaluate(self.dev,cfg,{'minimum_only':['cycle_life']})


if __name__=='__main__':unittest.main()
