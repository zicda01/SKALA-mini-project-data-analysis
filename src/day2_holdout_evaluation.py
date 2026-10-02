"""Evaluate the frozen Linear Regression candidate on Batch 1 holdout once.

Run from project root: .venv/bin/python -m src.day2_holdout_evaluation
"""
from pathlib import Path
from src.day2_evaluation_common import (
    PROJECT_ROOT, FEATURES, CONFIG, development_cv_mape, save_evaluation_figures,
)
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from src.day2_linear_comparison import make_model, SOURCE

TABLES = PROJECT_ROOT / 'outputs/tables/day2/holdout_evaluation'


def fit_and_evaluate(frame):
    train = frame.loc[frame.partition.eq('development')].copy()
    test = frame.loc[frame.partition.eq('holdout')].copy()
    if len(train) != 29 or len(test) != 7:
        raise ValueError(f'Expected frozen development/holdout sizes 29/7, got {len(train)}/{len(test)}')
    if not train.batch.eq('batch1').all() or not test.batch.eq('batch1').all():
        raise ValueError('Only Batch 1 is permitted')
    if train.barcode_key.isin(test.barcode_key).any():
        raise ValueError('Physical cell overlap between development and holdout')
    if set(train.protocol_key) & set(test.protocol_key):
        raise ValueError('Protocol group overlap between development and holdout')
    if test.cycle_life.isna().any() or not np.isfinite(test[FEATURES].to_numpy()).all():
        raise ValueError('Holdout labels/features must be present and finite')
    model = make_model(CONFIG)
    model.fit(train[FEATURES], train.cycle_life)
    pred = model.predict(test[FEATURES])
    if not np.isfinite(pred).all():
        raise ValueError('Nonfinite prediction')
    out = test[['batch','cell_id','barcode_key','protocol_key','cycle_life','log10_deltaQ_var']].copy()
    out = out.rename(columns={'cycle_life':'actual_life'})
    out['predicted_life'] = pred
    out['error_cycles'] = out.predicted_life - out.actual_life
    out['absolute_error_cycles'] = out.error_cycles.abs()
    out['ape_pct'] = 100 * out.absolute_error_cycles / out.actual_life
    cv_mape = development_cv_mape(frame)
    metrics = {'model':'Linear Regression','feature':'log10_deltaQ_var','target':'untransformed cycle_life',
               'development_n':len(train),'holdout_n':len(test),
               'holdout_mape_pct':100*mean_absolute_percentage_error(out.actual_life,out.predicted_life),
               'holdout_mae_cycles':mean_absolute_error(out.actual_life,out.predicted_life),
               'holdout_rmse_cycles':float(np.sqrt(mean_squared_error(out.actual_life,out.predicted_life))),
               'nonpositive_prediction_n':int((pred<=0).sum()),
               'development_cv_mean_fold_mape_pct':cv_mape,
               'holdout_minus_cv_mape_pp':100*mean_absolute_percentage_error(out.actual_life,out.predicted_life)-cv_mape,
               'holdout_evaluated':True,'batch2_read_or_evaluated':False,'selection_revisited':False}
    return model, out, metrics



def save_figures(predictions):
    save_evaluation_figures(predictions,
        PROJECT_ROOT / 'outputs/figures/day2/holdout_evaluation',
        'Batch 1 hold-out: frozen Linear Regression', '01_holdout_predictions.png')


def main():
    frame=pd.read_parquet(SOURCE)
    model,pred,metrics=fit_and_evaluate(frame)
    TABLES.mkdir(parents=True,exist_ok=True)
    save_figures(pred)
    pred.to_csv(TABLES/'holdout_predictions.csv',index=False)
    scaler=model.named_steps['scale']; reg=model.named_steps['regression']
    coeff=pd.DataFrame([{'feature':FEATURES[0],'train_mean':float(scaler.mean_[0]),'train_scale':float(scaler.scale_[0]),
                         'coefficient_scaled_input':float(reg.coef_[0]),
                         'coefficient_original_input':float(reg.coef_[0]/scaler.scale_[0]),
                         'intercept_scaled_input':float(reg.intercept_),
                         'intercept_original_input':float(reg.intercept_-reg.coef_[0]*scaler.mean_[0]/scaler.scale_[0])}])
    coeff.to_csv(TABLES/'fitted_model_parameters.csv',index=False)
    meta={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'candidate_selection':'outputs/tables/day2/boosting_comparison/candidate_selection.json',
          'configuration':CONFIG,'features':FEATURES,'metrics':metrics,'development_cv_folds':5,
          'holdout_used_for_selection':False,'prediction_clipping':False}
    (TABLES/'experiment_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))
    print(pred[['cell_id','actual_life','predicted_life','error_cycles','ape_pct']].to_string(index=False))

if __name__=='__main__': main()
