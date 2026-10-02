# DAY2 학습 집합과 고정 분할

- [cohort_counts.csv](cohort_counts.csv): batch·집합별 항목 수.
- [exclusions.csv](exclusions.csv): 제외한 20개 항목과 사유.
- [split_assignments.csv](split_assignments.csv): 전체 139개의 집합·검증 fold 배정.
- [cv_manifest.csv](cv_manifest.csv): 개발 29개 셀의 fold별 학습/검증 역할.
- [cv_summary.csv](cv_summary.csv): fold별 셀·프로토콜 수.
- [dataset_metadata.json](dataset_metadata.json): 소스 해시·버전·특징·설정.

Parquet 파일은 `data/processed/day2/`에 저장한다. CSV 분할 목록은 모델 입력 표가 아니라 관리·재현 자료다.

[구성 보고서](../../../reports/day2/dataset_preparation_report.md) · [확인 노트북](../../../../notebooks/06_day2_dataset_preparation.ipynb) · [재현 코드](../../../../src/day2_dataset.py)
