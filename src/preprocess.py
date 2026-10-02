"""Reversible quality flags and QD/IR analysis views; no target rewriting."""
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

KEYS = ['batch', 'cell_id']


@dataclass(frozen=True)
class QualityConfig:
    nominal_capacity_ah: float = 1.1
    eol_fraction: float = 0.8
    high_qd_factor: float = 1.2
    mask_high_qd: bool = False

    def __post_init__(self):
        if not np.isfinite(self.nominal_capacity_ah) or self.nominal_capacity_ah <= 0:
            raise ValueError('nominal_capacity_ah must be finite and positive')
        if not 0 < self.eol_fraction < 1:
            raise ValueError('eol_fraction must be within (0, 1)')
        if not np.isfinite(self.high_qd_factor) or self.high_qd_factor <= 1:
            raise ValueError('high_qd_factor must be finite and greater than 1')


def prepare_summary(summary, config=None):
    """Preserve all rows/raw columns; flag issues and add per-variable views.

    QD nonfinite/nonpositive is masked for QD curves; IR nonfinite/nonpositive
    is masked for IR analysis. High QD is a heuristic flag, opt-in mask only.
    Low positive QD, missing labels and post-label rows are NOT removed.
    """
    config = config or QualityConfig()
    required = [*KEYS, 'cycle', 'cycle_life', 'QD', 'QC', 'IR',
                'Tavg', 'Tmax', 'Tmin', 'chargetime']
    missing = set(required) - set(summary)
    if missing:
        raise ValueError(f'Missing summary fields: {sorted(missing)}')
    out = summary.copy(deep=True)
    out['flag_cycle_invalid'] = (~np.isfinite(out.cycle) | out.cycle.le(0)
                                 | out.cycle.ne(np.floor(out.cycle)))
    out['flag_cycle_duplicate'] = out.duplicated([*KEYS, 'cycle'], keep=False)
    out['flag_life_invalid'] = ~np.isfinite(out.cycle_life) | out.cycle_life.le(0)
    out['flag_after_life'] = ~out.flag_life_invalid & out.cycle.gt(out.cycle_life)
    out['flag_qd_invalid'] = ~np.isfinite(out.QD) | out.QD.le(0)
    out['flag_qd_high'] = np.isfinite(out.QD) & out.QD.gt(
        config.nominal_capacity_ah * config.high_qd_factor)
    out['flag_ir_invalid'] = ~np.isfinite(out.IR) | out.IR.le(0)
    measured = ['QD', 'QC', 'IR', 'Tavg', 'Tmax', 'Tmin', 'chargetime']
    out['flag_all_measurements_zero'] = out[measured].eq(0).all(axis=1)
    cycle_bad = out.flag_cycle_invalid | out.flag_cycle_duplicate
    out['QD_analysis'] = out.QD.mask(cycle_bad | out.flag_qd_invalid |
                                    (out.flag_qd_high & config.mask_high_qd))
    out['IR_analysis'] = out.IR.mask(cycle_bad | out.flag_ir_invalid)
    out.attrs['quality_config'] = asdict(config)
    return out


def cell_diagnostics(cells, prepared, config=None):
    """Summarize flags and threshold observations, keeping all original cells."""
    config = config or QualityConfig()
    if cells.duplicated(KEYS).any():
        raise ValueError('Cell metadata keys must be unique')
    rows = []
    threshold = config.nominal_capacity_ah * config.eol_fraction
    for (batch, cid), frame in prepared.groupby(KEYS, sort=False):
        ordered = frame.sort_values('cycle', kind='stable')
        finite_cycle = ordered.loc[np.isfinite(ordered.cycle), 'cycle']
        valid = ordered.loc[ordered.QD_analysis.notna() & ~ordered.flag_cycle_invalid
                            & ~ordered.flag_cycle_duplicate]
        crossing = valid.loc[valid.QD_analysis.le(threshold)]
        row = {'batch': batch, 'cell_id': cid, 'raw_rows': len(frame),
               'qd_masked_rows': int(frame.QD_analysis.isna().sum()),
               'ir_masked_rows': int(frame.IR_analysis.isna().sum()),
               'cycle_max': finite_cycle.max() if len(finite_cycle) else np.nan,
               'last_valid_QD': valid.QD_analysis.iloc[-1] if len(valid) else np.nan,
               'first_observed_cycle_le_eol': crossing.cycle.iloc[0] if len(crossing) else np.nan}
        for field in [k for k in prepared if k.startswith('flag_')]:
            row[field + '_rows'] = int(frame[field].sum())
        rows.append(row)
    result = cells.merge(pd.DataFrame(rows), on=KEYS, how='left', validate='one_to_one')
    result['record_end_minus_life'] = result.cycle_max - result.cycle_life
    result['crossing_minus_life'] = result.first_observed_cycle_le_eol - result.cycle_life
    result['eol_threshold_ah'] = threshold
    # Missing observed crossing is NOT treated as missing life or extrapolated.
    return result


def representative_cells(cells):
    """Pick the cell closest to each lifetime group's median; no fake fallback."""
    valid = cells.loc[np.isfinite(cells.cycle_life) & cells.cycle_life.gt(0)].copy()
    valid['life_group'] = np.select(
        [valid.cycle_life.lt(500), valid.cycle_life.gt(1000)],
        ['short (<500)', 'long (>1000)'], default='medium (500–1000)')
    picks = []
    for group in ['short (<500)', 'medium (500–1000)', 'long (>1000)']:
        sub = valid.loc[valid.life_group.eq(group)].copy()
        if sub.empty:
            continue
        median = sub.cycle_life.median()
        sub['distance_to_group_median'] = (sub.cycle_life - median).abs()
        pick = sub.sort_values(['distance_to_group_median', 'cell_id']).iloc[0]
        picks.append({'batch': pick.batch, 'cell_id': pick.cell_id,
                      'cycle_life': pick.cycle_life, 'life_group': group,
                      'group_cell_count': len(sub), 'group_median_life': median})
    return pd.DataFrame(picks, columns=[*KEYS, 'cycle_life', 'life_group',
                                       'group_cell_count', 'group_median_life'])
