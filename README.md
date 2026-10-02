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
git clone https://github.com/zicda01/SKALA-mini-project-data-analysis.git
cd SKALA-mini-project-data-analysis

uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python src/download_data.py
python -m jupyterlab
```

이미 저장소를 받은 경우 git clone을 생략하고 프로젝트 루트에서 실행합니다. 기존 .venv가 있으면 생성 명령을 생략합니다. 노트북 커널도 프로젝트 .venv를 선택합니다. 데이터 다운로드 모듈은 누락된 세 파일만 가져옵니다.

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

세 Batch를 각각 탐색하고 비교했습니다. 아래 EDA 통계는 **원본의 수명 라벨 유효 항목**을 기준으로 하며, DAY2에서 수명 정답 불확실성 때문에 제외한 Batch 1의 10개도 포함합니다. 최종 학습 표본 36개의 통계와는 구분합니다. 셀 번호는 각 파일 안의 0부터 시작하는 위치입니다.

### Cycle Life 분포

150–2300 cycles의 동일한 구간으로 Histogram을 작성했습니다. 단수명은 `<500`, 장수명은 `>1000`으로 정의하고, 수명 누락 항목은 비율 계산에서 제외했습니다.

| Batch | 수명 유효 n | 평균 (cycles) | 중앙값 (cycles) | 최소–최대 (cycles) | 단수명 비율 | 장수명 비율 |
|---|---:|---:|---:|---|---:|---:|
| Batch 1 | 46 | 844.7 | 858.5 | 534–1227 | 0.0% | 21.7% |
| Batch 2 | 39 | 565.7 | 472.0 | 392–1186 | 71.8% | 7.7% |
| Batch 3 | 44 | 1059.7 | 1005.5 | 541–1935 | 0.0% | 52.3% |

Batch 1은 중수명 중심, Batch 2는 단수명 중심에 긴 수명 꼬리, Batch 3는 장수명 비중이 큰 분포였습니다. Batch 2는 소수 장수명 셀 때문에 평균이 중앙값보다 높습니다. 가장 짧은 사례는 Batch 2 셀 19의 392 cycles였습니다. 다만 1.5×IQR 기준 이상치는 모두 긴 수명 쪽이어서, 단수명 셀을 곧바로 이상치나 오류로 취급하지 않았습니다.

**핵심 발견:** Batch별 수명 분포가 크게 다르므로 내부 검증 성능과 다른 Batch의 성능을 별도로 확인해야 합니다.

[수명 분포 그래프](outputs/figures/question_gallery/01_q1_cycle_life_distribution.png) · [수명 그룹 비율](outputs/figures/question_gallery/02_q1_life_group_ratios.png)

### 열화 곡선 분석

cycle별 방전 용량 `QD`의 전체 기록과 초기 10–100 구간을 비교했습니다. 초기 곡선은 서로 겹치거나 증가하는 경우가 있어 용량 수준 하나로 수명 그룹이 분리되지 않았습니다. 일부 셀은 후반에 감소가 가팔라져 전체 기간을 일정한 열화 속도로 설명하기 어려웠습니다.

장·단수명 셀이 모두 있는 Batch 2에서는 수명 그룹과 전체 열화 곡선을 함께 확인했습니다. 대표 단수명 셀 11은 340 cycle 부근, 대표 장수명 셀 33은 905 cycle 부근에서 Knee 후보가 나타났습니다. 두 사례만으로 장수명 셀의 열화가 항상 느리다고 일반화하지 않았습니다. Batch 1·3에는 `<500` 셀이 없어 동일 기준의 장·단수명 직접 비교가 불가능했습니다.

| Knee 탐색 사례 | 후보 시점 (cycle) | 관찰 |
|---|---:|---|
| Batch 1 셀 11 | 590 | 탐색 기준을 만족하는 기울기 변화 |
| Batch 2 셀 11 | 340 | 전후 기울기 약 −0.000044 → −0.001776 Ah/cycle |
| Batch 2 셀 33 | 905 | 장수명 대표 셀의 후반 기울기 변화 |

Knee는 분할 직선과 기울기 변화로 찾은 **탐색 후보**입니다. 평활·급등값 처리·최소 구간 조건에 민감하며 물리적으로 확정한 전환점은 아닙니다. 저장 수명 이후에도 기록이 남은 셀이 있어 기록 끝을 수명으로 사용하지 않았고, Knee 탐색에서는 알려진 수명 이후 기록을 제외했습니다.

**핵심 발견:** 초기 용량 추세와 후반 열화 가속은 구분해야 합니다. 전체 기록에서 찾은 Knee 시점은 미래 정보이므로 초기 수명 예측 입력에서 제외했습니다.

[열화 곡선 그래프](outputs/figures/question_gallery/03_q2_degradation_curves.png) · [Knee 관찰과 조건 민감도](outputs/reports/day1/window_knee_observation_report.md)

### ΔQ(V) 곡선 분석

cycle 10과 100의 방전 용량–전압 곡선을 같은 전압 격자에서 읽고 **ΔQ(V)=Q100(V)−Q10(V)**를 계산했습니다. 음수는 같은 전압에서 cycle 100의 용량이 더 작다는 뜻입니다. 회차와 상세 기록의 대응, 전압 격자의 유한값·단조성·일치를 확인했습니다.

Batch 2의 단수명 그룹 중앙 곡선은 음의 골이 더 깊었습니다. 단수명 `<500` 28개와 비단수명 `≥500` 11개를 비교하면 ΔQ 분산 중앙값은 각각 0.000358·0.000059 Ah²로 약 **6.10배** 차이가 났습니다. 별도의 장수명 `>1000` 그룹은 3개뿐이므로 대표성에 한계가 있습니다. Batch 1·3은 중·장수명 곡선을 비교했으며 개별 곡선의 겹침도 관찰했습니다.

곡선을 분산·최솟값·평균·평균 절댓값으로 요약했습니다. 분산은 전압 지점 전체에서 ΔQ 값이 얼마나 퍼져 있는지 나타내며, cycle별 QD 변동성과는 다릅니다.

**핵심 발견:** 초기 곡선 변화의 통계량은 수명 예측 후보가 될 수 있습니다. 분산과 최솟값을 모델 입력의 기본안·대체안으로 비교했습니다.

[ΔQ 곡선 그래프](outputs/figures/question_gallery/04_q3_delta_q_curves.png) · [ΔQ 분산과 수명](outputs/figures/question_gallery/05_q3_delta_q_variance.png)

### 충전 속도(C-rate)와 수명의 관계

충전 프로토콜별 개별 수명과 평균을 비교했습니다. 예를 들어 DAY1 Batch 1에서 `4C(80%)-4C`의 평균 수명은 **1226.5 cycles**, `5.4C(80%)-5.4C`는 **546.5 cycles**였습니다. 각 정책의 표본은 2개뿐이므로 이 차이를 충전 속도의 인과 효과로 확정하지 않았습니다.

cycle 10 전류 패턴도 초기 QD 기울기와 비교했습니다. 최대 양수 전류와 급등값을 가린 초기 기울기의 Pearson 상관은 Batch 1·2·3에서 각각 **−0.157·−0.374·−0.385**였습니다. 관계의 강도는 Batch와 처리 조건에 따라 달랐으며, 최대·평균 전류·유지 시간은 서로 같은 충전 지표가 아니었습니다. 저장 전류를 물리적 C-rate로 환산해 검증한 결과도 아닙니다.

**핵심 발견:** 정책별 수명 차이는 있지만 “빠를수록 반드시 짧다”는 단일 규칙은 확인하지 못했습니다. 프로토콜은 내부 검증의 그룹으로 사용하고, 전류 패턴의 추가 예측 효과는 후속 비교 과제로 남겼습니다.

[프로토콜별 수명 그래프](outputs/figures/question_gallery/06_q4_policy_lifetime.png) · [전류 패턴 분석](outputs/reports/day1/policy_exploration_observation_report.md)

### 추가 확인: 초기 신호의 상관관계와 데이터 품질

| Feature와 수명의 Pearson 상관 | Batch 1 | Batch 2 | Batch 3 |
|---|---:|---:|---:|
| 원래 ΔQ 분산 | −0.838 | −0.733 | −0.590 |
| ΔQ 최솟값 | +0.882 | +0.819 | +0.692 |

검토한 초기 12개 Feature에서 Pearson 절댓값이 가장 큰 것은 세 Batch 모두 ΔQ 최솟값, Spearman 절댓값이 가장 큰 것은 ΔQ 분산이었습니다. 두 통계량 사이에도 높은 중복이 있어 처음부터 함께 넣기보다 대표 입력 하나와 대체 후보를 비교했습니다. 표의 Pearson은 **로그 변환 전 분산** 기준입니다.

초기 QD 기울기는 급등값 처리에 민감했습니다. Batch 1의 수명 Pearson 상관은 급등 유지 시 +0.109, `QD>1.32 Ah`를 가리면 +0.524였습니다. 1.32 Ah는 탐색용 기준이며 측정 오류를 확정하는 기준은 아닙니다. 원본·수명 라벨을 바꾸거나 누락 수명을 0으로 채우지 않았습니다.

**핵심 발견:** 상관이 강하다는 이유만으로 입력을 늘리지 않고, 실제 CV에서 추가 정보와 처리 효과를 검증해야 합니다.

[Feature 상관 그래프](outputs/figures/question_gallery/09_q5_feature_correlations.png) · [품질 민감도](outputs/reports/day1/quality_sensitivity_observation_report.md) · [DAY1 문항별 답변](outputs/reports/day1/day1_question_answers.md)

## Modeling

### 피처 엔지니어링 전략

EDA에서 일관된 관계를 보인 ΔQ 분산을 기본 Feature로 두고, 초기 QD 기울기와 ΔQ 최솟값의 대안을 비교했습니다.

| 입력 후보 | 계산 방법 | EDA에서의 근거 | DAY2 판단 |
|---|---|---|---|
| `log10_deltaQ_var` | Q100−Q10의 전압별 분산에 log10 적용 | 세 Batch에서 수명과 같은 방향의 관계, 작은 표본에서 단순한 입력 구성 | 최종 입력으로 유지 |
| `deltaQ_min` | Q100−Q10의 최솟값 | 강한 수명 상관, 분산과 높은 중복 | 분산을 대체해 비교했으나 교체 이득 없음 |
| `QD_slope_retained` | cycle 10–100의 QD 직선 기울기 | 초기 용량 변화 추세를 보완할 가능성 | 추가 입력 후보로 비교 |
| `QD_slope_masked` | QD>1.32 Ah를 가린 뒤 동일 기울기 계산 | 급등값 처리에 대한 민감도 확인 | 추가 입력·마스킹의 일관된 이득 없음 |

최종 Feature 생성은 **cycle 10·100 곡선 대응 확인 → ΔQ 계산 → 분산 계산 → 양수·유한값 확인 → log10 변환** 순서입니다. 이는 한 셀을 하나의 숫자로 요약한 입력입니다. Target은 변환하지 않은 전체 `cycle_life`이며, 초기 100회를 관측했더라도 전체 수명이 800이면 정답은 800입니다. 잔여 수명 700으로 바꾸지 않습니다.

수명 그룹·전체 기록 길이·후반 Knee 위치는 입력에서 제외했습니다. 충전 정책과 barcode는 데이터 관리·분할에 사용했습니다. StandardScaler는 각 학습 집합에서만 적합하고 평가 데이터에는 같은 학습 통계를 적용합니다.

### 모델 선택 및 근거

- **후보 모델:** 학습 수명 중앙값 기준선, Linear Regression, Ridge, 제한된 Gradient Boosting.
- **최종 모델:** ΔQ 분산의 log10 값 하나로 전체 Cycle Life를 예측하는 **Linear Regression**.
- **선택 이유:** 기준선보다 오차가 낮고, 약한 Ridge와 차이가 매우 작으며, 추가 Feature·Target 변환·Boosting에서 교체할 이득이 확인되지 않았습니다. 작은 표본에서 해석이 쉽고 설정이 적은 구성을 유지했습니다.

모든 후보는 같은 Batch 1 개발 29개와 고정된 프로토콜 그룹 5-fold CV에서 비교했습니다.

| 비교 구성 | 평균 개발 CV MAPE | 선택에 반영한 판단 |
|---|---:|---|
| 학습 수명 중앙값만 예측 | 16.416% | 입력을 쓰지 않는 기준선 |
| ΔQ 분산 + Linear Regression | **8.617%** | 최종 구성 유지 |
| 같은 입력 + Ridge α=0.1 | 8.612% | 약 0.0044 pp 차이로 확실한 우위 근거 부족 |
| ΔQ 최솟값 + Linear Regression | 8.89% | 기본 입력보다 오차 증가 |
| ΔQ 분산 + masked QD 기울기 + Linear Regression | 11.332% | 입력 추가로 오차 증가 |
| 같은 두 입력 + Ridge α=10 | 9.976% | 규제로 개선됐지만 단일 입력보다 오차 큼 |
| ΔQ 분산 + Linear Regression + log10 Target | 8.874% | Target 변환 이득 없음 |
| 같은 단일 입력 + 제한된 Gradient Boosting | 최저 9.899% | 이번 설정에서 선형회귀보다 오차 큼 |

Ridge α는 0.1·1·10·100을 비교했습니다. Boosting은 최대 깊이 1·2, 트리 수 50·100을 비교하고 학습률 0.05·리프 최소 표본 10을 고정했습니다. 작은 fold 학습 표본에서는 실제 트리가 깊이 1만 사용했으므로, 모든 Boosting 모델의 성능을 평가한 결과로 일반화하지 않습니다.

최종 모델은 실제 scikit-learn **`Pipeline(StandardScaler → LinearRegression)` 객체**로 구현했습니다. Hold-out 7개는 후보 선택에서 제외했습니다. 선택 설정으로 개발 29개를 학습해 Hold-out을 평가한 뒤, 설정을 유지하고 Batch 1 전체 36개로 재학습해 Batch 2를 평가했습니다.

[선형·Ridge 비교](outputs/reports/day2/linear_comparison_report.md) · [Feature 비교](outputs/reports/day2/feature_comparison_report.md) · [Boosting 비교](outputs/reports/day2/boosting_comparison_report.md)

## 성능 결과

회귀 과제의 결과 양식에 따라 MAPE를 주 지표로 보고합니다. MAPE는 셀별 `|예측−실제| / 실제`의 평균에 100을 곱한 값입니다. Gap은 두 MAPE의 차이이므로 단위는 퍼센트포인트(pp)입니다.

| 구분 | MAPE (%) 또는 Gap (pp) | 계산·평가 대상 |
|---|---:|---|
| Train (Batch 1 CV) | 8.62% | 개발 29개에서 5개 검증 fold MAPE의 단순 평균 |
| Valid (Batch 1 Hold-out) | 9.08% | 개발 29개로 학습, 보관한 7개 평가 |
| Test (Batch 2) | **25.61%** | Batch 1 전체 36개로 학습, Batch 2 39개 평가 |
| Gap (Train-Valid) | +0.46 pp | Valid − CV |
| Gap (Valid-Test) | +16.53 pp | Test − Valid |
| Gap (Target-Test) | +16.51 pp | Test − 과제 기준 9.1% |

Batch 2의 MAE는 **129.23 cycles**, RMSE는 **153.03 cycles**입니다. CV 8.62%는 fold별 평균이며, 개발 29개의 OOF 예측을 합친 MAPE 8.66%와 구분합니다.

- **Train–Valid:** 오차 차이는 작지만 Hold-out이 7개뿐이므로 이 값만으로 과적합이 없다고 단정하지 않습니다.
- **Valid–Test:** 다른 Batch에서 오차가 크게 증가했습니다. 현재 모델의 Batch 간 일반화 한계가 드러났지만, 표본 구성과 학습량도 달라 단일 원인을 확정할 수 없습니다.
- **Target–Test:** 과제 기준보다 16.51 pp 높아 목표를 달성하지 못했습니다. 원 논문과 데이터 구성·전처리·모델이 다르므로 동일 조건의 재현 오차로 해석하지 않습니다.

DAY1 EDA에서 Batch 2의 수명·신호도 관찰했습니다. DAY2에서 테스트 점수로 후보를 튜닝하지 않았지만, 프로젝트 전체를 완전한 블라인드 외부 검증이라고 표현하지 않습니다.

[Batch 2 평가 보고서](outputs/reports/day2/batch2_evaluation_report.md) · [셀별 예측 CSV](outputs/tables/day2/batch2_evaluation/batch2_predictions.csv)

## 오류 분석

Batch 2의 **39개 중 35개를 실제보다 높게 예측**했고, 평균 예측−실제 오차는 **+119.9 cycles**였습니다. 절대 비율 오차가 가장 큰 세 셀은 다음과 같습니다.

| Batch 2 셀 | 실제 수명 (cycles) | 예측 수명 (cycles) | 예측−실제 (cycles) | 절대 비율 오차 |
|---|---:|---:|---:|---:|
| 18 | 449 | 744.3 | +295.3 | 65.76% |
| 6 | 393 | 650.7 | +257.7 | 65.57% |
| 15 | 396 | 643.4 | +247.4 | 62.48% |

### 크게 틀린 셀의 공통점

세 셀 모두 실제 수명이 500 cycles 미만이고 과대 예측됐습니다. 셀 6·15는 같은 `3.6C(9%)-5C` 정책에 속합니다. Batch 2 전반의 과대 예측과 함께 나타나지만, 정책이 같다는 사실만으로 열화 원인을 확정하지 않습니다.

### 원인 가설 및 개선 방향

| 관찰 근거 | 원인 가설 | 후속 확인·개선 방향 |
|---|---|---|
| 학습 Batch 1 수명 중앙값 772.5, Batch 2 472 cycles | 학습에서 본 관계가 낮은 수명 구간에 충분히 적용되지 않을 가능성 | 단수명 구간의 초기 신호와 오차를 비교하고 개발 표본 범위 확장 |
| Batch 2의 12개 정책 중 10개가 학습에 없음 | 프로토콜·실험 조건 차이가 전이에 영향을 줄 가능성 | 확인 가능한 조건별 잔차 비교, 학습 정책 다양화 |
| 관측했던 정책에서도 큰 오차 발생 | 미관측 정책만으로 설명되지 않는 셀·Batch 차이 | ΔQ 곡선 품질과 추가 초기 신호의 보완 효과 검토 |

이 가설들은 원인이 입증됐다는 뜻이 아닙니다. 현재 테스트 오류를 보고 셀을 제외하거나 모델을 재선택하지 않았습니다. 후속 Feature·모델 비교를 수행한다면 새 개발 실험으로 기록하고, 추가 자료로 독립 평가해야 합니다.

[오류 진단 보고서](outputs/reports/day2/model_diagnostics_report.md) · [셀별 오차 그래프](outputs/figures/day2/batch2_evaluation/02_cell_errors.png)

## ESS 도메인 해석

### 실제 BESS에서 어떤 의사결정에 활용할 수 있는가?

초기 관측으로 전체 수명을 추정하는 접근은 셀 선별 시험에서 수명이 짧을 가능성이 있는 셀을 검토하거나, 추가 수명 실험의 우선순위를 정하는 보조 정보로 활용할 수 있습니다. 긴 수명 시험을 모두 마치기 전에 후보 셀을 비교한다는 점에 의미가 있습니다.

다만 이번 결과는 실험실 개별 셀 데이터에 대한 실습입니다. 현재 모델의 Batch 2 오차와 과대 예측 편향을 고려하면, 예측값만으로 실제 ESS 팩의 교체 시기·수명 보증·운전 조건을 결정할 수준으로 검증되지는 않았습니다. 전체 Cycle Life 예측이며 현장 운전 중의 잔여 수명 예측 모델도 아닙니다.

### 한계와 실제 배포를 위해 추가로 필요한 것

| 현재 한계 | 추가로 필요한 검증·개발 |
|---|---|
| 학습 36개, Hold-out 7개의 작은 표본 | 다양한 제조사·셀·충전 정책의 데이터와 독립 검증 |
| Batch 2에서 높은 오차와 과대 예측 | 조건별 편향·단수명 셀 오차 검증, 예측 불확실성 평가 |
| 실험실 셀과 ESS 모듈·팩의 차이 | 온도·SOC·부하·셀 불균형을 포함한 모듈·팩 단위 평가 |
| 초기 100 cycle의 Q(V) 측정이 필요 | 현장 BMS에서 필요한 신호를 얻을 수 있는지와 측정 품질 확인 |

실제 활용에서는 예측 오차가 큰 셀을 놓치지 않도록 추가 시험·점검 기준을 함께 설계해야 합니다. 이번 프로젝트는 이러한 운영 의사결정을 검증한 결과가 아니라, **EDA → 설계 → 모델 비교 → 평가 → 한계 해석**의 과정을 실습한 결과입니다.

## 참고문헌

- Severson et al. (2019). Data-driven prediction of battery cycle life before capacity degradation. *Nature Energy*, 4, 383–391. [원 논문](https://web.mit.edu/braatzgroup/Severson_NatureEnergy_2019.pdf)
- [데이터 제공 페이지](https://www.kaggle.com/datasets/itshpark/data-driven-prediction-of-battery-cycle)
- [DAY1 요구사항](provided-references/day1_requirement.md) · [DAY2 요구사항](provided-references/dya2_requirement.md)
- [결과 작성 안내](provided-references/day2_result_form.md) · [평가 기준](provided-references/evaluation_criteria.md)

## 팀 구성

| 참여자 | 정보 | 수행 역할 |
|---|---|---|
| 최수빈 | 울산 캠퍼스 3반 | EDA, Feature Engineering, 모델 개발, 성능 평가 및 보고서 작성 (전체 작업 단독 수행) |
