"""Post-evaluation diagnostics only; does not tune or change the frozen model."""
from pathlib import Path
from src.day2_evaluation_common import PROJECT_ROOT
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=PROJECT_ROOT
PRED_DIR=PROJECT_ROOT / 'outputs/tables/day2'
OUT=PROJECT_ROOT / 'outputs/tables/day2/model_diagnostics'
FIG=PROJECT_ROOT / 'outputs/figures/day2/model_diagnostics'


def load_predictions():
    b1=pd.read_parquet(PROJECT_ROOT / 'data/processed/day2/train_batch1.parquet')
    b2=pd.read_parquet(PROJECT_ROOT / 'data/processed/day2/test_batch2.parquet')
    fmap=pd.concat([b1,b2])[['barcode_key','log10_deltaQ_var','protocol_key']].drop_duplicates('barcode_key')
    dev=pd.read_csv(PRED_DIR/'boosting_comparison/oof_predictions.csv')
    dev=dev.loc[dev.config_id.eq('linear_regression')].copy()
    hold=pd.read_csv(PRED_DIR/'holdout_evaluation/holdout_predictions.csv')
    test=pd.read_csv(PRED_DIR/'batch2_evaluation/batch2_predictions.csv')
    datasets=[]
    for label,frame in [('Batch 1 development OOF',dev),('Batch 1 holdout',hold),('Batch 2 test',test)]:
        f=frame.rename(columns={'actual_life':'actual_life','predicted_life':'predicted_life'}).copy()
        f['evaluation_set']=label
        if 'log10_deltaQ_var' not in f:
            f=f.merge(fmap,on=['barcode_key','protocol_key'],how='left',validate='many_to_one')
        if f.log10_deltaQ_var.isna().any():
            raise ValueError(f'Missing frozen feature in {label}')
        f['signed_error_cycles']=f.predicted_life-f.actual_life
        f['absolute_error_cycles']=f.signed_error_cycles.abs()
        f['ape_pct']=100*f.absolute_error_cycles/f.actual_life
        datasets.append(f[['evaluation_set','batch','cell_id','protocol_key','actual_life','predicted_life',
                           'log10_deltaQ_var','signed_error_cycles','absolute_error_cycles','ape_pct']])
    allp=pd.concat(datasets,ignore_index=True)
    if allp.duplicated(['evaluation_set','batch','cell_id']).any():raise ValueError('Duplicate cell prediction')
    return allp


def summarize(predictions):
    rows=[]
    for label,g in predictions.groupby('evaluation_set',sort=False):
        rows.append({'evaluation_set':label,'n':len(g),'mape_pct':g.ape_pct.mean(),
          'mae_cycles':g.absolute_error_cycles.mean(),'rmse_cycles':float(np.sqrt(np.mean(g.signed_error_cycles**2))),
          'mean_signed_error_cycles':g.signed_error_cycles.mean(),
          'overprediction_n':int(g.signed_error_cycles.gt(0).sum()),
          'underprediction_n':int(g.signed_error_cycles.lt(0).sum()),
          'median_feature':g.log10_deltaQ_var.median(),'feature_min':g.log10_deltaQ_var.min(),
          'feature_max':g.log10_deltaQ_var.max(),'median_actual_life':g.actual_life.median()})
    return pd.DataFrame(rows)


def protocol_summary(predictions, train):
    train_protocols=set(train.protocol_key)
    b2=predictions.loc[predictions.evaluation_set.eq('Batch 2 test')].copy()
    rows=[]
    for key,g in b2.groupby('protocol_key',sort=True):
        rows.append({'protocol_key':key,'n_cells':len(g),'seen_in_batch1_train':key in train_protocols,
          'mean_actual_life':g.actual_life.mean(),'mean_predicted_life':g.predicted_life.mean(),
          'mean_signed_error_cycles':g.signed_error_cycles.mean(),'mean_ape_pct':g.ape_pct.mean(),
          'max_ape_pct':g.ape_pct.max()})
    return pd.DataFrame(rows).sort_values(['mean_ape_pct','n_cells'],ascending=[False,False])


def leave_one_out_slope_influence(train):
    """One-feature OLS slope sensitivity; diagnostic only, not a new evaluation."""
    x=train.log10_deltaQ_var.to_numpy(float); y=train.cycle_life.to_numpy(float)
    rows=[]
    full=np.polyfit(x,y,1)[0]
    for i,row in enumerate(train.itertuples()):
        slope=np.polyfit(np.delete(x,i),np.delete(y,i),1)[0]
        rows.append({'cell_id':int(row.cell_id),'protocol_key':row.protocol_key,
          'full_slope_cycles_per_feature_unit':full,'slope_without_cell':slope,
          'slope_change_pct':100*(slope-full)/abs(full),
          'life':float(row.cycle_life),'feature':float(row.log10_deltaQ_var)})
    return pd.DataFrame(rows).sort_values('slope_change_pct',key=lambda s:s.abs(),ascending=False)


def save_figures(predictions,train):
    FIG.mkdir(parents=True,exist_ok=True)
    order=['Batch 1 development OOF','Batch 1 holdout','Batch 2 test']
    fig,axes=plt.subplots(1,3,figsize=(15,4.8),sharex=True,sharey=True)
    for ax,label in zip(axes,order):
        g=predictions.loc[predictions.evaluation_set.eq(label)]
        ax.scatter(g.actual_life,g.predicted_life,c='#4779a3',alpha=.8)
        lo=min(g.actual_life.min(),g.predicted_life.min());hi=max(g.actual_life.max(),g.predicted_life.max())
        ax.plot([lo,hi],[lo,hi],'--',color='gray')
        ax.set(title=f'{label}\nn={len(g)}',xlabel='Actual life (cycles)')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Predicted life (cycles)')
    fig.suptitle('Frozen Linear Regression: actual vs predicted by evaluation set')
    fig.tight_layout();fig.savefig(FIG/'01_actual_predicted_by_set.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,4.8),sharex=True)
    for ax,label in zip(axes,order):
        g=predictions.loc[predictions.evaluation_set.eq(label)]
        ax.scatter(g.log10_deltaQ_var,g.signed_error_cycles,c='#c26652',alpha=.8)
        ax.axhline(0,color='gray',ls='--')
        ax.set(title=label,xlabel='log10 deltaQ variance')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Prediction − actual (cycles)')
    fig.suptitle('Residual patterns; each panel has a different fitted training set')
    fig.tight_layout();fig.savefig(FIG/'02_residual_vs_feature.png',dpi=150);plt.close(fig)
    loo=leave_one_out_slope_influence(train).sort_values('slope_change_pct')
    show=pd.concat([loo.head(5),loo.tail(5)]).sort_values('slope_change_pct')
    fig,ax=plt.subplots(figsize=(9,5))
    ax.barh(show.cell_id.astype(str),show.slope_change_pct,color='#8073ac')
    ax.axvline(0,color='gray',lw=1);ax.set(xlabel='Slope change after removing one training cell (%)',
      ylabel='Batch 1 cell ID',title='One-cell-at-a-time coefficient sensitivity (diagnostic)')
    ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(FIG/'03_slope_influence.png',dpi=150);plt.close(fig)


def main():
    predictions=load_predictions()
    train=pd.read_parquet(PROJECT_ROOT / 'data/processed/day2/train_batch1.parquet')
    train=train.loc[train.partition.isin(['development','holdout'])].copy()
    summaries=summarize(predictions)
    protocols=protocol_summary(predictions,train)
    influence=leave_one_out_slope_influence(train)
    OUT.mkdir(parents=True,exist_ok=True)
    predictions.to_csv(OUT/'combined_cell_predictions.csv',index=False)
    summaries.to_csv(OUT/'evaluation_set_summary.csv',index=False)
    protocols.to_csv(OUT/'batch2_protocol_errors.csv',index=False)
    influence.to_csv(OUT/'training_cell_slope_sensitivity.csv',index=False)
    overlap=set(train.protocol_key)&set(predictions.loc[predictions.evaluation_set.eq('Batch 2 test'),'protocol_key'])
    meta={'model_changed':False,'hyperparameters_tuned':False,'batch2_used_only_for_posthoc_diagnostics':True,
      'independent_test_reused_for_selection':False,'development_oof_n':29,'holdout_n':7,'batch2_test_n':39,
      'batch1_batch2_protocol_groups_in_common':sorted(overlap),
      'batch1_only_protocol_group_count':len(set(train.protocol_key)-overlap),
      'batch2_only_protocol_group_count':len(set(predictions.loc[predictions.evaluation_set.eq('Batch 2 test'),'protocol_key'])-overlap),
      'interpretation':'descriptive post-evaluation diagnostics; no causal claims'}
    (OUT/'diagnostic_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    save_figures(predictions,train)
    print(summaries.to_string(index=False))
    print('Shared exact protocol groups:',sorted(overlap))
    print('Top Batch 2 protocol errors:\n',protocols.head(8).to_string(index=False))
    print('Largest slope influence:\n',influence.head(8).to_string(index=False))

if __name__=='__main__':main()
