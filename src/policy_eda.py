"""N04–N06: policy associations and selectively loaded cycle diagnostics."""
from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.load_data import BATCH_FILES, batch_path, load_batch, load_cycle_fields

BATCHES=list(BATCH_FILES)
MIN_GROUP_N=5
SELECTIONS={'batch1':[0,3,44], 'batch2':[0,38,22], 'batch3':[6,7,3]}
EVENTS=[('batch1',0,12),('batch2',38,100)]


def pair_stats(frame, minimum_n=MIN_GROUP_N):
    """Pearson on log10 variance, Spearman; small/constant pairs left unavailable."""
    p=frame.loc[np.isfinite(frame.deltaQ_var)&frame.deltaQ_var.gt(0)
                &np.isfinite(frame.cycle_life)&frame.cycle_life.gt(0)].copy()
    p['log10_deltaQ_var']=np.log10(p.deltaQ_var)
    available=len(p)>=minimum_n and p.log10_deltaQ_var.nunique()>1 and p.cycle_life.nunique()>1
    return {'n':len(p),'pearson_logvar':p.log10_deltaQ_var.corr(p.cycle_life) if available else np.nan,
            'spearman':p.deltaQ_var.corr(p.cycle_life,method='spearman') if available else np.nan,
            'status':'computed' if available else 'insufficient_or_constant'}


def validate_detail(frame,quality,detail,cycle):
    """Find unique cycle position; require detailed maxima/content alignment."""
    if not quality.cycle_lengths_match_summary:raise ValueError('Detailed field lengths differ from summary')
    pos=np.flatnonzero(frame.cycle.to_numpy()==cycle)
    if len(pos)!=1:raise ValueError('Ambiguous/missing summary cycle')
    arrays=[detail[k] for k in ['t','I','V','Qc','Qd']]
    if len({len(x) for x in arrays})!=1 or not len(arrays[0]):raise ValueError('Sample lengths mismatch/empty')
    if not all(np.isfinite(x).all() for x in arrays):raise ValueError('Nonfinite detailed samples')
    if (np.diff(detail['t'])<0).any():raise ValueError('Stored time decreases')
    row=frame.iloc[int(pos[0])]
    for source,target in [('Qd','QD'),('Qc','QC')]:
        if not np.isclose(detail[source].max(),row[target],rtol=1e-6,atol=1e-7):raise ValueError(f'{source} maximum does not align')
    return int(pos[0])


def build_policy_data(data_dir,gallery_features):
    """Join validated cell keys and load only requested detailed traces."""
    metadata=[];traces=[];audits=[];policies=[];groupstats=[]
    for b in BATCHES:
        cells,summary,quality=load_batch(batch_path(b,data_dir),b)
        metadata.append(cells[['batch','cell_id','charging_policy']])
        requested=[(cid,10,'policy_examples') for cid in SELECTIONS[b]]
        for batch,cid,center in EVENTS:
            if batch==b:requested.extend((cid,c,'event_neighborhood') for c in [center-1,center,center+1])
        for cid,cycle,reason in requested:
            frame=summary.loc[summary.cell_id.eq(cid)]  # retain original storage order
            pos=np.flatnonzero(frame.cycle.to_numpy()==cycle)
            if len(pos)!=1:raise ValueError(f'{b}/{cid}/{cycle}: missing mapping')
            detail=load_cycle_fields(batch_path(b,data_dir),cid,int(pos[0]),('t','I','V','Qc','Qd'))
            index=validate_detail(frame,quality.loc[quality.cell_id.eq(cid)].iloc[0],detail,cycle)
            cell=cells.loc[cells.cell_id.eq(cid)].iloc[0]
            record={'batch':b,'cell_id':cid,'cycle':cycle,'reason':reason,
                    'charging_policy':cell.charging_policy,'cycle_life':cell.cycle_life,
                    'storage_index':index,'detail':detail}
            traces.append(record)
            current=detail['I'];state=np.where(current>.05,1,np.where(current<-.05,-1,0))
            transitions=np.flatnonzero(np.diff(state)!=0)+1
            qc_change=np.diff(detail['Qc']);qd_change=np.diff(detail['Qd'])
            dt=np.diff(detail['t']);positive_dt=dt[dt>0]
            gap_limit=20*np.median(positive_dt) if len(positive_dt) else np.inf
            audits.append({k:record[k] for k in ['batch','cell_id','cycle','reason','charging_policy','storage_index']}|{
                'alignment_passed':True,'samples':len(current),'time_start_native':detail['t'][0],
                'time_end_native':detail['t'][-1],'duration_native':detail['t'][-1]-detail['t'][0],
                'max_positive_I_native':current[current>0].max() if (current>0).any() else np.nan,
                'min_I_native':current.min(),'max_Qc':detail['Qc'].max(),'max_Qd':detail['Qd'].max(),
                'largest_time_gap_native':dt.max() if len(dt) else 0.,
                'large_time_gaps':int(np.sum(dt>gap_limit)),
                'direction_transitions':len(transitions),'positive_blocks':int((state[0]==1)+np.sum((state[1:]==1)&(state[:-1]!=1))),
                'negative_blocks':int((state[0]==-1)+np.sum((state[1:]==-1)&(state[:-1]!=-1))),
                'Qc_increase_positive_steps':int(np.sum((qc_change>1e-5)&(current[1:]>.05))),
                'Qd_increase_negative_steps':int(np.sum((qd_change>1e-5)&(current[1:]<-.05)))})
    meta=pd.concat(metadata,ignore_index=True)
    f=gallery_features.merge(meta,on=['batch','cell_id'],how='outer',validate='one_to_one',indicator=True)
    if not f['_merge'].eq('both').all():raise ValueError('Feature/metadata cell keys differ')
    f=f.drop(columns='_merge')
    if not len(f)==len(meta):raise ValueError('Cell count mismatch')
    for b,g in f.groupby('batch',sort=False):
        for policy,sub in g.groupby('charging_policy',sort=True):
            policies.append({'batch':b,'charging_policy':policy,'n_total':len(sub),
                'n_life':int((np.isfinite(sub.cycle_life)&sub.cycle_life.gt(0)).sum()),
                'chargetime_min':sub.mean_chargetime.min(),'chargetime_max':sub.mean_chargetime.max(),
                'chargetime_mean':sub.mean_chargetime.mean(),
                'peak_I_min':sub.peak_positive_I_cycle10.min(),'peak_I_max':sub.peak_positive_I_cycle10.max()})
            groupstats.append({'batch':b,'group_type':'policy','group':policy}|pair_stats(sub))
        groupstats.append({'batch':b,'group_type':'all','group':'all'}|pair_stats(g))
        for group,sub in g.groupby('life_group'):
            groupstats.append({'batch':b,'group_type':'life_group','group':group}|pair_stats(sub))
    return f,pd.DataFrame(policies),traces,pd.DataFrame(audits),pd.DataFrame(groupstats)


def figure_policy_measures(features):
    fig,axes=plt.subplots(2,3,figsize=(27,16),gridspec_kw={'height_ratios':[1,2.2]})
    colors=plt.get_cmap('turbo');markers=['o','s','^','D','v','P','X','<']
    for j,b in enumerate(BATCHES):
        g=features.loc[features.batch.eq(b)];pols=sorted(g.charging_policy.unique());labels=[]
        for k,p in enumerate(pols):
            sub=g.loc[g.charging_policy.eq(p)];col=colors(k/max(1,len(pols)-1))
            ax=axes[0,j]
            ax.scatter(sub.mean_chargetime,sub.peak_positive_I_cycle10,color=col,marker=markers[k%8],s=35,alpha=.8)
            if sub.mean_chargetime.max()-sub.mean_chargetime.min()>.5:
                selected=sub.loc[[sub.mean_chargetime.idxmin(),sub.mean_chargetime.idxmax()]]
            else:selected=sub.iloc[:1]
            labels.extend((r.mean_chargetime,r.peak_positive_I_cycle10,f'P{k+1:02d}') for r in selected.itertuples())
            ax=axes[1,j];vals=sub.mean_chargetime.replace([np.inf,-np.inf],np.nan).dropna()
            offsets=np.linspace(-.12,.12,len(vals))
            ax.scatter(vals,k+offsets,color=col,s=23,marker=markers[k%8])
            if len(vals):ax.plot([vals.min(),vals.max()],[k,k],color=col,lw=1);ax.scatter([vals.mean()],[k],marker='D',color='k',s=17)
        axes[0,j].set(title=f'{b}: all cells n={len(g)}; policies={len(pols)}',xlabel='Mean stored chargetime (cycles 10–100)',ylabel='Peak positive stored I (cycle 10)')
        axes[0,j].margins(x=.12,y=.18)
        ax=axes[0,j];xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim();placed=[]
        for cx,cy,label in labels:
            u=(cx-xmin)/(xmax-xmin);v=(cy-ymin)/(ymax-ymin)
            candidates=[(u+dx,v+dy) for dy in [.025,.085,-.055,.145,-.115,.205,-.175] for dx in [.012,.08,-.065,.15]]
            valid=[(x,y) for x,y in candidates if .015<x<.96 and .025<y<.96 and not any(abs(x-a)<.065 and abs(y-bb)<.06 for a,bb in placed)]
            x,y=valid[0] if valid else (min(.94,max(.02,u+.02)),min(.94,max(.02,v+.04)))
            placed.append((x,y))
            ax.annotate(label,(cx,cy),xytext=(x,y),textcoords='axes fraction',fontsize=7,
                        arrowprops={'arrowstyle':'-','lw':.4,'color':'0.4'})
        axes[0,j].grid(alpha=.2)
        axes[1,j].set_yticks(range(len(pols)),[f'P{k+1:02d} | {p} (n={len(g[g.charging_policy.eq(p)])})' for k,p in enumerate(pols)],fontsize=7)
        axes[1,j].invert_yaxis();axes[1,j].set(xlabel='Mean stored chargetime (cycles 10–100)',title='Policy lookup: points=cells; black diamond=mean')
        axes[1,j].grid(axis='x',alpha=.2)
    fig.suptitle('N04 · Charging measure clusters and policy associations',fontsize=18)
    fig.text(.5,.01,'Policy codes/colors are local to each batch. Native units; no conversion to A or full-charge minutes. Unavailable-life cells included.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.04,1,.96));fig.subplots_adjust(wspace=.95,hspace=.25);return fig


def display_with_gap_breaks(t,values):
    """Do not connect samples across gaps >20x median positive spacing."""
    dt=np.diff(t);positive=dt[dt>0]
    gaps=np.flatnonzero(dt>20*np.median(positive))+1 if len(positive) else np.array([],dtype=int)
    return np.insert(t,gaps,np.nan),np.insert(values,gaps,np.nan),gaps


def figure_traces(records,title):
    fig,axes=plt.subplots(3,len(records),figsize=(6*len(records),10),squeeze=False)
    for j,r in enumerate(records):
        d=r['detail'];t=d['t'];state=np.where(d['I']>.05,1,np.where(d['I']<-.05,-1,0));positions=np.flatnonzero(np.diff(state)!=0)+1
        for i,key,col in [(0,'I','tab:blue'),(1,'V','tab:orange'),(2,'Qc','tab:blue'),(2,'Qd','tab:orange')]:
            tx,vals,gaps=display_with_gap_breaks(t,d[key])
            axes[i,j].plot(tx,vals,lw=.8,color=col,label='Stored '+key)
        axes[0,j].axhline(0,color='0.5',lw=.5);axes[2,j].legend(fontsize=8)
        for i,label in enumerate(['Stored I (native)','Stored V (native)','Stored capacity (native)']):
            axes[i,j].set(ylabel=label,xlabel='Stored t (native)');axes[i,j].grid(alpha=.2)
            for gap in gaps:axes[i,j].axvspan(t[gap-1],t[gap],color='0.7',alpha=.2)
            for p in positions:axes[i,j].axvline(t[p],color='0.4',ls=':',lw=.5,alpha=.5)
        axes[0,j].set_title(f'{r["batch"]} cell {r["cell_id"]} · cycle {r["cycle"]}\n{r["charging_policy"]}',fontsize=9)
    fig.suptitle(title,fontsize=16)
    fig.text(.5,.01,'Exact recorded cycle: summary QD/QC = detailed Qd/Qc maxima verified. Dotted: sampled I state transitions (±0.05). Gray: gap >20x median spacing, line broken; no interpolation.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.96));return fig


def figure_within_policy(features,batch,stats):
    g=features.loc[features.batch.eq(batch)];pols=sorted(g.charging_policy.unique())
    n=len(pols)+1;cols=4;rows=math.ceil(n/cols)
    fig,axes=plt.subplots(rows,cols,figsize=(18,3.1*rows),squeeze=False)
    positive=features.loc[features.deltaQ_var.gt(0),'deltaQ_var'];lo=np.log10(positive.min())-.12;hi=np.log10(positive.max())+.12
    for k,(name,sub) in enumerate([('ALL policies',g)]+[(p,g.loc[g.charging_policy.eq(p)]) for p in pols]):
        ax=axes.flat[k];v=sub.loc[np.isfinite(sub.cycle_life)&sub.cycle_life.gt(0)&np.isfinite(sub.deltaQ_var)&sub.deltaQ_var.gt(0)]
        ax.scatter(np.log10(v.deltaQ_var),v.cycle_life,color='tab:blue',s=23)
        for r in v.itertuples():ax.annotate(str(r.cell_id),(np.log10(r.deltaQ_var),r.cycle_life),xytext=(3,3),textcoords='offset points',fontsize=6)
        typ='all' if k==0 else 'policy';key='all' if k==0 else name
        st=stats.loc[stats.batch.eq(batch)&stats.group_type.eq(typ)&stats['group'].eq(key)].iloc[0]
        desc=f'r(log)={st.pearson_logvar:.2f}, rho={st.spearman:.2f}' if st.status=='computed' else 'correlation NA (n<5 or constant)'
        ax.set(title=f'{name}\nvalid n={len(v)}/{len(sub)}; {desc}',xlim=(lo,hi),ylim=(0,2100),xlabel='log10(delta-Q variance)',ylabel='Stored cycle life')
        ax.title.set_fontsize(8);ax.grid(alpha=.2)
    for ax in list(axes.flat)[n:]:ax.set_axis_off()
    fig.suptitle(f'N06 · {batch}: delta-Q variance vs life within each policy',fontsize=16)
    fig.text(.5,.01,'Point labels = cell IDs; common axes; no trend fit. Pearson uses log10 variance, Spearman uses ranks. Minimum n=5; unknown life omitted, empty policies retained.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.025,1,.96));return fig


def save_tables(output_dir,features,policies,traces,audit,stats):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for name,frame in [('policy_features.csv',features),('policy_measures.csv',policies),('detail_cycle_audit.csv',audit),('within_group_correlations.csv',stats)]:frame.to_csv(out/name,index=False)
    frames=[]
    for r in traces:
        f=pd.DataFrame(r['detail'])
        for k in ['batch','cell_id','cycle','reason']:f[k]=r[k]
        frames.append(f)
    pd.concat(frames,ignore_index=True).to_csv(out/'selected_cycle_samples.csv',index=False)
