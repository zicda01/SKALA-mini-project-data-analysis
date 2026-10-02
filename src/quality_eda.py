"""N01–N03: reversible quality sensitivity analysis and figures."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from src.load_data import BATCH_FILES, batch_path, load_batch
from src.preprocess import QualityConfig, prepare_summary

BATCHES = list(BATCH_FILES)
FEATURES = ['std_QD', 'QD_slope']
TEMP_NOTE = 'Review: early mean Tmax >100, Tmin <-50, or Tmax < Tmin (native values; heuristic)'


def temperature_review(frame):
    """Broad review flag, not a deletion rule or a validated instrument range."""
    return (frame.mean_Tmax.gt(100) | frame.mean_Tmin.lt(-50)
            | frame.mean_Tmax.lt(frame.mean_Tmin))


def qd_features(early):
    rows = []
    for cid, g in early.groupby('cell_id'):
        v = g.loc[g.QD_analysis.notna()].sort_values('cycle')
        rows.append({'cell_id': cid, 'std_QD': v.QD_analysis.std(),
                     'QD_slope': np.polyfit(v.cycle, v.QD_analysis, 1)[0] if len(v)>=5 else np.nan,
                     'n_QD': len(v)})
    return pd.DataFrame(rows)


def correlation(frame, x, y, method='pearson'):
    p=frame[[x,y]].replace([np.inf,-np.inf],np.nan).dropna()
    r=p[x].corr(p[y],method=method) if len(p)>=3 and p[x].nunique()>1 and p[y].nunique()>1 else np.nan
    return len(p),r


def build_quality_data(data_dir):
    """Recompute early features from raw summaries; retain every original cell."""
    feature_rows=[]; quality_rows=[]
    for b in BATCHES:
        cells, raw, _ = load_batch(batch_path(b,data_dir),b)
        base=prepare_summary(raw)
        masked=prepare_summary(raw,QualityConfig(mask_high_qd=True))
        early=base.loc[base.cycle.between(10,100)]
        alt=masked.loc[masked.cycle.between(10,100)]
        f=cells.merge(qd_features(early),on='cell_id',validate='one_to_one')
        f=f.merge(qd_features(alt),on='cell_id',suffixes=('_retained','_masked'),validate='one_to_one')
        t=early.groupby('cell_id')[['Tmax','Tmin','Tavg']].mean().rename(columns=lambda c:'mean_'+c)
        f=f.merge(t,on='cell_id',validate='one_to_one')
        f['temperature_review']=temperature_review(f)
        f['temperature_unavailable']=~np.isfinite(f[['mean_Tmax','mean_Tmin']]).all(axis=1)
        f['early_high_QD_rows']=f.cell_id.map(early.groupby('cell_id').flag_qd_high.sum()).fillna(0).astype(int)
        feature_rows.append(f)
        for c in cells.itertuples():
            g=base.loc[base.cell_id.eq(c.cell_id)]
            e=early.loc[early.cell_id.eq(c.cell_id)]
            row=f.loc[f.cell_id.eq(c.cell_id)].iloc[0]
            quality_rows.append({'batch':b,'cell_id':c.cell_id,'charging_policy':c.charging_policy,
                'life_unavailable':not(np.isfinite(c.cycle_life) and c.cycle_life>0),
                'no_valid_IR_full':not g.IR_analysis.notna().any(),
                'high_QD_full':bool(g.flag_qd_high.any()),'high_QD_early':bool(e.flag_qd_high.any()),
                'temperature_review':bool(row.temperature_review),
                'temperature_unavailable':bool(row.temperature_unavailable),
                'early_rows':len(e),'n_QD_early':int(e.QD_analysis.notna().sum()),
                'n_IR_early':int(e.IR_analysis.notna().sum()),
                'QD_coverage':e.QD_analysis.notna().sum()/91,
                'IR_coverage':e.IR_analysis.notna().sum()/91})
    f=pd.concat(feature_rows,ignore_index=True);q=pd.DataFrame(quality_rows)
    stats=[]
    for b,g in f.groupby('batch',sort=False):
        g=g.loc[np.isfinite(g.cycle_life)&g.cycle_life.gt(0)]
        for feat in FEATURES:
            cols=[feat+'_retained',feat+'_masked']
            common=g.replace([np.inf,-np.inf],np.nan).dropna(subset=cols+['cycle_life'])
            for method in ['pearson','spearman']:
                for mode in ['retained','masked']:
                    for pop,frame in [('common_cells',common),('all_valid',g)]:
                        n,r=correlation(frame,feat+'_'+mode,'cycle_life',method)
                        stats.append({'batch':b,'feature':feat,'method':method,'mode':mode,
                                      'population':pop,'n':n,'correlation':r})
    temperatures=[]
    for b,g in f.groupby('batch',sort=False):
        for mode,sub in [('all',g),('review_excluded',g.loc[~g.temperature_review])]:
            n,r=correlation(sub,'mean_Tmax','mean_Tmin')
            temperatures.append({'batch':b,'mode':mode,'n':n,'pearson':r})
    return f,q,pd.DataFrame(stats),pd.DataFrame(temperatures)


def figure_qd_sensitivity(features,stats):
    fig,axes=plt.subplots(3,3,figsize=(17,12))
    for j,b in enumerate(BATCHES):
        g=features.loc[features.batch.eq(b)]
        for i,feat in enumerate(FEATURES):
            ax=axes[i,j]
            annotations=[]
            for row in g.itertuples():
                vals=[getattr(row,feat+'_retained'),getattr(row,feat+'_masked')]
                changed=row.early_high_QD_rows>0
                ax.plot([0,1],vals,'o-',color='tab:red' if changed else '0.65',alpha=.85 if changed else .25,ms=3,lw=.8)
                if changed: annotations.append((vals[1],row.cell_id))
            if annotations:
                low,high=ax.get_ylim();spacing=(high-low)*.035;previous=-np.inf
                for value,cid in sorted(annotations):
                    label_y=max(value,previous+spacing);previous=label_y
                    ax.annotate(str(cid),(1,value),xytext=(1.08,label_y),fontsize=8,
                                arrowprops={'arrowstyle':'-','lw':.5,'color':'0.4'})
            ax.set_xticks([0,1],['Retained','Masked >1.32 Ah'])
            ax.set(xlim=(-.2,1.3),ylabel=feat+(' (Ah)' if feat=='std_QD' else ' (Ah/cycle)'), title=f'{b}: all cells n={len(g)}; affected={g.early_high_QD_rows.gt(0).sum()}')
            ax.grid(alpha=.2)
        ax=axes[2,j]
        s=stats.loc[stats.batch.eq(b)&stats.population.eq('common_cells')]
        labels=[];before=[];after=[];ns=[]
        for feat in FEATURES:
            for method in ['pearson','spearman']:
                pair=s.loc[s.feature.eq(feat)&s.method.eq(method)].set_index('mode')
                labels.append(feat+'\n'+method);before.append(pair.at['retained','correlation']);after.append(pair.at['masked','correlation']);ns.append(pair.at['masked','n'])
        x=np.arange(4)
        ax.bar(x-.18,before,.36,label='Retained',color='0.6');ax.bar(x+.18,after,.36,label='Masked',color='tab:blue')
        ax.set_xticks(x,[f'{label}\nn={n}' for label,n in zip(labels,ns)],fontsize=8)
        ax.set(ylim=(-1.15,1.15),ylabel='Correlation with stored life',title='Same valid cells in both conditions')
        ax.axhline(0,color='k',lw=.5);ax.legend(fontsize=8)
        for k,(v,w) in enumerate(zip(before,after)):
            for pos,val in [(k-.18,v),(k+.18,w)]:
                if np.isfinite(val):ax.text(pos,val+(0.04 if val>=0 else -.04),f'{val:.2f}',ha='center',va='bottom' if val>=0 else 'top',fontsize=7)
    fig.suptitle('N01 · Early QD feature sensitivity to positive spikes',fontsize=16)
    fig.text(.5,.01,'Cycles 10–100; red = affected cells (IDs at masked values). No cell deletion/imputation; raw QD and delta-Q unchanged.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));return fig


def figure_temperature(features,stats):
    fig,axes=plt.subplots(2,3,figsize=(16,9))
    for j,b in enumerate(BATCHES):
        g=features.loc[features.batch.eq(b)].replace([np.inf,-np.inf],np.nan).dropna(subset=['mean_Tmax','mean_Tmin'])
        clean=g.loc[~g.temperature_review]
        for i in [0,1]:
            ax=axes[i,j]
            ax.scatter(g.mean_Tmax,g.mean_Tmin,c=np.where(g.temperature_review,'tab:red','tab:blue'),alpha=.7,s=25)
            if i==1 and len(clean):
                for axis,col in [('x','mean_Tmax'),('y','mean_Tmin')]:
                    low,high=clean[col].min(),clean[col].max();margin=max((high-low)*.12,.25)
                    getattr(ax,'set_'+axis+'lim')(low-margin,high+margin)
            for row in g.loc[g.temperature_review].itertuples():
                if i==0: ax.annotate(f'cell {row.cell_id}',(row.mean_Tmax,row.mean_Tmin),xytext=(-50,8),textcoords='offset points',fontsize=9)
            stat=stats.loc[stats.batch.eq(b)&stats['mode'].eq('all' if i==0 else 'review_excluded')].iloc[0]
            ax.set(title=f'{b}: {"full range" if i==0 else "zoom to non-reviewed range"}\n{"all" if i==0 else "review excluded"} r={stat.pearson:.3f}, n={stat.n}',xlabel='Mean stored Tmax',ylabel='Mean stored Tmin')
            ax.grid(alpha=.2)
            if i==1:
                xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim()
                outside=~(g.mean_Tmax.between(xmin,xmax)&g.mean_Tmin.between(ymin,ymax))
                ax.text(.02,.98,f'Outside view: {outside.sum()}',transform=ax.transAxes,va='top',fontsize=9)
    fig.suptitle('N02 · Temperature extreme values and correlation sensitivity',fontsize=16)
    fig.text(.5,.01,'Cycles 10–100; all original points retained in scatter; zoom may hide extremes. '+TEMP_NOTE,ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.95));return fig


def figure_quality_map(quality):
    flags=['life_unavailable','no_valid_IR_full','high_QD_full','high_QD_early','temperature_review','temperature_unavailable']
    names=['Life NA','No IR\nfull','High QD\nfull','High QD\nearly','Temp\nreview','Temp\nNA']
    fig,axes=plt.subplots(1,6,figsize=(27,18),gridspec_kw={'width_ratios':[6,1.8,6,1.8,6,1.8]})
    for j,b in enumerate(BATCHES):
        g=quality.loc[quality.batch.eq(b)].sort_values(['charging_policy','cell_id'])
        ax=axes[2*j];ax.imshow(g[flags].astype(int),aspect='auto',cmap=ListedColormap(['#eeeeee','#c44e52']),vmin=0,vmax=1)
        labels=[f'{r.cell_id:02d} | {r.charging_policy}' for r in g.itertuples()]
        ax.set_yticks(range(len(g)),labels,fontsize=6);ax.set_xticks(range(6),names,fontsize=8)
        ax.xaxis.tick_top();ax.set_title(f'{b}: n={len(g)}',pad=40)
        ax=axes[2*j+1];im=ax.imshow(g[['QD_coverage','IR_coverage']],aspect='auto',cmap='Blues',vmin=0,vmax=1)
        ax.set_yticks([]);ax.set_xticks([0,1],['QD','IR']);ax.xaxis.tick_top();ax.set_title('Early coverage',pad=40,fontsize=10)
        for i,row in enumerate(g.itertuples()):
            for k,n in enumerate([row.n_QD_early,row.n_IR_early]):ax.text(k,i,str(n),ha='center',va='center',fontsize=6,color='white' if n/91>.6 else 'black')
    fig.suptitle('N03 · Cell/policy quality map: red = review or unavailable; gray = no flag',fontsize=16,y=.99)
    fig.text(.5,.01,'Early = cycles 10–100; coverage denominator = 91 expected cycles, numbers = valid observations. '+TEMP_NOTE,ha='center',fontsize=9)
    fig.subplots_adjust(left=.12,right=.96,top=.9,bottom=.04,wspace=1.4)
    cax=fig.add_axes([.973,.15,.008,.5]);fig.colorbar(im,cax=cax,label='Valid early observations / 91')
    return fig


def save_quality_outputs(output_dir,features,quality,stats,temperatures):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for name,frame in [('early_qd_sensitivity.csv',features),('cell_quality_map.csv',quality),('qd_correlation_sensitivity.csv',stats),('temperature_correlation_sensitivity.csv',temperatures)]:frame.to_csv(out/name,index=False)
