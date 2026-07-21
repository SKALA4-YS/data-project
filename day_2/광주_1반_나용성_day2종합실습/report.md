# End2End 데이터 분석 리포트 — Adult Census Income
_자동 생성: 2026-07-21 17:59:47_

## 1. 데이터 개요 (Pandas vs Polars)
- 원본: `https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data`
- Pandas shape: `(32561, 15)` / Polars shape: `(32561, 15)`
- shape 일치: **True** / 결측 수 일치: **True**

## 2. 결측치·중복 처리
- 중복 제거: **24행**
- 결측(컬럼별): `{'workclass': 1836, 'occupation': 1843, 'native-country': 583}`
- 처리 방식: 중복 제거 후, 결측은 ML 파이프라인 내 `SimpleImputer(최빈값)`로 대치
- 최종 행 수: **32,537** / income 분포: `{'<=50K': 24698, '>50K': 7839}`

## 3. 기술통계 (수치형)
```
            age  education-num  capital-gain  capital-loss  hours-per-week
count  32537.00       32537.00      32537.00      32537.00        32537.00
mean      38.59          10.08       1078.44         87.37           40.44
std       13.64           2.57       7387.96        403.10           12.35
min       17.00           1.00          0.00          0.00            1.00
25%       28.00           9.00          0.00          0.00           40.00
50%       37.00          10.00          0.00          0.00           40.00
75%       48.00          12.00          0.00          0.00           45.00
max       90.00          16.00      99999.00       4356.00           99.00
```

## 4. 상관계수
```
                  age  education-num  capital-gain  capital-loss  hours-per-week
age             1.000          0.036         0.078         0.058           0.069
education-num   0.036          1.000         0.123         0.080           0.148
capital-gain    0.078          0.123         1.000        -0.032           0.078
capital-loss    0.058          0.080        -0.032         1.000           0.054
hours-per-week  0.069          0.148         0.078         0.054           1.000
```

## 5. 통계 검정 (t-test)
- 대상: 소득 그룹(>50K vs <=50K)의 주당 근무시간(hours-per-week) 평균 차이
- 평균: >50K = **45.47h**, <=50K = **38.84h**
- 결과: t = 45.0950, p = < 1e-308 (극소값)
- **해석: p < 0.05 → 두 그룹의 근무시간 평균은 유의미한 차이가 있다.**

## 6. 핵심 인사이트 (다중 컬럼 분석)
- **성별 격차**: 고소득(>50K) 비율 — Male 30.6%, Female 11.0%
- **결혼상태**: `Married-civ-spouse` 그룹이 44.7%로 가장 높음
- **직업**: `Exec-managerial` 이 48.4%로 가장 높음
- **연령**: 고소득 평균 44.3세 vs 저소득 평균 36.8세

## 7. 시각화 산출물
- 정적(Seaborn 2×2): `outputs/seaborn_overview.png`
- 인터랙티브(Plotly): `outputs/income_by_education.html`, `outputs/income_by_occupation.html`

## 8. ML Pipeline 평가
- 모델: `LogisticRegression` (ColumnTransformer 전처리 포함)
- 정확도(accuracy): **0.8557**
- F1(macro): **0.7911** / F1(>50K): **0.675**
- 모델 저장: `outputs/model.joblib`
