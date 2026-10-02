# Linear Regression 오류 진단 산출물

- [combined_cell_predictions.csv](combined_cell_predictions.csv): 개발 OOF 29·Hold-out 7·Batch 2 39개 셀의 실제·예측·Feature·잔차.
- [evaluation_set_summary.csv](evaluation_set_summary.csv): 자료별 MAPE·MAE·RMSE·편향·Feature/수명 범위.
- [batch2_protocol_errors.csv](batch2_protocol_errors.csv): 프로토콜별 표본 수·학습 경험 여부·오차 요약.
- [training_cell_slope_sensitivity.csv](training_cell_slope_sensitivity.csv): Batch 1 학습 셀 하나씩 제외 시 기울기 변화.
- [diagnostic_metadata.json](diagnostic_metadata.json): 평가 범위와 모델 변경 여부.
- [진단 보고서](../../../reports/day2/model_diagnostics_report.md)
