# DAY2 학습 전 점검 표

재현: 프로젝트 루트에서 `python -m src.day2_data_audit`.

- [cell_audit.csv](cell_audit.csv): 실제 barcode·channel, 원시 객체 핸들, 수명과 기록 범위, QD crossing·초기 품질.
- [batch_audit_summary.csv](batch_audit_summary.csv): batch별 수명 일치·관측 범위·정책 수.
- [barcode_overlap.csv](barcode_overlap.csv): 대소문자 정규화 barcode 교집합.
- [serialized_payload_overlap.csv](serialized_payload_overlap.csv): 객체 핸들 일치 수. 물리 셀 ID로 사용하지 않는다.
- [exact_early_trace_duplicates.csv](exact_early_trace_duplicates.csv): batch 간 완전 동일 초기 배열 탐지. 현재 결과 0행.
- [protocol_counts.csv](protocol_counts.csv): 프로토콜별 전체·유효 라벨 수와 셀 목록.
- [protocol_overlap.csv](protocol_overlap.csv): batch 간 프로토콜 교집합.
- [split_feasibility_preview.csv](split_feasibility_preview.csv): Batch 1 원본 46개 기준 예비 분할. 확정 학습 집합 아님.
- [cv_feasibility_preview.csv](cv_feasibility_preview.csv): 예비 개발 집합의 그룹 5-fold 수.
- [audit_metadata.json](audit_metadata.json): 파일 내부 날짜, 문자열 구조, 분할 설정.

[점검 보고서](../../../reports/day2/data_audit_report.md) · [재현 코드](../../../../src/day2_data_audit.py)
