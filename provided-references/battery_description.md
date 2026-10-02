## ESS - 전력망의 배터리

### WHY ESS?

- AIDC 전력 수요 폭증 : 2023 → 2030 데이터센터 소비 4배+ (전체 데이터센터는 2배)
- 재생에너지 변동성 대응 : 태양광/풍력 간헐성 해결 → ESS 필수 인프라
- 글로벌 BESS 시장 급팽창 : 2025년 설치량 300GWh 돌파, 전년 대비 +51%
- 배터리 수명 관리 = 핵심 경쟁력 : 교체 비용이 ESS CAPEX 30~40%

Reference : 

- AIDC 전력 수요 : https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai
- DC 165% 증가 전망 : https://www.goldmansachs.com/insights/articles/ai-to-drive-165-increase-in-data-center-power-demand-by-2030
- BESS 2025년 315GWh/+51% : https://www.ess-news.com/2026/01/20/global-bess-demand-jumps-51-in-2025-as-installations-top-300-gwh/
- BESS 시장 전망 2025-2030 : https://www.marketsandmarkets.com/Market-Reports/battery-energy-storage-system-market-112809494.html
- BESS 심층 분석 : https://climatedrift.substack.com/p/the-battery-energy-storage-system
- https://n.news.naver.com/mnews/article/277/0005816959

### 리튬이온 배터리

- 구성 요소
    - 양극 : 배터리 성능과 스펙을 결정짓는 요소
        - 배터리 전압 : 양극과 음극의 전위차에 의해 결정, 양극 구조에 따른 전위값이 전압에 큰 영향을 미침
        - 업계에서는 양극 성능 향상 위해 양극 활물질을 개선하는데 주력하고 있음
        - 활물질 (Active Material) : 에너지가 들어있는 물질. 리튬이온 배터리는 리튬금속산화물 사용
            - 알루미늄은 전류(전자)를 수집하는 역할 담당
            - 수집된 전류는 탭(전지의 극과 닿는 부분)을 통해 흐름
            - 충전 시에는 전자를 내주는 산화 반응이 일어나고, 방전 시에는 전자를 받는 환원 반응이 일어남
            - 이 때 산화와 환원 반응에 참여하는 것이 리튬금속산화물 ⇒ 배터리의 용량과 전압 결정
    - 음극 : 충전 시 양극에서 방출된 리튬이온을 저장했다가, 방전 시 다시 양극으로 방출하는 역할 (전류 공급원)
        - 구리 : 음극에서 전자를 수집하는 역할을 담당
        - 흑연 : 음극 활물질. 전자와 이온을 받았다가 내보내는 과정에서 물리적인 팽창과 수축 반복 ⇒ 배터리 수명에 영향 미침
    - 분리막 : 양극과 음극의 물리적인 접촉 막는 역할
        - 리튬이온 배터리는 양극과 음극이 닿게 되면 단락(Short) 발생하여 화재로 이어짐
        - 분리막은 이러한 상황을 막아주어 배터리의 안전성을 높이는데 중요한 역할 담당
    - 전해질 : 이온은 통과시키고, 전자는 출입하지 못하게 하여 외부 도선으로 이동 시킴
        - 리튬염을 유기 용매에 녹인 액체 형태가 일반적
        - 최근 고체 전해일(전고체 배터리) 연구 활발
  
---

- Lithium-ion : 가장 작고 가벼우면서 강력한 에너지를 오래낼 수 있는 효율성. 하지만 구조적으로 화재에 취약
    - 압도적인 에너지 밀도
        - 리튬은 금속 중 가장 가볍고 전자를 잃기 쉬운 성질을 가지고 있음
        - 이 덕분에 같은 무게나 부피 대비 훨씬 많은 에너지를 저장할 수 있음 ⇒ 경량화 & 고전압
    - 긴 수명과 관리의 편의성
        - 메모리 효과 없음 : 언제든 충전해도 용량 손실이 거의 없음
        - 긴 사이클 수명 : 보통 500회, 많게는 수천번까지 충방전 가능
        - 낮은 자가 방전율 : 사용하지 않을 때 배터리가 자연적으로 소모되는 비율이 한 달에 1.5~2% 미만으로 매우 낮음
    - 생태계와 기술 성숙도
        - 시장 지배력 : 현재 전기차 배터리 수요의 90% 이상 점유, 부품 수급이나 재활용 인프라가 리튬이온 중심으로 짜여져 있음
        - 다양한 변주 : 에너지 밀도가 높은 NCM(니켈, 코발트, 망간) 방식과, 가격이 저렴하고 안전한 LFP(리튬인산, 철) 방식 등으로 분화되어 용도에 맞게 선택할 수 있음
    - 구조적으로 화재와 폭발에 취약
        - 배터리 내부에서 이온이 이동하는 통로인 전해질은 주로 가연성 액체(유기 용매)로 이루어져 있음
        - 해당 전해질은 다음과 같은 상황에서 위험함 :
            - Thermal Runaway : 배터리가 과충전되거나 외부 충격을 받아 내부 온도가 일정 수준(약 130~150도)를 넘어서면 전해질이 기화하며 가스가 발생하고 내부 압력이 급증. 이 때 발생한 열이 주변 셀로 번지면 순식간에 폭발하는 화재
            - Dendrite 현상 : 충방전을 반복하다 보면 음격 표면에 리튬이 나뭇가지 모양의 결정(Dendrite)가 쌓임. 이 결정이 분리막을 뜷으면 단락이 발생해 화제 발생

---

- Next Generation
    - 전고체 배터리, All-Solid-State Battery
        - 원리 : 가연성 액체 전해질을 불에 타지 않는 고체 전해질로 교체
        - 안전성 : 고체 자체가 분리막 역할까지 담당. Dendrite 의한 단락 위험이 낮고, 열에 강해 폭발 위험이 거의 없음 (So called, 꿈의 배터리)
        - 상태 : 아직 제조 공정이 까다롭고 대당 단가가 너무 높아 양산화 단계에 머물러 있음
    - 나트륨 이온 배터리, Sodium-ion Battery
        - 원리 : 리튬 대신 나트륨 사용
        - 안전성 : 리튬 보다 화학적 반응성이 낮아 열적 안정성 높음. 방전 상태로 운송이 가능해 이동 중 화재 위험이 리튬이온 보다 현저히 낮음
        - 상태 : 리튬 보다 무겁고 에너지 밀도가 낮아 주행 거리가 중요한 장거리 전기차에는 부적합

---
- 충방전
    - 충전, Charge
        - 외부 전원이 에너지를 공급하면 반응이 시작됨
        - 양극의 리튬 이온이 전해질을 통해 음극으로 이동
        - 전자는 외부 회로 통해 음극으로 이동 : 리튬과 전자가 음극에 저장됨 ⇒ 음극에 에너지가 축적된 상태
    - 방전, Discharge
        - 부하(전구, 모터 등)에 연결되면 저장된 에너지가 방출됨
        - 음극의 리튬이온이 전해질 통해 다시 양극으로 복귀
        - 전자는 외부 회로를 흘러 부하에 전력 공급
        - 양극과 음극의 리튬 농도 차이가 전압을 만들어냄 ⇒ 농도가 줄수록 전압 하락
    - 열화, Degradation
        - 리튬 손실  : 충방전이 반복될수록 리튬이온이 전극에 영구 흡착되어 순환 가능한 리튬 감소(손실)
        - SEI 성장 : 음극 표현에 SEI(Solid Electrolyte Interphase, 고체 전해질 계면) 막이 두꺼워지며 내부 저항 증가
        - 양극 구조 붕괴 : 반복 충방전으로 결정 구조가 무너지며 용량 감소
        - 물리적 열화 : 전극 소재의 물리적 균열, 수축, 팽창이 누적되어 활물질 손실 발생
        
        ⇒ 결과적으로 용량(Capacity) 감소 → SOH 하락 → 결국 EOL(End of Life, 수명 종료) 도달

---
### Battery Index

- State
    - SOC, State of Charge
        - SOC = 현재 충전량 / 최대 충전 가능 용량 * 100 (%)
        - 배터리에 지금 얼마나 충전되어 있는지 (스마트폰 배터리 잔량과 동일한 개념)
        - BMS가 SOC를 기반으로 충방전 제어 및 과충방전 방지
    - SOH, State of Health
        - SOH = 현재 용량 / 초기 용량 * 100 (%)
        - 배터리가 얼마나 건강한지, SOH 80% 이하 → ESS 교체 기준
        - 100 사이클 후 SOH=95% → 아직 5% 열화
    - SOP, State of Power
        - SOP = 현재 출력 가능한 최대 전력 (W)
        - 지금 ESS가 얼마나 빠르게 충방전할 수 있는가
        - SOP 감소 → 피크 대응 능력 저하 신호
- Derived
    - RUL, Remaining Useful Life
        - RUL = EOL 도달까지 남은 사이클 수
        - 언제 교체해야 하는가? → 예지 보전 (PdM)의 핵심 타겟

---
### 배터리 교체 비용 = CAPEX 30~40%

- 예측 없이 운영하면
    - 갑자기 배터리 수명 종료 → 예기치 못한 설비 중단
    - 과도한 예방적 교체 → 불필요한 비용 발생
    - 용량 저하 예측 실패 → 피크 대응 불가 → 계약 위약금
    - ESS 1MWh 기준, 셀 교체 비용 $30,000 ~ $80,000
- 데이터 기반 수명 에측
    - 초기 100 사이클만으로 전체 수명 예측 가능
    - 최적 교체 시점을 사전 계획 가능 → 운영 비용 20~35% 절감
    - 열화 속도 예측 → 충방전 전략 최적화
    - 배터리 제조사 수율 선별 → 팩 구성 최적화

---
## MIT and Stanford Research

- *Data-driven prediction of battery cycle life before capacity degradation* (Nature Energy, 2019)
    
    https://www.nature.com/articles/s41560-019-0356-8

    ``` markdown
    **Abstract** 
    Accurately predicting the lifetime of complex, nonlinear systems such as lithium-ion batteries is critical for accelerating technology development. However, diverse aging mechanisms, significant device variability and dynamic operating conditions have remained major challenges. We generate a comprehensive dataset consisting of 124 commercial lithium iron phosphate/graphite cells cycled under fast-charging conditions, with widely varying cycle lives ranging from 150 to 2,300 cycles. Using discharge voltage curves from early cycles yet to exhibit capacity degradation, we apply machine-learning tools to both predict and classify cells by cycle life. Our best models achieve 9.1% test error for quantitatively predicting cycle life using the first 100 cycles (exhibiting a median increase of 0.2% from initial capacity) and 4.9% test error using the first 5 cycles for classifying cycle life into two groups. This work highlights the promise of combining deliberate data generation with data-driven modelling to predict the behaviour of complex dynamical systems.
    ```

---
### Regression - 배터리 수명 예측

- 초기 100 사이클 데이터만으로 배터리의 총 잔여 수명 충전(사이클 수) 예측
- 데이터 : 초기 100 사이클
- Target : `cycle_life` - EOL(80% SOH 도달)까지의 총 사이클 수
- 성능 : 테스트 오차 9.1%

---
### Classification - 배터리 수명 분류 (Binary)

- 단 5 사이클만으로 배터리의 장/단 수명을 즉시 선별 → 제조 직후 빠른 스크리닝 목표
- 데이터 : 초기 5 사이클
- Target : `cycle_life` 이진화한 파생 변수로 정의
    
    ```python
    # cycle_life 기준 550사이클로 이진 레이블 생성
    df['label'] = (df['cycle_life'] >= 550).astype(int)
    # 1 = 장수명(Long-life), 0 = 단수명(Short-life)
    ```
    
- 성능 : 테스트 오차 4.9% (1-Accuracy)

---
### Features

- Descriptors : 배터리 수준 스칼라
    - `cycle_life` : EOL(80% 용량)까지 총 사이클 수 ⇒ Target Variable
    - `charging_policy` : 충전 프로토콜 (e.g. : `"4.8C(80%)-3.6C"`- 용량의 80%까지 4.8C 속도로 빠르게 충전하고, 이후 나머지는 3.6C로 천천히 충전한다)
- Summary : 사이클별 요약 스칼라
    - `QD` : 방전 용량 (Ah)
    - `Qc` : 충전 용량 (Ah)
    - `IR` : 내부 저항 (Ohm)
    - `Tmax` / `Tavg` / `Tmin` : 사이클 내 최고, 평균, 최저 온도
    - `chargetime` : 충전 소요 시간
    - `discharge_time` : 방전 소요 시간
- Cycles : 사이클 내부 시계열
    - `t` : 시간 (분)
    - `V` : 전압 (V)
    - `I` : 전류 (A)
    - `T` : 온도 (°C)
    - `Qc`/ `Qd` : 충전/방전 용량
    - `Qdlin` : `ΔQ(V)` 곡선 계산의 기반 데이터, 전압 축으로 선형 보간된 방전 용량 (1,000포인트, 2V ~ 3.6V)
    - `Tdlin` : 전압 축으로 선형 보간된 온도 (1,000 포인트)
    - `discharge_dQdV` : 방전 dQ/dV 곡선 (파생변수)