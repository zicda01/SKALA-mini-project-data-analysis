"""Matplotlib figures for inspecting raw and flagged degradation curves."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


def plot_degradation_overview(prepared, cells, batch_name, early_end=100):
    """Raw vs analysis QD, full vs early cycles; unknown life shown in gray."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharey='row')
    valid_life = cells.loc[np.isfinite(cells.cycle_life) & cells.cycle_life.gt(0), 'cycle_life']
    norm = Normalize(vmin=valid_life.min() if len(valid_life) else 0,
                     vmax=valid_life.max() if len(valid_life) else 1)
    cmap = plt.get_cmap('viridis')
    for _, frame in prepared.groupby('cell_id'):
        frame = frame.sort_values('cycle')
        life = frame.cycle_life.iloc[0]
        color = cmap(norm(life)) if np.isfinite(life) and life > 0 else '0.6'
        for row, colname in enumerate(['QD', 'QD_analysis']):
            for col in [0, 1]:
                sub = frame if col == 0 else frame.loc[frame.cycle.le(early_end)]
                axes[row, col].plot(sub.cycle, sub[colname], color=color, alpha=.65, linewidth=.7)
    for row in [0, 1]:
        for col in [0, 1]:
            ax = axes[row, col]
            ax.set(title=f'{"Raw" if row == 0 else "Analysis view"} / '
                         f'{"full record" if col == 0 else f"cycles <= {early_end}"}',
                   xlabel='Stored summary cycle', ylabel='Discharge capacity (Ah)')
            ax.grid(alpha=.2)
    masked = int(prepared.QD_analysis.isna().sum())
    fig.suptitle(f'{batch_name}: {len(cells)} cells; QD masked {masked}/{len(prepared)} rows; '
                 'gray = unavailable life')
    fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=axes.ravel().tolist(),
                 label='Stored cycle life', fraction=.025, pad=.025)
    fig.subplots_adjust(top=.87, right=.87, hspace=.45, wspace=.25)
    return fig, axes


def plot_representatives(prepared, representatives, batch_name, early_end=100,
                         eol_threshold_ah=.88):
    """Full and early QD for median representatives; threshold is a reference."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharey='row')
    groups = ['short (<500)', 'medium (500–1000)', 'long (>1000)']
    for col, group in enumerate(groups):
        match = representatives.loc[representatives.life_group.eq(group)]
        if match.empty:
            for ax in axes[:, col]:
                ax.text(.5, .5, f'{group}\nNo cells with a valid life in this group',
                        ha='center', va='center', transform=ax.transAxes)
                ax.set_axis_off()
            continue
        cell = match.iloc[0]
        frame = prepared.loc[prepared.cell_id.eq(cell.cell_id)].sort_values('cycle')
        for row in [0, 1]:
            sub = frame if row == 0 else frame.loc[frame.cycle.le(early_end)]
            ax = axes[row, col]
            if row == 0:
                ax.plot(sub.cycle, sub.QD, color='0.65', linewidth=1, label='Raw')
            ax.plot(sub.cycle, sub.QD_analysis, color='tab:blue', linewidth=1,
                    label='Analysis view')
            if row == 0:
                ax.axhline(eol_threshold_ah, color='tab:red', linestyle='--', linewidth=.8,
                           label=f'Reference: {eol_threshold_ah:g} Ah')
            ax.set(title=f'{group}; cell {int(cell.cell_id)}; stored life {cell.cycle_life:g}'
                         if row == 0 else f'Early cycles <= {early_end}',
                   xlabel='Stored summary cycle', ylabel='Discharge capacity (Ah)')
            ax.grid(alpha=.2)
            ax.tick_params(axis='y', labelleft=True)
            if row == 0:
                ax.legend(fontsize=8)
    fig.suptitle(f'{batch_name}: nearest-to-median representatives (not group averages)')
    fig.tight_layout()
    return fig, axes
