## DAY 2 - 모델 개발 및 평가

모델 설계 전략을 기반으로 **최적의 모델을 개발**하고, 논문에서 제시한 성능(Target)과 비교

- Modeling (mandatory)
    - Batch 1을 학습 데이터셋으로, Batch 2를 테스트 데이터셋
- additional (not mandatory)
    - 개발한 최적 모델로 Batch 3 테스트 데이터셋으로 추가 성능 검증
    - 단 Batch 3 데이터셋은 배치 간 차이 있어 성능이 떨어질 수 있음
    - Batch 3 (Optional) :
        - Cycle Life 분포가 배치 별로 상이 : Batch 1/2는 유사하지만, Batch 3는 분포 차이 있음
        - 충전 커브 시작 시점이 배치별로 상이 : `Qdlin` 변수를 단순 비교하면 왜곡 발생
        - 이상치 제거 고려 : 배치 수집 시기 사이에 수개월 공백이 있어, 일부 셀은 데이터 품질 문제로 원논문에서도 제거됨

---
### Performance Reporting

모델 성능은 아래 항목으로 구분하며, Format 맞춰 작성함 

- Index :
    - Train (Batch 1 CV) : Batch 1 내 Cross-Validation 평균 성능
    - Valid (Batch 1 Hold-out) : Batch 1 내 Hold-out 검증 성능
        - Valid를 CV가 아닌 Hold-out으로 사용하는 이유 :
            - 배터리 데이터는 셀 단위로 독립적이며, 각 셀이 서로 다른 충전 프로토콜(C-rate)로 실험됨
            - 이 경우 CV를 적용하면 동일 프로토콜 셀이 train/valid에 나뉘어 들어가 데이터 누수(leakage) 위험 잔존
            - Hold-out은 셀 단위 분리를 명확히 보장하며, 배치 간 일반화를 평가하는 이번 프로젝트 구조에서 더 적합
    - Test (Batch 2) : Batch 2 최종 평가 성능
    - Gap (Train-Valid) : Train 과적합 확인
    - Gap (Valid-Test) : 배치 간 일반화 차이 확인
    - Gap (Target-Test) : 원논문 성능 대비 차이
        - 원논문 성능 : Regression 9.1%(MAPE), Classification 4.9%(1-Accuracy)
        - Performace Metric
            - Regression : MAPE
            - Regression : F1-Score, Accuracy
- Format :
## Reporting format (for Regression)

| 구분 | MAPE (%) | 비고 |
|---|---:|---|
| Train (Batch 1 CV) |  |  |
| Valid (Batch 1 Hold-out) |  |  |
| Test (Batch 2) |  |  |
| Gap (Train-Valid) |  | (+) : 과적합 의심 |
| Gap (Valid-Test) |  | (+) : 배치간 일반화 저하 의심 |
| Gap (Target-Test) |  | Target : 원논문 9.1% |