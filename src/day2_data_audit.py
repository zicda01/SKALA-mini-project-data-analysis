"""Read-only DAY2 audit of identities, lifetime consistency, and protocol groups.

Run: python -m src.day2_data_audit
Raw files and DAY1 feature tables are never modified. Crossings are diagnostics,
not replacement lifetime labels; serialized MATLAB string payloads are not IDs.
"""
from pathlib import Path
from src.day2_evaluation_common import PROJECT_ROOT
from itertools import combinations
import hashlib
import json
import re

import h5py
import numpy as np
import pandas as pd

from src.load_data import BATCH_FILES, batch_path, load_batch

OUT = PROJECT_ROOT / 'outputs/tables/day2/data_audit'


def protocol_key(text):
    """Whitespace-only normalization; preserve structure/slow-cycle suffixes."""
    return re.sub(r'\s+', '', str(text))


def decode_dataset_string(file, dataset):
    """Decode only the scalar MCOS string layout observed in these three files.

    This is not a general MATLAB object decoder. Object IDs address MCOS entries
    after two metadata entries; packed UTF-16LE data follows a five-word header.
    Fail on unsupported layouts rather than treating object handles as IDs.
    """
    payload = dataset[()].reshape(-1)
    if dataset.attrs.get('MATLAB_class') != b'string' or payload.dtype != np.dtype('uint32'):
        raise ValueError('Unsupported string object payload')
    if len(payload) != 6 or not np.array_equal(payload[:4], [3707764736, 2, 1, 1]) or payload[5] != 1:
        raise ValueError('Unsupported non-scalar string object')
    refs = file['#subsystem#/MCOS'][()].reshape(-1)
    slot = int(payload[4]) + 1
    if not 2 <= slot < len(refs):
        raise ValueError('Invalid MCOS object ID')
    packed = file[refs[slot]][()].reshape(-1)
    if packed.dtype != np.dtype('uint64') or len(packed) < 5 or not np.array_equal(packed[:4], [1, 2, 1, 1]):
        raise ValueError('Unsupported packed string layout')
    length = int(packed[4])
    raw = np.asarray(packed[5:], dtype='<u8').tobytes()
    if 2 * length > len(raw):
        raise ValueError('Truncated UTF-16 data')
    return raw[:2 * length].decode('utf-16-le')


def first_crossing(frame, threshold):
    eligible = frame.loc[np.isfinite(frame.cycle) & frame.cycle.gt(0)
                         & np.isfinite(frame.QD) & frame.QD.gt(0)]
    cross = eligible.loc[eligible.QD.le(threshold), 'cycle']
    return float(cross.min()) if len(cross) else np.nan


def early_fingerprint(frame):
    """Exact trace equality is evidence of copied records, not an identity decoder."""
    early = frame.loc[frame.cycle.between(10, 100)].sort_values('cycle')
    a = early[['cycle', 'QD', 'QC', 'IR', 'Tavg', 'Tmax', 'Tmin', 'chargetime']].to_numpy(dtype='<f8')
    return hashlib.sha256(a.tobytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, file_rows = [], []
    for batch in BATCH_FILES:
        cells, summary, quality = load_batch(batch_path(batch, PROJECT_ROOT / 'data/raw'), batch)
        with h5py.File(batch_path(batch, PROJECT_ROOT / 'data/raw'), 'r') as raw:
            date = ''.join(chr(int(v)) for v in raw['batch_date'][()].ravel())
            field_info = {}
            decoded = {}
            for field in ['barcode', 'channel_id']:
                refs = raw['batch'][field][()].reshape(-1, order='F')
                classes, dtypes = set(), set()
                decoded[field] = []
                for ref in refs:
                    ds = raw[ref]
                    classes.add(ds.attrs.get('MATLAB_class', b'').decode())
                    dtypes.add(str(ds.dtype))
                    text = decode_dataset_string(raw, ds)
                    pattern = r'(?i)EL\d{12}' if field == 'barcode' else r'\d+'
                    if re.fullmatch(pattern, text) is None:
                        raise ValueError(f'Unexpected {field}: {text!r}')
                    decoded[field].append(text)
                field_info[field] = {'matlab_classes': sorted(classes), 'storage_dtypes': sorted(dtypes),
                                     'identity_decoded': True}
            if len(set(x.upper() for x in decoded['barcode'])) != len(cells):
                raise ValueError(f'Duplicate barcode within {batch}')
        file_rows.append({'batch': batch, 'filename': BATCH_FILES[batch], 'internal_batch_date': date,
                          'n_cells': len(cells), 'identity_fields': field_info})
        for cell in cells.itertuples():
            frame = summary.loc[summary.cell_id.eq(cell.cell_id)].sort_values('cycle')
            valid = frame.loc[np.isfinite(frame.QD) & frame.QD.gt(0)]
            life_valid = bool(np.isfinite(cell.cycle_life) and cell.cycle_life > 0)
            crossing = first_crossing(frame, .88)
            q2 = frame.loc[frame.cycle.eq(2), 'QD']
            ref2 = float(q2.iloc[0]) if len(q2) and np.isfinite(q2.iloc[0]) and q2.iloc[0] > 0 else np.nan
            cross_initial = first_crossing(frame, .8 * ref2) if np.isfinite(ref2) else np.nan
            last = frame.cycle.max()
            initial = frame.loc[frame.cycle.between(10, 100)]
            diag = quality.loc[quality.cell_id.eq(cell.cell_id)].iloc[0]
            status = ('missing_label' if not life_valid else
                      'no_observed_nominal_80pct_crossing' if not np.isfinite(crossing) else
                      'label_equals_first_nominal_80pct_crossing' if crossing == cell.cycle_life else
                      'label_differs_from_first_nominal_80pct_crossing')
            rows.append({'batch': batch, 'cell_id': cell.cell_id, 'cycle_life': cell.cycle_life,
                         'life_valid': life_valid, 'charging_policy': cell.charging_policy,
                         'protocol_key': protocol_key(cell.charging_policy),
                         'barcode_payload': repr(cell.barcode_raw), 'channel_payload': repr(cell.channel_id_raw),
                         'barcode_decoded': decoded['barcode'][cell.cell_id],
                         'barcode_key': decoded['barcode'][cell.cell_id].upper(),
                         'channel_id_decoded': decoded['channel_id'][cell.cell_id],
                         'physical_identity_status': 'decoded_barcode_unique_within_batch',
                         'cycle_min': frame.cycle.min(), 'cycle_max': last, 'summary_rows': len(frame),
                         'last_minus_label': last-cell.cycle_life if life_valid else np.nan,
                         'last_positive_QD': valid.QD.iloc[-1] if len(valid) else np.nan,
                         'terminal_QD_above_0p90_review': bool(len(valid) and valid.QD.iloc[-1] > .90),
                         'first_crossing_QD_le_0p88': crossing, 'cycle2_QD': ref2,
                         'first_crossing_QD_le_80pct_cycle2': cross_initial,
                         'life_audit_status': status,
                         'rows_after_label': int((frame.cycle > cell.cycle_life).sum()) if life_valid else 0,
                         'early_rows_10_100': len(initial),
                         'early_positive_finite_QD_n': int((np.isfinite(initial.QD) & initial.QD.gt(0)).sum()),
                         'early_QD_over_1p32_n': int((np.isfinite(initial.QD) & initial.QD.gt(1.32)).sum()),
                         'cycle_duplicates': diag.cycle_duplicates,
                         'cycle_lengths_match_summary': bool(diag.cycle_lengths_match_summary),
                         'early_trace_sha256': early_fingerprint(frame)})
        print(batch, 'audited', len(cells), flush=True)
    audit = pd.DataFrame(rows)
    audit.to_csv(OUT/'cell_audit.csv', index=False)
    known = audit.loc[audit.life_valid]
    protocol = audit.groupby(['batch', 'protocol_key'], sort=True).agg(
        n_all=('cell_id', 'size'), n_valid_life=('life_valid', 'sum'),
        cell_ids=('cell_id', lambda x: ','.join(map(str, x)))).reset_index()
    protocol.to_csv(OUT/'protocol_counts.csv', index=False)
    overlap, duplicates, payloads, identities = [], [], [], []
    for a, b in combinations(BATCH_FILES, 2):
        ga, gb = audit.loc[audit.batch.eq(a)], audit.loc[audit.batch.eq(b)]
        for scope in ['all_entries', 'valid_life']:
            va = ga if scope == 'all_entries' else ga.loc[ga.life_valid]
            vb = gb if scope == 'all_entries' else gb.loc[gb.life_valid]
            sa, sb = set(va.protocol_key), set(vb.protocol_key)
            overlap.append({'batch_a': a, 'batch_b': b, 'scope': scope,
                            'protocols_a': len(sa), 'protocols_b': len(sb),
                            'shared_protocols': len(sa & sb),
                            'shared_keys': '|'.join(sorted(sa & sb))})
        match = ga.merge(gb, on='early_trace_sha256', suffixes=('_a', '_b'))
        for r in match.itertuples():
            duplicates.append({'batch_a': a, 'cell_a': r.cell_id_a, 'batch_b': b, 'cell_b': r.cell_id_b})
        same_barcode = ga.merge(gb, on='barcode_key')
        identities.append({'batch_a': a, 'batch_b': b, 'shared_barcode_n': len(same_barcode),
                           'shared_barcodes': '|'.join(sorted(set(same_barcode.barcode_key)))})
        for field in ['barcode_payload', 'channel_payload']:
            same = ga.merge(gb, on=field)
            payloads.append({'batch_a': a, 'batch_b': b, 'field': field,
                             'equal_payload_pair_n': len(same), 'usable_as_physical_identity': False})
    pd.DataFrame(overlap).to_csv(OUT/'protocol_overlap.csv', index=False)
    pd.DataFrame(duplicates, columns=['batch_a','cell_a','batch_b','cell_b']).to_csv(OUT/'exact_early_trace_duplicates.csv', index=False)
    pd.DataFrame(payloads).to_csv(OUT/'serialized_payload_overlap.csv', index=False)
    pd.DataFrame(identities).to_csv(OUT/'barcode_overlap.csv', index=False)
    stats=[]
    for batch,g in audit.groupby('batch'):
        k=g.loc[g.life_valid]
        counts=k.groupby('protocol_key').size()
        stats.append({'batch':batch,'n_all':len(g),'n_valid_life':len(k),'n_missing_life':len(g)-len(k),
                      'n_valid_life_no_nominal_crossing':int(k.first_crossing_QD_le_0p88.isna().sum()),
                      'n_valid_life_label_matches_nominal_crossing':int(k.life_audit_status.eq('label_equals_first_nominal_80pct_crossing').sum()),
                      'n_last_equals_life_minus_1':int(k.last_minus_label.eq(-1).sum()),
                      'n_record_after_life':int(k.rows_after_label.gt(0).sum()),
                      'n_known_life_terminal_QD_above_0p90':int(k.terminal_QD_above_0p90_review.sum()),
                      'n_protocols_known_life':len(counts),'protocol_group_min':int(counts.min()),
                      'protocol_group_max':int(counts.max()),
                      'nominal_crossing_without_label_n':int((~g.life_valid & g.first_crossing_QD_le_0p88.notna()).sum())})
    pd.DataFrame(stats).to_csv(OUT/'batch_audit_summary.csv', index=False)
    # A split-feasibility preview only: it is not the approved training cohort.
    from sklearn.model_selection import GroupShuffleSplit, GroupKFold
    b1=known.loc[known.batch.eq('batch1')].reset_index(drop=True)
    dev_idx,hold_idx=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(b1,groups=b1.protocol_key))
    dev,hold=b1.iloc[dev_idx],b1.iloc[hold_idx]
    assert not (set(dev.protocol_key)&set(hold.protocol_key))
    split_rows=[]
    for part,frame in [('development',dev),('holdout',hold)]:
        for row in frame.itertuples():split_rows.append({'batch':row.batch,'cell_id':row.cell_id,'protocol_key':row.protocol_key,'preview_partition':part})
    pd.DataFrame(split_rows).to_csv(OUT/'split_feasibility_preview.csv',index=False)
    folds=[]
    for fold,(train_idx,valid_idx) in enumerate(GroupKFold(n_splits=5).split(dev,groups=dev.protocol_key),1):
        tr,va=dev.iloc[train_idx],dev.iloc[valid_idx]
        assert not (set(tr.protocol_key)&set(va.protocol_key))
        folds.append({'fold':fold,'train_n':len(tr),'valid_n':len(va),'train_protocols':tr.protocol_key.nunique(),'valid_protocols':va.protocol_key.nunique()})
    pd.DataFrame(folds).to_csv(OUT/'cv_feasibility_preview.csv',index=False)
    info={'files':file_rows,'identity_decoder_scope':'observed scalar MCOS UTF-16LE layout only',
          'shared_cross_batch_barcode_n':sum(r['shared_barcode_n'] for r in identities),
          'physical_identity_evidence':'decoded unique barcodes; no assertion about unrecorded relabeling',
          'exact_cross_batch_early_trace_matches':len(duplicates),
          'nominal_crossing_threshold_Ah':.88,'nominal_capacity_reference_Ah':1.1,
          'split_preview':{'seed':42,'test_group_fraction':.2,'development_n':len(dev),'holdout_n':len(hold),
                           'development_protocols':int(dev.protocol_key.nunique()),'holdout_protocols':int(hold.protocol_key.nunique()),
                           'approved_for_training':False}}
    (OUT/'audit_metadata.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    print(pd.DataFrame(stats).to_string(index=False),flush=True)
    print('No labels changed; split preview is not an approved cohort.',flush=True)


if __name__ == '__main__':
    main()
