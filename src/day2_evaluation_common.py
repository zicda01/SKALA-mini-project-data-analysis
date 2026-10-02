"""Shared frozen evaluation settings and paths (selection is not repeated here)."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURES = ['log10_deltaQ_var']
CONFIG = {'config_id': 'linear_regression', 'model': 'ols',
          'feature_set': 'variance_only', 'target': 'raw', 'alpha': None}


def development_cv_mape(frame):
    """Recompute the selected configuration using development rows only."""
    from src.day2_linear_comparison import evaluate
    dev = frame.loc[frame.partition.eq('development')].copy()
    summary, *_ = evaluate(dev, [CONFIG], {'variance_only': FEATURES})
    return float(summary.iloc[0].mean_fold_mape_pct)


def save_evaluation_figures(predictions, output_dir, title, prediction_filename,
                            error_filename=None):
    """Create evaluation plots from the predictions supplied by this execution."""
    import matplotlib.pyplot as plt
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(predictions.actual_life, predictions.predicted_life)
    low = min(predictions.actual_life.min(), predictions.predicted_life.min())
    high = max(predictions.actual_life.max(), predictions.predicted_life.max())
    ax.plot([low, high], [low, high], '--', color='gray')
    ax.set(title=title, xlabel='Actual life (cycles)', ylabel='Predicted life (cycles)')
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(out / prediction_filename, dpi=150)
    plt.close(fig)
    if error_filename:
        p = predictions.sort_values('cell_id')
        fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        axes[0].bar(p.cell_id.astype(str), p.error_cycles)
        axes[0].axhline(0, color='gray', lw=1)
        axes[0].set(ylabel='Prediction − actual (cycles)', title=title)
        axes[1].bar(p.cell_id.astype(str), p.ape_pct)
        axes[1].set(xlabel='Cell ID', ylabel='Absolute percentage error (%)')
        for ax in axes:
            ax.grid(axis='y', alpha=.2)
        fig.tight_layout()
        fig.savefig(out / error_filename, dpi=150)
        plt.close(fig)
