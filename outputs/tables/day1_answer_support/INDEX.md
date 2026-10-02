# DAY1 답변 보완 — 표 산출물

- [all_cell_default_knee.csv](all_cell_default_knee.csv)
- [batch2_short_group_comparison.csv](batch2_short_group_comparison.csv)
- [cycle10_pattern_features.csv](cycle10_pattern_features.csv)
- [pattern_correlations.csv](pattern_correlations.csv)
- [policy_life_context.csv](policy_life_context.csv)
- [short_life_case_comparisons.csv](short_life_case_comparisons.csv)
- [selected_feature_summary.csv](selected_feature_summary.csv): 제출 보고서의 두 입력 특징에 대한 batch별 요약 통계. 기존 `cell_features_for_gallery.csv`와 `early_qd_sensitivity.csv`를 `batch`·`cell_id`로 일대일 연결하고, 유효 수명 항목에서 양수·유한 ΔQ 분산의 log10 및 마스킹 QD 기울기를 집계했다. 아래 재현 코드는 기존 보완 표에 해당하며 이 통계표는 기존 CSV를 별도 집계한 결과다.

[답변 보고서](../../reports/day1/day1_question_answers.md) · [재현 코드](../../../src/report_answer_support.py)
