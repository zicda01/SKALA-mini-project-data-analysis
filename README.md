# ESS 배터리 수명 예측

MIT–Stanford 배터리 데이터를 탐색하고, 초기 100 cycle의 신호로 셀의 전체 Cycle Life를 예측하는 회귀 프로젝트입니다. EDA에서 Feature와 모델을 설계하고, 대안을 같은 조건에서 비교한 뒤 선택 이유와 실제 성능을 설명하는 실습을 목표로 합니다.

DAY1 EDA와 설계, DAY2 모델 비교·Hold-out·Batch 2 평가 및 오류 진단을 완료했습니다. 최종 모델은 **ΔQ 분산의 log10 값 하나를 사용한 Linear Regression**이며, Batch 2 MAPE는 **25.61%**입니다.

[DAY2 결과 보고서](outputs/reports/day2/day2_result_report.md) · [프로젝트 통합 보고서](outputs/reports/project_integrated_report.md) · [DAY1 설계 보고서](outputs/reports/day1/day1_design_report.md)

## 프로젝트 개요

- 데이터셋: MIT–Stanford Battery Dataset (Severson et al., Nature Energy 2019) 계열의 제공된 세 MATLAB HDF5 Batch.
- 학습 데이터: Batch 1 (2017-05-12), 기본 학습 셀 36개.
- 평가 데이터: Batch 2 (2018-02-20), 수명 라벨 유효 39개.
- 태스크: **Regression — 전체 Cycle Life 예측**. 초기 100 cycle의 신호로 원래 cycle_life를 예측합니다.
- 내부 검증: 개발 29개의 프로토콜 그룹 5-fold CV와 별도 Hold-out 7개.
- 추가 평가: Batch 3는 EDA에 사용했고, 선택 사항인 모델 평가는 수행하지 않았습니다.

Batch 1의 수명 정답이 불확실한 10개는 학습 전 점검에서 구분했습니다. Batch 2의 테스트 오차를 근거로 셀을 제외하지 않았습니다. [제외 근거와 데이터 점검](outputs/reports/day2/data_audit_report.md)을 참고하세요.

## 파일 구조

주요 파일과 실제 저장 경로는 다음과 같습니다.

```text
.
├── data/                                  # Git 제외; 다운로드·재생성
│   ├── raw/                               # 원본 MATLAB HDF5 세 Batch
│   └── processed/day2/                    # 학습·테스트 Parquet
├── notebooks/                             # 주요 실행 노트북
│   ├── 02_question_graphs.ipynb            # 요구 질문별 EDA·Feature 추출
│   ├── 03_quality_sensitivity.ipynb        # 급등값 처리·품질 민감도
│   ├── 06_day2_dataset_preparation.ipynb   # 학습 표·분할 확인
│   ├── 07_day2_linear_comparison.ipynb     # 선형·Ridge·Target 비교
│   ├── 08_day2_feature_comparison.ipynb    # Feature 대안 비교
│   ├── 09_day2_boosting_comparison.ipynb   # 모델 교체 비교
│   ├── 10_day2_holdout_evaluation.ipynb    # Hold-out 평가
│   ├── 11_day2_batch2_evaluation.ipynb     # Batch 2 최종 테스트
│   └── 12_day2_model_diagnostics.ipynb     # 오류 진단
├── src/                                   # 주요 공통 Python 모듈
│   ├── download_data.py                   # 데이터 다운로드
│   ├── load_data.py                       # HDF5 로딩
│   ├── preprocess.py                      # 초기 신호·품질 처리
│   ├── day2_data_audit.py                  # 셀 식별·수명 점검
│   ├── day2_dataset.py                     # Feature 표·그룹 분할
│   ├── day2_linear_comparison.py           # 공통 Pipeline·CV
│   └── day2_batch2_evaluation.py           # 고정 모델 최종 평가
├── outputs/
│   ├── figures/                           # EDA·모델 비교·오류 그래프
│   ├── tables/day2/                       # 예측 CSV·메타데이터
│   │   └── batch2_evaluation/
│   │       ├── batch2_predictions.csv
│   │       └── experiment_metadata.json
│   └── reports/
│       ├── project_integrated_report.md   # 전체 과정·결과
│       ├── day1/day1_design_report.md     # DAY1 설계
│       └── day2/day2_result_report.md     # DAY2 결과
├── provided-references/                   # 공식 요구사항·평가 기준
├── docs/                                  # DAY1·DAY2 설명·작업 계획
├── requirements.txt
└── README.md
```

## 환경 설정

Python 3.11과 uv를 사용합니다. 프로젝트 루트에서 환경을 준비합니다.

```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python src/download_data.py
python -m jupyterlab
```

기존 .venv가 있으면 생성 명령을 생략합니다. 노트북 커널도 프로젝트 .venv를 선택합니다. 데이터 다운로드 모듈은 누락된 세 파일만 가져옵니다.

DAY2 가공 표는 DAY1에서 저장한 Feature CSV에 의존합니다. 새 환경에서 재현할 때는 먼저 02_question_graphs.ipynb와 03_quality_sensitivity.ipynb를 순서대로 실행해 입력 표를 만듭니다. 새 환경에서는 입력 CSV를 만든 뒤 아래의 데이터 점검·학습 표 생성 명령 두 개를 먼저 실행합니다. 이후 06번부터 12번 노트북을 순서대로 실행하면 데이터·모델·평가 결과를 확인할 수 있습니다. 모델 비교·평가 계산은 아래의 나머지 명령으로도 실행합니다.

```bash
python -m src.day2_data_audit
python -m src.day2_dataset
python -m src.day2_linear_comparison
python -m src.day2_feature_comparison
python -m src.day2_boosting_comparison
python -m src.day2_holdout_evaluation
python -m src.day2_batch2_evaluation
python -m src.day2_model_diagnostics
```

그래프와 노트북 출력을 함께 확인하려면 해당 DAY2 노트북을 실행합니다. 원본·가공 데이터 폴더는 Git에서 제외하고 outputs/의 결과 CSV는 포함합니다. 새 환경에서는 원본 다운로드와 학습 표 생성이 필요하며, 원본부터 Feature를 다시 계산하려면 02·03번 노트북도 실행합니다. [학습 표 재현 안내](outputs/reports/day2/dataset_preparation_report.md)에 의존 파일과 분할 검증 내용을 기록했습니다.

원본 로딩만 확인하려면 Batch별 raw_preview 노트북을 사용하세요. 상세 문서는 [문서 안내](docs/README.md)에서 찾을 수 있습니다.

## EDA

- **수명 분포:** Batch 1은 중수명 중심, Batch 2는 단수명 중심, Batch 3는 장수명 비중이 컸습니다. 아래 표는 DAY1 원본의 수명 라벨 유효 항목 기준입니다. Batch 1의 이후 학습 제외 10개도 포함하므로 최종 학습 36개의 통계와 구분합니다.

| DAY1 수명 라벨 유효 항목 | 유효 n | 수명 중앙값 (cycles) | 단수명 <500 | 장수명 >1000 |
|---|---:|---:|---:|---:|
| Batch 1 | 46 | 858.5 | 0.0% | 21.7% |
| Batch 2 | 39 | 472.0 | 71.8% | 7.7% |
| Batch 3 | 44 | 1005.5 | 0.0% | 52.3% |

- **방전 용량 열화:** 초기 곡선은 겹치거나 증가했고, 전체 기록의 일부 셀에서는 후반 감소가 가팔라졌습니다. 탐색 기준으로 Batch 1 셀 11의 590 cycle, Batch 2 셀 11의 340 cycle 등에서 knee 후보를 찾았습니다. 물리적으로 확정한 전환점은 아니며 후반 정보는 초기 예측 입력에서 제외했습니다.
- **ΔQ(V):** 같은 전압에서 Q100(V)−Q10(V)를 계산했습니다. Batch 2 단수명 그룹은 음의 골이 더 깊었지만 장수명 그룹은 3개뿐이었습니다. Batch 1·3에는 <500인 셀이 없어 장·단수명 직접 비교에 한계가 있습니다.
- **충전 조건:** DAY1 Batch 1에서 4C(80%)-4C 정책의 평균 수명은 1226.5 cycles, 5.4C(80%)-5.4C는 546.5 cycles였습니다. 각 그룹이 2개뿐이라 고속 충전의 인과 효과로 일반화하지 않았고, 정책은 내부 분할의 그룹으로 사용했습니다.
- **초기 신호와 중복:** 원래 ΔQ 분산과 수명의 Pearson 상관은 Batch 1·2·3에서 각각 −0.84·−0.73·−0.59였습니다. 분산과 최솟값끼리도 높은 중복이 관찰되어 대표 통계 하나를 기본 입력으로 두고 대체 후보와 비교했습니다. 상관은 예측력이나 인과관계의 검증 결과가 아닙니다.

[DAY1 질문별 답변](outputs/reports/day1/day1_question_answers.md)과 [그래프 목록](outputs/figures/question_gallery/INDEX.md)에 관찰 근거가 있습니다.

## Modeling

### 피처 엔지니어링 전략

이 관찰을 바탕으로ΔQ 분산에 log10을 적용한 변수를 기준 Feature로 삼았습니다. 초기 QD 기울기는 처리·Batch에 민감해 추가 입력 후보로 검증했고, ΔQ 최솟값은 분산을 대체하는 후보로 비교했습니다. 이 방식으로 EDA의 연관성을 실제 추가 예측력 검증으로 연결했습니다.

Feature 생성은 같은 전압에서 ΔQ(V)=Q100(V)−Q10(V)를 계산한 뒤 분산에 log10을 적용하는 방식입니다. 초기 방전 용량 기울기는 cycle 10–100의 QD 추세로 계산했고, masked 구성에서는 탐색용 기준 QD>1.32 Ah를 계산에서 가렸습니다. 원본 데이터를 삭제하거나 측정 오류로 확정한 처리는 아닙니다.

### 모델 선택 및 근거

- 후보 모델: 학습 수명 중앙값 기준선, Linear Regression, Ridge, 제한된 Gradient Boosting.
- 최종 모델: **ΔQ 분산의 log10 값 하나를 사용하는 Linear Regression**.
- 선택 이유: 약한 Ridge와 성능 차이가 작고, 추가 Feature·Target 변환·Boosting 비교에서 교체할 이득이 확인되지 않아 단순한 구성을 유지했습니다.

ΔQ 분산 하나, 기울기를 추가한 구성, ΔQ 최솟값 대체, Target 로그 변환, Ridge와 제한된 Gradient Boosting을 같은 개발 CV에서 비교했습니다.

| 비교 예시 | 평균 개발 CV MAPE |
|---|---:|
| 학습 수명 중앙값만 예측 | 16.42% |
| ΔQ 분산 + Linear Regression | **8.62%** |
| 같은 입력 + Ridge α=0.1 | 8.61% |
| ΔQ 최솟값 + Linear Regression | 8.89% |
| ΔQ 분산 + masked QD 기울기 + Linear Regression | 11.33% |
| 같은 단일 분산 입력 + 제한된 Gradient Boosting | 최저 9.90% |

Ridge와 Linear Regression의 차이는 약 0.0044 퍼센트포인트로 작았습니다. 기울기·Target 변환·Boosting에서도 교체할 이득이 확인되지 않아 설정이 적은 Linear Regression을 유지했습니다. 모든 모델이 아니라 현재 입력·표본·제한된 설정에 대한 비교 결과입니다.

최종 Pipeline은 **log10_deltaQ_var → StandardScaler → LinearRegression**입니다. Target은 원래 cycle_life이며 표준화는 학습 분할 안에서만 적합했습니다. 후보 선택은 개발 29개에서 수행했고, Hold-out 평가 후 설정을 유지해 Batch 1 전체 36개로 재학습했습니다.

[선형·Ridge 비교](outputs/reports/day2/linear_comparison_report.md) · [Feature 비교](outputs/reports/day2/feature_comparison_report.md) · [Boosting 비교](outputs/reports/day2/boosting_comparison_report.md)

## 성능 결과

| 구분 | MAPE (%) 또는 Gap (pp) | 정의 |
|---|---:|---|
| Train (Batch 1 CV) | 8.62% | 5개 검증 fold MAPE의 평균 |
| Valid (Batch 1 Hold-out) | 9.08% | 개발에서 보관한 셀 7개 |
| Test (Batch 2) | **25.61%** | 테스트 셀 39개 |
| Gap (Train-Valid) | +0.46 pp | Valid − CV |
| Gap (Valid-Test) | +16.53 pp | Test − Valid |
| Gap (Target-Test) | +16.51 pp | Test − 과제 기준 9.1% |

Batch 1 내부 CV와 Hold-out의 오차 차이는 0.46 pp였지만, Batch 2에서는 Hold-out보다 16.53 pp 증가했습니다. 현재 모델은 Batch 2로 충분히 전이되지 않았으며, 과제 기준 대비 오차도 16.51 pp 높았습니다. 표본 수·구성 및 학습량이 달라 이 차이만으로 과적합이나 특정 실험 조건을 원인으로 확정하지 않습니다.

Batch 2 MAE는 129.23 cycles, RMSE는 153.03 cycles입니다. 과제의 9.1%는 비교 기준이며, 이번 데이터·모델·분할은 원 논문과 동일하지 않습니다. CV는 후보 선택에 사용한 점수입니다. DAY1 EDA에서 Batch 2도 이미 살펴봤으므로 완전한 블라인드 외부 검증으로 표현하지 않습니다.

## 오류 분석

Batch 2의 39개 중 35개를 실제보다 높게 예측했습니다. 평균 예측−실제 오차는 +119.9 cycles였습니다. Batch 2 프로토콜 12개 중 10개는 Batch 1 학습에 없었지만, 관찰했던 프로토콜에서도 큰 오차가 나타나 미관측 프로토콜만을 원인으로 설명할 수 없었습니다.

| Batch 2 셀 | 실제 수명 (cycles) | 예측 수명 (cycles) | 절대 비율 오차 |
|---|---:|---:|---:|
| 18 | 449 | 744.3 | 65.76% |
| 6 | 393 | 650.7 | 65.57% |
| 15 | 396 | 643.4 | 62.48% |

절대 비율 오차가 가장 큰 세 셀은 실제 수명이 낮고 과대 예측됐으며, 셀 6·15는 같은 3.6C(9%)-5C 정책에 속했습니다. 이 공통점이 원인을 입증하지는 않습니다. 후속 검토에서는 낮은 수명 구간의 ΔQ 신호와 확인 가능한 온도·충전 조건을 함께 살펴 편향이 남는지 확인할 수 있습니다. 모델을 변경한다면 새 개발 실험으로 기록하고 추가 자료로 독립 평가해야 합니다.

[셀별 평가와 오류 진단](outputs/reports/day2/model_diagnostics_report.md)에서 세부 근거를 확인할 수 있습니다.

## ESS 도메인 해석

현재 결과는 실험실 개별 셀의 수명 예측 실습입니다. 향후 셀 선별·추가 실험 우선순위 판단을 지원하려면 다양한 셀·온도·정책의 외부 검증과 불확실성 평가가 필요합니다. ESS 팩의 교체·운전 결정을 적용하려면 모듈·팩 수준 검증도 필요합니다.

[Batch 2 평가와 셀별 오류](outputs/reports/day2/batch2_evaluation_report.md) · [모델 진단](outputs/reports/day2/model_diagnostics_report.md)

## 참고문헌

- Severson et al. (2019). Data-driven prediction of battery cycle life before capacity degradation. Nature Energy, 4, 383–391. [원 논문](https://web.mit.edu/braatzgroup/Severson_NatureEnergy_2019.pdf)
- [데이터 제공 페이지](https://www.kaggle.com/datasets/itshpark/data-driven-prediction-of-battery-cycle)
- [DAY2 요구사항](provided-references/dya2_requirement.md) · [결과 작성 안내](provided-references/day2_result_form.md) · [평가 기준](provided-references/evaluation_criteria.md)

## 팀 구성

| 참여자 | 정보 |
|---|---|
| 최수빈 | 울산 캠퍼스 3반|
