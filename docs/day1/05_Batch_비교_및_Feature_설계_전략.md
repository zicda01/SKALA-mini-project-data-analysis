# Batch 비교 및 Feature Engineering 전략

## 1. 왜 Batch 비교가 필요한가

이번 DAY 1 과제는 단순히 세 Batch를 모두 분석하는 것에서 끝나지 않는다.

핵심은:

> 같은 Feature 또는 패턴이 Batch가 바뀌어도 유지되는가?

를 확인하는 것이다.

특정 Batch에서만 강한 Feature는 향후 모델이 Batch 특성에 과도하게 맞춰질 위험이 있다.

---

## 2. Batch 비교 기준

각 Feature는 다음 관점에서 비교한다.

### 2.1 방향 일관성

예:

```text
Feature ↑
Cycle Life ↑
```

관계의 방향이 세 Batch에서 동일한지 확인한다.

### 2.2 관계 강도

Correlation coefficient 또는 그룹 평균 차이를 비교한다.

### 2.3 분포 차이

Batch별 Feature 분포 자체가 크게 다른지 확인한다.

### 2.4 Outlier 민감도

몇 개의 극단값 때문에 관계가 강해 보이는지 확인한다.

---

## 3. Feature 후보 분류

EDA 후 Feature를 다음 세 그룹으로 나눈다.

### A. 주요 후보

세 Batch에서 비교적 일관된 관계를 보이는 Feature.

### B. 보조 후보

관계는 있지만 Batch별 차이가 존재하는 Feature.

### C. 제외 또는 추가 검토 후보

- 관계가 매우 약함
- Batch마다 방향이 다름
- 다른 Feature와 매우 강하게 중복됨
- 이상치에 지나치게 민감함

---

## 4. 기본 Feature 후보

### Capacity 계열

```text
mean_QD
std_QD
delta_QD
QD_slope
```

### Resistance 계열

```text
mean_IR
delta_IR
IR_slope
```

### Temperature 계열

```text
mean_Tavg
mean_Tmax
mean_Tmin
```

### Charging 계열

```text
mean_chargetime
charging_policy
```

### ΔQ(V) 계열

```text
deltaQ_mean
deltaQ_std
deltaQ_var
deltaQ_min
deltaQ_max
deltaQ_abs_mean
```

---

## 5. 초기 Cycle 기준과 정보 누수 방지

노트북 상단에서 초기 구간을 설정하고 Feature 표에 사용 조건과 유효 관측 수를 기록한다. 구간을 바꾸어 관계가 유지되는지 탐색할 수 있지만, 서로 다른 조건으로 계산한 결과를 같은 Feature처럼 비교하지 않는다.

전체 수명에서 계산한 knee point, 전체 구간 평균·기울기, 종료 cycle 수는 열화 설명에 활용할 수 있다. 초기 수명 예측 입력에서는 관측 시점 이후 정보를 사용하지 않는다. Batch 간 동일 물리 셀의 측정 연장이 확인되면 후속 학습·검증 분리에 반영한다.


Feature Engineering은 향후 모델링 목적에 맞게 초기 구간만 사용한다.

과제의 Scratch에서는 Regression에 초기 100 cycle,
Classification에 초기 5 cycle을 예시로 제시했다.

DAY 1에서는 실제 모델을 확정하기 전이므로,
분석 결과를 토대로 어떤 초기 구간이 적합한지 설명한다.

---

## 6. Multicollinearity 처리 전략

다음과 같은 Feature는 서로 강하게 연관될 수 있다.

```text
Tavg
Tmax
Tmin
```

또는:

```text
QD
QC
```

강한 상관이 확인되면 다음 중 하나를 제안할 수 있다.

- 대표 Feature 하나 선택
- 변화량 Feature로 대체
- 정규화/규제가 있는 모델 활용
- Tree-based 모델과 선형 모델의 차이 비교

실제 적용 여부는 EDA 결과를 근거로 결정한다.

---

## 7. Model Problem 선택

과제에서는 Regression과 Classification 중 하나를 선택해야 한다.

### Regression

Target:

```text
cycle_life
```

목표:

```text
초기 cycle Feature
→ 전체 Cycle Life 수치 예측
```

장점:

- 원래 Cycle Life 정보를 그대로 사용
- 수명 예측이라는 문제와 직접 연결

검토 요소:

- Target 분포
- 이상치
- 비선형 관계

---

### Classification

Target 예시:

```text
long-life / short-life
```

과제에서 제공된 기준을 참고하면:

```text
long-life: > 1000
short-life: < 500
```

다만 중간 구간을 어떻게 처리할지는 별도 전략이 필요하다.

검토 요소:

- 클래스 비율
- 중간 수명 셀 처리
- threshold 근거

---

## 8. 최종 선택 기준

문제 형태는 사전에 임의로 결정하지 않고 EDA 결과를 토대로 선택한다.

판단 기준 예:

```text
Cycle Life가 충분히 연속적이고 Feature와 연속적 관계가 확인됨
→ Regression

장/단 수명 그룹 간 초기 Feature 차이가 매우 명확함
→ Classification
```

---

## 9. 후보 모델 제안 방식

오늘은 실제 모델을 학습하지 않고 후보만 제시한다.

예:

### Regression 후보

```text
Linear Regression / Ridge / Lasso
Random Forest Regressor
Gradient Boosting 계열
```

### Classification 후보

```text
Logistic Regression
Random Forest Classifier
Gradient Boosting 계열
```

후보 모델은 EDA에서 확인한 다음 특성과 연결해 설명한다.

- 선형 관계 여부
- 비선형성
- Feature 수
- Multicollinearity
- 이상치

---

## 10. 최종 모델링 전략 문장 구조

최종 보고서에서는 다음 구조로 작성한다.

```text
EDA에서 A, B, C 특성을 확인하였다.

따라서 Target은 ○○로 정의하고,
문제 형태는 Regression/Classification으로 설정한다.

입력 Feature는 △△를 중심으로 구성하며,
□□ Feature는 중복성/불안정성 때문에 제외 또는 보조적으로 사용한다.

데이터 특성상 선형 모델과 비선형 모델을 후보로 비교할 예정이다.
```
