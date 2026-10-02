"""Same-feature/same-CV model replacement experiment; no holdout or Batch 2 evaluation.

Run: python -m src.day2_boosting_comparison
"""
from pathlib import Path
from src.day2_evaluation_common import PROJECT_ROOT
import hashlib
import importlib.metadata
import json

import numpy as np
import pandas as pd
from src.day2_linear_comparison import evaluate, make_model, SOURCE
import matplotlib.pyplot as plt

TABLES=PROJECT_ROOT / 'outputs/tables/day2/boosting_comparison'
FIGURES=PROJECT_ROOT / 'outputs/figures/day2/boosting_comparison'
FEATURES=['log10_deltaQ_var']
FEATURE_SETS={'variance_only':FEATURES}


def configurations():
    yield {'config_id':'linear_regression','model':'ols','feature_set':'variance_only','target':'raw','alpha':None}
    yield {'config_id':'ridge_a0.1','model':'ridge','feature_set':'variance_only','target':'raw','alpha':.1}
    for depth in [1,2]:
        for trees in [50,100]:
            yield {'config_id':f'boosting_d{depth}_n{trees}','model':'gradient_boosting',
                   'feature_set':'variance_only','target':'raw','alpha':None,
                   'max_depth':depth,'n_estimators':trees}


def paired_predictions(predictions):
    baseline=predictions.loc[predictions.config_id.eq('linear_regression'),
                             ['barcode_key','cell_id','fold','actual_life','predicted_life','ape_pct']]
    rows=[]
    for name,g in predictions.loc[predictions.config_id.ne('linear_regression')].groupby('config_id'):
        paired=baseline.merge(g[['barcode_key','predicted_life','ape_pct']],on='barcode_key',
                              validate='one_to_one',suffixes=('_linear','_alternative'))
        paired['config_id']=name
        paired['alternative_minus_linear_ape_pp']=paired.ape_pct_alternative-paired.ape_pct_linear
        rows.append(paired)
    return pd.concat(rows,ignore_index=True)


def run_comparison(dev):
    tree_rows=[]
    def observe(config,fold,model):
        if config['model']!='gradient_boosting':return
        reg=model.named_steps['regression']
        for i,tree in enumerate(reg.estimators_.ravel(),1):
            leaves=tree.tree_.children_left==-1
            tree_rows.append({'config_id':config['config_id'],'fold':fold,'tree_index':i,
                              'requested_max_depth':config['max_depth'],'actual_depth':tree.get_depth(),
                              'leaf_count':tree.get_n_leaves(),
                              'min_observed_leaf_samples':int(tree.tree_.n_node_samples[leaves].min())})
    result=evaluate(dev,list(configurations()),FEATURE_SETS,fitted_observer=observe)
    return (*result,pd.DataFrame(tree_rows))


def save_figures(dev,summary,scores,predictions,best_boosting):
    FIGURES.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    ordered=list(configurations());ids=[x['config_id'] for x in ordered]
    s=summary.set_index('config_id').loc[ids]
    axes[0].barh(ids,s.mean_fold_mape_pct,xerr=s.std_fold_mape_pct,capsize=3,color='#4779a3')
    axes[0].invert_yaxis();axes[0].set(xlabel='Mean CV MAPE (%) ± sample SD',title='Same feature and target: model comparison')
    for name in ['linear_regression','ridge_a0.1',best_boosting]:
        g=scores.loc[scores.config_id.eq(name)].sort_values('fold')
        axes[1].plot(g.fold,g.mape_pct,marker='o',label=name)
    axes[1].set(xlabel='Fixed validation fold',ylabel='MAPE (%)',title='Fold-by-fold errors');axes[1].set_xticks(range(1,6));axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(FIGURES/'01_model_comparison.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharex=True,sharey=True)
    p=predictions.loc[predictions.config_id.isin(['linear_regression',best_boosting])]
    lo=min(p.actual_life.min(),p.predicted_life.min())-20;hi=max(p.actual_life.max(),p.predicted_life.max())+20
    for ax,name in zip(axes,['linear_regression',best_boosting]):
        g=p.loc[p.config_id.eq(name)]
        ax.scatter(g.actual_life,g.predicted_life,c=g.fold,cmap='viridis',vmin=1,vmax=5)
        ax.plot([lo,hi],[lo,hi],'--',color='gray');ax.set(xlabel='Actual life (cycles)',ylabel='OOF prediction (cycles)',title=name);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(FIGURES/'02_oof_predictions.png',dpi=140);plt.close(fig)
    # Diagnostic development fits, not validation estimates or deployment models.
    grid=pd.DataFrame({FEATURES[0]:np.linspace(dev[FEATURES[0]].min(),dev[FEATURES[0]].max(),200)})
    fig,ax=plt.subplots(figsize=(9,5));ax.scatter(dev[FEATURES[0]],dev.cycle_life,color='gray',label='Development observations')
    for config in ordered:
        if config['config_id'] not in ['linear_regression','ridge_a0.1',best_boosting]:continue
        model=make_model(config);model.fit(dev[FEATURES],dev.cycle_life)
        ax.plot(grid[FEATURES[0]],model.predict(grid),label=config['config_id'])
    ax.set(xlabel='log10 deltaQ variance',ylabel='Life (cycles)',title='Development-fit response curves (not a validation score)')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(FIGURES/'03_response_curves.png',dpi=140);plt.close(fig)


def main():
    train=pd.read_parquet(SOURCE)
    dev=train.loc[train.partition.eq('development')].sort_values(['batch','cell_id']).reset_index(drop=True)
    summary,scores,predictions,coefficients,scales,trees=run_comparison(dev)
    paired=paired_predictions(predictions)
    best=summary.loc[summary.model.eq('gradient_boosting')].sort_values(['mean_fold_mape_pct','config_id']).iloc[0].config_id
    TABLES.mkdir(parents=True,exist_ok=True)
    for name,frame in [('summary',summary),('fold_scores',scores),('oof_predictions',predictions),
                       ('linear_coefficients',coefficients),('scaler_statistics',scales),
                       ('tree_audit',trees),('paired_cell_errors',paired)]:
        frame.to_csv(TABLES/f'{name}.csv',index=False)
    old=pd.read_csv(PROJECT_ROOT / 'outputs/tables/day2/linear_comparison/summary.csv').set_index('config_id')
    current=summary.set_index('config_id')
    for new,previous in [('linear_regression','ols_F1_raw'),('ridge_a0.1','ridge_F1_raw_a0.1')]:
        np.testing.assert_allclose(current.loc[new,'mean_fold_mape_pct'],old.loc[previous,'mean_fold_mape_pct'],rtol=1e-12)
    save_figures(dev,summary,scores,predictions,best)
    info={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'development_n':len(dev),'cv_fits':30,'diagnostic_development_fits':3,
          'features':FEATURES,'target':'untransformed cycle_life','configurations':list(configurations()),
          'boosting_fixed_parameters':{'min_samples_leaf':10,'learning_rate':.05,'random_state':42,
                                      'loss':'squared_error','subsample':1.0},
          'best_boosting_cv_config':best,'holdout_evaluated':False,'batch2_read_or_evaluated':False,
          'prediction_clipping':False,'prior_linear_results_reproduced':True,
          'response_curve_is_development_fit':True,'selection_on_same_cv':True,
          'sklearn_version':importlib.metadata.version('scikit-learn')}
    (TABLES/'experiment_metadata.json').write_text(json.dumps(info,indent=2)+'\n')
    print(summary.to_string(index=False))
    print('Best boosting:',best)
    print(trees.groupby('config_id').agg(max_actual_depth=('actual_depth','max'),max_leaves=('leaf_count','max')).to_string())
    print(paired.groupby('config_id').alternative_minus_linear_ape_pp.agg(['mean','min','max']).to_string())


if __name__=='__main__':main()
