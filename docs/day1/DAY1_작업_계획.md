# DAY 1 작업 계획

## 현재 우선 목표

공통 데이터 접근 계층과 탐색 노트북을 마련하여 사용자가 그래프·표를 직접 확인할 수 있게 한다. 노트북에서 관찰·가설·추가 분석을 반복하며, 결과가 축적된 후 아래 최종 목표와 보고서를 완성한다.

공통 계산은 `.py`, 실험·결과 확인·관찰 기록은 `.ipynb`에서 수행한다. 각 Phase에서 필요한 만큼 구현하고 실제 결과를 확인한 뒤 확장한다.

## 최종 목표

Batch 1, Batch 2, Batch 3에 대해 동일한 EDA를 수행하고,
Batch 간 특성을 비교하여 **데이터에 근거한 모델 설계 전략**을 완성한다.

작업 순서는 다음과 같다.

```text
환경 / 데이터 확인
→ 공통 Loader
→ 공통 전처리
→ Batch 1 EDA 구현
→ Batch 2 / 3 확장
→ 5개 질문 분석
→ Batch 비교
→ Feature 후보 선정
→ 문제 유형 선택
→ 모델 전략 보고서 작성
```

---

# Phase 0. 현재 프로젝트 상태 확인

## 작업

Codex는 먼저 현재 Repository를 확인한다.

확인 대상:

```text
현재 디렉토리 구조
download_data.py
.gitignore
requirements.txt
data/raw 존재 여부
Scratch notebook 위치
기존 분석 코드 존재 여부
```

## 완료 조건

- 세 Batch 파일의 존재 여부를 확인
- 파일명과 경로 확인
- 기존 코드와 충돌하지 않는 작업 계획 확정
- 노트북 커널과 의존성 확인 (`ipykernel`, 실행 도구, 선택한 캐시 엔진)
- 원본 Scratch는 `provided-references/`에 보존하고 새 노트북 위치 확정

2026-10-01 확인 상태: 세 원본 파일과 Python 3.11 환경은 존재한다. `src/`에는 다운로드 코드만 있고, 탐색 노트북과 분석 모듈은 아직 없다. 현재 `.venv`에는 `ipykernel`, `jupyter`, `mat73`, `pyarrow`가 없다. 이는 확인 시점의 상태이며 구현 전에 다시 점검한다.

기존 파일을 무조건 덮어쓰지 않는다.

---

# Phase 1. 데이터 로딩 계층 구현

## 목표

세 Batch를 동일한 방식으로 로드할 수 있게 한다.

## 구현 대상

```text
src/load_data.py
```

## 주요 함수 예시

```python
load_mat(path)
normalize_batch(raw_batch)
load_batch(path, batch_name)
```

## 확인 사항

- 메타데이터·summary를 우선 읽고 필요한 cycle 곡선만 선택적으로 접근
- `.mat` 파일 정상 로딩
- Cell 수 확인
- 주요 key 확인
- `cycle_life`
- `summary`
- `cycles`
- `policy`

## 완료 조건

Batch 1을 대상으로 정상 로딩 확인 후
Batch 2, Batch 3에서도 같은 함수로 실제 실행해 구조를 확인한다.

`00_data_inspection.ipynb`에서 셀 수·필드·표본 값을 직접 확인한다. 전체 원시 시계열을 메모리에 한꺼번에 올리는 방식은 기본값으로 삼지 않는다.

---

# Phase 2. 공통 전처리 구현

## 목표

EDA에 사용할 Cycle-level DataFrame을 생성한다.

## 구현 대상

```text
src/preprocess.py
```

## 생성 컬럼 예시

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

## 작업

- `summary` 구조 추출
- DataFrame 변환
- Batch 정보 추가
- Cell 식별자 유지
- 결측 / 비정상값 현황 확인
- 실제 `summary.cycle` 보존, summary 필드 길이와 상세 cycle 대응 확인
- `00_data_inspection.ipynb`에서 표·품질 현황과 간단한 수명 분포 확인

## 첫 단계 완료 조건

Batch 1 메타데이터와 Cycle-level 표를 공통 모듈로 생성하고 노트북에서 직접 확인할 수 있다. 커널 재시작 후 전체 실행이 성공하고, 같은 로더·전처리를 Batch 2·3에서도 검증한다. 이후 `01_batch_eda.ipynb`로 질문별 탐색을 확장한다.

## 선택적 캐시

```text
data/processed/batch1_summary.parquet
data/processed/batch2_summary.parquet
data/processed/batch3_summary.parquet
```

대용량 `.mat` 재로딩 비용이 크다면 저장한다.

---

# Phase 3. Question 1 — Cycle Life 분포

## 분석

각 Batch에서:

```text
Histogram: 150 ~ 2300
장수명: >1000
단수명: <500
평균
중앙값
최소/최대
이상치
```

## 출력

예:

```text
outputs/figures/batch1/cycle_life_distribution.png
outputs/figures/batch2/cycle_life_distribution.png
outputs/figures/batch3/cycle_life_distribution.png
outputs/figures/comparison/cycle_life_distribution_comparison.png
```

## 보고서에 기록

- Batch별 분포 차이
- 장/단 수명 비율
- 이상치 셀
- Target 분포 관점의 모델링 시사점

---

# Phase 4. Question 2 — 열화 곡선

## 분석

각 Batch에서 대표 셀을 선정하여 Qd 추이를 비교한다.

가능한 그룹:

```text
long-life
medium-life
short-life
```

## 확인

- 초기 Qd 차이
- Qd 감소 속도
- 열화 가속 여부
- Knee Point

## Feature 후보

```text
initial_QD
mean_QD
std_QD
delta_QD
QD_slope
knee_cycle  # 전체 곡선 EDA용; 초기 예측 입력과 구분
```

## 주의

Knee Point 탐색 알고리즘은 지나치게 복잡하게 시작하지 않는다.
먼저 시각적으로 패턴을 확인하고,
필요하면 간단하고 설명 가능한 방법을 제안한다.

---

# Phase 5. Question 3 — ΔQ(V)

## 계산

과제 기준:

```text
ΔQ(V)
= Qdlin(cycle 100)
- Qdlin(cycle 10)
```

## 구현 대상

```text
src/delta_q_analysis.py
```

## 분석

- 장수명 / 단수명 셀 ΔQ(V) 비교
- Batch별 곡선 형태 비교
- 통계 Feature 계산

## Feature 후보

```text
deltaQ_mean
deltaQ_std
deltaQ_var
deltaQ_min
deltaQ_max
deltaQ_abs_mean
```

## 완료 조건

어떤 통계값이 장/단 수명 차이를 설명할 가능성이 있는지
실제 결과를 통해 정리.

---

# Phase 6. Question 4 — C-rate / 충전 조건

## 분석

사용 변수:

```text
policy
policy_readable
chargetime
I
```

확인 내용:

- protocol별 평균 cycle_life
- 고속 충전과 cycle_life 관계
- chargetime 관계
- 충전 전류 패턴과 열화 속도

## 주의

다음과 같이 쓰지 않는다.

```text
고속 충전이 수명을 단축시킨다.
```

EDA만으로 인과성을 확정하지 않는다.

대신:

```text
고속 충전 조건과 짧은 cycle_life 사이의 연관 패턴이 관찰되었다.
```

처럼 실제 결과 수준에서 기술한다.

---

# Phase 7. Question 5 — 상관관계와 Multicollinearity

## 구현 대상

```text
src/feature_analysis.py
```

## Cell-level Feature 생성

초기 cycle 범위에서 다음과 같은 Feature를 생성한다.

```text
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

deltaQ_*
```

## 분석

- `cycle_life`와 Feature 상관관계
- Feature 간 상관관계
- Batch별 correlation 비교
- 강한 Feature 중 Batch 간 방향이 유지되는지 확인
- 중복 Feature 탐색

## 선택적 분석

필요하면 Pearson 외에 Spearman을 보조적으로 사용한다.
단, 필요성을 결과와 함께 설명한다.

---

# Phase 8. Batch 비교

## 구현 대상

```text
src/compare_batches.py
```

## 비교표 예시

```text
Feature        Batch1      Batch2      Batch3      판단
-------------------------------------------------------
mean_QD
delta_QD
mean_IR
delta_IR
mean_Tavg
mean_chargetime
deltaQ_var
...
```

숫자는 실제 실행 결과를 사용한다.

`02_batch_comparison.ipynb`에서 같은 초기 구간·필터·Feature 정의로 생성한 표와 그래프를 확인한다.

## 판단 기준

각 Feature마다:

```text
관계 방향 일관성
관계 강도
분포 차이
이상치 민감도
Batch-specific 가능성
```

을 검토한다.

---

# Phase 9. Feature 후보 확정

Feature를 세 범주로 정리한다.

## A. 주요 후보

여러 Batch에서 비교적 일관된 관계를 보이는 Feature.

## B. 보조 후보

일부 관계가 있지만 Batch 차이가 존재하는 Feature.

## C. 제외 / 추가 검토

- 관계가 약함
- Batch마다 방향이 다름
- Multicollinearity가 강함
- 이상치 영향이 지나치게 큼

---

# Phase 10. Regression vs Classification 선택

과제에서는 둘 중 하나만 선택한다.

선택은 EDA를 완료한 후 한다.

## Regression 선택 근거 예시

```text
cycle_life가 연속적인 Target으로 충분한 분산을 가지고,
초기 Feature와 연속적인 관계가 확인되는 경우
```

Target:

```text
cycle_life
```

## Classification 선택 근거 예시

```text
장수명 / 단수명 그룹의 초기 Feature 차이가 매우 명확하고,
클래스 정의가 분석 목적에 적합한 경우
```

단, Classification 선택 시 `<500`, `>1000` 사이의
중간 수명 셀 처리 전략을 반드시 설명한다.

---

# Phase 11. 후보 모델 전략 작성

오늘은 학습하지 않고 후보를 제시한다.

EDA 결과에 따라 후보를 설명한다.

예:

```text
선형 관계가 뚜렷함
→ Linear / Ridge / Lasso 계열 검토

비선형 관계와 변수 간 상호작용이 큼
→ Random Forest / Gradient Boosting 계열 검토
```

모델 이름을 나열하는 것이 아니라
**EDA에서 확인한 데이터 특성과 후보 모델을 연결**한다.

---

# Phase 12. 최종 보고서 작성

최종 파일:

```text
outputs/reports/day1_model_strategy_report.md
```

노트북에 검증된 관찰과 추가 분석 결과가 충분히 쌓였을 때 진행한다. 각 결론에 해당 노트북·그래프·분석 조건을 연결하며, 미확인 항목은 미확인으로 남긴다.

## 보고서 순서

```text
1. 분석 목적
2. 데이터셋 구조
3. Batch별 기본 특성
4. Q1 Cycle Life
5. Q2 열화 곡선
6. Q3 ΔQ(V)
7. Q4 C-rate
8. Q5 상관관계
9. Batch 간 핵심 차이
10. Feature Engineering 후보
11. 제외 / 추가 검토 Feature
12. Regression vs Classification 선택
13. Target Variable
14. 데이터 처리 전략
15. 후보 모델
16. 다음 단계
```

각 주요 분석은 다음 구조로 작성한다.

```text
결과
→ 관찰
→ 해석
→ Batch 비교
→ 모델링 시사점
```

---

# 작업 우선순위

시간이 제한될 경우 다음 순서로 우선한다.

```text
1. 데이터 로딩 안정화
2. Cycle-level 전처리
3. Cycle Life 분포
4. 열화 곡선
5. ΔQ(V)
6. 상관관계
7. C-rate
8. Batch 비교
9. Feature 선정
10. 모델 전략 보고서
```

단, 최종 과제에서는 5개 질문을 모두 다뤄야 한다.

---

# Codex 실행 방식

Codex는 각 Phase를 한꺼번에 구현하지 말고 다음 방식으로 진행한다.

```text
작은 단위 구현
→ 실행
→ 실제 출력 확인
→ 오류 수정
→ 결과 검증
→ 다음 단계
```

특히 대용량 `.mat` 데이터이므로
코드를 작성만 하고 실행 검증 없이 다음 단계로 넘어가지 않는다.

각 단계가 끝날 때 다음을 짧게 기록한다.

```text
무엇을 구현했는가
무엇을 실행했는가
무엇을 확인했는가
다음 작업은 무엇인가
```

EDA 노트북에는 질문·조건·출력·관찰·가설·추가 확인 결과를 함께 기록한다. 중요한 결과는 커널 재시작 후 전체 실행으로 재현하고, 반복되는 로직을 공통 모듈로 옮긴다. 세부 품질 기준은 `docs/day1/04_EDA_세부_분석_계획.md`를 따른다.

---

# DAY 1 종료 기준

다음 조건을 만족하면 완료한다.

- [ ] 세 Batch 로딩 가능
- [ ] 공통 전처리 완료
- [ ] 5개 EDA 질문 완료
- [ ] Batch 간 비교 완료
- [ ] Feature 후보 분류 완료
- [ ] Regression / Classification 선택
- [ ] Target Variable 정의
- [ ] 데이터 처리 전략 작성
- [ ] 후보 모델 제시
- [ ] Markdown 최종 보고서 생성
