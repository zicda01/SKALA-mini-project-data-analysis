"""Build unscaled DAY2 cell tables and freeze protocol-group splits.

Run from project root: python -m src.day2_dataset
Reuses audited DAY1 features; never changes raw files or lifetime labels.
"""
from pathlib import Path
from src.day2_evaluation_common import PROJECT_ROOT
import hashlib
import importlib.metadata
import json
import platform

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

KEYS = ['batch', 'cell_id']
F1 = ['log10_deltaQ_var']
F2 = [*F1, 'QD_slope_masked']
TARGET = 'cycle_life'
BATCH1_UNCERTAIN_IDS = {0, 1, 2, 3, 4, 8, 10, 12, 13, 22}
SOURCES = {
    'gallery': PROJECT_ROOT / 'outputs/figures/question_gallery/cell_features_for_gallery.csv',
    'quality': PROJECT_ROOT / 'outputs/figures/quality_sensitivity/early_qd_sensitivity.csv',
    'audit': PROJECT_ROOT / 'outputs/tables/day2/data_audit/cell_audit.csv',
}
DATA_DIR = PROJECT_ROOT / 'data/processed/day2'
TABLE_DIR = PROJECT_ROOT / 'outputs/tables/day2/dataset'


def check_keys(frame, name):
    if frame[KEYS].isna().any().any() or frame.duplicated(KEYS).any():
        raise ValueError(f'{name}: missing or duplicate cell keys')


def check_sources(gallery, quality, audit):
    """Reject partial/stale sources instead of silently dropping or mismatching cells."""
    for name, frame in [('gallery', gallery), ('quality', quality), ('audit', audit)]:
        check_keys(frame, name)
    for name, frame in [('gallery', gallery), ('quality', quality)]:
        comparison = audit[KEYS + [TARGET]].merge(frame[KEYS + [TARGET]], on=KEYS,
            how='outer', suffixes=('_audit', '_source'), validate='one_to_one', indicator=True)
        if not comparison['_merge'].eq('both').all():
            raise ValueError(f'{name}: different cell coverage from audit')
        if not np.allclose(comparison.cycle_life_audit, comparison.cycle_life_source, rtol=0, atol=0, equal_nan=True):
            raise ValueError(f'{name}: lifetime labels disagree with audit')
        if 'charging_policy' in frame:
            policies = audit[KEYS + ['charging_policy']].merge(frame[KEYS + ['charging_policy']], on=KEYS,
                suffixes=('_audit','_source'), validate='one_to_one')
            if not policies.charging_policy_audit.eq(policies.charging_policy_source).all():
                raise ValueError(f'{name}: charging policies disagree with audit')
    if audit.barcode_key.isna().any() or audit.barcode_key.duplicated().any():
        raise ValueError('Physical barcode is missing or repeated across cells')


def build_cell_table(gallery, quality, audit):
    check_sources(gallery, quality, audit)
    base = audit[KEYS + ['barcode_key', 'channel_id_decoded', 'charging_policy', 'protocol_key']].copy()
    base = base.merge(gallery[KEYS + [TARGET, 'deltaQ_var', 'deltaQ_min', 'deltaQ_status',
                                     'peak_positive_I_cycle10', 'early_observed_rows']], on=KEYS, validate='one_to_one')
    base = base.merge(quality[KEYS + ['QD_slope_masked', 'QD_slope_retained', 'n_QD_masked',
                                     'n_QD_retained', 'early_high_QD_rows']], on=KEYS, validate='one_to_one')
    # Pointwise transforms only. No fitted imputation, scaling, or feature selection.
    positive_var = np.isfinite(base.deltaQ_var) & base.deltaQ_var.gt(0)
    base['log10_deltaQ_var'] = np.log10(base.deltaQ_var.where(positive_var))
    base['lifetime_label_valid'] = np.isfinite(base[TARGET]) & base[TARGET].gt(0)
    base['lifetime_label_uncertain'] = base.batch.eq('batch1') & base.cell_id.isin(BATCH1_UNCERTAIN_IDS)
    base['initial_features_valid'] = (base.deltaQ_status.eq('accepted') & positive_var
        & np.isfinite(base.QD_slope_masked) & np.isfinite(base.QD_slope_retained)
        & base.n_QD_masked.ge(5) & base.n_QD_retained.ge(5))
    base['exclusion_reason'] = ''
    base.loc[~base.lifetime_label_valid, 'exclusion_reason'] = 'missing_or_invalid_lifetime_label'
    base.loc[base.lifetime_label_valid & base.lifetime_label_uncertain, 'exclusion_reason'] = 'batch1_incomplete_lifetime_record'
    base.loc[base.lifetime_label_valid & ~base.lifetime_label_uncertain & ~base.initial_features_valid,
             'exclusion_reason'] = 'invalid_initial_feature_definition'
    base['cohort_eligible'] = base.exclusion_reason.eq('')
    base['partition'] = 'excluded'
    base.loc[base.cohort_eligible & base.batch.eq('batch1'), 'partition'] = 'batch1_pending_split'
    base.loc[base.cohort_eligible & base.batch.eq('batch2'), 'partition'] = 'test_batch2'
    base.loc[base.cohort_eligible & base.batch.eq('batch3'), 'partition'] = 'batch3_candidate'
    for col in ['cell_id', 'early_observed_rows', 'n_QD_masked', 'n_QD_retained', 'early_high_QD_rows']:
        base[col] = base[col].astype('int64')
    for col in ['batch', 'barcode_key', 'channel_id_decoded', 'charging_policy', 'protocol_key',
                'deltaQ_status', 'exclusion_reason', 'partition']:
        base[col] = base[col].astype('string')
    return base.sort_values(KEYS).reset_index(drop=True)


def assign_splits(table, seed=42, holdout_group_fraction=.2, n_splits=5):
    """Freeze split membership independent of target values and incoming row order."""
    table = table.sort_values(KEYS).reset_index(drop=True).copy()
    train = table.loc[table.cohort_eligible & table.batch.eq('batch1')].copy()
    if train.protocol_key.nunique() < 3:
        raise ValueError('Too few protocol groups for holdout and CV')
    dev_i, hold_i = next(GroupShuffleSplit(n_splits=1, test_size=holdout_group_fraction,
        random_state=seed).split(train, groups=train.protocol_key))
    dev, hold = train.iloc[dev_i], train.iloc[hold_i]
    if dev.protocol_key.nunique() < n_splits:
        raise ValueError('Too few development protocol groups for requested CV')
    if set(dev.protocol_key) & set(hold.protocol_key):
        raise ValueError('Protocol overlap between development and holdout')
    table.loc[dev.index, 'partition'] = 'development'
    table.loc[hold.index, 'partition'] = 'holdout'
    table['cv_valid_fold'] = pd.Series(pd.NA, index=table.index, dtype='Int64')
    manifests, summaries = [], []
    for fold, (tr_i, va_i) in enumerate(GroupKFold(n_splits=n_splits).split(dev, groups=dev.protocol_key), 1):
        tr, va = dev.iloc[tr_i], dev.iloc[va_i]
        if set(tr.protocol_key) & set(va.protocol_key) or set(tr.barcode_key) & set(va.barcode_key):
            raise ValueError('CV group overlap')
        table.loc[va.index, 'cv_valid_fold'] = fold
        for role, frame in [('train', tr), ('valid', va)]:
            for row in frame.itertuples():
                manifests.append({'fold': fold, 'role': role, 'batch': row.batch, 'cell_id': row.cell_id,
                                  'barcode_key': row.barcode_key, 'protocol_key': row.protocol_key})
        summaries.append({'fold': fold, 'train_n': len(tr), 'valid_n': len(va),
                          'train_protocols': tr.protocol_key.nunique(), 'valid_protocols': va.protocol_key.nunique()})
    if table.loc[table.partition.eq('development'), 'cv_valid_fold'].isna().any():
        raise ValueError('Missing validation fold membership')
    for partition in ['holdout', 'test_batch2', 'batch3_candidate', 'excluded']:
        if table.loc[table.partition.eq(partition), 'cv_valid_fold'].notna().any():
            raise ValueError(f'{partition} leaked into development CV')
    return table, pd.DataFrame(manifests), pd.DataFrame(summaries)


def main():
    inputs = {name: pd.read_csv(path) for name, path in SOURCES.items()}
    table, manifest, folds = assign_splits(build_cell_table(**inputs))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    cohorts = {
        'all_cells': table,
        'train_batch1': table.loc[table.partition.isin(['development', 'holdout'])],
        'test_batch2': table.loc[table.partition.eq('test_batch2')],
        'batch3_candidates': table.loc[table.partition.eq('batch3_candidate')],
    }
    for name, frame in cohorts.items():
        path = DATA_DIR / f'{name}.parquet'
        frame.to_parquet(path, index=False, engine='pyarrow')
        pd.testing.assert_frame_equal(frame.reset_index(drop=True), pd.read_parquet(path))
    table.loc[~table.cohort_eligible, KEYS + ['barcode_key', TARGET, 'exclusion_reason']].to_csv(TABLE_DIR/'exclusions.csv', index=False)
    split_cols = KEYS + ['barcode_key', 'protocol_key', 'partition', 'cv_valid_fold']
    table[split_cols].to_csv(TABLE_DIR/'split_assignments.csv', index=False)
    manifest.to_csv(TABLE_DIR/'cv_manifest.csv', index=False)
    folds.to_csv(TABLE_DIR/'cv_summary.csv', index=False)
    counts = table.groupby(['batch', 'partition'], observed=True).size().rename('n').reset_index()
    counts.to_csv(TABLE_DIR/'cohort_counts.csv', index=False)
    metadata = {
        'schema_version': 1, 'created_date': '2026-10-02',
        'sources': {name: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                    for name, path in SOURCES.items()},
        'versions': {name: importlib.metadata.version(name) for name in ['pandas', 'numpy', 'scikit-learn', 'pyarrow']},
        'python': platform.python_version(), 'prediction_cycle': 100, 'feature_window': [10,100],
        'target': TARGET, 'feature_sets': {'F1': F1, 'F2': F2},
        'batch1_excluded_uncertain_ids': sorted(BATCH1_UNCERTAIN_IDS),
        'exclusion_basis': 'DAY2 data audit report: incomplete EOL observations; not an automatic 0.90 Ah filter',
        'split': {'seed':42,'holdout_group_fraction':.2,'cv_folds':5,'group':'protocol_key'},
        'fitted_preprocessing': False, 'models_trained': False,
        'batch3_status': 'candidates only; additional curve-quality review needed before optional evaluation',
        'artifacts': {name: str(DATA_DIR/f'{name}.parquet') for name in cohorts},
        'counts': counts.to_dict(orient='records'),
    }
    (TABLE_DIR/'dataset_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    print(counts.to_string(index=False))
    print(folds.to_string(index=False))
    print('Parquet round-trips checked. No models, imputation, or scaling fitted.')


if __name__ == '__main__':
    main()
