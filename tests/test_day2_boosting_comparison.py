"""Verify the planned tree constraints and model comparison use reserved-safe CV."""
import unittest
import numpy as np
import pandas as pd
from src.day2_boosting_comparison import run_comparison, configurations, paired_predictions
from src.day2_linear_comparison import make_model


class BoostingTests(unittest.TestCase):
    def setUp(self):
        x=np.linspace(-5,-3,25)
        self.dev=pd.DataFrame({'batch':['batch1']*25,'cell_id':range(25),
            'barcode_key':[f'cell-{i}' for i in range(25)],'protocol_key':[f'protocol-{i//5}' for i in range(25)],
            'partition':['development']*25,'cv_valid_fold':np.repeat(range(1,6),5),
            'log10_deltaQ_var':x,'QD_slope_masked':np.linspace(-.001,.001,25),
            'cycle_life':900-100*(x+4)+10*np.sin(np.arange(25))})

    def test_planned_constraints_and_depth_limit(self):
        summary,scores,pred,coefs,scales,trees=run_comparison(self.dev)
        self.assertEqual(len(summary),6);self.assertEqual(len(scores),30)
        self.assertEqual(len(pred),6*25)
        self.assertEqual(set(coefs.model),{'ols','ridge'})
        self.assertGreater(len(trees),0)
        self.assertTrue(trees.min_observed_leaf_samples.ge(10).all())
        self.assertTrue(trees.actual_depth.le(1).all())  # train=20 cannot make 3 leaves of >=10
        self.assertFalse(pred.duplicated(['config_id','barcode_key']).any())
        for n in [50,100]:
            a=pred.loc[pred.config_id.eq(f'boosting_d1_n{n}'),'predicted_life']
            b=pred.loc[pred.config_id.eq(f'boosting_d2_n{n}'),'predicted_life']
            np.testing.assert_allclose(a,b)
        paired=paired_predictions(pred)
        self.assertEqual(len(paired),5*25)
        np.testing.assert_allclose(paired.alternative_minus_linear_ape_pp,paired.ape_pct_alternative-paired.ape_pct_linear)

    def test_boosting_parameters_are_fixed_and_unknown_models_fail(self):
        cfg=next(c for c in configurations() if c['model']=='gradient_boosting')
        reg=make_model(cfg).named_steps['regression']
        self.assertEqual(reg.min_samples_leaf,10)
        self.assertEqual(reg.learning_rate,.05)
        self.assertEqual(reg.random_state,42)
        self.assertEqual(reg.n_estimators,50)
        bad=dict(cfg,model='typo')
        with self.assertRaisesRegex(ValueError,'Unknown model'):make_model(bad)


if __name__=='__main__':unittest.main()
