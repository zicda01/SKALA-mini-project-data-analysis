"""Compare alternative ΔQ descriptors and QD masking on the same development folds.

Run: python -m src.day2_feature_comparison
Uses the common first-experiment CV engine. Target remains untransformed cycle_life.
"""
from pathlib import Path
from src.day2_evaluation_common import PROJECT_ROOT
import hashlib
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from src.day2_linear_comparison import evaluate, SOURCE

TABLES=PROJECT_ROOT / 'outputs/tables/day2/feature_comparison'
FIGURES=PROJECT_ROOT / 'outputs/figures/day2/feature_comparison'
FEATURE_SETS={
    'variance_only':['log10_deltaQ_var'],
    'minimum_only':['deltaQ_min'],
    'variance_retained':['log10_deltaQ_var','QD_slope_retained'],
    'variance_masked':['log10_deltaQ_var','QD_slope_masked'],
    'minimum_retained':['deltaQ_min','QD_slope_retained'],
    'minimum_masked':['deltaQ_min','QD_slope_masked'],
}
LABELS={'variance_only':'log10 variance only','minimum_only':'minimum only',
        'variance_retained':'log10 variance + slope (retained)',
        'variance_masked':'log10 variance + slope (masked)',
        'minimum_retained':'minimum + slope (retained)',
        'minimum_masked':'minimum + slope (masked)'}


def configurations():
    for name in FEATURE_SETS:
        for model,alpha in [('ols',None),('ridge',.1),('ridge',10.)]:
            suffix='' if alpha is None else f'_a{alpha:g}'
            yield {'config_id':f'{model}_{name}{suffix}','model':model,'feature_set':name,
                   'target':'raw','alpha':alpha}


def paired_fold_deltas(scores):
    rows=[]
    comparisons=[('descriptor_replacement','variance_only','minimum_only'),
                 ('masking_variance','variance_retained','variance_masked'),
                 ('masking_minimum','minimum_retained','minimum_masked')]
    for name,base,alternative in comparisons:
        for model,alpha in [('ols',None),('ridge',.1),('ridge',10.)]:
            select=scores.model.eq(model)
            if alpha is not None:select &= scores.alpha.eq(alpha)
            b=scores.loc[select & scores.feature_set.eq(base)]
            a=scores.loc[select & scores.feature_set.eq(alternative)]
            joined=b[['fold','mape_pct']].merge(a[['fold','mape_pct']],on='fold',validate='one_to_one',suffixes=('_base','_alternative'))
            for r in joined.itertuples():
                rows.append({'comparison':name,'model':model,'alpha':alpha,'fold':r.fold,
                             'base_feature_set':base,'alternative_feature_set':alternative,
                             'base_mape_pct':r.mape_pct_base,'alternative_mape_pct':r.mape_pct_alternative,
                             'alternative_minus_base_pp':r.mape_pct_alternative-r.mape_pct_base})
    return pd.DataFrame(rows)


def save_figures(dev,summary,scores,predictions):
    FIGURES.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(12,6))
    order=list(FEATURE_SETS);positions=np.arange(len(order));width=.25
    for offset,model,alpha,label in [(-1,'ols',None,'Linear Regression'),(0,'ridge',.1,'Ridge alpha=0.1'),(1,'ridge',10.,'Ridge alpha=10')]:
        sub=summary.loc[summary.model.eq(model)]
        if alpha is not None:sub=sub.loc[sub.alpha.eq(alpha)]
        sub=sub.set_index('feature_set').loc[order]
        ax.barh(positions+offset*width,sub.mean_fold_mape_pct,height=width,
                xerr=sub.std_fold_mape_pct,capsize=2,label=label)
    ax.set_yticks(positions,[LABELS[k] for k in order]);ax.invert_yaxis()
    ax.set(xlabel='Mean fold MAPE (%) ± sample SD',title='Alternative features, same target and CV (development n=29)')
    ax.legend();ax.grid(axis='x',alpha=.2);fig.tight_layout()
    fig.savefig(FIGURES/'01_feature_comparison.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharex=True,sharey=True)
    p=predictions.loc[predictions.config_id.isin(['ols_variance_only','ols_minimum_only'])]
    low=min(p.actual_life.min(),p.predicted_life.min())-20;high=max(p.actual_life.max(),p.predicted_life.max())+20
    for ax,name in zip(axes,['variance_only','minimum_only']):
        group=p.loc[p.feature_set.eq(name)]
        ax.scatter(group.actual_life,group.predicted_life,c=group.fold,cmap='viridis',vmin=1,vmax=5)
        ax.plot([low,high],[low,high],'--',color='gray')
        score=summary.loc[summary.config_id.eq('ols_'+name)].iloc[0]
        ax.set(xlabel='Actual life (cycles)',ylabel='OOF predicted life (cycles)',
               title=f'Linear Regression: {LABELS[name]}\nMean fold MAPE {score.mean_fold_mape_pct:.2f}%')
        ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(FIGURES/'02_descriptor_predictions.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    changed=~np.isclose(dev.QD_slope_retained,dev.QD_slope_masked,rtol=1e-10,atol=1e-12)
    axes[0].scatter(dev.QD_slope_retained,dev.QD_slope_masked,c=np.where(changed,'#c34f36','#48749b'))
    lo=min(dev.QD_slope_retained.min(),dev.QD_slope_masked.min());hi=max(dev.QD_slope_retained.max(),dev.QD_slope_masked.max())
    axes[0].plot([lo,hi],[lo,hi],'--',color='gray')
    for r in dev.loc[changed].itertuples():axes[0].annotate(f'cell {r.cell_id}',(r.QD_slope_retained,r.QD_slope_masked),xytext=(5,5),textcoords='offset points')
    axes[0].set(xlabel='Slope: high QD retained (Ah/cycle)',ylabel='Slope: high QD masked (Ah/cycle)',title=f'Changed slope values: {int(changed.sum())} / {len(dev)}')
    axes[0].ticklabel_format(style='sci',axis='both',scilimits=(0,0));axes[0].grid(alpha=.2)
    for name in ['variance_retained','variance_masked','minimum_retained','minimum_masked']:
        g=scores.loc[scores.model.eq('ols') & scores.feature_set.eq(name)].sort_values('fold')
        axes[1].plot(g.fold,g.mape_pct,marker='o',linestyle='--' if 'retained' in name else '-',label=LABELS[name])
    axes[1].set(xlabel='Fixed CV validation fold',ylabel='MAPE (%)',title='Masking sensitivity: Linear Regression')
    axes[1].set_xticks(range(1,6));axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.tight_layout();fig.savefig(FIGURES/'03_masking_sensitivity.png',dpi=140);plt.close(fig)


def main():
    train=pd.read_parquet(SOURCE)
    dev=train.loc[train.partition.eq('development')].sort_values(['batch','cell_id']).reset_index(drop=True)
    summary,scores,predictions,coefficients,scales=evaluate(dev,list(configurations()),FEATURE_SETS)
    TABLES.mkdir(parents=True,exist_ok=True)
    changes=dev[['batch','cell_id','barcode_key','cv_valid_fold','early_high_QD_rows','QD_slope_retained','QD_slope_masked']].copy()
    changes['masked_minus_retained']=changes.QD_slope_masked-changes.QD_slope_retained
    changes['slope_changed']=~np.isclose(changes.QD_slope_masked,changes.QD_slope_retained,rtol=1e-10,atol=1e-12)
    deltas=paired_fold_deltas(scores)
    for name,frame in [('summary',summary),('fold_scores',scores),('oof_predictions',predictions),
                       ('coefficients',coefficients),('scaler_statistics',scales),
                       ('masking_feature_changes',changes),('paired_fold_deltas',deltas)]:
        frame.to_csv(TABLES/f'{name}.csv',index=False)
    old=pd.read_csv(PROJECT_ROOT / 'outputs/tables/day2/linear_comparison/summary.csv').set_index('config_id')
    current=summary.set_index('config_id')
    for new,previous in [('ols_variance_only','ols_F1_raw'),('ridge_variance_only_a0.1','ridge_F1_raw_a0.1'),
                         ('ols_variance_masked','ols_F2_raw'),('ridge_variance_masked_a10','ridge_F2_raw_a10')]:
        np.testing.assert_allclose(current.loc[new,'mean_fold_mape_pct'],old.loc[previous,'mean_fold_mape_pct'],rtol=1e-12)
    save_figures(dev,summary,scores,predictions)
    info={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'feature_sets':FEATURE_SETS,'target':'untransformed cycle_life',
          'deltaQ_min_representation':'direct signed minimum; no log or absolute-value transform',
          'ridge_alphas':[.1,10.],'configurations':18,'development_n':len(dev),'folds':5,
          'changed_slope_cell_ids':changes.loc[changes.slope_changed,'cell_id'].tolist(),
          'holdout_evaluated':False,'batch2_read_or_evaluated':False,'prior_results_reproduced':True,
          'new_feature_extraction':False,'prediction_clipping':False,'selection_on_same_cv':True}
    (TABLES/'experiment_metadata.json').write_text(json.dumps(info,indent=2)+'\n')
    print(summary.to_string(index=False))
    print('Changed slopes:',info['changed_slope_cell_ids'])
    print(deltas.groupby(['comparison','model','alpha'],dropna=False).alternative_minus_base_pp.mean().to_string())


if __name__=='__main__':main()
