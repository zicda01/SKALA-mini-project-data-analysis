# DAY2 Feature 대체·masking 비교 결과

- [summary.csv](summary.csv): 18개 구성의 평균·편차·최악 회차 오차.
- [fold_scores.csv](fold_scores.csv): 90개 fold 평가.
- [oof_predictions.csv](oof_predictions.csv): 522개 셀별 예측.
- [paired_fold_deltas.csv](paired_fold_deltas.csv): 같은 fold에서 대체 조건 − 기준 조건 MAPE 차이.
- [masking_feature_changes.csv](masking_feature_changes.csv): 기울기 입력 변화. 개발 셀 18 한 개가 변경됨.
- [coefficients.csv](coefficients.csv): 모델 계수와 절편.
- [scaler_statistics.csv](scaler_statistics.csv): 학습 fold의 표준화 통계.
- [experiment_metadata.json](experiment_metadata.json): 입력 해시·구성·평가 범위.

`variance/minimum`은 ΔQ 분산/최솟값, `retained/masked`는 기울기 계산 시 급등값 유지/가림, `ols`는 Linear Regression이다. Target은 전 구성에서 변환하지 않은 전체 수명이다.

[보고서](../../../reports/day2/feature_comparison_report.md) · [노트북](../../../../notebooks/08_day2_feature_comparison.ipynb) · [코드](../../../../src/day2_feature_comparison.py)
