"""Regression coverage for dynamic metrics, notebook paths and generated artifacts."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src import day2_batch2_evaluation as batch2
from src import day2_holdout_evaluation as holdout
from src import day2_model_diagnostics as diagnostics
from src.day2_evaluation_common import PROJECT_ROOT, development_cv_mape, save_evaluation_figures


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        n = 36
        self.train = pd.DataFrame({
            'batch': ['batch1'] * n, 'cell_id': range(n),
            'barcode_key': [f'b1-{i}' for i in range(n)],
            'protocol_key': [f'p{i % 5}' if i < 29 else 'reserved' for i in range(n)],
            'partition': ['development'] * 29 + ['holdout'] * 7,
            'cv_valid_fold': [i % 5 + 1 for i in range(29)] + [np.nan] * 7,
            'log10_deltaQ_var': np.linspace(-5, -3, n),
            'QD_slope_masked': np.linspace(-.0002, -.0001, n),
            'cycle_life': 1500 - np.arange(n) * 20 + np.sin(np.arange(n)) * 35,
        })
        self.test = self.train.iloc[:1].copy().loc[self.train.index[:1].repeat(39)].reset_index(drop=True)
        self.test['batch'] = 'batch2'
        self.test['cell_id'] = range(39)
        self.test['barcode_key'] = [f'b2-{i}' for i in range(39)]
        self.test['partition'] = 'test_batch2'
        self.test['cycle_life'] = np.linspace(400, 900, 39)

    def test_pipeline_and_gaps_use_current_data(self):
        model, _, h = holdout.fit_and_evaluate(self.train)
        self.assertIsInstance(model, Pipeline)
        dev = self.train.loc[self.train.partition.eq('development')]
        self.assertAlmostEqual(model.named_steps['scale'].mean_[0], dev.log10_deltaQ_var.mean())
        self.assertAlmostEqual(h['development_cv_mean_fold_mape_pct'], development_cv_mape(self.train))
        _, _, b = batch2.evaluate_batch2(self.train, self.test)
        self.assertAlmostEqual(b['holdout_mape_pct'], h['holdout_mape_pct'])
        self.assertAlmostEqual(b['test_minus_holdout_mape_pp'], b['test_mape_pct'] - h['holdout_mape_pct'])
        changed = self.train.copy()
        changed.loc[0, 'cycle_life'] *= 2
        _, _, c = holdout.fit_and_evaluate(changed)
        self.assertNotAlmostEqual(h['development_cv_mean_fold_mape_pct'], c['development_cv_mean_fold_mape_pct'])
        # Reserved targets must not affect development CV or the fitted holdout model.
        changed = self.train.copy()
        changed.loc[changed.partition.eq('holdout'), 'cycle_life'] *= 2
        changed_model, _, c = holdout.fit_and_evaluate(changed)
        self.assertEqual(h['development_cv_mean_fold_mape_pct'], c['development_cv_mean_fold_mape_pct'])
        np.testing.assert_allclose(model.predict(dev[holdout.FEATURES]), changed_model.predict(dev[holdout.FEATURES]))

    def test_evaluation_rejects_cell_or_protocol_leakage(self):
        bad = self.train.copy()
        bad.loc[29, 'protocol_key'] = bad.loc[0, 'protocol_key']
        with self.assertRaisesRegex(ValueError, 'Protocol group overlap'):
            holdout.fit_and_evaluate(bad)
        bad = self.test.copy()
        bad.loc[0, 'barcode_key'] = self.train.loc[0, 'barcode_key']
        with self.assertRaisesRegex(ValueError, 'Physical cell overlap'):
            batch2.evaluate_batch2(self.train, bad)

    def test_all_three_evaluation_plots_are_created(self):
        _, hp, _ = holdout.fit_and_evaluate(self.train)
        _, tp, _ = batch2.evaluate_batch2(self.train, self.test)
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            save_evaluation_figures(hp, d, 'Holdout', 'holdout.png')
            save_evaluation_figures(tp, d, 'Batch2', 'prediction.png', 'errors.png')
            for name in ['holdout.png', 'prediction.png', 'errors.png']:
                with Image.open(Path(d) / name) as im:
                    im.verify()

    def test_diagnostics_resolve_inputs_from_notebook_directory(self):
        cwd = Path.cwd()
        frames = [self.train, self.test]
        _, hp, _ = holdout.fit_and_evaluate(self.train)
        _, tp, _ = batch2.evaluate_batch2(self.train, self.test)
        dp = hp.copy()
        dp['config_id'] = 'linear_regression'
        with patch.object(diagnostics.pd, 'read_parquet', side_effect=frames) as pq, patch.object(diagnostics.pd, 'read_csv', side_effect=[dp, hp, tp]) as csv:
            try:
                os.chdir(PROJECT_ROOT / 'notebooks')
                result = diagnostics.load_predictions()
            finally:
                os.chdir(cwd)
            self.assertEqual(len(result), 53)
            for call in [*pq.call_args_list, *csv.call_args_list]:
                self.assertTrue(Path(call.args[0]).is_absolute())

    def test_diagnostics_writes_parseable_json(self):
        _, tp, _ = batch2.evaluate_batch2(self.train, self.test)
        tp['evaluation_set'] = 'Batch 2 test'
        tp['signed_error_cycles'] = tp.error_cycles
        with tempfile.TemporaryDirectory() as d, patch.object(diagnostics, 'OUT', Path(d)), patch.object(diagnostics, 'load_predictions', return_value=tp), patch.object(diagnostics.pd, 'read_parquet', return_value=self.train), patch.object(diagnostics, 'save_figures'), contextlib.redirect_stdout(io.StringIO()):
            diagnostics.main()
            meta = json.loads((Path(d) / 'diagnostic_metadata.json').read_text())
            self.assertFalse(meta['model_changed'])


if __name__ == '__main__':
    unittest.main()
