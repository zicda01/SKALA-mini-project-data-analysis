# 모델 교체 비교 산출물

- [summary.csv](summary.csv): 6개 구성의 평균 fold 점수와 편차.
- [fold_scores.csv](fold_scores.csv): 30개 회차별 점수.
- [oof_predictions.csv](oof_predictions.csv): 셀별 검증 예측 174개.
- [paired_cell_errors.csv](paired_cell_errors.csv): 선형 기준 대비 같은 셀의 오차 변화.
- [linear_coefficients.csv](linear_coefficients.csv): 선형·Ridge 회차별 계수.
- [scaler_statistics.csv](scaler_statistics.csv): 학습 fold에서 계산한 표준화 통계.
- [tree_audit.csv](tree_audit.csv): CV 트리 1,500개의 실제 깊이·리프 수·최소 표본 수.
- [experiment_metadata.json](experiment_metadata.json): 입력 해시·환경·설정·평가 범위.
- [candidate_selection.json](candidate_selection.json): 다음 예약 데이터 평가에 사용할 고정 후보 설정.

[비교 보고서](../../../reports/day2/boosting_comparison_report.md)
