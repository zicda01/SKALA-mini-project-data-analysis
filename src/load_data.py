"""Selective readers for the battery dataset's MATLAB v7.3 files.

Cell IDs are zero-based positions within a file, not physical battery IDs.
No filtering, cycle renumbering, or missing-value imputation is applied.
"""
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

BATCH_FILES = {
    'batch1': '2017-05-12_batchdata_updated_struct_errorcorrect.mat',
    'batch2': '2018-02-20_batchdata_updated_struct_errorcorrect.mat',
    'batch3': '2018-04-12_batchdata_updated_struct_errorcorrect.mat',
}
SUMMARY_FIELDS = {
    'QDischarge': 'QD', 'QCharge': 'QC', 'IR': 'IR',
    'Tavg': 'Tavg', 'Tmax': 'Tmax', 'Tmin': 'Tmin',
    'chargetime': 'chargetime',
}


def batch_path(batch_name, data_dir='data/raw'):
    """Resolve a registered batch under the caller's project data directory."""
    if batch_name not in BATCH_FILES:
        raise ValueError(f'Unknown batch: {batch_name}; choose {list(BATCH_FILES)}')
    return Path(data_dir) / BATCH_FILES[batch_name]


def _cell_field(file, batch, field, cell_id):
    refs = batch[field][()].reshape(-1, order='F')
    return file[refs[cell_id]]


def _text(dataset):
    return ''.join(chr(int(v)) for v in dataset[()].reshape(-1, order='F'))


def load_batch(path, batch_name):
    """Return (cell metadata, cycle summary, cell quality table).

    Reads only metadata and summary. Summary field lengths must match the
    stored cycle array; malformed structures raise with cell/field context.
    Raw barcode/channel payloads are preserved, not decoded as identities.
    """
    cells, summaries, quality = [], [], []
    with h5py.File(path, 'r') as file:
        batch = file['batch']
        n_cells = batch['cycle_life'].size
        for field in ['cycle_life', 'policy', 'policy_readable', 'summary',
                      'cycles', 'barcode', 'channel_id']:
            if batch[field].size != n_cells:
                raise ValueError(f'{batch_name}: inconsistent cell count for {field}')
        for cell_id in range(n_cells):
            get = lambda field: _cell_field(file, batch, field, cell_id)
            life_values = get('cycle_life')[()].reshape(-1)
            if life_values.size != 1:
                raise ValueError(f'{batch_name}/{cell_id}: non-scalar cycle_life')
            life = float(life_values[0])
            policy = _text(get('policy_readable')) or _text(get('policy'))
            summary = get('summary')
            cycle = summary['cycle'][()].reshape(-1)
            values = {'cycle': cycle}
            for source, target in SUMMARY_FIELDS.items():
                array = summary[source][()].reshape(-1)
                if len(array) != len(cycle):
                    raise ValueError(f'{batch_name}/{cell_id}/{source}: '
                                     f'{len(array)} values vs {len(cycle)} cycles')
                values[target] = array
            frame = pd.DataFrame(values)
            frame.insert(0, 'cell_id', cell_id)
            frame.insert(0, 'batch', batch_name)
            frame['cycle_life'] = life
            frame['charging_policy'] = policy
            summaries.append(frame)
            cycle_fields = get('cycles')
            cycle_lengths = {k: v.size for k, v in cycle_fields.items()}
            cells.append({
                'batch': batch_name, 'cell_id': cell_id, 'cycle_life': life,
                'charging_policy': policy, 'policy_raw': _text(get('policy')),
                'barcode_raw': tuple(get('barcode')[()].reshape(-1).tolist()),
                'channel_id_raw': tuple(get('channel_id')[()].reshape(-1).tolist()),
                'summary_rows': len(cycle),
            })
            finite_cycle = cycle[np.isfinite(cycle)]
            row = {
                'batch': batch_name, 'cell_id': cell_id,
                'cycle_min': finite_cycle.min() if finite_cycle.size else np.nan,
                'cycle_max': finite_cycle.max() if finite_cycle.size else np.nan,
                'cycle_duplicates': int(pd.Series(cycle).duplicated().sum()),
                'cycle_strictly_increasing': bool(np.isfinite(cycle).all()
                                                and np.all(np.diff(cycle) > 0)),
                'cycle_integer_positive': bool(np.isfinite(cycle).all()
                                              and np.all(cycle > 0)
                                              and np.all(cycle == np.floor(cycle))),
                'cycle_field_lengths': str(cycle_lengths),
                'cycle_lengths_match_summary': all(v == len(cycle) for v in cycle_lengths.values()),
                'cycle_life_finite_positive': bool(np.isfinite(life) and life > 0),
            }
            for field in ['cycle', *SUMMARY_FIELDS.values()]:
                a = values[field]
                row[f'{field}_nonfinite'] = int((~np.isfinite(a)).sum())
                row[f'{field}_zero'] = int((a == 0).sum())
            quality.append(row)
    return pd.DataFrame(cells), pd.concat(summaries, ignore_index=True), pd.DataFrame(quality)


def load_cycle_fields(path, cell_id, cycle_index, fields=('Qdlin',)):
    """Read requested arrays at an explicit zero-based storage index.

    The caller must verify how this index maps to an experimental cycle
    number. Equal summary/cycles lengths alone do not prove that mapping.
    """
    with h5py.File(path, 'r') as file:
        batch = file['batch']
        if not isinstance(cell_id, (int, np.integer)) or not 0 <= cell_id < batch['cycles'].size:
            raise IndexError(f'Invalid cell_id: {cell_id}')
        cycles = _cell_field(file, batch, 'cycles', cell_id)
        result = {}
        for field in fields:
            refs = cycles[field][()].reshape(-1, order='F')
            if not isinstance(cycle_index, (int, np.integer)) or not 0 <= cycle_index < len(refs):
                raise IndexError(f'Invalid cycle_index for {field}: {cycle_index}')
            result[field] = file[refs[cycle_index]][()].reshape(-1).copy()
        if 'Qdlin' in fields:
            result['Vdlin'] = _cell_field(file, batch, 'Vdlin', cell_id)[()].reshape(-1).copy()
        return result
