# DAY2 머신러닝용 학습 테이블과 고정 분할

작성일: 2026-10-02 · 상태: 표·분할 생성 및 노트북 확인 완료, 모델 학습 미실행

## 1. 결과

기존 초기 특징과 DAY2 식별·수명 점검 결과를 배터리별로 연결해 pandas DataFrame을 만들고 Parquet으로 저장했다. 배터리 하나가 한 행이다. Batch 1의 수명 정답 불확실 10개를 제외한 36개를 기본 학습 집합으로 확정하고, Batch 2의 라벨 유효 39개를 테스트로 유지한다.

| 구분 | 항목 수 | 용도 |
|---|---:|---|
| 전체 원본 항목 | 139 | 제외 항목까지 보존한 특징·관리 표 |
| Batch 1 개발 | 29 | 고정 CV를 통한 특징·모델·설정 선택 |
| Batch 1 Hold-out | 7 | 선택 설정의 내부 평가 |
| Batch 2 테스트 | 39 | 설정 확정 후 최종 평가 |
| Batch 3 후보 | 44 | 추가 곡선 품질 점검 후 선택 평가 가능 |
| 제외 | 20 | Batch 1 불확실 10개, Batch 2/3 라벨 누락 8/2개 |

제외 사유는 [학습 전 점검](data_audit_report.md)에 따른다. 0.90 Ah를 일괄 적용한 자동 제외가 아니라 명시된 Batch 1의 10개를 구분했다. 라벨·원본·DAY1 특징은 변경하지 않았다. 제외 항목도 전체 Parquet과 별도 표에 남긴다.

## 2. 저장 파일과 pandas 사용

가공 데이터는 `data/processed/day2/`에 저장한다.

- [all_cells.parquet](../../../data/processed/day2/all_cells.parquet): 전체 139개.
- [train_batch1.parquet](../../../data/processed/day2/train_batch1.parquet): 개발·Hold-out을 포함한 Batch 1 36개.
- [test_batch2.parquet](../../../data/processed/day2/test_batch2.parquet): 테스트 39개.
- [batch3_candidates.parquet](../../../data/processed/day2/batch3_candidates.parquet): 추가 검토 전 후보 44개.

프로젝트 루트에서 다음처럼 불러온다.

```python
import pandas as pd
from src.day2_dataset import F1, F2, TARGET

train = pd.read_parquet('data/processed/day2/train_batch1.parquet')
development = train.loc[train['partition'].eq('development')].copy()
X_dev = development[F2].copy()
y_dev = development[TARGET].copy()
```

`train` 전체로 처음부터 CV를 수행하면 보관한 Hold-out이 모델 선택에 들어간다. 후보 선택에는 development 29개만 사용하고, 36개 전체는 설정 고정 후 최종 재학습에 사용한다.

## 3. 열의 의미

Feature는 모델에 넣는 정보, Target은 예측할 정답이다. F1·F2는 Feature set(입력 정보 조합)의 이름이며 모델 이름이 아니다. F1은 ΔQ 분산 하나, F2는 ΔQ 분산과 초기 용량 기울기를 함께 쓰는 구성이다. [모델 비교 보고서의 용어 설명](linear_comparison_report.md#2-보고서에서-사용하는-용어)에서 CV·Hold-out과 수명 변환도 확인할 수 있다.

| 구분 | 열 | 사용 방식 |
|---|---|---|
| 셀 관리 | batch, cell_id, barcode_key, channel_id_decoded | 식별·대조, 기본 입력 제외 |
| 프로토콜 | charging_policy, protocol_key | 그룹 분할, 기본 입력 제외 |
| 정답 | cycle_life | 원본 라벨 그대로, 초기 100회 관측 후 전체 수명 예측 |
| F1 | log10_deltaQ_var | 초기 Q100−Q10 분산의 log10 |
| F2 추가 | QD_slope_masked | cycle 10–100의 QD>1.32 마스킹 기울기 |
| 비교 특징 | QD_slope_retained, deltaQ_min, peak_positive_I_cycle10 | 유지 조건·대체 통계·보조 입력 비교용 |
| 초기 품질 | deltaQ_status, early_observed_rows, n_QD_masked, n_QD_retained, early_high_QD_rows | 점검·재현, 기본 입력 제외 |
| 집합 관리 | lifetime_label_valid, lifetime_label_uncertain, initial_features_valid, cohort_eligible, exclusion_reason | 포함·제외 근거, 기본 입력 제외 |
| 분할 | partition, cv_valid_fold | 고정 학습·평가 구분, 기본 입력 제외 |

입력은 F1/F2의 열 목록으로 명시적으로 선택한다. 수명 관련 플래그나 분할 열을 숫자형이라는 이유로 모델에 넣지 않는다. 끝점 QD·전체 기록 길이 등 미래 진단값은 이 표에 포함하지 않았다.

두 기본 특징은 학습 36개·테스트 39개 모두 유효하고 결측이 없다. 마스킹/유지 기울기는 최소 유효 5개 조건을 검사했다. 로그 입력은 양수·유한 분산에만 적용한다. 0에 임의 상수를 더하지 않으며, 특징 정의 실패는 제외 사유로 기록한다.

## 4. 고정 분할

`protocol_key`는 공백만 제거하며 실험 구조 suffix를 보존한다. 셀 식별 키는 복원한 barcode를 사용한다.

- GroupShuffleSplit: seed 42, Hold-out 그룹 비율 0.2.
- 개발: 29개·16개 프로토콜, Hold-out: 7개·4개 프로토콜.
- 개발 집합의 GroupKFold: 5-fold, shuffle 없음.
- 입력 행 순서를 정렬하고, 타깃 값과 무관하게 분할한다.

| CV fold | 학습 셀 | 검증 셀 | 학습 프로토콜 | 검증 프로토콜 |
|---:|---:|---:|---:|---:|
| 1 | 23 | 6 | 13 | 3 |
| 2 | 23 | 6 | 13 | 3 |
| 3 | 23 | 6 | 13 | 3 |
| 4 | 23 | 6 | 12 | 4 |
| 5 | 24 | 5 | 13 | 3 |

Hold-out–개발 및 각 fold의 학습–검증 프로토콜 교집합은 0이다. Batch 2와 Hold-out은 개발 CV에 포함되지 않는다. 개발 셀은 검증 fold 하나에만 배정되고 나머지 fold에서는 학습으로 사용된다. `cv_valid_fold`를 이용해 재로드한 development 행 순서에 맞춘 위치 인덱스를 생성할 수 있다. 단순히 저장 CSV의 행 번호를 다른 DataFrame 인덱스로 사용하지 않는다.

CV는 실제 fold 학습 표본이 23–24개로 작다. 모델 복잡도·탐색 범위를 제한하고 fold별 편차를 함께 보고한다. 이 단계에서 성능 수치나 최적 모델을 결정하지 않았다.

## 5. 재현과 검증

재현 코드: [day2_dataset.py](../../../src/day2_dataset.py)

```bash
# 프로젝트 루트, 기존 DAY1 특징 CSV가 생성되어 있는 환경
.venv/bin/python -m src.day2_data_audit
.venv/bin/python -m src.day2_dataset
```

DAY1 특징 CSV가 없다면 기존 [02_question_graphs.ipynb](../../../notebooks/02_question_graphs.ipynb)와 [03_quality_sensitivity.ipynb](../../../notebooks/03_quality_sensitivity.ipynb)의 저장 과정을 먼저 실행한다. 이번 작업에서는 기존 특징을 재사용했으며 새 그래프를 생성하지 않았다.

[06_day2_dataset_preparation.ipynb](../../../notebooks/06_day2_dataset_preparation.ipynb)는 Parquet 로드, 자료형·결측, 제외 사유, 고정 분할, X/y 구성과 CV 위치 인덱스를 표시한다. 프로젝트 `.venv` 새 커널에서 전체 실행한 출력을 저장했다.

검증 결과:

- 입력 표의 셀 키 일대일 대응, 항목 범위, 원본 수명 라벨 및 제공된 정책의 일치 확인.
- Parquet 4개 저장 후 재로드하여 값·자료형의 DataFrame 일치 확인.
- 그룹 분할과 테스트/Hold-out의 CV 제외 확인.
- stale 라벨·누락 행 거부, 제외 사유, 타깃·행 순서와 무관한 분할에 관한 새 테스트 3개와 기존 점검 테스트 4개 통과.

결측 대체·표준화·모델 적합은 수행하지 않았다. 향후 학습 fold 내부 Pipeline에서 처리한다. 입력 CSV SHA-256, 패키지 버전, 특징 목록, 분할 설정은 [메타데이터](../../tables/day2/dataset/dataset_metadata.json)에 저장했다.

## 6. 다음 작업

같은 CV 목록을 사용하는 중앙값 기준 모델과 F1/F2 선형 회귀·Ridge를 구현하고 CV MAPE를 비교한다. Hold-out은 후보 선택에 사용하지 않고 선택한 설정을 평가할 때 사용한다. Batch 2 성능은 설정 고정 후에 산출한다.
