"""N07–N08: endpoint comparisons and explicitly heuristic knee candidates."""
from pathlib import Path
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.load_data import BATCH_FILES,batch_path,load_batch,load_cycle_fields
from src.preprocess import prepare_summary,QualityConfig
from src.question_gallery import life_group,GROUPS,GROUP_COLORS

BATCHES=list(BATCH_FILES)
ENDS=[50,75,100]
KNEE_CELLS={'batch1':[11,2,0,18],'batch2':[11,9,33,38],'batch3':[5,19]}
KNEE_CONFIGS=list(itertools.product([False,True],[1,11,31],[30,75]))


def curve_review_flags(q,qd_max):
    """Inspect interpolated range only; preserve original curve and statistics."""
    q=np.asarray(q,dtype=float)
    return bool(q.min()<-.05 or q.max()>1.2*qd_max)


def exact_curve(path,frame,quality,cell_id,cycle):
    positions=np.flatnonzero(frame.cycle.to_numpy()==cycle)
    if len(positions)!=1 or not quality.cycle_lengths_match_summary:
        raise ValueError(f'{cell_id}/{cycle}: ambiguous mapping')
    idx=int(positions[0]);d=load_cycle_fields(path,cell_id,idx,('Qdlin','Qd'))
    maximum=np.max(d['Qd']) if len(d['Qd']) else np.nan
    if not np.isfinite(maximum) or not np.isclose(maximum,frame.iloc[idx].QD,rtol=1e-6,atol=1e-7):
        raise ValueError(f'{cell_id}/{cycle}: QD content mismatch')
    v=d['Vdlin'];q=d['Qdlin']
    if len(v)!=len(q) or len(v)<2 or not np.isfinite(v).all() or not np.isfinite(q).all() or not (np.diff(v)<0).all():
        raise ValueError(f'{cell_id}/{cycle}: invalid voltage grid')
    return (v,q),{'cell_id':cell_id,'cycle':cycle,'storage_index':idx,'summary_QD':frame.iloc[idx].QD,
                  'detail_Qd_max':maximum,'alignment_passed':True,'grid_points':len(v),'Qdlin_min':q.min(),'Qdlin_max':q.max(),
                  'Qdlin_range_review':curve_review_flags(q,maximum)}


def longest_finite_segment(cycle,values):
    """Never join across invalid values or missing cycle numbers."""
    x=np.asarray(cycle,dtype=float);y=np.asarray(values,dtype=float)
    valid=np.isfinite(x)&np.isfinite(y)
    segments=[];start=None
    for i in range(len(x)):
        if not valid[i] or (i and (not valid[i-1] or x[i]-x[i-1]!=1)):
            if start is not None:segments.append((start,i));start=None
        if valid[i] and start is None:start=i
    if start is not None:segments.append((start,len(x)))
    if not segments:return np.array([]),np.array([])
    start,end=max(segments,key=lambda pair:pair[1]-pair[0])
    return x[start:end],y[start:end]


def smooth_without_gap_fill(values,window):
    s=pd.Series(values,dtype=float)
    return s.rolling(window,center=True,min_periods=window).median().to_numpy() if window>1 else s.to_numpy(copy=True)


def rolling_slope(cycle,values,window):
    x=np.asarray(cycle,dtype=float);y=np.asarray(values,dtype=float);out=np.full(len(x),np.nan)
    half=window//2
    for i in range(half,len(x)-half):
        xx=x[i-half:i+half+1];yy=y[i-half:i+half+1]
        if np.isfinite(yy).all() and (np.diff(xx)==1).all():out[i]=np.polyfit(xx,yy,1)[0]
    return out


def fit_knee(cycle,values,min_span=75,min_points=20,step=5):
    """Continuous two-line fit; a descriptive candidate, not physical ground truth.

    Search knots every five observed cycle positions in longest valid segment.
    Require >=20 points and min_span cycles on both sides. Heuristic acceptance:
    >=20% SSE improvement, post slope <0, slope decrease >1e-5 Ah/cycle and
    >=1.5x increase in negative slope magnitude (when pre slope is negative).
    """
    x,y=longest_finite_segment(cycle,values)
    result={'n_fit':len(x),'segment_start':x[0] if len(x) else np.nan,
            'segment_end':x[-1] if len(x) else np.nan,'candidate_cycle':np.nan,
            'pre_slope':np.nan,'post_slope':np.nan,'relative_sse_improvement':np.nan,
            'fit_a':np.nan,'fit_b':np.nan,'fit_c':np.nan,'status':'insufficient_record'}
    if len(x)<2*min_points or x[-1]-x[0]<2*min_span:return result
    z=x-x[0];base=np.column_stack([np.ones(len(x)),z]);linear=np.linalg.lstsq(base,y,rcond=None)[0]
    sse_linear=float(np.square(y-base@linear).sum())
    candidates=[i for i in range(min_points,len(x)-min_points,step)
                if x[i]-x[0]>=min_span and x[-1]-x[i]>=min_span]
    if not candidates:return result
    best=None
    for i in candidates:
        mat=np.column_stack([base,np.maximum(0,x-x[i])]);coef=np.linalg.lstsq(mat,y,rcond=None)[0]
        sse=float(np.square(y-mat@coef).sum())
        if best is None or sse<best[0]:best=(sse,i,coef)
    sse,i,coef=best;before=coef[1];after=coef[1]+coef[2]
    improvement=1-sse/sse_linear if sse_linear>1e-20 else 0.
    acceleration=(after<0 and after-before<-1e-5 and (before>=0 or abs(after)>=1.5*abs(before)))
    status='candidate_passed_heuristic' if improvement>=.2 and acceleration else 'best_split_unconfirmed'
    result.update(candidate_cycle=x[i],pre_slope=before,post_slope=after,
                  relative_sse_improvement=improvement,fit_a=coef[0],fit_b=coef[1],fit_c=coef[2],status=status)
    return result


def build_window_knee_data(data_dir):
    features=[];audit=[];selected={};fits=[];curve_rows=[];review_samples=[]
    for b in BATCHES:
        path=batch_path(b,data_dir);cells,raw,quality=load_batch(path,b)
        retained=prepare_summary(raw);masked=prepare_summary(raw,QualityConfig(mask_high_qd=True))
        for cell in cells.itertuples():
            frame=retained.loc[retained.cell_id.eq(cell.cell_id)]
            alt=masked.loc[masked.cell_id.eq(cell.cell_id)]
            arrays={};reviews={}
            for cycle in [10,*ENDS]:
                arrays[cycle],record=exact_curve(path,frame,quality.loc[quality.cell_id.eq(cell.cell_id)].iloc[0],cell.cell_id,cycle)
                audit.append({'batch':b,**record});reviews[cycle]=record['Qdlin_range_review']
            if any(reviews.values()):
                for cycle,(v,q) in arrays.items():
                    review_samples.append(pd.DataFrame({'batch':b,'cell_id':cell.cell_id,'cycle':cycle,'voltage':v,'Qdlin':q,'range_review':reviews[cycle]}))
            for end in ENDS:
                v10,q10=arrays[10];v,q=arrays[end]
                if not np.array_equal(v10,v):raise ValueError(f'{b}/{cell.cell_id}/{end}: voltage grids differ')
                delta=q-q10
                row={'batch':b,'cell_id':cell.cell_id,'end_cycle':end,'cycle_life':cell.cycle_life,
                     'life_group':life_group(cell.cycle_life),'charging_policy':cell.charging_policy,
                     'deltaQ_var':delta.var(),'deltaQ_min':delta.min(),'delta_curve_review':reviews[10] or reviews[end],
                     'delta_status':'accepted_review' if reviews[10] or reviews[end] else 'accepted',
                     'endpoint_high_QD':bool(frame.loc[frame.cycle.eq(end),'flag_qd_high'].iloc[0])}
                for mode,g in [('retained',frame),('masked',alt)]:
                    early=g.loc[g.cycle.between(10,end)];valid=early.loc[early.QD_analysis.notna()]
                    row['n_QD_'+mode]=len(valid)
                    row['QD_slope_'+mode]=np.polyfit(valid.cycle,valid.QD_analysis,1)[0] if len(valid)>=5 else np.nan
                features.append(row)
        for cid in KNEE_CELLS[b]:
            cell=cells.loc[cells.cell_id.eq(cid)].iloc[0]
            g=retained.loc[retained.cell_id.eq(cid)].copy()
            # Label-based cutoff is for retrospective description only.
            g=g.loc[g.cycle.ge(10)&(g.cycle.le(cell.cycle_life) if np.isfinite(cell.cycle_life) and cell.cycle_life>0 else True)]
            g['QD_masked']=masked.loc[g.index,'QD_analysis']
            g['smoothed_masked_11']=smooth_without_gap_fill(g.QD_masked,11)
            g['slope_masked_31']=rolling_slope(g.cycle,g.QD_masked,31)
            g['slope_masked_75']=rolling_slope(g.cycle,g.QD_masked,75)
            selected[(b,cid)]={'frame':g,'policy':cell.charging_policy,'life':cell.cycle_life}
            curve_rows.append(g[['batch','cell_id','cycle','cycle_life','QD','QD_analysis','QD_masked','smoothed_masked_11','slope_masked_31','slope_masked_75']])
            for mask,window,span in KNEE_CONFIGS:
                y=g.QD_masked if mask else g.QD_analysis
                smoothed=smooth_without_gap_fill(y,window)
                fit=fit_knee(g.cycle,smoothed,min_span=span)
                fits.append({'batch':b,'cell_id':cid,'mask_high_QD':mask,'median_window':window,
                             'min_span':span,'cycle_life':cell.cycle_life,**fit})
    f=pd.DataFrame(features);stats=[]
    for b,g in f.groupby('batch',sort=False):
        for feat in ['deltaQ_var','deltaQ_min','QD_slope_retained','QD_slope_masked']:
            common_ids=set.intersection(*(set(sub.loc[np.isfinite(sub[feat])&np.isfinite(sub.cycle_life)&sub.cycle_life.gt(0),'cell_id']) for _,sub in g.groupby('end_cycle')))
            for end,sub in g.groupby('end_cycle'):
                for population,part in [('common_cells',sub.loc[sub.cell_id.isin(common_ids)]),('all_valid',sub),('curve_review_excluded',sub.loc[~sub.delta_curve_review])]:
                    p=part.loc[np.isfinite(part[feat])&np.isfinite(part.cycle_life)&part.cycle_life.gt(0)]
                    for method in ['pearson','spearman']:
                        value=p[feat].corr(p.cycle_life,method=method) if len(p)>=5 and p[feat].nunique()>1 and p.cycle_life.nunique()>1 else np.nan
                        stats.append({'batch':b,'feature':feat,'end_cycle':end,'population':population,'method':method,'n':len(p),'correlation':value})
    return f,pd.DataFrame(audit),pd.DataFrame(stats),selected,pd.DataFrame(fits),pd.concat(curve_rows,ignore_index=True),pd.concat(review_samples,ignore_index=True) if review_samples else pd.DataFrame(columns=['batch','cell_id','cycle','voltage','Qdlin','range_review'])


def figure_window_relationship(features,stats,kind,zoom=False):
    fig,axes=plt.subplots(3,3,figsize=(17,12))
    for i,end in enumerate(ENDS):
        for j,b in enumerate(BATCHES):
            ax=axes[i,j];g=features.loc[features.batch.eq(b)&features.end_cycle.eq(end)]
            g=g.loc[np.isfinite(g.cycle_life)&g.cycle_life.gt(0)]
            feat='deltaQ_var' if kind=='delta' else 'QD_slope_retained'
            for group,color in zip(GROUPS,GROUP_COLORS):
                sub=g.loc[g.life_group.eq(group)];ax.scatter(sub[feat],sub.cycle_life,color=color,s=22,alpha=.65)
            if kind=='delta':
                ax.set_xscale('log');vals=features.loc[(~features.delta_curve_review if zoom else True)&features.deltaQ_var.gt(0),'deltaQ_var']
                ax.set_xlim(vals.min()*.7,vals.max()*1.4)
                lo,hi=ax.get_xlim();outside=~g.deltaQ_var.between(lo,hi)
                ax.text(.02,.03,f'Outside view: {outside.sum()}',transform=ax.transAxes,fontsize=8)
                for r in g.loc[g.delta_curve_review].itertuples():
                    if not zoom:ax.annotate(f'cell {r.cell_id}: curve review',(r.deltaQ_var,r.cycle_life),xytext=(-110,12),textcoords='offset points',fontsize=7)
            else:
                changed=~np.isclose(g.QD_slope_retained,g.QD_slope_masked,rtol=1e-8,atol=1e-12)
                for r in g.loc[changed].itertuples():
                    ax.plot([r.QD_slope_retained,r.QD_slope_masked],[r.cycle_life]*2,color='tab:red',lw=.7)
                    ax.scatter(r.QD_slope_masked,r.cycle_life,marker='x',color='tab:red',s=35)
                    ax.annotate(str(r.cell_id),(r.QD_slope_masked,r.cycle_life),fontsize=7)
                v=features[['QD_slope_retained','QD_slope_masked']].to_numpy().ravel();v=v[np.isfinite(v)]
                margin=(v.max()-v.min())*.08;ax.set_xlim(v.min()-margin,v.max()+margin)
            st=stats.loc[stats.batch.eq(b)&stats.end_cycle.eq(end)&stats.feature.eq(feat)&stats.population.eq('common_cells')].set_index('method')
            desc=f'P={st.at["pearson","correlation"]:.2f}, rho={st.at["spearman","correlation"]:.2f}, n={st.at["pearson","n"]}'
            if kind=='slope':
                s=stats.loc[stats.batch.eq(b)&stats.end_cycle.eq(end)&stats.feature.eq('QD_slope_masked')&stats.population.eq('common_cells')].set_index('method')
                desc+=f'\nmasked: P={s.at["pearson","correlation"]:.2f}, rho={s.at["spearman","correlation"]:.2f}'
            ax.set(title=f'{b} · cycles 10–{end}\n{desc}',xlabel='Variance of delta-Q (Ah²; log axis)' if kind=='delta' else 'Early QD slope (Ah/cycle)',ylabel='Stored cycle life',ylim=(300,2050));ax.grid(alpha=.2)
    fig.suptitle('N07 · '+('Delta-Q variance and life across endpoints'+(' (zoom; original correlations)' if zoom else ' (full range)') if kind=='delta' else 'Early QD slope and life across endpoints'),fontsize=16)
    fig.text(.5,.01,'Correlation uses original values, common valid cells across endpoints. '+('No target prediction or trend fit.' if kind=='delta' else 'Colored dots: retained; red crosses/connections: changed by high-QD masking; labels=cell IDs.'),ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.96));return fig


def figure_all_cell_windows(features):
    fig,axes=plt.subplots(3,3,figsize=(17,11))
    for j,b in enumerate(BATCHES):
        g=features.loc[features.batch.eq(b)]
        for cid,sub in g.groupby('cell_id'):
            sub=sub.sort_values('end_cycle');flag=sub.endpoint_high_QD.any();review=sub.delta_curve_review.any();color='tab:purple' if review else 'tab:red' if flag else '0.6'
            for i,feat in enumerate(['deltaQ_var','QD_slope_retained','QD_slope_masked']):
                axes[i,j].plot(sub.end_cycle,sub[feat],'o-',color=color,alpha=.8 if flag or review else .25,ms=3,lw=.7)
        for i,feat in enumerate(['deltaQ_var','QD_slope_retained','QD_slope_masked']):
            axes[i,j].set(title=f'{b}: all cells n={g.cell_id.nunique()}',xlabel='End cycle (start=10)',ylabel=feat)
            axes[i,j].set_xticks(ENDS);axes[i,j].grid(alpha=.2)
        axes[0,j].set_yscale('log')
    fig.suptitle('N07 · Endpoint sensitivity including unavailable-life cells',fontsize=16)
    fig.text(.5,.01,'Red: high endpoint QD; purple: interpolated curve range review. Detailed delta-Q is unmodified; masking applies only to summary QD slopes.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));return fig


def figure_knee_curves(selected,fits,batch):
    ids=KNEE_CELLS[batch];fig,axes=plt.subplots(3,len(ids),figsize=(6*len(ids),11),squeeze=False)
    for j,cid in enumerate(ids):
        r=selected[(batch,cid)];g=r['frame'];st=fits.loc[fits.batch.eq(batch)&fits.cell_id.eq(cid)&fits.mask_high_QD&fits.median_window.eq(11)&fits.min_span.eq(75)].iloc[0]
        axes[0,j].plot(g.cycle,g.QD,color='0.5',lw=.7,label='Raw QD')
        axes[1,j].plot(g.cycle,g.QD_masked,color='0.7',lw=.7,label='Masked >1.32 Ah')
        axes[1,j].plot(g.cycle,g.smoothed_masked_11,color='tab:blue',lw=1,label='Centered median 11')
        if np.isfinite(st.candidate_cycle):
            x=g.loc[g.cycle.between(st.segment_start,st.segment_end),'cycle'].to_numpy()
            y=st.fit_a+st.fit_b*(x-st.segment_start)+st.fit_c*np.maximum(0,x-st.candidate_cycle)
            axes[1,j].plot(x,y,color='tab:orange',ls='--',lw=1,label='Continuous two-line fit')
            for i in [0,1,2]:axes[i,j].axvline(st.candidate_cycle,color='tab:purple' if st.status=='candidate_passed_heuristic' else '0.4',ls='--',lw=.8)
        for window,color in [(31,'tab:blue'),(75,'tab:orange')]:axes[2,j].plot(g.cycle,g[f'slope_masked_{window}'],color=color,lw=.8,label=f'Local OLS {window}')
        axes[2,j].axhline(0,color='0.5',lw=.5)
        axes[0,j].set_title(f'{batch} cell {cid} · life {r["life"]:g}\n{r["policy"]}',fontsize=9)
        axes[1,j].set_title(f'k={st.candidate_cycle:g} · {st.status}\nSSE improvement={st.relative_sse_improvement:.2f}',fontsize=8)
        axes[1,j].set_ylim(.8,1.15)
        axes[1,j].text(.02,.03,f'Raw points outside zoom: {(~g.QD.between(.8,1.15)).sum()}',transform=axes[1,j].transAxes,fontsize=7)
        for i in range(3):
            ax=axes[i,j];ax.set(xlabel='Stored summary cycle',ylabel='QD (Ah)' if i<2 else 'Local QD slope (Ah/cycle)');ax.grid(alpha=.2);ax.legend(fontsize=6,loc='best')
            if i<2:ax.axhline(.88,color='tab:red',ls=':',lw=.6)
    fig.suptitle(f'N08 · {batch}: retrospective degradation and heuristic knee candidates',fontsize=16)
    fig.text(.5,.01,'Cycles >=10; stop at stored life if known. Default: high QD masked, median 11, min span 75 each side; gray split = unconfirmed. No filling across invalid cycles.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.96));return fig


def figure_knee_sensitivity(fits):
    fig,axes=plt.subplots(1,3,figsize=(18,7));colors={1:'tab:blue',11:'tab:orange',31:'tab:green'}
    for j,b in enumerate(BATCHES):
        g=fits.loc[fits.batch.eq(b)];ids=KNEE_CELLS[b]
        for i,cid in enumerate(ids):
            sub=g.loc[g.cell_id.eq(cid)];passed=sub.loc[sub.status.eq('candidate_passed_heuristic')]
            if len(passed):axes[j].plot([passed.candidate_cycle.min(),passed.candidate_cycle.max()],[i,i],color='0.6',lw=2)
            for k,r in enumerate(sub.itertuples()):
                if np.isfinite(r.candidate_cycle):axes[j].scatter(r.candidate_cycle,i+(k-5.5)*.025,color=colors[r.median_window],marker='x' if r.mask_high_QD else 'o',s=30,alpha=.9 if r.status=='candidate_passed_heuristic' else .2)
            axes[j].text(.98,(i+.5)/len(ids),f'pass {len(passed)}/12',transform=axes[j].transAxes,ha='right',va='center',fontsize=8)
        axes[j].set(ylim=(-.5,len(ids)-.5),xlim=(0,1600),xlabel='Best split / candidate cycle',title=b)
        axes[j].set_yticks(range(len(ids)),[f'cell {cid}' for cid in ids]);axes[j].grid(alpha=.2)
    from matplotlib.lines import Line2D
    handles=[Line2D([],[],marker='o',ls='',color=c,label=f'Median {w}') for w,c in colors.items()]
    handles +=[Line2D([],[],marker='o',ls='',color='0.4',label='High QD retained'),Line2D([],[],marker='x',ls='',color='0.4',label='High QD masked')]
    fig.legend(handles=handles,loc='lower center',ncol=5,fontsize=9)
    fig.suptitle('N08 · Knee sensitivity: 12 configurations per selected cell',fontsize=16)
    fig.text(.5,.055,'Minimum span 30/75; faint points = best split failed acceleration/SSE heuristic. Gray range uses passed candidates only. Missing fits are not fabricated.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.1,1,.94));return fig


def figure_curve_review(samples):
    keys=samples[['batch','cell_id']].drop_duplicates()
    fig,axes=plt.subplots(len(keys),2,figsize=(13,5*len(keys)),squeeze=False)
    for i,key in enumerate(keys.itertuples(index=False)):
        g=samples.loc[samples.batch.eq(key.batch)&samples.cell_id.eq(key.cell_id)]
        for cycle,sub in g.groupby('cycle'):
            for j in [0,1]:axes[i,j].plot(sub.voltage,sub.Qdlin,label=f'cycle {cycle}'+(' · review' if sub.range_review.any() else ''),lw=.8)
        for j in [0,1]:
            axes[i,j].set(title=f'{key.batch} cell {key.cell_id}: '+('full interpolated range' if j==0 else 'zoom (all curves retained)'),xlabel='Stored Vdlin',ylabel='Stored Qdlin');axes[i,j].grid(alpha=.2);axes[i,j].legend(fontsize=8)
        axes[i,1].set_ylim(-.05,1.2)
    fig.suptitle('N07 · Interpolated curve range review',fontsize=16)
    fig.text(.5,.01,'Review only: Qdlin min < -0.05 Ah or max >1.2 x detailed max Qd. No curve replacement; finite grid and Qd-summary alignment alone do not ensure Qdlin quality.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.95));return fig


def save_tables(output_dir,features,audit,stats,fits,curves,review_samples):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    for name,frame in [('endpoint_features.csv',features),('endpoint_alignment_audit.csv',audit),('endpoint_correlations.csv',stats),('knee_candidates.csv',fits),('selected_degradation_curves.csv',curves),('curve_review_samples.csv',review_samples)]:frame.to_csv(out/name,index=False)
