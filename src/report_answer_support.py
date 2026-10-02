"""Table-only support for DAY1 Q1/Q4, reusing raw data and existing EDA inputs.

Run from project root: python -m src.report_answer_support
No plots, target rewriting, or raw-data mutation. Time/current keep native units.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from src.load_data import BATCH_FILES, batch_path, load_batch, load_cycle_fields

OUT = Path('outputs/tables/day1_answer_support')
PATTERNS = ['peak_I_native', 'mean_positive_I_native', 'positive_duration_native',
            'near_peak_time_share', 'late_minus_early_I_native']


def pattern_metrics(detail):
    """Observed positive-current intervals; no interpolation across gaps/states.

    Early/late halves divide cumulative accepted positive duration, not SOC.
    Near-peak is >=80% of positive peak. State deadband=0.05 native I.
    """
    t, current = detail['t'], detail['I']
    dt = np.diff(t)
    positive_dt = dt[dt > 0]
    gap_limit = 20 * np.median(positive_dt) if len(positive_dt) else np.inf
    gap = dt > gap_limit
    positive = current > .05
    use = (dt > 0) & ~gap & positive[:-1] & positive[1:]
    weights = dt[use]
    midpoint_I = (current[:-1][use] + current[1:][use]) / 2
    duration = weights.sum()
    peak = current[positive].max() if positive.any() else np.nan
    result = {'peak_I_native': peak, 'mean_positive_I_native': np.nan,
              'positive_duration_native': duration, 'near_peak_time_share': np.nan,
              'late_minus_early_I_native': np.nan,
              'positive_intervals_used': int(use.sum()), 'gap_count': int(gap.sum()),
              'excluded_gap_duration_native': float(dt[gap].sum()),
              'record_duration_native': float(t[-1]-t[0])}
    if duration > 0:
        end = np.cumsum(weights); start = end - weights; half = duration / 2
        early_w = np.maximum(0, np.minimum(end, half) - start)
        late_w = weights - early_w
        # Both interval endpoints must satisfy the near-peak criterion.
        high = (current[:-1][use] >= .8 * peak) & (current[1:][use] >= .8 * peak)
        result.update(mean_positive_I_native=float(np.average(midpoint_I, weights=weights)),
                      near_peak_time_share=float(weights[high].sum()/duration),
                      late_minus_early_I_native=float(np.average(midpoint_I, weights=late_w)
                                                     - np.average(midpoint_I, weights=early_w)))
    return result


def correlations(frame, batch, grouping, group):
    rows = []
    for feature in PATTERNS:
        for target in ['QD_slope_masked', 'cycle_life']:
            p = frame[[feature, target]].replace([np.inf, -np.inf], np.nan).dropna()
            if target == 'cycle_life': p = p[p[target] > 0]
            usable = len(p) >= 5 and p[feature].nunique() > 1 and p[target].nunique() > 1
            rows.append({'batch': batch, 'grouping': grouping, 'group': group,
                         'feature': feature, 'target': target, 'n': len(p),
                         'pearson': p[feature].corr(p[target]) if usable else np.nan,
                         'spearman': p[feature].corr(p[target], method='spearman') if usable else np.nan,
                         'status': 'computed' if usable else 'insufficient_or_constant'})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = pd.read_csv('outputs/figures/policy_exploration/policy_features.csv')
    q = pd.read_csv('outputs/figures/quality_sensitivity/early_qd_sensitivity.csv')
    f = f.merge(q[['batch', 'cell_id', 'QD_slope_masked', 'std_QD_masked']],
                on=['batch', 'cell_id'], validate='one_to_one')
    rows = []; knee_rows = []
    from src.preprocess import prepare_summary, QualityConfig
    from src.window_knee_eda import smooth_without_gap_fill, fit_knee
    for batch in BATCH_FILES:
        path = batch_path(batch)
        cells, summary, quality = load_batch(path, batch)
        for cid in cells.cell_id:
            frame = summary[summary.cell_id.eq(cid)]  # original storage order
            pos = np.flatnonzero(frame.cycle.to_numpy() == 10)
            assert len(pos) == 1
            assert quality.loc[quality.cell_id.eq(cid), 'cycle_lengths_match_summary'].iloc[0]
            detail = load_cycle_fields(path, int(cid), int(pos[0]), ('t', 'I', 'V', 'Qc', 'Qd'))
            arrays = list(detail.values())
            assert len({len(a) for a in arrays}) == 1 and len(arrays[0]) > 1
            assert all(np.isfinite(a).all() for a in arrays)
            assert (np.diff(detail['t']) >= 0).all()
            row = frame.iloc[int(pos[0])]
            for source, target in [('Qc', 'QC'), ('Qd', 'QD')]:
                assert np.isclose(detail[source].max(), row[target], rtol=1e-6, atol=1e-7)
            rows.append({'batch': batch, 'cell_id': cid, 'cycle': 10,
                         'storage_index': int(pos[0]), 'samples': len(arrays[0]),
                         'alignment_passed': True, **pattern_metrics(detail)})
        prepared = prepare_summary(summary, QualityConfig(mask_high_qd=True))
        for cell in cells.itertuples():
            g = prepared[prepared.cell_id.eq(cell.cell_id)]
            known_life = np.isfinite(cell.cycle_life) and cell.cycle_life > 0
            g = g[g.cycle.ge(10) & (g.cycle.le(cell.cycle_life) if known_life else True)]
            fit = fit_knee(g.cycle, smooth_without_gap_fill(g.QD_analysis, 11), min_span=75)
            knee_rows.append({'batch':batch, 'cell_id':cell.cell_id, 'cycle_life':cell.cycle_life,
                              'known_life':known_life, 'mask_high_QD':True,
                              'median_window':11,'min_span':75,**fit})
        print(batch, 'cycle 10 validated and default knee explored:', len(cells), flush=True)
    patterns = f.merge(pd.DataFrame(rows), on=['batch', 'cell_id'], validate='one_to_one')
    patterns.to_csv(OUT/'cycle10_pattern_features.csv', index=False)
    pd.DataFrame(knee_rows).to_csv(OUT/'all_cell_default_knee.csv', index=False)
    stats = []
    for batch, g in patterns.groupby('batch'):
        stats.extend(correlations(g, batch, 'all_entries', 'all'))
        known = g[g.cycle_life.notna() & g.cycle_life.gt(0)]
        stats.extend(correlations(known, batch, 'known_life', 'all'))
        stats.extend(correlations(known[known.gap_count.eq(0)], batch, 'known_life_no_time_gap', 'all'))
        for policy, sub in known.groupby('charging_policy'):
            stats.extend(correlations(sub, batch, 'policy_known_life', policy))
    pd.DataFrame(stats).to_csv(OUT/'pattern_correlations.csv', index=False)
    cases = []; contrasts = []; policies = []
    for batch, g in patterns.groupby('batch'):
        v = g[g.cycle_life.notna() & g.cycle_life.gt(0)]
        for policy, group in v.groupby('charging_policy'):
            policies.append({'batch': batch, 'charging_policy': policy, 'n_life': len(group),
                             'life_min': group.cycle_life.min(), 'life_median': group.cycle_life.median(),
                             'life_max': group.cycle_life.max()})
        for _, cell in v.nsmallest(3, 'cycle_life').iterrows():
            peers = v[(v.charging_policy == cell.charging_policy) & (v.cell_id != cell.cell_id)]
            record = cell.to_dict()
            record.update(batch_life_median=v.cycle_life.median(),
                          batch_deltaQ_var_median=v.deltaQ_var.median(),
                          deltaQ_var_to_batch_median=cell.deltaQ_var/v.deltaQ_var.median(),
                          batch_QD_slope_masked_median=v.QD_slope_masked.median(),
                          same_policy_peer_n=len(peers), same_policy_peer_life_median=peers.cycle_life.median(),
                          same_policy_peer_deltaQ_var_median=peers.deltaQ_var.median(),
                          same_policy_peer_QD_slope_masked_median=peers.QD_slope_masked.median())
            cases.append(record)
        if batch == 'batch2':
            for name, sub in [('short_lt500', v[v.cycle_life < 500]),
                              ('nonshort_ge500', v[v.cycle_life >= 500])]:
                record = {'batch': batch, 'group': name, 'n': len(sub)}
                for col in ['cycle_life','deltaQ_var','deltaQ_min','QD_slope_masked',*PATTERNS]:
                    record[col+'_median'] = sub[col].median()
                contrasts.append(record)
    pd.DataFrame(cases).to_csv(OUT/'short_life_case_comparisons.csv', index=False)
    pd.DataFrame(contrasts).to_csv(OUT/'batch2_short_group_comparison.csv', index=False)
    pd.DataFrame(policies).to_csv(OUT/'policy_life_context.csv', index=False)
    metadata = {'created':'2026-10-01','cycle':10,'n_cell_entries':len(patterns),
                'current_state_threshold_native':.05,'near_peak_fraction':.8,
                'gap_rule':'dt >20*median(positive dt)',
                'time_weight':'only intervals with dt>0, no gap, positive I at both endpoints',
                'phase_definition':'first/last half of accepted positive-current duration; not SOC',
                'correlation_minimum_n':5,'no_imputation':True,'no_new_plots':True,
                'scope':'cycle10 proxy pattern features vs early10-100 masked QD slope and stored life',
                'knee_config':{'mask_high_QD':True,'median_window':11,'min_span':75,'known_life_cutoff':True,'single_condition_only':True},
                'limitations':['native units','one representative cycle per entry','observational correlations',
                               'known-life/all-entries and within-policy statistics separated']}
    (OUT/'analysis_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    print('Saved', len(patterns), 'pattern rows and',len(cases),'short-life cases to',OUT)


if __name__ == '__main__':
    main()
