# 질문별 그래프 목록

관찰과 해석을 작성하기 전 직접 살펴볼 이미지 9개입니다. 각 그림은 세 Batch를 포함합니다.

| 번호 | 요구 질문 | 이미지 |
|---|---|---|
| 01 | Q1 수명 분포·이상치 위치 | [Histogram 및 Box plot](01_q1_cycle_life_distribution.png) |
| 02 | Q1 장·중·단수명 비율 | [그룹 비율](02_q1_life_group_ratios.png) |
| 03 | Q2 용량 변화·열화 곡선 | [전체·초기·용량 확대](03_q2_degradation_curves.png) |
| 04 | Q3 장·단수명 ΔQ(V) 곡선 | [개별 곡선 및 그룹 중앙값](04_q3_delta_q_curves.png) |
| 05 | Q3 통계 Feature | [ΔQ(V) 분산과 수명](05_q3_delta_q_variance.png) |
| 06 | Q4 충전 프로토콜과 수명 | [정책별 개별 수명·평균·표준편차](06_q4_policy_lifetime.png) |
| 07 | Q4 충전 시간·전류와의 관계 | [충전 지표와 수명·초기 용량 기울기](07_q4_charging_relationships.png) |
| 08 | Q5 초기 Feature와 수명 | [Pearson·Spearman 및 유효 셀 수](08_q5_target_correlations.png) |
| 09 | Q5 Feature 간 상관 | [상관행렬](09_q5_feature_correlations.png) |

## 재생성

프로젝트 `.venv` 커널에서 `notebooks/02_question_graphs.ipynb`를 위에서부터 전체 실행합니다. 그래프의 개별 표시·저장 함수는 `src/question_gallery.py`에 있습니다.

## 표시와 계산 조건

- 초기 Feature 구간: summary cycle 10–100. ΔQ(V): cycle 100 − cycle 10.
- 상세 cycle 위치는 summary 번호에서 찾아 Qd 최댓값과 summary QD의 일치를 확인합니다. 전압 격자·유한값도 검증합니다.
- 원본 셀과 수명은 보존합니다. QD/IR의 비유한값·0 이하 값만 해당 분석용 열에서 NaN으로 표시합니다. 높은 양의 QD값은 제외하지 않습니다.
- Q2 마지막 행은 0.8–1.15 Ah 범위 확대이며, 범위 밖 점 수를 표시합니다. 첫 행에는 전체 범위가 있습니다.
- 수명 그룹: <500 / 500–1000(양끝 포함) / >1000 / 수명 값 없음.
- 전류 I·충전 시간 지표는 원본 단위이며 A 또는 완충 시간으로 환산하지 않습니다.
- 상관계수는 변수 쌍별 유효 관측을 사용합니다. 결측 대체·모델 학습·셀 병합·타깃 재계산은 수행하지 않습니다.
- IQR 표시는 통계적 위치 표시이며 측정 오류 판정이 아닙니다. 정책별 ±1 표준편차는 신뢰구간이 아닙니다.

계산에 사용한 셀별 값은 `cell_features_for_gallery.csv`, 위치 검증은 `cycle_alignment_audit.csv`, 그림 목록과 설정은 `gallery_metadata.json`에 저장합니다. 원본 파일은 수정하지 않습니다.
