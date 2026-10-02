# DAY2 모델 개발 및 평가 결과 보고서

- 기준일: 2026-10-02
- 과제: 초기 배터리 관측을 이용한 전체 Cycle Life 회귀
- 최종 모델: ΔQ 분산의 log10 값 하나를 입력으로 하는 Linear Regression

## 1. 결과 요약

DAY1 EDA를 바탕으로 세운 Feature·모델 전략을 구현하고, Batch 1 내부에서 대안을 비교·검증한 뒤 설정을 고정해 Batch 2를 평가했다. Batch 2 테스트 MAPE는 **25.61%**로 과제에서 제시한 9.1%보다 **16.51 퍼센트포인트(pp) 높다**. 결과는 목표치를 달성한 사례가 아니라 현재 실험 설계의 성능과 한계를 확인한 기록이다. 학습 목적에 맞춰 Feature와 모델을 비교해 선택 근거를 남겼으며, 테스트 결과를 보고 모델을 재선택하지 않았다.

| 결과 양식 항목 | MAPE (%) | 계산 및 해석 |
|---|---:|---|
| Train (Batch 1 CV) | 8.62 | 개발 29개 셀의 5-fold 검증 MAPE 평균 |
| Valid (Batch 1 Hold-out) | 9.08 | 따로 보관한 7개 셀 |
| Test (Batch 2) | **25.61** | Batch 1 유효 36개로 학습, Batch 2 39개로 테스트 |
| Gap (Train-Valid) | +0.46 pp | Valid − CV |
| Gap (Valid-Test) | +16.53 pp | Test − Valid |
| Gap (Target-Test) | +16.51 pp | Test − 과제 기준 9.1% |

Batch 2의 보조 지표는 MAE 129.23 cycles, RMSE 153.03 cycles다. 이 값은 MAPE와 단위·해석이 다르므로 별도 지표로 본다.

MAPE는 각 셀의 |예측 수명 − 실제 수명| / 실제 수명을 평균하고 100을 곱한 값이다. 예를 들어 실제 수명이 800 cycles이고 예측이 880이면 그 셀의 절대 비율 오차는 10%다. 공식 표의 CV 8.62%는 fold별 MAPE의 단순 평균이며, 29개 OOF 예측을 합친 MAPE 8.66%와 구분한다. OOF는 해당 셀을 학습에서 제외한 fold에서 만든 예측이다. Fold별 검증 표본 수가 5–6개라 두 평균이 조금 다르다.

## 2. 문제와 데이터

예측 입력은 첫 100 cycle 안에서 계산한 신호이고, Target은 셀의 전체 cycle_life다. 잔여 수명으로 바꾸지 않았다. 한 셀이 학습 표에서 한 행이 되며, 모델 입력 Feature와 정답 Target을 분리했다.

원본 데이터는 MATLAB HDF5 계층형 구조다. 셀 하나에 수명·충전 정책·cycle별 요약 및 상세 측정이 들어 있다. Batch 1의 원본 항목 46개 중 수명 정답 불확실성이 확인된 10개를 기본 학습에서 제외해 36개를 사용했다. Batch 2는 수명 유효 39개를 최종 테스트로 유지했다. Batch 1은 개발 29개와 Hold-out 7개로 분할했다. 제외 결정은 Batch 2 성능을 보기 전에 수행했다.

분석된 Batch 2는 2018-02-20 데이터다. 원 논문에서 primary test로 사용한 2017-06-30 구성과 날짜·구성·모델 조건이 같다고 가정하지 않는다. 따라서 과제 기준 9.1%와의 Gap은 과제 요구치에 대한 수치 비교이며 원 논문 결과를 동일 조건으로 재현했다는 뜻은 아니다.

자세한 셀 식별·라벨 점검은 [데이터 점검 보고서](data_audit_report.md), 표 구성과 고정 분할은 [학습 테이블 보고서](dataset_preparation_report.md)에 있다.

Batch 1의 10개는 짧은 수명이나 높은 예측 오차 때문에 제외한 항목이 아니다. 기록 종료 시 EOL 기준인 0.88 Ah 부근에 이르지 않은 관측과 원저자의 중단·연장 처리 근거를 함께 검토한 결과다. 0.90 Ah를 모든 데이터에 적용하는 자동 제외 규칙으로 쓰지 않았다. Barcode를 복원해 비교했을 때 Batch 간 동일 문자열 교집합은 0개였다. Batch 3 유효 라벨 44개는 추가 평가 후보로만 두었고, 선택 사항인 Batch 3 모델 평가는 수행하지 않았다.

## 3. EDA에서 Feature 전략으로

DAY1에서는 세 Batch의 Cycle Life 분포, 방전 용량 열화, cycle 100과 10의 ΔQ(V), 충전 조건과 수명, 초기 변수와 수명의 관계를 탐색했다. Batch별 수명 분포 차이가 컸고, 초기 ΔQ 분산과 최솟값은 수명과 함께 변하는 후보 신호였다. 초기 QD 기울기와 충전 지표는 데이터 처리와 Batch에 민감했고, 상관만으로 모델에 추가할 예측 정보가 있다고 단정할 수 없었다.

Feature는 예측에 쓰는 입력 정보이며 Target은 맞히려는 정답이다. F1과 F2는 모델 이름이 아니라 입력 조합의 별칭이다. F1은 ΔQ 분산 하나, F2는 여기에 초기 QD 기울기를 추가한 조합이다. DAY1에서는 로그 Target, 복수 Feature, Ridge를 우선 검토했지만, DAY2에서는 이를 포함해 대안을 비교하고 실제 결과에 따라 갱신했다.

최종 입력은 다음 순서로 만든다.

1. 셀의 cycle 10과 cycle 100에서 방전 용량-전압 곡선 Q(V)를 읽고 전압 격자 대응을 확인한다.
2. 같은 전압 지점에서 ΔQ(V) = Q100(V) − Q10(V)를 계산한다.
3. 전압 지점 전체의 ΔQ 값에 대한 분산을 계산한다.
4. 양수·유한 분산에 log10을 적용해 입력 변수 log10_deltaQ_var를 만든다.

이 값은 cycle별 방전 용량의 단순 차이가 아니라, 전압에 따른 곡선 변화가 얼마나 퍼져 있는지를 요약한다. 분산 자체는 양수지만 1보다 작은 수의 로그는 음수가 될 수 있다. 모델은 이 숫자로 전체 cycle_life를 예측한다. 예를 들어 전체 수명 정답이 800 cycles라면 초기 100회를 관측했더라도 Target은 800이며 700으로 바꾸지 않는다. 수명 그룹, 전체 기록 길이, 후반 knee 위치는 초기 예측 입력에서 제외했다.

## 4. 후보 비교와 최종 선택

모든 후보 비교에는 같은 Batch 1 개발 29개와 프로토콜 그룹 5-fold를 사용했다. StandardScaler는 각 학습 fold 안에서만 적합했다.

| 비교 후보 | 개발 CV MAPE | 결과 |
|---|---:|---|
| 학습 수명 중앙값을 모든 셀에 예측 | 16.416% | 입력을 사용하지 않는 기준선 |
| ΔQ 분산 하나 + Linear Regression + 원래 수명 | **8.617%** | 기준 모델로 유지 |
| ΔQ 분산 하나 + Ridge α=0.1 | 8.612% | 차이가 약 0.004%p로 사실상 유사 |
| ΔQ 최솟값 하나 + Linear Regression | 8.89% | 분산 기준을 일관되게 개선하지 않아 교체하지 않음 |
| ΔQ 분산 + masked QD 기울기 + Linear Regression | 11.332% | 동일 모델에서 입력 추가로 오차 증가 |
| ΔQ 분산 + masked QD 기울기 + Ridge α=10 | 9.976% | 규제로 개선되었지만 단일 분산 기준보다 오차 큼 |
| ΔQ 분산 하나 + Linear Regression + log10 수명 | 8.874% | 동일 입력·모델에서 Target 변환 이득 없음 |
| 제한된 Gradient Boosting | 최저 9.899% | Linear Regression보다 평균 MAPE가 약 1.282%p 높음 |

ΔQ 분산을 사용한 선형회귀는 중앙값 기준보다 개발 CV MAPE가 약 7.80 pp 낮았다. 입력 신호의 활용 효과는 이 개발 표본에서 확인됐지만, Batch 2에도 같은 효과가 난다고 가정하지 않는다. Ridge가 수치상 최저라는 사실은 그대로 보고한다. 약 0.0044 pp 차이를 확실한 우위로 해석할 근거가 없고, 추가 규제 설정이 없는 단순한 모델을 유지한 것이 선택 이유다.

Target 로그 변환은 최종 설정으로 선택되지 않았다. 급등값 마스킹은 입력·모델 조합에 따라 효과 방향이 달라 항상 우월한 처리로 채택하지 않았다. Gradient Boosting은 작은 fold 학습 표본과 리프 제한 때문에 요청한 깊이 2를 실제 트리에서 사용하지 못했다. 따라서 모든 Boosting 모델에 대한 결론이 아니라 이번 제한된 후보 비교 결과다.

비교 범위는 첫 선형·Ridge·Target 비교 21개 구성, Feature·마스킹 비교 18개 구성, 모델 교체 비교 6개 구성이다. 각 단계가 기존 기준 후보를 다시 포함하므로 이 수를 모두 서로 다른 후보의 개수로 합산하지 않는다. Ridge alpha는 0.1·1·10·100, Boosting은 최대 깊이 1·2와 트리 수 50·100을 제한적으로 비교했다. Boosting의 학습률은 0.05, 리프 최소 표본은 10으로 고정했다. 깊이·설정·특징을 넓게 탐색해 최적 모델을 보장한 실험은 아니다.

![모델 대안의 평균·fold별 CV MAPE 비교](../../figures/day2/boosting_comparison/01_model_comparison.png)

그림의 편차는 5개 fold 사이의 표본 표준편차로 신뢰구간이 아니다. 표의 선택 근거와 함께 평균값 및 회차별 악화 사례를 확인한다.

최종 설정은 **log10_deltaQ_var 하나 → StandardScaler → LinearRegression**이며 Target은 변환하지 않은 cycle_life다. StandardScaler는 모델 Pipeline 안에서 학습 자료에만 적합한다. Ridge와 Boosting 등 비교 이력은 [선형 모델 비교](linear_comparison_report.md), [Feature 비교](feature_comparison_report.md), [Boosting 비교](boosting_comparison_report.md)에서 확인할 수 있다.

QD 기울기는 cycle 10–100의 요약 방전 용량에 직선을 맞춰 얻은 변화 추세다. Masked 구성에서는 탐색용 기준인 QD>1.32 Ah 값을 기울기 계산에서 가린다. 이는 원본 삭제나 측정 오류 확정이 아니다. StandardScaler는 학습 입력의 평균과 표준편차로 입력을 표준화하고, 평가 입력에는 같은 학습 통계를 적용한다.

## 5. 데이터 분할과 평가 절차

1. Batch 1 유효 셀 36개를 프로토콜 그룹을 고려해 개발 29개와 Hold-out 7개로 나눴다.
2. 개발 셀 29개로 고정된 GroupKFold 5-fold CV를 수행했다. 각 fold의 학습·검증 프로토콜은 겹치지 않았다.
3. 후보 Feature와 모델은 개발 CV에서 비교했다. Hold-out은 선택 과정에서 제외했다.
4. 선택 설정을 고정한 뒤 개발 29개로 학습해 Hold-out 7개를 평가했다.
5. 재선택 없이 Batch 1 전체 36개로 최종 재학습해 Batch 2의 39개를 평가했다.

Hold-out은 GroupShuffleSplit(seed 42, 그룹 비율 0.2)로 분리했으며 개발과 Hold-out의 프로토콜 교집합은 0개다. 개발 CV의 학습 셀 수는 23–24개, 검증 셀 수는 5–6개다. 프로토콜 이름·barcode·Batch 번호는 기본 수치 입력이 아니라 관리·분할에 사용했다. 저장된 분할을 재사용하고, 표준화 통계는 매 학습 집합에서 적합했다. 예측값 clipping은 적용하지 않았다.

![Batch 2 실제 수명과 예측 수명](../../figures/day2/batch2_evaluation/01_actual_vs_predicted.png)

분할·데이터 표는 [고정 분할 목록](../../tables/day2/dataset/INDEX.md), 실행 절차는 [Hold-out 노트북](../../../notebooks/10_day2_holdout_evaluation.ipynb)과 [Batch 2 노트북](../../../notebooks/11_day2_batch2_evaluation.ipynb)에 있다.

## 6. 성능 해석

Train과 Valid의 차이는 +0.46 pp다. Hold-out 표본이 7개라 개별 셀의 오차가 평균에 크게 영향을 줄 수 있고, 이 차이만으로 과적합을 확정하지 않는다. Valid에서 Test로는 +16.53 pp 증가했다. 이는 현재 모델이 Batch 2에 잘 전이되지 않은 관찰과 부합하지만, Gap만으로 원인을 식별할 수는 없다.

과제 기준 대비 Test Gap은 +16.51 pp다. 제공된 요구사항 중 F1-score와 Accuracy를 회귀 지표로 적은 부분은 분류 지표와 혼재된 표기로 보인다. 이 프로젝트는 회귀 문제이므로 결과 양식의 MAPE를 주 지표로 따랐고, MAE와 RMSE를 보조 지표로 보고했다.

CV는 후보 선택에 반복 사용했고, Hold-out은 29개 개발 셀로 학습한 모델의 결과이며 Test는 36개 전체로 재학습한 모델의 결과다. 따라서 세 값은 같은 모델을 동일 조건에서 반복 측정한 값이 아니다. DAY1 EDA에서는 Batch 2의 수명과 신호도 이미 살펴봤다. DAY2에서는 Batch 2 점수로 후보를 튜닝하지 않았지만, 프로젝트 전체 관점에서 Batch 2를 처음 보는 완전한 블라인드 외부 검증이라고 표현할 수는 없다.

## 7. 오류 분석

Batch 2에서 39개 중 **35개를 실제보다 높게 예측**했다. 평균 signed error는 +119.9 cycles였다. Batch 1 개발 OOF는 29개 중 16개 과대, Hold-out은 7개 중 2개 과대여서 Batch 2에서 편향 방향이 뚜렷해졌다.

![Batch 2 셀별 예측 오차](../../figures/day2/batch2_evaluation/02_cell_errors.png)

Batch 2 프로토콜 그룹 12개 중 10개가 Batch 1 학습에서 없었다. 하지만 Batch 1에서 관측한 이름의 프로토콜에서도 큰 과대 예측이 나타났다. 그룹당 셀 수가 2–6개로 작고 프로토콜 문자열만으로 실험 조건 전체를 통제하지 못하므로, 미관측 프로토콜을 단독 원인으로 결론 내리지 않는다. Batch 2의 실제 수명 중앙값은 472 cycles, Batch 1 학습은 772.5 cycles였다. 분포 차이와 오차 방향이 함께 나타났지만 인과관계를 증명한 것은 아니다.

| Batch 2 셀 | 실제 수명 | 예측 수명 | 예측 − 실제 (cycles) | 절대 비율 오차 |
|---:|---:|---:|---:|---:|
| 18 | 449 | 744.3 | +295.3 | 65.76% |
| 6 | 393 | 650.7 | +257.7 | 65.57% |
| 15 | 396 | 643.4 | +247.4 | 62.48% |

큰 오차 세 사례는 실제 수명이 낮고 과대 예측됐으며, 셀 6·15는 동일한 충전 정책에 속한다. 하지만 이 공통점만으로 열화 메커니즘을 확인한 것은 아니다. 후속 질문은 낮은 수명 구간에서 초기 ΔQ 신호가 어떤 정보까지 설명하는지, 프로토콜·온도 등 확인 가능한 조건을 추가해도 편향이 남는지다. 후속 모델 비교는 새로운 개발 실험으로 표시하고, 독립 성능 확인에는 추가 평가 자료가 필요하다.

가장 큰 오차 셀과 셀별 예측은 [Batch 2 평가 보고서](batch2_evaluation_report.md), OOF·Hold-out·프로토콜 그룹·기울기 민감도는 [모델 진단 보고서](model_diagnostics_report.md)에 수록했다. 해당 진단 뒤 모델·Feature를 수정하지 않았다.

## 8. ESS 관점과 한계

이번 모델은 실험실의 개별 셀에서 얻은 초기 신호로 전체 cycle_life를 추정한다. 향후 평가된 데이터 범위 안에서 추가 실험이 필요한 셀을 선별하는 보조 아이디어를 논의할 수는 있지만, 현재 결과만으로 ESS/BESS 팩의 수명 보증이나 운전·교체 결정을 내릴 수 없다.

실제 적용을 논의하려면 다양한 셀 제조사·온도·충전 프로토콜을 포함한 외부 검증, 모듈·팩 단위 실험, 예측 불확실성 및 안전 기준을 추가해야 한다. 이번 표본은 작고, Batch 2에서 관찰된 오류 원인을 분리하지 못했다. MAPE 목표 미달도 숨기지 않고 설계와 검증의 한계로 기록한다.

## 9. 요구사항·평가 기준 대응

| DAY2 평가 항목 | 배점 | 보고서 근거 |
|---|---:|---|
| 전략을 Feature·모델 구현에 반영 | 20 | 3–5절 |
| Pipeline·데이터 분할·핵심 변수 | 40 | 2절·5절 |
| 성능 리포팅 및 목표 Gap 해석 | 20 | 1절·6절 |
| 도메인 관점 결과 해석 및 한계 | 20 | 7–8절 |

결과 안내의 README 예시가 요구하는 EDA, 모델 전략, 성능 결과, 오류 분석, ESS 해석, 참고문헌 항목은 각각 이 보고서와 세부 문서에 반영했다. 다만 제공 안내상 제출물은 공개 GitHub 링크다. 공개 저장소 URL과 DAY2 전체 팀 역할은 확인된 실제 정보로 별도 기입해야 한다. 점수는 평가자가 최종 판단하며, 항목을 다뤘다는 사실이 목표 달성이나 만점을 뜻하지 않는다.

## 10. 근거 자료와 재현 경로

- [제공 DAY2 결과 양식](../../../provided-references/day2_result_form.md)
- [DAY2 요구사항](../../../provided-references/dya2_requirement.md)
- [산출물 평가 기준](../../../provided-references/evaluation_criteria.md)
- [DAY1 설계 배경](../day1/day1_design_report.md)
- [학습 전 데이터 점검](data_audit_report.md)
- [모델 오류 진단](model_diagnostics_report.md)
- [Batch 2 예측 CSV](../../tables/day2/batch2_evaluation/batch2_predictions.csv)
- [실행 코드](../../../src/day2_batch2_evaluation.py)
- [평가 노트북](../../../notebooks/11_day2_batch2_evaluation.ipynb)

노트북 실행 순서는 02·03번에서 DAY1 입력 CSV를 생성한 다음, 데이터 점검 및 학습 표 생성 모듈을 먼저 실행하고 DAY2 06번 학습 표 확인 → 07번 선형·Ridge → 08번 Feature → 09번 Boosting → 10번 Hold-out → 11번 Batch 2 → 12번 진단이다. 06번 노트북은 이미 저장된 Parquet을 읽으므로 새 환경에서 표 생성 단계가 먼저 필요하다. [루트 README](../../../README.md)의 환경 준비와 재현 명령에 상세 절차를 정리했다.

선택 기록 JSON의 holdout_evaluated=false 및 batch2_evaluated=false는 후보 선택 당시의 상태다. 현재 평가 완료 여부와 실제 수치는 [Hold-out 메타데이터](../../tables/day2/holdout_evaluation/experiment_metadata.json) 및 [Batch 2 메타데이터](../../tables/day2/batch2_evaluation/experiment_metadata.json)를 기준으로 확인한다.

참고 논문: Severson et al. (2019), “Data-driven prediction of battery cycle life before capacity degradation,” Nature Energy, 4, 383–391. 논문의 실험 배치, 전처리 및 세부 모델 점수와 이번 프로젝트의 조건은 다르므로, 9.1%는 과제에서 제시한 비교 목표로만 다룬다.
