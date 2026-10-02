"""Verify CV train-only preprocessing, validation coverage, and reserved data rejection."""
import unittest
import numpy as np
import pandas as pd
from src.day2_linear_comparison import evaluate, validate_development


class LinearComparisonTests(unittest.TestCase):
    def setUp(self):
        self.dev=pd.DataFrame({'batch':['batch1']*10,'cell_id':range(10),
            'barcode_key':[f'cell-{i}' for i in range(10)],'protocol_key':[f'protocol-{i//2}' for i in range(10)],
            'partition':['development']*10,'cv_valid_fold':np.repeat(range(1,6),2),
            'log10_deltaQ_var':np.linspace(-5,-3,10),'QD_slope_masked':np.linspace(-.0002,.0001,10)**2,
            'cycle_life':[1200.,1100.,1000.,950.,850.,800.,700.,600.,550.,500.]})

    def test_reserved_partitions_are_rejected(self):
        for column,value in [('partition','holdout'),('batch','batch2')]:
            bad=self.dev.copy();bad.loc[0,column]=value
            with self.assertRaisesRegex(ValueError,'Only Batch 1 development'):validate_development(bad)

    def test_predictions_and_scalers_are_fold_local(self):
        summary,scores,predictions,coefficients,scales=evaluate(self.dev)
        self.assertEqual(len(summary),21);self.assertEqual(len(scores),105)
        self.assertFalse(predictions.duplicated(['config_id','barcode_key']).any())
        for row in scales.itertuples():
            train=self.dev.loc[self.dev.cv_valid_fold.ne(row.fold),row.feature]
            self.assertAlmostEqual(row.train_mean,train.mean())
            self.assertAlmostEqual(row.train_scale,train.std(ddof=0))
        for fold in range(1,6):
            baseline=predictions.loc[predictions.config_id.eq('median_raw') & predictions.fold.eq(fold)]
            expected=self.dev.loc[self.dev.cv_valid_fold.ne(fold),'cycle_life'].median()
            np.testing.assert_allclose(baseline.predicted_life,expected)
        for row in scores.itertuples():
            p=predictions.loc[predictions.config_id.eq(row.config_id) & predictions.fold.eq(row.fold)]
            self.assertAlmostEqual(row.mape_pct,p.ape_pct.mean())
            self.assertEqual(row.valid_n,len(p))
        self.assertTrue((summary.oof_n==len(self.dev)).all())


if __name__=='__main__':unittest.main()
