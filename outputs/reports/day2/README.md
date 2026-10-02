# DAY2 결과 보고서

- [DAY2 결과 보고서](day2_result_report.md): 모델 개발·평가 과정과 지정 성능 결과를 단독으로 읽을 수 있게 정리했다.
- [프로젝트 통합 보고서](../project_integrated_report.md): DAY1·DAY2 요구사항, 평가 기준, 분석 과정과 주요 결과를 한 문서로 정리했다.
- [최종 결과 보고서 작성 계획](../../../docs/day2/DAY2_결과_보고서_작성_계획.md): 결과 양식과 평가 기준에 맞춰 각 절의 근거·성능값·그림·검토 항목을 정리했다.

학습 전 점검, 모델 성능과 Gap, 오류 분석·ESS 해석 결과를 이 폴더에 정리한다. 모델 비교, Hold-out, Batch 2 테스트와 오류 진단을 완료했다.

- [학습 전 데이터 점검](data_audit_report.md): barcode 복원·중복, 수명 라벨·기록 범위, 프로토콜과 분할 가능성.
- [학습 테이블 구성](dataset_preparation_report.md): Parquet·제외 사유·확정 Hold-out/CV와 검증 결과.
- [첫 모델 비교](linear_comparison_report.md): F1/F2·선형 회귀/Ridge·타깃 표현 비교와 후보 변경 이유.
- [Feature 대체·masking 비교](feature_comparison_report.md): ΔQ 분산/최솟값과 용량 급등값 처리 비교, 유지·교체 근거.

[작업 계획](../../../docs/day2/DAY2_작업_계획.md) · [DAY1 설계 보고서](../day1/day1_design_report.md)

- [모델 교체 비교](boosting_comparison_report.md): Linear Regression·Ridge·제한된 Gradient Boosting 비교와 다음 평가 설정.

- [Batch 1 Hold-out 평가](holdout_evaluation_report.md): 고정 후보의 예약 셀 7개 성능과 예측 오차.

- [Batch 2 최종 평가](batch2_evaluation_report.md): 39개 테스트 결과·셀 오류·목표 Gap.

- [모델 오류 진단](model_diagnostics_report.md): 개발 OOF·Hold-out·Batch 2 오차와 Feature·프로토콜 관찰.
