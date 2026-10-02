"""First development-CV comparison; holdout and test partitions are never fitted/evaluated.

Run: python -m src.day2_linear_comparison
"""
from pathlib import Path
from src.day2_evaluation_common import PROJECT_ROOT
import hashlib
import importlib.metadata
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from src.day2_dataset import F1, F2, TARGET

SOURCE = PROJECT_ROOT / 'data/processed/day2/train_batch1.parquet'
TABLES = PROJECT_ROOT / 'outputs/tables/day2/linear_comparison'
FIGURES = PROJECT_ROOT / 'outputs/figures/day2/linear_comparison'
ALPHAS = [.1, 1., 10., 100.]


def inverse_log10(y):
    return np.power(10., y)


def configurations():
    yield {'config_id':'median_raw','model':'median','feature_set':'F1','target':'raw','alpha':None}
    for features in ['F1','F2']:
        for target in ['raw','log10']:
            yield {'config_id':f'ols_{features}_{target}','model':'ols','feature_set':features,'target':target,'alpha':None}
            for alpha in ALPHAS:
                yield {'config_id':f'ridge_{features}_{target}_a{alpha:g}','model':'ridge','feature_set':features,'target':target,'alpha':alpha}


def make_model(config):
    if config['model']=='median':return DummyRegressor(strategy='median')
    if config['model']=='ols':
        regression=LinearRegression()
    elif config['model']=='ridge':
        regression=Ridge(alpha=config['alpha'])
    elif config['model']=='gradient_boosting':
        regression=GradientBoostingRegressor(
            max_depth=config['max_depth'], n_estimators=config['n_estimators'],
            min_samples_leaf=10, learning_rate=.05, random_state=42,
            loss='squared_error', subsample=1.0)
    else:
        raise ValueError(f"Unknown model: {config['model']}")
    pipeline=Pipeline([('scale',StandardScaler()),('regression',regression)])
    if config['target']=='log10':
        return TransformedTargetRegressor(regressor=pipeline,func=np.log10,inverse_func=inverse_log10)
    return pipeline


def validate_development(frame):
    if not frame.partition.eq('development').all() or not frame.batch.eq('batch1').all():
        raise ValueError('Only Batch 1 development rows may enter this comparison')
    if frame.barcode_key.duplicated().any() or frame.cv_valid_fold.isna().any():
        raise ValueError('Missing CV assignment or repeated physical cells')
    if set(frame.cv_valid_fold.astype(int))!={1,2,3,4,5}:
        raise ValueError('Expected saved five-fold assignments')
    if not np.isfinite(frame[F2+[TARGET]].to_numpy()).all() or not frame[TARGET].gt(0).all():
        raise ValueError('Invalid features or lifetime labels')
    for _,g in frame.groupby('protocol_key'):
        if g.cv_valid_fold.nunique()!=1:raise ValueError('Protocol spans validation folds')


def evaluate(frame, configs=None, feature_sets=None, fitted_observer=None):
    validate_development(frame)
    feature_sets = {'F1': F1, 'F2': F2} if feature_sets is None else feature_sets
    scores,predictions,coefficients,scale_rows=[],[],[],[]
    for config in configurations() if configs is None else configs:
        features=feature_sets[config['feature_set']]
        if not features or TARGET in features or not np.isfinite(frame[features].to_numpy()).all():
            raise ValueError('Invalid or target-containing feature set')
        for fold in range(1,6):
            train=frame.loc[frame.cv_valid_fold.ne(fold)]
            valid=frame.loc[frame.cv_valid_fold.eq(fold)]
            if set(train.protocol_key)&set(valid.protocol_key):raise ValueError('Protocol leakage')
            model=make_model(config)
            model.fit(train[features],train[TARGET])
            if fitted_observer is not None:
                fitted_observer(config,fold,model)
            pred=model.predict(valid[features])
            if not np.isfinite(pred).all():raise ValueError('Nonfinite predictions')
            scores.append({**config,'fold':fold,'train_n':len(train),'valid_n':len(valid),
                           'mape_pct':100*mean_absolute_percentage_error(valid[TARGET],pred),
                           'mae_cycles':mean_absolute_error(valid[TARGET],pred),
                           'rmse_cycles':float(np.sqrt(mean_squared_error(valid[TARGET],pred))),
                           'nonpositive_prediction_n':int((pred<=0).sum())})
            for row,value in zip(valid.itertuples(),pred):
                predictions.append({**config,'fold':fold,'batch':row.batch,'cell_id':row.cell_id,
                                    'barcode_key':row.barcode_key,'protocol_key':row.protocol_key,
                                    'actual_life':row.cycle_life,'predicted_life':float(value),
                                    'error_cycles':float(value-row.cycle_life),
                                    'absolute_error_cycles':float(abs(value-row.cycle_life)),
                                    'ape_pct':float(100*abs(value-row.cycle_life)/row.cycle_life)})
            if config['model']!='median':
                pipe=model.regressor_ if config['target']=='log10' else model
                scaler,reg=pipe.named_steps['scale'],pipe.named_steps['regression']
                for i,feature in enumerate(features):
                    scale_rows.append({**config,'fold':fold,'feature':feature,
                                       'train_mean':float(scaler.mean_[i]),'train_scale':float(scaler.scale_[i])})
                    if hasattr(reg,'coef_'):
                        original=np.asarray(reg.coef_)/scaler.scale_
                        original_intercept=float(reg.intercept_-np.dot(original,scaler.mean_))
                        coefficients.append({**config,'fold':fold,'feature':feature,'coefficient_scaled_input':float(reg.coef_[i]),
                                             'coefficient_original_input':float(original[i]),
                                             'intercept_scaled_input':float(reg.intercept_),
                                             'intercept_original_input':original_intercept})
    scores=pd.DataFrame(scores);predictions=pd.DataFrame(predictions)
    summaries=[]
    for config_id,g in scores.groupby('config_id',sort=False):
        p=predictions.loc[predictions.config_id.eq(config_id)]
        summaries.append({**{key:g.iloc[0][key] for key in ['config_id','model','feature_set','target','alpha']},
                          'mean_fold_mape_pct':g.mape_pct.mean(),'std_fold_mape_pct':g.mape_pct.std(ddof=1),
                          'worst_fold_mape_pct':g.mape_pct.max(),'mean_fold_mae_cycles':g.mae_cycles.mean(),
                          'mean_fold_rmse_cycles':g.rmse_cycles.mean(),'pooled_oof_mape_pct':p.ape_pct.mean(),
                          'oof_n':len(p),'nonpositive_prediction_n':int(g.nonpositive_prediction_n.sum())})
    summary=pd.DataFrame(summaries).sort_values(['mean_fold_mape_pct','config_id']).reset_index(drop=True)
    return summary,scores,predictions,pd.DataFrame(coefficients),pd.DataFrame(scale_rows)


def save_figures(summary,scores,predictions,coefficients):
    FIGURES.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(11,9))
    ax.barh(summary.config_id[::-1],summary.mean_fold_mape_pct[::-1],
            xerr=summary.std_fold_mape_pct[::-1],color='#497ba6',capsize=3)
    ax.set(xlabel='Mean validation-fold MAPE (%) ± sample SD',title='Development CV: fixed protocol groups, n=29')
    ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(FIGURES/'01_cv_comparison.png',dpi=140);plt.close(fig)
    median=summary.loc[summary.model.eq('median')].iloc[0]
    ols=summary.loc[summary.model.eq('ols')].iloc[0]
    ridge=summary.loc[summary.model.eq('ridge')].iloc[0]
    fig,axes=plt.subplots(1,3,figsize=(15,4.8))
    for ax,row in zip(axes,[median,ols,ridge]):
        p=predictions.loc[predictions.config_id.eq(row.config_id)]
        ax.scatter(p.actual_life,p.predicted_life,c=p.fold,cmap='viridis',vmin=1,vmax=5)
        low=min(p.actual_life.min(),p.predicted_life.min())-20;high=max(p.actual_life.max(),p.predicted_life.max())+20
        ax.plot([low,high],[low,high],'--',color='gray');ax.set(xlabel='Actual life (cycles)',ylabel='OOF predicted life (cycles)',
                title=f'{row.config_id}\nMean-fold MAPE {row.mean_fold_mape_pct:.2f}%')
        ax.grid(alpha=.2)
    fig.suptitle('Exploratory out-of-fold predictions; selected on these same folds')
    fig.tight_layout();fig.savefig(FIGURES/'02_oof_predictions.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for ax,target in zip(axes,['raw','log10']):
        for fs,feature,color in [('F1',F1[0],'#3676a0'),('F2',F1[0],'#d48235'),('F2',F2[1],'#63934a')]:
            g=coefficients.loc[coefficients.model.eq('ridge') & coefficients.target.eq(target)
                               & coefficients.feature_set.eq(fs) & coefficients.feature.eq(feature)]
            means=g.groupby('alpha').coefficient_scaled_input.agg(['mean','std'])
            ax.errorbar(means.index,means['mean'],yerr=means['std'],marker='o',label=f'{fs}: {feature}',color=color,capsize=3)
        ax.set_xscale('log');ax.axhline(0,color='gray',lw=1)
        ax.set(xlabel='Ridge alpha',ylabel=f'Coefficient: {"cycles" if target=="raw" else "log10 life"} per input SD',title=f'Target: {target}')
        ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Regularization changes coefficients (mean ± SD across folds)')
    fig.tight_layout();fig.savefig(FIGURES/'03_ridge_coefficients.png',dpi=140);plt.close(fig)


def main():
    train=pd.read_parquet(SOURCE)
    dev=train.loc[train.partition.eq('development')].sort_values(['batch','cell_id']).reset_index(drop=True)
    summary,scores,predictions,coefficients,scales=evaluate(dev)
    TABLES.mkdir(parents=True,exist_ok=True)
    for name,frame in [('summary',summary),('fold_scores',scores),('oof_predictions',predictions),
                       ('coefficients',coefficients),('scaler_statistics',scales)]:
        frame.to_csv(TABLES/f'{name}.csv',index=False)
    save_figures(summary,scores,predictions,coefficients)
    info={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'development_n':len(dev),'configurations':21,'folds':5,'ridge_alphas':ALPHAS,
          'selection_metric':'unweighted mean of validation-fold MAPE percentages',
          'holdout_evaluated':False,'batch2_read_or_evaluated':False,'batch3_read_or_evaluated':False,
          'model_selection_uses_same_cv_as_reported':True,'prediction_clipping':False,
          'versions':{k:importlib.metadata.version(k) for k in ['scikit-learn','pandas','numpy']}}
    (TABLES/'experiment_metadata.json').write_text(json.dumps(info,indent=2)+'\n')
    print(summary.to_string(index=False))


if __name__=='__main__':main()
