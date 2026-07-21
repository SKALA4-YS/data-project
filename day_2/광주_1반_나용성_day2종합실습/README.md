# Day 2 종합실습 — End2End 데이터 분석 (Adult Census Income)

UCI Adult Census Income 데이터로 **데이터 준비 → 시각화 → 통계 분석 → ML Pipeline → 리포트 자동화**까지 수행하는 End2End 파이프라인.

## 구성

| 파일 | 역할 |
|------|------|
| `main.py` | 전체 파이프라인 (데이터/시각화/통계/ML/report.md 자동생성) |
| `report.md` | 실행 시 **자동 생성**되는 분석 리포트 |
| `outputs/seaborn_corr.png` | Seaborn 정적 차트 (상관 히트맵) |
| `outputs/income_by_education.html` | Plotly 인터랙티브 차트 (교육수준별 고소득 비율) |
| `outputs/model.joblib` | 저장된 ML Pipeline 모델 |

## 주요 처리

- **데이터**: Pandas·Polars 양쪽 로딩 후 shape·결측 수 비교 (일치 확인)
- **결측치**: `?` → `na_values="?"` 로 인식(4,262건), ML 파이프라인 내 `SimpleImputer(최빈값)` 대치
- **중복**: 24행 제거
- **통계**: 기술통계·상관계수 + 소득 그룹별 근무시간 t-test (p<0.05 해석)
- **ML**: `ColumnTransformer + LogisticRegression` Pipeline → income(>50K) 예측, 정확도·F1 출력, joblib 저장

## 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py        # 콘솔 출력 + outputs/ 생성 + report.md 자동 생성
```

## 데이터 주의사항

원본은 결측을 `?` 로 표기한다. `skipinitialspace=True` 가 앞 공백을 제거하므로
`na_values="?"` 로 지정해야 결측이 올바르게 인식된다. (`" ?"` 로 두면 결측 0건으로 잘못 잡힘)
