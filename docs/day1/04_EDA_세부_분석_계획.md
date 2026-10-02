# DAY 1 EDA 세부 분석 계획

## 0. 탐색과 기록 방식

각 질문은 노트북에서 그래프·표를 확인한 뒤 관찰과 다음 질문을 기록한다. 결과가 모호하면 표시 범위, 초기 구간, 대표 셀 또는 필터 조건을 바꾸어 검토한다. 결과를 보기 전에 결론이나 Feature 순위를 채우지 않는다.

노트북 기록 형식:

```text
질문 / 분석 조건
→ 그래프·표와 수치
→ 관찰한 사실
→ 가능한 해석 또는 가설
→ 추가 확인할 질문
→ 추가 분석 결과와 판단
```

### 공통 검증 기준

- `summary.cycle`을 확인하고 원본 번호를 유지한다. 배열 위치를 cycle 번호로 가정하지 않는다.
- ΔQ(V)의 cycle 10·100과 `cycles` 배열 위치의 대응을 확인한다. `Vdlin`과 `Qdlin`의 길이·전압 정렬·결측을 검사한다. 대응이 불명확하거나 필요한 cycle이 없으면 제외 사유를 기록한다.
- 초기 Feature는 사용한 cycle 시작·끝과 유효 관측 수를 명시한다. 부족한 구간은 임의로 채우지 않는다.
- 전체 열화 곡선과 knee point는 EDA에 사용하되, 초기 수명 예측 Feature에는 관측 시점 이후 정보를 넣지 않는다.
- 필터 적용 전후 결과와 제거된 셀·행 수를 비교한다. 수명 종료 부근의 실제 열화를 이상치로 일괄 제거하지 않는다.
- 그래프 색상을 수명에 대응시키려면 실제 `cycle_life`로 매핑하고 범례나 colorbar를 표시한다. 셀 순서 색상을 수명으로 해석하지 않는다.
- EOL 선을 표시할 경우 기준 용량과 비율의 근거를 명시한다. 코드의 계수와 표시한 비율이 일치해야 한다.
- 정책별 표본 수와 상관계수 계산에 사용한 셀 수를 함께 확인한다.
- `(batch, cell_id)`는 파일 내 식별자이다. `barcode` 등으로 Batch 간 동일 물리 셀의 연속 측정 여부를 확인하고, 중복 또는 연장 이력이 있으면 처리 근거를 기록한다.

## 1. 공통 원칙

각 질문은 Batch 1, Batch 2, Batch 3에 동일하게 적용한다.

분석 결과는 아래 형식으로 정리한다.

```text
Batch별 결과
→ Batch 간 비교
→ 관찰
→ 해석
→ 모델링 시사점
```

---

# Question 1. Cycle Life 분포

## 분석 내용

각 Batch에 대해:

- Histogram
- 최소값 / 최대값
- 평균 / 중앙값
- 장수명 셀 비율
- 단수명 셀 비율
- 이상치 탐색

과제 기준:

```text
장수명: cycle_life > 1000
단수명: cycle_life < 500
```

Histogram 범위:

```text
150 ~ 2300 cycle
```

## Batch 비교 포인트

- 평균 수명 차이
- 분산 차이
- 장수명/단수명 셀 비율 차이
- 특정 Batch에만 극단값이 존재하는지

## 모델링 연결

- Target 분포 불균형 여부
- Regression Target 변환 필요성
- Classification Threshold 사용 가능성

---

# Question 2. 방전 용량 열화 곡선

## 분석 변수

```text
QDischarge / Qd
```

## 분석 내용

대표 셀을 선택해:

```text
long-life
medium-life
short-life
```

세 그룹의 cycle별 Qd를 비교한다.

확인 항목:

- 초기 용량 차이
- 감소 속도
- 열화 가속 여부
- Knee Point

## Feature 후보

```text
initial_QD
mean_QD_early
delta_QD
QD_slope
knee_cycle
```

## Batch 비교 포인트

- Batch별 평균 열화 속도
- Knee Point 분포
- 장수명/단수명 그룹의 곡선 차이가 Batch마다 재현되는지

---

# Question 3. ΔQ(V)

## 과제 기준 계산

```text
ΔQ(V)
= Qdlin(cycle 100)
- Qdlin(cycle 10)
```

## 분석 내용

장수명 셀과 단수명 셀을 나누어 ΔQ(V) 곡선을 비교한다.

## Feature 후보

곡선 전체를 그대로 사용하기보다 통계 Feature 후보를 우선 검토한다.

```text
deltaQ_mean
deltaQ_std
deltaQ_var
deltaQ_min
deltaQ_max
deltaQ_abs_mean
```

필요하면 특정 voltage 구간 기반 통계도 추가한다.

## Batch 비교 포인트

- 장/단 수명 그룹의 ΔQ(V) 차이가 세 Batch에서 공통적으로 나타나는지
- 특정 Feature가 Batch에 따라 방향이 바뀌는지
- 특정 Batch에만 강하게 나타나는 패턴인지

---

# Question 4. 충전 조건(C-rate)과 수명

## 분석 변수

```text
policy
policy_readable
chargetime
I
```

## 분석 내용

- 충전 프로토콜별 평균 Cycle Life
- 고속 충전 조건의 Cycle Life
- chargetime과 Cycle Life
- 충전 전류 패턴과 열화 속도

## Batch 비교 포인트

- 동일한 또는 유사한 프로토콜이 Batch별로 같은 경향을 보이는지
- Batch 자체의 차이가 policy 효과와 혼재되어 있는지

## 모델링 연결

Feature 후보:

```text
charging_policy
mean_chargetime
current-related statistics
```

단, 범주형 policy를 그대로 사용할지 여부는 분석 결과를 보고 결정한다.

---

# Question 5. 초기 신호와 Cycle Life 상관관계

## 초기 Feature 후보

예:

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

deltaQ_var
deltaQ_min
deltaQ_mean
```

## 분석 내용

- Cycle Life와 Pearson correlation
- 필요 시 Spearman correlation 검토
- Feature 간 correlation
- Multicollinearity 확인

## Batch 비교 포인트

Feature가 좋은 후보가 되려면 단순히 Batch 1에서만 강한 상관을 보이는 것이 아니라:

```text
Batch 1
Batch 2
Batch 3
```

에서 방향과 크기가 어느 정도 일관적인지 확인한다.

---

# 6. EDA에서 Feature Engineering으로 연결

각 분석 결과를 다음 형태로 요약한다.

```text
Feature
↓
Batch별 관찰
↓
Cycle Life와 관계
↓
Batch 간 일관성
↓
모델 후보 여부
```

예:

```text
deltaQ_var

Batch 1: 강한 음의 관계
Batch 2: 유사한 음의 관계
Batch 3: 유사한 음의 관계

→ Batch 간 일관성 높음
→ 주요 모델 Feature 후보
```

반대로:

```text
mean_Tmax

Batch 1: 강한 관계
Batch 2: 약한 관계
Batch 3: 거의 없음

→ Batch-specific 가능성
→ 단독 핵심 Feature로 사용하기 전에 추가 검토
```

---

# 7. 최종 EDA 산출물

권장 Figure 목록:

```text
01_cycle_life_distribution_by_batch.png
02_cycle_life_group_ratio.png
03_degradation_curves_by_batch.png
04_knee_point_comparison.png
05_delta_q_long_vs_short.png
06_policy_vs_cycle_life.png
07_correlation_by_batch.png
08_feature_correlation_matrix.png
```

분석 보고서에서는 Figure 자체보다 각 Figure의 **모델 설계 의미**를 설명하는 것이 중요하다.
