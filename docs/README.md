# 작업 문서 안내

## DAY1 — 데이터 이해와 EDA·모델 설계

기존 설명·분석 계획·작업 기록은 `day1/`에 정리했다.

- [DAY1 작업 가이드](day1/README_작업_가이드.md)
- [DAY1 작업 계획](day1/DAY1_작업_계획.md)
- [데이터셋 입문 안내](day1/00_데이터셋_쉽게_이해하기.md)
- [DAY1 제출용 설계 보고서](../outputs/reports/day1/day1_design_report.md)

## DAY2 — 모델 개발과 평가

- [DAY2 결과 보고서](../outputs/reports/day2/day2_result_report.md): 입력 정의·후보 비교·성능표·오류 분석·평가 한계와 재현 경로.
- [DAY2 결과 보고서 작성 계획](day2/DAY2_결과_보고서_작성_계획.md): 제공된 결과 양식과 평가 기준에 맞춘 목차, 근거 자료, 성능 수치 및 검토 순서.
- [DAY2 작업 계획](day2/DAY2_작업_계획.md): DAY1 대비 변경, 분할·모델 선택·평가·제출 절차.
- [DAY2 학습 전 데이터 점검](../outputs/reports/day2/data_audit_report.md): 물리 셀 식별·수명 정답·프로토콜 점검 결과.
- [DAY2 학습 테이블 구성](../outputs/reports/day2/dataset_preparation_report.md): 가공 표·제외 사유·고정 분할.
- [DAY2 첫 모델 비교](../outputs/reports/day2/linear_comparison_report.md): 개발 CV와 대안 선택·교체 근거.
- [DAY2 Feature 대체·masking 비교](../outputs/reports/day2/feature_comparison_report.md): 핵심 입력과 용량 급등값 처리 대안 검증.

결과 보고서는 `outputs/reports/day1/`과 `outputs/reports/day2/`로 구분한다. 제공 자료는 `provided-references/`에서 유지한다.

- [DAY2 모델 교체 비교](../outputs/reports/day2/boosting_comparison_report.md): 같은 입력의 선형·Boosting 비교와 유지 근거.

- [DAY2 Batch 1 Hold-out 평가](../outputs/reports/day2/holdout_evaluation_report.md): 고정 모델의 예약 셀 평가와 셀별 예측.

- [DAY2 Batch 2 최종 평가](../outputs/reports/day2/batch2_evaluation_report.md): 고정 모델의 39개 테스트 예측, Gap과 도메인 관찰.

- [DAY2 Linear Regression 오류 진단](../outputs/reports/day2/model_diagnostics_report.md): 세 평가 묶음의 잔차·프로토콜 동반 패턴·계수 민감도.
# 문서 안내

## DAY2

- [DAY2 결과 보고서 작성 계획](day2/DAY2_결과_보고서_작성_계획.md): 제공된 결과 양식과 평가 기준에 맞춘 목차, 근거 자료, 성능 수치 및 검토 순서.
