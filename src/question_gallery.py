"""A neutral nine-figure gallery for the five assignment questions.

No cell/feature ranking or model decision is produced. Raw summary columns
are retained; only nonpositive/nonfinite QD/IR are masked in analysis views.
Detailed cycle positions must match summary QD maxima before being used.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.lines import Line2D

from src.load_data import BATCH_FILES, batch_path, load_batch, load_cycle_fields
from src.preprocess import prepare_summary, QualityConfig

BATCH_NAMES = list(BATCH_FILES)
EARLY_START, EARLY_END = 10, 100
FEATURES = ['mean_QD', 'std_QD', 'delta_QD', 'QD_slope', 'mean_IR',
            'delta_IR', 'mean_Tavg', 'mean_Tmax', 'mean_Tmin',
            'mean_chargetime', 'deltaQ_var', 'deltaQ_min']
GROUPS = ['short (<500)', 'medium (500–1000)', 'long (>1000)', 'unavailable life']
GROUP_COLORS = ['tab:orange', '0.55', 'tab:blue', '0.8']


def life_group(life):
    if not np.isfinite(life) or life <= 0:
        return GROUPS[3]
    return GROUPS[0] if life < 500 else GROUPS[2] if life > 1000 else GROUPS[1]


def build_gallery_data(data_dir):
    """Read three summaries plus cycles 10/100 only; return figures' inputs/audit."""
    batches, feature_rows, curves, audit = {}, [], [], []
    for name in BATCH_NAMES:
        path = batch_path(name, data_dir)
        cells, raw, quality = load_batch(path, name)
        prepared = prepare_summary(raw)
        batches[name] = (cells, prepared)
        for cell in cells.itertuples():
            frame = prepared.loc[prepared.cell_id.eq(cell.cell_id)].sort_values('cycle')
            early = frame.loc[frame.cycle.between(EARLY_START, EARLY_END)]
            row = {'batch': name, 'cell_id': cell.cell_id, 'cycle_life': cell.cycle_life,
                   'life_group': life_group(cell.cycle_life),
                   'early_observed_rows': len(early),
                   'early_high_QD_rows': int(early.flag_qd_high.sum())}
            for source, label in [('QD_analysis', 'QD'), ('IR_analysis', 'IR'),
                                  ('Tavg', 'Tavg'), ('Tmax', 'Tmax'), ('Tmin', 'Tmin'),
                                  ('chargetime', 'chargetime')]:
                vals = early[source].replace([np.inf, -np.inf], np.nan)
                row[f'mean_{label}'] = vals.mean()
                row[f'n_{label}'] = int(vals.notna().sum())
            valid_qd = early.loc[early.QD_analysis.notna()]
            row['std_QD'] = valid_qd.QD_analysis.std()
            row['QD_slope'] = np.polyfit(valid_qd.cycle, valid_qd.QD_analysis, 1)[0] if len(valid_qd) >= 5 else np.nan
            # Differences require both exact endpoints, not nearest available cycles.
            for source, label in [('QD_analysis', 'QD'), ('IR_analysis', 'IR')]:
                ends = frame.loc[frame.cycle.isin([EARLY_START, EARLY_END])].set_index('cycle')
                row[f'delta_{label}'] = (ends.at[EARLY_END, source] - ends.at[EARLY_START, source]
                                       if EARLY_START in ends.index and EARLY_END in ends.index else np.nan)
            delta_arrays = []
            cycle10 = None
            issues = []
            for cycle in [EARLY_START, EARLY_END]:
                positions = np.flatnonzero(frame.cycle.to_numpy() == cycle)
                if len(positions) != 1 or not quality.loc[quality.cell_id.eq(cell.cell_id), 'cycle_lengths_match_summary'].iloc[0]:
                    issues.append(f'cycle {cycle}: ambiguous/missing positional mapping')
                    continue
                index = int(positions[0])
                fields = ('Qdlin', 'Qd', 'I') if cycle == EARLY_START else ('Qdlin', 'Qd')
                detail = load_cycle_fields(path, cell.cell_id, index, fields)
                expected = float(frame.iloc[index].QD)
                observed = np.max(detail['Qd']) if len(detail['Qd']) else np.nan
                # Confirm the actual discharge content aligns with the summary.
                matched = np.isfinite(observed) and np.isclose(observed, expected, rtol=1e-6, atol=1e-7)
                audit.append({'batch': name, 'cell_id': cell.cell_id, 'cycle': cycle,
                              'storage_index': index, 'summary_QD': expected,
                              'detail_Qd_max': observed, 'QD_alignment_passed': bool(matched)})
                if not matched:
                    issues.append(f'cycle {cycle}: summary QD / detailed Qd mismatch')
                    continue
                q, v = detail['Qdlin'], detail['Vdlin']
                if (len(q) != len(v) or len(v) < 2 or not np.isfinite(q).all()
                        or not np.isfinite(v).all() or not (np.diff(v) < 0).all()):
                    issues.append(f'cycle {cycle}: invalid voltage/capacity grid')
                    continue
                delta_arrays.append((v, q))
                if cycle == EARLY_START:
                    cycle10 = detail
            row['peak_positive_I_cycle10'] = np.nan
            if cycle10 is not None:
                current = cycle10['I']
                current = current[np.isfinite(current) & (current > 0)]
                row['peak_positive_I_cycle10'] = current.max() if len(current) else np.nan
            for key in ['deltaQ_mean', 'deltaQ_var', 'deltaQ_min', 'deltaQ_abs_mean']:
                row[key] = np.nan
            if len(delta_arrays) == 2 and not issues:
                v10, q10 = delta_arrays[0]
                v100, q100 = delta_arrays[1]
                if np.array_equal(v10, v100):
                    delta = q100 - q10
                    row.update(deltaQ_mean=delta.mean(), deltaQ_var=delta.var(),
                               deltaQ_min=delta.min(), deltaQ_abs_mean=np.abs(delta).mean())
                    curves.append({'batch': name, 'cell_id': cell.cell_id,
                                   'life_group': row['life_group'], 'voltage': v10, 'delta': delta})
                else:
                    issues.append('voltage grids do not match')
            row['deltaQ_status'] = '; '.join(issues) if issues else 'accepted'
            feature_rows.append(row)
    return batches, pd.DataFrame(feature_rows), curves, pd.DataFrame(audit)


def _title(fig, title, note):
    fig.suptitle(title, fontsize=15)
    fig.text(.5, .01, note, ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .045, 1, .95))


def _life_norm(batches):
    values = pd.concat([v[0].cycle_life for v in batches.values()])
    values = values[np.isfinite(values) & values.gt(0)]
    return Normalize(values.min(), values.max())


def figure_life_distribution(batches):
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    bins = np.linspace(150, 2300, 23)
    for col, name in enumerate(BATCH_NAMES):
        c, _ = batches[name]
        valid = c.loc[np.isfinite(c.cycle_life) & c.cycle_life.gt(0)]
        life = valid.cycle_life
        ax = axes[0, col]
        ax.hist(life, bins=bins, edgecolor='white')
        ax.set(xlim=(150, 2300), title=f'{name}: known life n={len(life)}; unavailable={len(c)-len(life)}',
               xlabel='Stored cycle life', ylabel='Cell count')
        ax.text(.98, .94, f'Outside range: {(~life.between(150, 2300)).sum()}',
                ha='right', va='top', transform=ax.transAxes, fontsize=9)
        ax = axes[1, col]
        ax.boxplot(life, vert=False, tick_labels=[name], showfliers=False)
        offsets = np.linspace(-.15, .15, len(valid))
        ax.scatter(life, 1 + offsets, s=15, alpha=.6)
        q1, q3 = life.quantile([.25, .75]); iqr = q3 - q1
        outliers = valid.loc[(life < q1 - 1.5 * iqr) | (life > q3 + 1.5 * iqr)]
        if len(outliers):
            mask = valid.index.isin(outliers.index)
            ax.scatter(life[mask], 1 + offsets[mask], s=35, facecolors='none',
                       edgecolors='tab:red', linewidths=.8)
            ids = [str(v) for v in outliers.cell_id]
            lines = [', '.join(ids[i:i+4]) for i in range(0, len(ids), 4)]
            ax.text(.98, .95, 'IQR-flagged cell IDs:\n' + '\n'.join(lines),
                    transform=ax.transAxes, ha='right', va='top', fontsize=8)
        ax.set_ylim(.5, 2.0)
        ax.set(xlim=(150, 2300), xlabel='Stored cycle life', title='Box plot + individual cells; IQR rule labels')
    _title(fig, 'Q1 · Cycle-life distributions', 'Shared bins/range 150–2300; unavailable/nonpositive life omitted only from life plots. IQR flags are descriptive.')
    return fig


def figure_group_ratios(batches):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, name in zip(axes, BATCH_NAMES):
        c, _ = batches[name]
        counts = c.cycle_life.map(life_group).value_counts().reindex(GROUPS, fill_value=0)
        bars = ax.bar(range(4), counts / len(c) * 100, color=GROUP_COLORS)
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                    f'n={count}\n{count/len(c):.1%}', ha='center', fontsize=9)
        ax.set(ylim=(0, 100), title=f'{name}: total n={len(c)}', ylabel='Share of all cell entries (%)')
        ax.set_xticks(range(4), ['<500', '500–1000', '>1000', 'Unavailable'])
    _title(fig, 'Q1 · Lifetime-group proportions', 'Denominator includes all original cell entries; 500 and 1000 belong to the middle group.')
    return fig


def figure_degradation(batches):
    fig, axes = plt.subplots(3, 3, figsize=(15, 11))
    norm = _life_norm(batches); cmap = plt.get_cmap('viridis')
    for col, name in enumerate(BATCH_NAMES):
        cells, summary = batches[name]
        for _, frame in summary.groupby('cell_id'):
            frame = frame.sort_values('cycle'); life = frame.cycle_life.iloc[0]
            color = cmap(norm(life)) if np.isfinite(life) and life > 0 else '0.65'
            for row in [0, 1, 2]:
                sub = frame if row != 1 else frame.loc[frame.cycle.between(1, 100)]
                axes[row, col].plot(sub.cycle, sub.QD_analysis, color=color, linewidth=.7, alpha=.7)
        for row in [0, 1, 2]:
            view_name = ['full record', 'cycles 1–100', 'full record; capacity zoom'][row]
            axes[row, col].set(title=f'{name}: {view_name}',
                              xlabel='Stored summary cycle', ylabel='Discharge capacity (Ah)')
            axes[row, col].grid(alpha=.2)
            if row == 2:
                axes[row, col].set_ylim(.8, 1.15)
                outside = (summary.QD_analysis.notna() & ~summary.QD_analysis.between(.8, 1.15)).sum()
                axes[row, col].text(.02, .03, f'Outside displayed y-range: {outside} points',
                                   transform=axes[row, col].transAxes, fontsize=8)
    _title(fig, 'Q2 · Discharge-capacity trajectories', 'Only nonpositive/nonfinite QD masked. Positive spikes/post-life records retained. Bottom row zooms to 0.8–1.15 Ah, with off-scale count; gray = unavailable life.')
    fig.subplots_adjust(right=.9, wspace=.3)
    cax = fig.add_axes([.92, .17, .012, .65])
    fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, label='Stored cycle life (shared color scale)')
    return fig


def figure_delta_curves(curves):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
    for ax, name in zip(axes, BATCH_NAMES):
        for group, color in zip(GROUPS, GROUP_COLORS):
            members = [r for r in curves if r['batch'] == name and r['life_group'] == group]
            for r in members:
                ax.plot(r['voltage'], r['delta'], color=color, alpha=.25, linewidth=.6)
            if members:
                v0 = members[0]['voltage']
                if all(np.array_equal(r['voltage'], v0) for r in members):
                    median = np.median(np.stack([r['delta'] for r in members]), axis=0)
                    ax.plot(v0, median, color=color, linewidth=2, label=f'{group}: n={len(members)}')
                else:
                    ax.plot([], [], color=color, label=f'{group}: n={len(members)}; no median')
            else:
                ax.plot([], [], color=color, linestyle=':', label=f'{group}: n=0')
        ax.axhline(0, color='0.3', linewidth=.7)
        ax.set(title=name, xlabel='Voltage (V)', ylabel='Q100(V) − Q10(V) (Ah)')
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    _title(fig, 'Q3 · Delta-Q(V) curves', 'Thin lines = individual cells; thick lines = group medians. Only aligned, finite curves included; empty groups remain empty.')
    return fig


def figure_delta_variance(features):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharex=True, sharey=True)
    for ax, name in zip(axes, BATCH_NAMES):
        sub = features.loc[features.batch.eq(name)]
        pairs = sub.loc[np.isfinite(sub.deltaQ_var) & sub.deltaQ_var.gt(0) &
                        np.isfinite(sub.cycle_life) & sub.cycle_life.gt(0)]
        for group, color in zip(GROUPS[:3], GROUP_COLORS[:3]):
            group_data = pairs.loc[pairs.life_group.eq(group)]
            ax.scatter(group_data.deltaQ_var, group_data.cycle_life, color=color, s=25,
                       alpha=.75, label=f'{group}: n={len(group_data)}')
        ax.set(xscale='log', title=f'{name}: usable n={len(pairs)} / {len(sub)}',
               xlabel='Variance of delta-Q(V) (Ah²; log axis)', ylabel='Stored cycle life')
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    _title(fig, 'Q3 · Delta-Q(V) variance and cycle life', 'Variance uses all valid voltage points (ddof=0). Zero variance and unavailable life omitted; no fitted trend.')
    return fig


def figure_policy(batches):
    fig, axes = plt.subplots(1, 3, figsize=(19, 12), sharex=True)
    for ax, name in zip(axes, BATCH_NAMES):
        cells, _ = batches[name]
        valid = cells.loc[np.isfinite(cells.cycle_life) & cells.cycle_life.gt(0)]
        policies = sorted(cells.charging_policy.unique())
        for y, policy in enumerate(policies):
            life = valid.loc[valid.charging_policy.eq(policy), 'cycle_life']
            if len(life):
                ax.scatter(life, np.full(len(life), y), color='tab:blue', alpha=.4, s=14)
                ax.errorbar(life.mean(), y, xerr=life.std() if len(life)>1 else 0,
                            color='0.15', marker='D', markersize=4, capsize=2)
            ax.text(1.01, y, f'n={len(life)}', transform=ax.get_yaxis_transform(),
                    va='center', fontsize=8)
        ax.set_yticks(range(len(policies)), policies, fontsize=8)
        ax.set(title=name, xlabel='Stored cycle life')
        ax.set_xlim(0, 2300)
        ax.invert_yaxis(); ax.grid(axis='x', alpha=.2)
    _title(fig, 'Q4 · Cycle life by charging policy', 'Points = individual cells; diamond = mean; whisker = ±1 sample SD (not a confidence interval). Labels show known-life n; n=0 retained.')
    return fig


def figure_charging(features):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for col, name in enumerate(BATCH_NAMES):
        sub = features.loc[features.batch.eq(name)]
        for row, x, y, xlabel, ylabel in [
            (0, 'mean_chargetime', 'cycle_life', 'Mean stored chargetime (cycles 10–100; native units)', 'Stored cycle life'),
            (1, 'peak_positive_I_cycle10', 'QD_slope', 'Peak positive stored I (cycle 10; native units)', 'QD slope (cycles 10–100; Ah/cycle)')]:
            pairs = sub.loc[np.isfinite(sub[x]) & np.isfinite(sub[y])]
            if y == 'cycle_life': pairs = pairs.loc[pairs[y].gt(0)]
            for group, color in zip(GROUPS, GROUP_COLORS):
                g = pairs.loc[pairs.life_group.eq(group)]
                axes[row,col].scatter(g[x], g[y], color=color, s=20, alpha=.7)
            axes[row,col].set(title=f'{name}: pairwise n={len(pairs)}', xlabel=xlabel, ylabel=ylabel)
            axes[row,col].grid(alpha=.2)
    handles=[Line2D([],[],marker='o',linestyle='',color=color,label=group)
             for group,color in zip(GROUPS,GROUP_COLORS)]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5,.945), ncol=4, fontsize=9)
    _title(fig, 'Q4 · Charging measures, lifetime, and early capacity slope', 'I and chargetime units/aggregation are kept in native form; no conversion to amperes or full-charge minutes assumed. Positive QD spikes retained.')
    fig.subplots_adjust(top=.85, hspace=.5)
    return fig


def figure_target_correlations(features):
    fig, axes = plt.subplots(1, 3, figsize=(12, 9), sharey=True)
    for ax, name in zip(axes, BATCH_NAMES):
        sub = features.loc[features.batch.eq(name) & np.isfinite(features.cycle_life) & features.cycle_life.gt(0)]
        values = np.full((len(FEATURES), 2), np.nan); counts = []
        for i, feature in enumerate(FEATURES):
            pair = sub[[feature,'cycle_life']].replace([np.inf,-np.inf],np.nan).dropna()
            counts.append(len(pair))
            if len(pair) >= 3 and pair[feature].nunique()>1 and pair.cycle_life.nunique()>1:
                values[i]=[pair[feature].corr(pair.cycle_life,method=m) for m in ['pearson','spearman']]
        cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('0.88')
        im=ax.imshow(values,cmap=cmap,vmin=-1,vmax=1,aspect='auto')
        ax.set_xticks([0,1],['Pearson','Spearman'])
        ax.set_yticks(range(len(FEATURES)),FEATURES,fontsize=9)
        ax.tick_params(axis='y',labelleft=True);ax.set_title(name)
        for i in range(len(FEATURES)):
            for j in range(2):
                label=f'{values[i,j]:.2f}\nn={counts[i]}' if np.isfinite(values[i,j]) else f'NA\nn={counts[i]}'
                ax.text(j,i,label,ha='center',va='center',fontsize=8,
                        color='white' if np.isfinite(values[i,j]) and abs(values[i,j])>.6 else 'black')
    _title(fig,'Q5 · Feature correlations with stored cycle life','Fixed feature order; pairwise complete cells, no imputation. NA = insufficient/constant data; features use cycles 10–100.')
    fig.subplots_adjust(right=.9,wspace=.9)
    cax=fig.add_axes([.92,.17,.015,.65]);fig.colorbar(im,cax=cax,label='Correlation')
    return fig


def figure_feature_correlations(features):
    fig,axes=plt.subplots(1,3,figsize=(20,7))
    for ax,name in zip(axes,BATCH_NAMES):
        sub=features.loc[features.batch.eq(name),FEATURES].replace([np.inf,-np.inf],np.nan)
        corr=sub.corr(method='pearson',min_periods=3)
        cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('0.88')
        im=ax.imshow(corr,cmap=cmap,vmin=-1,vmax=1)
        ax.set_xticks(range(len(FEATURES)),FEATURES,rotation=75,ha='right',fontsize=8)
        ax.set_yticks(range(len(FEATURES)),FEATURES,fontsize=8)
        ax.set_title(f'{name}: all cell entries n={len(sub)}')
    _title(fig,'Q5 · Feature-to-feature correlations','Pearson, pairwise complete observations (minimum n=3), including cells with unavailable life. Cell counts vary by pair; no imputation.')
    fig.subplots_adjust(right=.92,wspace=.5)
    cax=fig.add_axes([.94,.25,.01,.55]);fig.colorbar(im,cax=cax,label='Correlation')
    return fig


FIGURE_SPECS = [
    ('01_q1_cycle_life_distribution.png', 'Q1', 'Cycle-life distribution and box plots', figure_life_distribution, 'batches'),
    ('02_q1_life_group_ratios.png', 'Q1', 'Lifetime-group proportions', figure_group_ratios, 'batches'),
    ('03_q2_degradation_curves.png', 'Q2', 'Full and early discharge-capacity curves', figure_degradation, 'batches'),
    ('04_q3_delta_q_curves.png', 'Q3', 'Delta-Q curves by lifetime group', figure_delta_curves, 'curves'),
    ('05_q3_delta_q_variance.png', 'Q3', 'Delta-Q variance vs lifetime', figure_delta_variance, 'features'),
    ('06_q4_policy_lifetime.png', 'Q4', 'Lifetime by charging policy', figure_policy, 'batches'),
    ('07_q4_charging_relationships.png', 'Q4', 'Charging measures vs lifetime/early slope', figure_charging, 'features'),
    ('08_q5_target_correlations.png', 'Q5', 'Pearson/Spearman correlations with lifetime', figure_target_correlations, 'features'),
    ('09_q5_feature_correlations.png', 'Q5', 'Feature correlation matrices', figure_feature_correlations, 'features'),
]


def save_gallery_figure(spec, inputs, output_dir):
    filename, _, _, function, key = spec
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    fig = function(inputs[key])
    fig.savefig(output_dir / filename, dpi=130, bbox_inches='tight')
    return fig


def save_audit(inputs, output_dir):
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    inputs['audit'].to_csv(output_dir/'cycle_alignment_audit.csv',index=False)
    inputs['features'].to_csv(output_dir/'cell_features_for_gallery.csv',index=False)
    metadata={'early_start':EARLY_START,'early_end':EARLY_END,
              'quality_config': {'mask_high_qd':False,'nonpositive_QD_IR':'masked in analysis columns only'},
              'figures':[{'filename':s[0],'question':s[1],'description':s[2]} for s in FIGURE_SPECS],
              'sources':['https://www.nature.com/articles/s41560-019-0356-8',
                         'https://github.com/rdbraatz/data-driven-prediction-of-battery-cycle-life-before-capacity-degradation'],
              'no_imputation':True,'no_target_recalculation':True,'no_cell_merging':True}
    (output_dir/'gallery_metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
