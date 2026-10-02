# 배터리 수명 분석 프로젝트 통합 보고서

- 기준일: 2026-10-02
- 목적: 사용자가 프로젝트의 분석 과정과 결과, 제공된 과제 요구사항 및 평가 기준 대응을 한 문서에서 확인하기 위한 통합 기록
- 제출 형식 참고: 제공된 DAY2 안내는 공개 GitHub 링크를 제출하도록 한다. 별도 DAY2 PDF 보고서 제출은 명시되어 있지 않다. 이 Markdown은 저장소 내 설명 자료다. DAY1 지정 설계 PDF는 [DAY1 제출용 설계 보고서](day1/DS-MINI-Design-울산캠퍼스_3반-최수빈.pdf)에 별도로 보관되어 있다.

## 1. 핵심 요약

이 프로젝트는 MATLAB HDF5 계층형 배터리 데이터를 이해하고, EDA에서 찾은 초기 신호를 Feature와 모델 후보로 구체화한 뒤, 후보를 구현·비교·평가하는 실습이다. DAY1에는 세 Batch의 데이터와 열화·수명 특성을 살펴 모델 설계 근거를 만들었다. DAY2에는 Batch 1 안에서 후보를 비교하고 검증한 후, 선택을 고정해 Batch 2에서 평가했다.

현재 최종 모델은 cycle 10과 100의 방전 용량-전압 곡선 차이인 ΔQ(V)에서 계산한 **분산의 log10 값 하나**를 입력으로 사용하고, 변환하지 않은 전체 cycle_life를 예측하는 **Linear Regression**이다. Batch 2 MAPE는 **25.61%**로 과제 기준 9.1%보다 **16.51 퍼센트포인트 높다**. 이는 목표 달성 결과가 아니라 고정한 설계가 해당 Batch에 얼마나 전이되는지 확인한 값이다. Ridge, 제한된 Gradient Boosting, 대체 Feature와 Target 표현도 실제 구현해 비교했고 선택 근거와 한계를 기록했다.

## 2. 요구사항과 평가 기준

### DAY1 — 모델 전략 수립

DAY1 요구사항은 Batch 1·2·3에 대해 다섯 질문을 탐색하고, 그래프를 나열하는 데 그치지 않고 관찰에서 시사점을 도출해 모델 전략으로 연결하도록 한다.

| 평가 항목 | 배점 | 이 보고서에서 확인할 곳 |
|---|---:|---|
| 핵심 변수 분포, 통계량 해석, Feature 선택·생성 | 50 | 4절 |
| EDA 시사점과 전략의 논리적 연결 | 30 | 5절 |
| Feature 설계와 모델 후보 선택 논리 | 20 | 5–6절 |

### DAY2 — 모델 개발 및 평가

필수 평가 구조는 Batch 1 학습, Batch 2 테스트다. Batch 3 평가는 선택 사항이며 이번 필수 흐름에는 포함하지 않았다. 성능은 Batch 1 CV, Batch 1 Hold-out, Batch 2 Test 및 세 Gap을 지정 형식으로 보고한다.

| 평가 항목 | 배점 | 이 보고서에서 확인할 곳 |
|---|---:|---|
| 전략을 Feature와 모델 구현에 반영 | 20 | 5–7절 |
| Pipeline, 데이터 분할, 핵심 변수 구현 | 40 | 3절·7절 |
| 지정 형식의 성능 및 목표 Gap 해석 | 20 | 8절 |
| 도메인 관점 분석 및 한계 | 20 | 9절 |

요구사항 본문 중 회귀 평가 지표에 F1-score와 Accuracy도 적힌 부분은 분류 지표와 혼재된 표기로 보인다. 이 프로젝트는 회귀를 선택했으므로 명시된 회귀 성능 형식에 맞춰 MAPE를 주 지표로 쓰고, MAE·RMSE를 보조 지표로 제시한다.

## 3. 데이터와 범위

원본은 일반 CSV가 아니라 MATLAB HDF5 계층형 실험 데이터다. 최소 분석 단위는 배터리 셀 하나다. 셀에는 수명 라벨·충전 정책, 각 cycle의 요약값, cycle 안의 시간·전류·전압·용량 측정이 있다. 머신러닝용 표에서는 셀 하나를 한 행으로 만들고 초기 관측에서 계산한 Feature를 열로 둔다.

| 항목 | Batch 1 | Batch 2 | Batch 3 |
|---|---:|---:|---:|
| 원본 셀 항목 | 46 | 47 | 46 |
| 수명 라벨 유효 항목 | 46 | 39 | 44 |
| DAY2 기본 구성 | 학습 후보 36 | 테스트 39 | 추가 평가 후보 44 |

MATLAB 객체 핸들은 물리 셀 ID로 사용하지 않았다. 복원한 barcode 기준 Batch 간 교집합은 0개였으나, 이 결과가 기록되지 않은 재라벨링 가능성까지 배제하지는 않는다. Batch 1의 10개 라벨은 기록이 끝날 때도 방전 용량이 0.90 Ah보다 높아 완전한 수명 정답인지 불확실한 후보로 분리했다. 테스트 오차를 보고 제외한 것이 아니다. Batch 2 유효 라벨 39개는 테스트 집합으로 유지했다.

과제에서 제공된 Batch 2의 내부 날짜는 2018-02-20이다. 원 논문의 primary test로 보고된 2017-06-30 구성과 같은 테스트셋으로 취급하지 않는다. Batch 3 평가는 추가 선택 사항이다.

자세한 확인 결과는 [데이터 점검 보고서](day2/data_audit_report.md), 분할 자료는 [학습 테이블 구성 보고서](day2/dataset_preparation_report.md)에 있다.

## 4. DAY1 EDA — 다섯 질문과 관찰

| 요구 질문 | 핵심 관찰 | 설계 시사점 |
|---|---|---|
| 1. Cycle Life 분포와 짧은 수명 | Batch 1은 중수명 중심, Batch 2는 단수명 중심, Batch 3는 장수명 비중이 컸다. 짧은 수명 원인을 단일 충전 조건으로 확정할 수 없었다. | Batch 간 분포를 섞지 말고 Batch 2 전이를 따로 확인한다. |
| 2. 방전 용량 열화와 knee | 초기 곡선은 겹치고 일부는 증가했다. 전체 기록에는 후반 감소 가속 후보가 있었지만 knee 기준은 탐색용이었다. | 초기 기울기를 곧바로 열화 속도로 간주하지 않고 급등값 처리 민감도를 점검한다. |
| 3. ΔQ(V) 차이 | Q100−Q10 차이 곡선은 셀별 모양이 달랐고 분산·최솟값이 수명 관련 후보 신호로 보였다. | ΔQ 분산을 기준 후보로 두고 최솟값 대안과 비교한다. |
| 4. 충전 조건과 수명 | 정책별 차이가 관찰됐지만 그룹별 표본이 작고 Batch 구성도 달랐다. 전류 패턴 지표별 관계도 일관되지 않았다. | 정책을 기본 입력으로 무심코 넣기보다 분할 그룹과 해석 맥락으로 다룬다. |
| 5. 상관·Feature 중복 | 초기 신호와 수명의 관계는 Batch 및 급등값 처리에 민감했다. 상관만으로 추가 예측력을 보장하지 않았다. | 작은 표본에서 Feature를 제한하고 추가 입력의 기여를 실험으로 확인한다. |

![세 Batch의 Cycle Life 분포](../figures/question_gallery/01_q1_cycle_life_distribution.png)

![초기 Q100−Q10 차이 곡선](../figures/question_gallery/04_q3_delta_q_curves.png)

![충전 정책별 수명 분포](../figures/question_gallery/06_q4_policy_lifetime.png)

질문별 설명은 [DAY1 답변 보고서](day1/day1_question_answers.md), 추가 그림은 [그래프 목록](../figures/question_gallery/INDEX.md)에서 확인할 수 있다.

## 5. EDA에서 모델 전략으로

**Feature**는 모델 입력, **Target**은 맞히려는 정답이다. F1·F2는 모델 이름이 아니라 Feature 조합 이름이다. F1은 ΔQ 분산 하나, F2는 여기에 초기 방전 용량 기울기를 더한 구성이다. 예측 목표는 초기 100회 이후의 잔여 수명이 아니라 원본 전체 cycle_life다.

DAY1 출발 설계는 ΔQ 분산과 기울기 조합, 로그 수명 Target, Ridge 우선이었다. DAY2에서는 이를 확정 답으로 두지 않고 단일·복수 Feature, 로그/원래 Target, Linear Regression·Ridge·제한된 Gradient Boosting을 비교했다. 기울기 추가에서 안정된 이득이 확인되지 않았고, 약한 Ridge는 Linear Regression과 거의 같았다. 로그 Target도 선택 기준을 개선하지 않았다. 제한된 Boosting은 같은 CV에서 평균 오차와 fold 편차가 더 컸다.

따라서 현재는 ΔQ 분산 하나, 변환하지 않은 전체 수명, Linear Regression을 유지한다. 이는 선형 모델이 항상 우수하다는 주장이 아니라, 현재 표본·입력·비교 설정에서 교체 근거가 확인되지 않았다는 결정이다.

## 6. 모델 대안 비교

후보 비교는 Batch 1 개발 셀 29개의 동일한 프로토콜 그룹 5-fold CV에서 수행했다. 아래 값은 후보 선택용 개발 점수다.

| 후보 | 입력·설정 | 평균 CV MAPE | 판단 |
|---|---|---:|---|
| Linear Regression | ΔQ 분산 하나, 원래 수명 | **8.617%** | 단순 기준 모델로 유지 |
| Ridge α=0.1 | 같은 입력·Target | 8.612% | 차이 약 0.004%p, 실질적 우위를 주장하지 않음 |
| ΔQ 최솟값 + Linear Regression | 대체 통계 하나 | 8.89% | 일관된 개선이 없어 교체하지 않음 |
| ΔQ 분산 + 기울기 | 기울기 유지/급등값 마스킹 조합 | 조합별 변동 | 단일 분산 기준보다 나은 근거가 없어 기울기를 제외 |
| Gradient Boosting | 같은 단일 입력, 제한된 트리 설정 | 최저 9.899% | 평균 MAPE가 기준보다 약 1.282%p 높아 교체하지 않음 |

개발 fold의 학습 셀은 23–24개뿐이다. Boosting은 최소 리프 설정 때문에 깊이 2를 실제 트리에서 활용하지 못했다. 그러므로 이 실험은 제한된 후보 비교이지 비선형 모델 전체가 부적합하다는 증명은 아니다. 자세한 비교는 [Linear/Ridge](day2/linear_comparison_report.md), [Feature](day2/feature_comparison_report.md), [Boosting](day2/boosting_comparison_report.md) 보고서를 참조한다.

## 7. 데이터 분할과 Pipeline

1. 데이터 점검에서 라벨이 불확실한 Batch 1 셀 10개를 표시하고 기본 학습 집합 36개를 정했다.
2. Batch 1을 프로토콜 그룹 기준으로 개발 29개와 Hold-out 7개로 나눴다. seed는 42다.
3. 개발 29개에서 GroupKFold 5-fold를 사용했고 각 학습/검증 fold의 프로토콜 교집합은 0이었다.
4. StandardScaler와 모델을 Pipeline으로 묶어 scaler는 각 학습 fold에서만 적합했다. Hold-out은 후보 선택에 사용하지 않았다.
5. 선택 모델을 고정해 개발 29개로 Hold-out 7개를 평가했다.
6. 재선택 없이 Batch 1 유효 셀 36개로 재학습해 Batch 2 테스트 39개를 평가했다.

![Batch 2 실제 수명과 예측 수명](../figures/day2/batch2_evaluation/01_actual_vs_predicted.png)

분할과 데이터 표는 [학습 테이블 보고서](day2/dataset_preparation_report.md), [분할 목록](../tables/day2/dataset/INDEX.md)에 있다. 평가 코드는 [Python 모듈](../../src/day2_batch2_evaluation.py), 실행 순서는 [노트북 11](../../notebooks/11_day2_batch2_evaluation.ipynb), 셀별 결과는 [예측 CSV](../tables/day2/batch2_evaluation/batch2_predictions.csv)에 연결되어 있다.

## 8. 성능과 Gap

주 지표는 MAPE다. Gap은 퍼센트가 아니라 **퍼센트포인트(pp)**이며 뺄셈 방향을 표에 표시했다.

| 구분 | MAPE (%) | 비고 |
|---|---:|---|
| Train (Batch 1 CV) | 8.62 | 개발 29개, 5-fold 평균 |
| Valid (Batch 1 Hold-out) | 9.08 | 보류 셀 7개 |
| Test (Batch 2) | **25.61** | Batch 1 유효 36개 학습, 테스트 39개 |
| Gap (Train-Valid) | +0.46 pp | Valid − CV |
| Gap (Valid-Test) | +16.53 pp | Test − Valid |
| Gap (Target-Test) | +16.51 pp | Test − 과제 기준 9.1% |

Batch 2 보조 지표는 MAE 129.23 cycles, RMSE 153.03 cycles다. 평가 집합과 학습량이 달라 Gap 하나만으로 과적합이나 Batch 차이를 원인으로 확정하지 않는다. 원 논문 초록의 9.1%와 이번 실험은 데이터 구성·모델·Target 처리·분할이 같지 않다. 따라서 +16.51pp는 과제 기준과 현재 Test MAPE의 차이로만 해석한다.

## 9. 오류 분석과 ESS 관점

Batch 2 셀 39개 중 **35개를 실제보다 높게 예측**했고 평균 signed error는 +119.9 cycles였다. Batch 1 OOF와 Hold-out에서는 같은 방향 편향이 뚜렷하지 않아, 이 모델이 Batch 2에 충분히 전이되지 않았다는 관찰을 지지한다.

Batch 2 프로토콜 문자열 12개 중 10개는 Batch 1 학습에서 관찰되지 않았다. 하지만 학습에 있었던 프로토콜 셀에도 큰 과대 예측이 나타났다. 그룹별 표본이 작고 문자열만으로 실험 조건을 통제할 수 없으므로 미관측 프로토콜만을 원인으로 단정하지 않는다. Batch별 수명 분포와 충전 정책 차이, 입력 범위 밖 예측 등이 가능한 검토 가설이지만 자료만으로 각 원인을 분리할 수 없다.

![Batch 2 셀별 예측 오차](../figures/day2/batch2_evaluation/02_cell_errors.png)

분석 대상은 실험실의 개별 셀 초기 신호와 전체 cycle_life다. 이 결과만으로 ESS/BESS 팩 수명이나 운영·교체 결정을 보증할 수 없다. 실제 적용 논의에는 다양한 제조사·셀·온도·충전 정책을 포함한 외부 검증, 모듈/팩 단위 평가, 예측 불확실성과 안전 기준이 필요하다. 상세 분석은 [Batch 2 평가](day2/batch2_evaluation_report.md)와 [오류 진단](day2/model_diagnostics_report.md)에 있다.

## 10. 요구사항 대응표

| 제공 기준 | 프로젝트에서 수행한 내용 | 근거 |
|---|---|---|
| DAY1 Q1 수명 분포와 짧은 수명 사례 | Batch별 분포·통계·사례를 비교하고 원인을 단정하지 않음 | 4절, DAY1 답변 |
| DAY1 Q2 열화·가속·knee | 곡선과 탐색 기준 기반 후보를 분석 | 4절, knee 관찰 보고서 |
| DAY1 Q3 ΔQ(V) | Q100−Q10 곡선과 통계 Feature를 탐색 | 4–6절 |
| DAY1 Q4 충전 조건·C-rate | 정책별 수명과 충전 패턴 관계를 제한점과 함께 검토 | 4절, 정책 관찰 보고서 |
| DAY1 Q5 상관·Feature 중복 | 초기 신호 관계를 검토하고 추가 예측력은 모델 비교로 확인 | 4–6절 |
| DAY1 평가: EDA→전략 연결 | 관찰을 Feature·모델 후보와 검증 계획으로 연결 | 5–6절 |
| DAY2 전략 구현 20점 | Feature·Target·모델 대안을 코드와 노트북으로 구현 | 5–7절 |
| DAY2 Pipeline·분할·핵심 변수 40점 | 라벨 점검, 그룹 CV, Hold-out, Batch 2 평가 | 3절·7절 |
| DAY2 성능·Gap 20점 | 지정 회귀 표와 계산 방향으로 결과 보고 | 8절 |
| DAY2 도메인 해석·한계 20점 | 오류 관찰과 ESS 적용 한계를 인과 주장과 구분 | 9절 |

평가 항목에 대응하는 분석을 수행했다는 것은 목표 점수를 달성했다는 뜻이 아니다. 실제 평점은 평가자 판단에 달려 있다.

## 11. 제출용 README에 반영할 항목

제공된 DAY2 결과 안내는 공개 GitHub 저장소 README를 간결하게 작성하고, 프로젝트 개요, 환경 설정, EDA, Feature 전략, 모델 선택 이유, 지정 성능 결과, 오류 분석, ESS 해석, 참고문헌과 팀 구성을 안내하도록 제시한다. 본 통합 보고서는 상세 근거를 확인하기 위한 자료이며, 공개 저장소 README는 핵심 내용을 요약하고 관련 분석으로 연결해야 한다.

| 제출 안내 항목 | 현재 상태 |
|---|---|
| 프로젝트 목적·데이터·Batch·회귀 과제 | 저장소 README에 개요가 있음 |
| EDA, 모델 전략 및 선택 이유 | DAY1/DAY2 분석 문서에 근거가 있음 |
| 성능표·오류 분석·ESS 해석 | DAY2 결과 문서에 근거가 있음 |
| 참고문헌 | 원 논문을 결과 문서에서 인용 |
| 팀원·역할 | DAY1 지정 PDF에 작성자 정보가 있음. DAY2 전체 역할 분담은 확인 가능한 정보만 기입해야 함 |
| 공개 GitHub URL | 작업 자료만으로 공개 URL을 확인하지 못함. 제출 시 실제 링크가 필요함 |

공개 링크와 확인되지 않은 팀 역할은 임의로 만들어 기재하지 않는다.

## 12. 주요 근거 자료

- [DAY1 상세 답변](day1/day1_question_answers.md)
- [DAY1 설계 보고서](day1/day1_design_report.md)
- [DAY2 데이터 점검](day2/data_audit_report.md)
- [DAY2 학습 테이블·분할](day2/dataset_preparation_report.md)
- [선형·Ridge 비교](day2/linear_comparison_report.md)
- [Feature 비교](day2/feature_comparison_report.md)
- [Boosting 비교](day2/boosting_comparison_report.md)
- [Hold-out 평가](day2/holdout_evaluation_report.md)
- [Batch 2 평가와 원 논문 조건 비교](day2/batch2_evaluation_report.md)
- [모델 오류 진단](day2/model_diagnostics_report.md)
- [제공된 요구사항 및 평가 기준](../../provided-references/)
- 참고 논문: Severson et al. (2019), “Data-driven prediction of battery cycle life before capacity degradation,” Nature Energy, 4, 383–391.

프로젝트의 중심 성과는 특정 점수 자체보다, EDA 관찰을 Feature 후보로 바꾸고 모델 대안을 같은 분할에서 비교해 선택 근거를 남긴 과정이다. 이미 확인한 Batch 2 점수는 현재 고정 모델의 테스트 결과로 보존하며, 이후 모델 변경은 새로운 개발 실험으로 구분한다.
