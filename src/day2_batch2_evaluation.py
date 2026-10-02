"""Final Batch 2 evaluation using frozen DAY2 candidate; run from project root."""
from pathlib import Path
from src.day2_evaluation_common import (
    PROJECT_ROOT, FEATURES, CONFIG, development_cv_mape, save_evaluation_figures,
)
import hashlib, json
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from src.day2_linear_comparison import make_model
from src.day2_dataset import TARGET
from src.day2_holdout_evaluation import fit_and_evaluate

TRAIN = PROJECT_ROOT / 'data/processed/day2/train_batch1.parquet'
TEST = PROJECT_ROOT / 'data/processed/day2/test_batch2.parquet'
TABLES = PROJECT_ROOT / 'outputs/tables/day2/batch2_evaluation'


def evaluate_batch2(train_frame, test_frame):
    train=train_frame.loc[train_frame.partition.isin(['development','holdout'])].copy()
    test=test_frame.loc[test_frame.partition.eq('test_batch2')].copy()
    if len(train)!=36 or len(test)!=39: raise ValueError(f'Expected Batch 1/2 sizes 36/39, got {len(train)}/{len(test)}')
    if set(train.batch)!={'batch1'} or set(test.batch)!={'batch2'}: raise ValueError('Unexpected batch in evaluation')
    if train.barcode_key.isin(test.barcode_key).any(): raise ValueError('Physical cell overlap across batches')
    if train[TARGET].isna().any() or test[TARGET].isna().any(): raise ValueError('Missing target label')
    if not np.isfinite(train[FEATURES+ [TARGET]].to_numpy()).all() or not np.isfinite(test[FEATURES].to_numpy()).all():
        raise ValueError('Nonfinite input or label')
    model=make_model(CONFIG)
    model.fit(train[FEATURES],train[TARGET])
    pred=model.predict(test[FEATURES])
    if not np.isfinite(pred).all(): raise ValueError('Nonfinite predictions')
    out=test[['batch','cell_id','barcode_key','protocol_key',TARGET,*FEATURES]].copy()
    out=out.rename(columns={TARGET:'actual_life'})
    out['predicted_life']=pred
    out['error_cycles']=out.predicted_life-out.actual_life
    out['absolute_error_cycles']=out.error_cycles.abs()
    out['ape_pct']=100*out.absolute_error_cycles/out.actual_life
    mape=100*mean_absolute_percentage_error(out.actual_life,out.predicted_life)
    _, _, holdout_metrics = fit_and_evaluate(train_frame)
    holdout_mape = holdout_metrics['holdout_mape_pct']
    cv_mape = holdout_metrics['development_cv_mean_fold_mape_pct']
    metrics={'model':'Linear Regression','feature':'log10_deltaQ_var','target':'untransformed cycle_life',
      'train_batch':'batch1','train_n':len(train),'test_batch':'batch2','test_n':len(test),
      'test_mape_pct':mape,'test_mae_cycles':mean_absolute_error(out.actual_life,out.predicted_life),
      'test_rmse_cycles':float(np.sqrt(mean_squared_error(out.actual_life,out.predicted_life))),
      'nonpositive_prediction_n':int((pred<=0).sum()),'target_mape_pct':9.1,
      'test_minus_target_mape_pp':mape-9.1,'holdout_mape_pct':holdout_mape,
      'development_cv_mean_fold_mape_pct':cv_mape,
      'test_minus_holdout_mape_pp':mape-holdout_mape,
      'test_minus_development_cv_mape_pp':mape-cv_mape,
      'candidate_reselected_after_holdout':False,'batch2_used_for_tuning':False,'prediction_clipping':False}
    return model,out,metrics



def save_figures(predictions):
    save_evaluation_figures(predictions,
        PROJECT_ROOT / 'outputs/figures/day2/batch2_evaluation',
        'Batch 2: frozen Linear Regression',
        '01_actual_vs_predicted.png', '02_cell_errors.png')


def main():
    train=pd.read_parquet(TRAIN); test=pd.read_parquet(TEST)
    model,pred,metrics=evaluate_batch2(train,test)
    TABLES.mkdir(parents=True,exist_ok=True)
    save_figures(pred)
    pred.to_csv(TABLES/'batch2_predictions.csv',index=False)
    scaler=model.named_steps['scale']; reg=model.named_steps['regression']
    params={'train_feature_mean':float(scaler.mean_[0]),'train_feature_scale':float(scaler.scale_[0]),
      'coefficient_scaled_input':float(reg.coef_[0]),'coefficient_original_input':float(reg.coef_[0]/scaler.scale_[0]),
      'intercept_scaled_input':float(reg.intercept_),'intercept_original_input':float(reg.intercept_-reg.coef_[0]*scaler.mean_[0]/scaler.scale_[0])}
    (TABLES/'fitted_model_parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    meta={'train_path':str(TRAIN),'train_sha256':hashlib.sha256(TRAIN.read_bytes()).hexdigest(),
      'test_path':str(TEST),'test_sha256':hashlib.sha256(TEST.read_bytes()).hexdigest(),
      'frozen_candidate':'outputs/tables/day2/boosting_comparison/candidate_selection.json',
      'configuration':CONFIG,'features':FEATURES,'metrics':metrics,'development_cv_fold_mape_pct':metrics['development_cv_mean_fold_mape_pct'],
      'holdout_metrics_path':'outputs/tables/day2/holdout_evaluation/experiment_metadata.json',
      'test_used_for_tuning':False}
    (TABLES/'experiment_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))
    print(pred.sort_values('ape_pct',ascending=False)[['cell_id','actual_life','predicted_life','error_cycles','ape_pct']].head(8).to_string(index=False))

if __name__=='__main__':main()
