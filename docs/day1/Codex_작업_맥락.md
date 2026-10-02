# Codex 작업 맥락

## 1. 프로젝트 개요

이 프로젝트는 Stanford & MIT의 배터리 수명 데이터셋
**Data-driven prediction of battery cycle life before capacity degradation**
를 이용한 데이터 분석 과제이다.

현재 단계는 **노트북 중심 분석 아키텍처 구축과 실제 EDA 준비**이다.

사용자는 노트북에서 그래프·표를 직접 살펴보고 아이디어를 얻으며 분석을 확장하려 한다. 공통 로딩·전처리·계산은 `.py`로 제공하고, 탐색·실험·관찰 기록은 새 노트북에서 수행한다. 보고서는 이 과정에서 검증된 결과를 축적한 이후 작성한다.

DAY 1의 목적은 모델을 실제로 학습하는 것이 아니라 다음을 수행하는 것이다.

- Batch 1, Batch 2, Batch 3 각각에 대해 동일한 EDA 수행
- Batch 간 데이터 특성 비교
- EDA 결과를 근거로 유의미한 Feature 후보 선정
- Regression 또는 Classification 중 하나의 문제 형태 선택
- Target Variable 정의
- 데이터 처리 및 후보 모델을 포함한 모델링 전략 제시
- 최종 결과를 Markdown 분석 보고서로 정리

실제 모델 개발 및 평가 분석은 다음 작업 단계에서 진행한다.

---

## 2. 데이터셋

Kaggle Dataset:

```text
itshpark/data-driven-prediction-of-battery-cycle
```

사용 파일:

```text
2017-05-12_batchdata_updated_struct_errorcorrect.mat
2018-02-20_batchdata_updated_struct_errorcorrect.mat
2018-04-12_batchdata_updated_struct_errorcorrect.mat
```

다음 파일은 이번 과제에서 사용하지 않는다.

```text
2018-04-03_varcharge_batchdata_updated_struct_errorcorrect.mat
```

원본 파일은 MATLAB v7.3 / HDF5 계열의 대용량 `.mat` 파일이다.

데이터는 `data/raw/` 아래에 저장하며 Git에는 포함하지 않는다.

---

## 3. 제공된 Scratch Notebook

참고 파일:

```text
30-ESSHealth-scratch.ipynb
```

Scratch는 완성 답안이 아니라 다음 용도의 참고자료이다.

- `.mat` 데이터 로딩 방법
- 배터리 데이터 구조 이해
- `summary` 데이터 추출 방법
- 기본 EDA 예시
- ΔQ(V) 분석 힌트

Scratch의 로컬 절대경로는 그대로 사용하지 않는다.

프로젝트에서는 반드시 상대경로를 사용한다.

예:

```python
from pathlib import Path

DATA_DIR = Path("data/raw")
```

Scratch Notebook 자체를 분석 코드의 중심으로 만들지 않는다.
새 탐색 노트북을 `notebooks/`에 작성한다. 반복되는 분석 로직은 `.py` 파일로 분리하되, 아직 탐색 중인 일회성 실험은 노트북에 둘 수 있다. Scratch 원본은 `provided-references/`에 유지한다.

---

## 4. 데이터 구조

각 Batch에는 여러 Battery Cell이 존재한다.

주요 Cell 필드:

```text
Vdlin
barcode
channel_id
cycle_life
cycles
policy
policy_readable
summary
```

### summary

주요 필드:

```text
IR
QCharge
QDischarge
Tavg
Tmax
Tmin
chargetime
cycle
```

### cycles

주요 필드:

```text
I
Qc
Qd
Qdlin
T
Tdlin
V
discharge_dQdV
t
```

Scratch에서는 `mat73` 로딩 결과의 dict-of-lists 구조를
list-of-dicts 형태로 변환하여 사용한다.

---

## 5. DAY 1 공식 분석 질문

### Q1. Cycle Life 분포

각 Batch에 대해 다음을 확인한다.

- 150 ~ 2,300 cycle 범위 Histogram
- 장수명 셀 비율: `cycle_life > 1000`
- 단수명 셀 비율: `cycle_life < 500`
- 이상치 셀 식별
- Batch 간 분포 차이

### Q2. 열화 곡선

각 Batch에 대해:

- cycle별 Qd 추이 시각화
- 열화 속도가 일정한지 확인
- 열화가 가속되는지 확인
- Knee Point 탐색
- 장수명 / 중간 / 단수명 셀 비교

### Q3. ΔQ(V)

과제 기준:

```text
ΔQ(V) = Q(V, cycle 100) - Q(V, cycle 10)
```

Scratch 힌트:

```python
cycles[n]["Qdlin"]
```

수행 내용:

- 장수명 셀 vs 단수명 셀의 ΔQ(V) 곡선 비교
- 그룹 차이를 설명할 통계 Feature 추출
- Batch 간 패턴 일관성 확인

후보 Feature 예:

```text
deltaQ_mean
deltaQ_std
deltaQ_var
deltaQ_min
deltaQ_max
deltaQ_abs_mean
```

### Q4. 충전 조건(C-rate)과 수명

확인 내용:

- 충전 프로토콜별 평균 Cycle Life
- 고속 충전 셀의 수명 경향
- `chargetime`과 Cycle Life 관계
- 충전 전류 패턴과 열화 속도 관계
- Batch 간 차이

### Q5. 상관관계

확인 내용:

- 초기 cycle Feature와 `cycle_life` 상관계수
- 가장 강한 관계 식별
- Feature 간 Multicollinearity
- Batch별 관계 방향 및 강도 비교

---

## 6. 분석 단위

### Cycle-level DataFrame

한 행은 한 Cell의 한 Cycle을 나타낸다.

예상 컬럼:

```text
batch
cell_id
cycle
cycle_life
charging_policy
QD
QC
IR
Tavg
Tmax
Tmin
chargetime
```

용도:

- 열화 곡선
- 초기 cycle 분석
- 변화량 / 기울기 계산
- Cell-level Feature 생성

### Cell-level Feature Table

한 행은 하나의 Battery Cell을 나타낸다.

예상 Feature 후보:

```text
batch
cell_id
cycle_life
charging_policy

mean_QD
std_QD
delta_QD
QD_slope

mean_IR
delta_IR
IR_slope

mean_Tavg
mean_Tmax
mean_Tmin

mean_chargetime

deltaQ_mean
deltaQ_var
deltaQ_min
deltaQ_max
deltaQ_abs_mean
```

최종 모델링 전략은 이 Cell-level 데이터를 기준으로 설계한다.

---

## 7. Batch 처리 원칙

세 Batch를 처음부터 하나로 합쳐 분석하지 않는다.

반드시 Batch 구분을 유지한다.

식별자는 최소한 다음 조합을 사용한다.

```text
(batch, cell_id)
```

권장 흐름:

```text
Batch 1
→ 공통 분석 로직 개발 및 검증

Batch 2
→ 동일 로직 적용

Batch 3
→ 동일 로직 적용

세 결과
→ Batch 간 비교
```

Batch 1 전용 코드를 만들지 말고
공통 함수 또는 공통 모듈로 작성한다.

예:

```python
analyze_batch(batch, batch_name)
```

---

## 8. 프로젝트 구조

권장 구조:

```text
.
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── download_data.py
│   ├── load_data.py
│   ├── preprocess.py
│   ├── eda.py
│   ├── delta_q_analysis.py
│   ├── feature_analysis.py
│   └── compare_batches.py
│
├── notebooks/
│   ├── 00_data_inspection.ipynb
│   ├── 01_batch_eda.ipynb
│   └── 02_batch_comparison.ipynb
│
├── provided-references/
│   ├── 30-ESSHealth-scratch.ipynb
│   └── day1_requirement.md
│
├── outputs/
│   ├── figures/
│   │   ├── batch1/
│   │   ├── batch2/
│   │   ├── batch3/
│   │   └── comparison/
│   └── reports/
│
├── requirements.txt
├── README.md
└── .gitignore
```

필요에 따라 파일을 합치거나 세분화할 수 있지만,
데이터 로딩 / 전처리 / EDA / Feature 분석 / Batch 비교의 책임은 구분한다.

---

## 9. 데이터 관리 원칙

`data/raw/`의 원본 `.mat` 파일은 수정하지 않는다.

```text
data/raw
→ load
→ preprocess
→ data/processed
```

반복 EDA를 위해 가공 결과를 저장할 경우
CSV보다 Parquet을 우선 고려한다.

예:

```text
data/processed/batch1_summary.parquet
data/processed/batch2_summary.parquet
data/processed/batch3_summary.parquet
```

대용량 데이터를 매 실행마다 불필요하게 다시 파싱하지 않도록 한다.

---

## 10. Git / 재현성 원칙

`.gitignore`에는 최소한 다음을 포함한다.

```gitignore
data/
.venv/
__pycache__/
*.pyc
.DS_Store
.env
```

데이터 획득도 코드로 재현한다.

```bash
python src/download_data.py
```

환경은 Python 3.11 기준으로 관리한다.

예:

```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## 11. Codex가 지켜야 할 작업 원칙

1. **분석 결과를 미리 가정하지 않는다.**
   - 상관계수, 분포, Knee Point, Batch 차이는 실제 실행 결과를 확인한 뒤 작성한다.

2. **Scratch의 예시 결과를 최종 결과로 복사하지 않는다.**
   - Scratch는 분석 방향 참고용이다.

3. **동일한 분석 로직을 세 Batch에 적용한다.**

4. **단순 상관관계를 인과관계로 표현하지 않는다.**

5. **그래프만 생성하지 않는다.**
   각 분석 결과는 다음 구조로 연결한다.

```text
관찰
→ 해석
→ Batch 간 비교
→ 모델링 시사점
```

6. **Feature 선택은 실제 EDA 근거를 제시한다.**

7. **오늘은 실제 모델을 학습하는 것이 주목적이 아니다.**
   DAY 1의 최종 결과는 모델 설계 전략이다.

8. **대용량 파일이므로 메모리 사용을 의식한다.**
   동일 데이터를 불필요하게 여러 번 메모리에 복제하지 않는다.

9. **개인 PC 절대경로를 코드에 넣지 않는다.**

10. **기존 파일을 수정하기 전에 현재 구조와 코드를 먼저 확인한다.**

11. **노트북을 결과 확인의 중심으로 사용한다.**
    - 관찰·가설·추가 질문을 출력 근처에 기록한다.
    - 중요한 분석은 커널 재시작 후 전체 실행으로 검증한다.

12. **실제 cycle 번호와 관측 가능 시점을 확인한다.**
    - 상세 기준은 `docs/day1/04_EDA_세부_분석_계획.md`를 따른다.
    - Scratch의 인덱스·색상·EOL·인과 해석을 검증 없이 복사하지 않는다.

---

## 12. DAY 1 최종 산출물

최종적으로 다음이 남아야 한다.

```text
outputs/
├── figures/
│   ├── batch1/
│   ├── batch2/
│   ├── batch3/
│   └── comparison/
│
└── reports/
    └── day1_model_strategy_report.md
```

보고서는 최소한 다음 내용을 포함한다.

- 데이터셋 및 Batch 특성
- 5개 EDA 질문의 분석 결과
- Batch 간 비교
- Feature Engineering 후보
- 제거 또는 추가 검토 Feature
- Regression vs Classification 선택
- Target Variable 정의
- 데이터 처리 전략
- 후보 모델
- 다음 단계 모델링 계획

---

## 13. 다음 단계에 대한 현재 방향

사용자는 실제 모델 개발 및 평가를 DAY 1 이후 별도 단계에서 진행할 예정이다.

현재 예상 흐름은:

```text
DAY 1
Batch 1 + 2 + 3 EDA
→ 모델 전략 수립

다음 단계
Batch 1 중심 모델 개발
→ Batch 2 테스트
→ 필요 시 Batch 3 추가 검증
```

단, DAY 1 EDA 결과가 모델링 전략 변경의 근거가 될 수 있으므로
모델 종류나 Feature를 사전에 고정하지 않는다.
