"""
================================================================================
[실습 4] 시각화 4종 · 통계 검정 · sklearn Pipeline (실습 3 연계)
--------------------------------------------------------------------------------
프로그램 설명
  실습 3의 산출물(IQR 이상치 제거된 DataFrame, region·category 집계)을 이어받아
  sales_100k.csv 를 대상으로 아래를 수행한다.
    1) EDA 시각화 4종 : plt.subplots(2,2) 한 figure 에
                       히스토그램+KDE / 지역별 박스플롯 / 월별 총매출 라인 / 상관 히트맵
    2) 통계 검정      : 서울 vs 부산 매출 t-test, region×category 카이제곱 (p<0.05 해석)
    3) sklearn Pipeline: ColumnTransformer + LogisticRegression 을 Pipeline 으로 구성,
                        fit·predict·score 후 joblib 저장 및 재로딩
    4) Plotly         : 지역·카테고리별 총매출 막대차트를 .html 로 저장

실습 3 연계
  - IQR 정상 범위(Q1-1.5*IQR ~ Q3+1.5*IQR)로 이상치를 제거한 DataFrame 을 입력으로 사용
  - region·category 집계를 Plotly 차트/카이제곱 분할표의 기반 변수로 활용

변경내역 (Change History)
  2026-07-21  v1.0  최초 작성 - 시각화 4종 + 통계검정 + Pipeline 저장/재로딩 + Plotly

작성자 : 광주_1반_나용성
================================================================================
"""

from pathlib import Path

import joblib
import matplotlib
import pandas as pd
import plotly.express as px
import seaborn as sns
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

matplotlib.use("Agg")  # 파일 저장 전용 백엔드 (GUI 불필요)
import matplotlib.pyplot as plt  # noqa: E402

# 한글 폰트 설정 (차트 라벨 깨짐 방지)
plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "sales_100k.csv"
OUTPUT_DIR = BASE_DIR / "practice4_outputs"
PNG_PATH = OUTPUT_DIR / "eda_2x2.png"
MODEL_PATH = OUTPUT_DIR / "model.joblib"
HTML_PATH = OUTPUT_DIR / "sales_chart.html"

REQUIRED_COLS = {
    "order_date", "region", "category", "quantity", "unit_price",
    "customer_age", "payment_method", "customer_gender", "amount",
}
IQR_K = 1.5
VIZ_SAMPLE_N = 50_000    # 시각화용 샘플 (렌더링 속도)
ML_SAMPLE_N = 100_000    # 모델 학습용 샘플 (속도)
RANDOM_STATE = 42


# =========================================================================
# 데이터 로드 + 실습 3 연계 정제 (IQR 이상치 제거)
# =========================================================================
def load_and_clean(path: Path) -> pd.DataFrame:
    """CSV 로드 → order_date 파싱 → IQR 이상치 제거 → 그룹 키 결측 제거."""
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except FileNotFoundError:
        raise SystemExit(f"[오류] 데이터 파일을 찾을 수 없습니다: {path}")
    except pd.errors.EmptyDataError:
        raise SystemExit(f"[오류] 데이터 파일이 비어 있습니다: {path}")

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise SystemExit(f"[오류] 필수 컬럼이 없습니다: {missing}")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # 실습 3과 동일: IQR 정상 범위로 amount 이상치 제거 + 그룹 키 결측 제거
    q1, q3 = df["amount"].quantile(0.25), df["amount"].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - IQR_K * iqr, q3 + IQR_K * iqr
    clean = df[
        df["amount"].between(lower, upper)
        & df["region"].notna()
        & df["category"].notna()
    ].copy()
    return clean


# =========================================================================
# 1) EDA 시각화 4종 (2×2 서브플롯)
# =========================================================================
def task1_visualize(df: pd.DataFrame, out_path: Path) -> None:
    """히스토그램+KDE / 박스플롯 / 월별 라인 / 상관 히트맵을 한 figure 에 그린다."""
    viz = df.sample(n=min(VIZ_SAMPLE_N, len(df)), random_state=RANDOM_STATE)
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))

    # (0,0) 매출액 히스토그램 + KDE
    sns.histplot(viz["amount"], kde=True, ax=axes[0, 0], color="steelblue")
    axes[0, 0].set_title("① 매출액 분포 (히스토그램 + KDE)")

    # (0,1) 지역별 매출 박스플롯
    sns.boxplot(data=viz, x="region", y="amount", ax=axes[0, 1])
    axes[0, 1].set_title("② 지역별 매출 박스플롯")

    # (1,0) 월별 총매출 라인 (전체 데이터 기준)
    monthly = df.groupby(df["order_date"].dt.to_period("M"))["amount"].sum()
    axes[1, 0].plot(monthly.index.astype(str), monthly.values, marker="o")
    axes[1, 0].set_title("③ 월별 총매출 추이")
    axes[1, 0].tick_params(axis="x", rotation=45)

    # (1,1) 수치형 변수 상관 히트맵
    corr = df[["quantity", "unit_price", "customer_age", "amount"]].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=axes[1, 1])
    axes[1, 1].set_title("④ 수치형 변수 상관 히트맵")

    fig.tight_layout()
    fig.savefig(out_path, dpi=100)
    plt.close(fig)


# =========================================================================
# 2) 통계 검정 (t-test + 카이제곱, p<0.05 해석)
# =========================================================================
def task2_stat_tests(df: pd.DataFrame) -> None:
    """서울 vs 부산 t-test 와 region×category 카이제곱 검정을 수행/해석한다."""
    # t-test: 두 지역(서울/부산)의 평균 매출 차이
    seoul = df.loc[df["region"] == "서울", "amount"]
    busan = df.loc[df["region"] == "부산", "amount"]
    t_stat, t_p = stats.ttest_ind(seoul, busan, equal_var=False)  # Welch t-test
    print(f"[t-test] 서울 vs 부산 평균 매출 → t={t_stat:.4f}, p={t_p:.4g}")
    if t_p < 0.05:
        print("  해석: p<0.05 → 두 지역의 평균 매출에 통계적으로 유의미한 차이가 있다.")
    else:
        print("  해석: p>=0.05 → 두 지역 평균 매출 차이는 유의미하지 않다.")

    # 카이제곱: region × category 독립성
    table = pd.crosstab(df["region"], df["category"])
    chi2, chi_p, dof, _ = stats.chi2_contingency(table)
    print(f"\n[chi2] region×category 독립성 → chi2={chi2:.4f}, p={chi_p:.4g}, dof={dof}")
    if chi_p < 0.05:
        print("  해석: p<0.05 → 지역과 카테고리는 독립이 아니다(연관성 있음).")
    else:
        print("  해석: p>=0.05 → 지역과 카테고리는 서로 독립이다(연관성 없음).")


# =========================================================================
# 3) sklearn Pipeline 구성 + 저장 + 재로딩
# =========================================================================
def task3_pipeline(df: pd.DataFrame, model_path: Path) -> None:
    """ColumnTransformer + LogisticRegression 을 Pipeline 으로 구성/학습/저장/재로딩.

    타깃은 customer_gender(이진 분류). 합성 데이터라 정확도는 baseline 수준이며,
    본 실습의 목적은 성능이 아니라 Pipeline 구조와 저장/재로딩 시연이다.
    """
    data = df.sample(n=min(ML_SAMPLE_N, len(df)), random_state=RANDOM_STATE)
    num_features = ["quantity", "unit_price", "customer_age", "amount"]
    cat_features = ["region", "category", "payment_method"]
    x = data[num_features + cat_features]
    y = data["customer_gender"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    # 전처리(수치 표준화 + 범주 원핫)와 모델을 하나의 Pipeline 으로 묶는다.
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
        ]
    )
    pipe = Pipeline(
        steps=[
            ("prep", preprocessor),
            ("model", LogisticRegression(max_iter=1000)),
        ]
    )

    pipe.fit(x_train, y_train)
    preds = pipe.predict(x_test)
    acc = pipe.score(x_test, y_test)
    print(f"[Pipeline] 학습 완료 · 테스트 정확도(accuracy) = {acc:.4f}")
    print(f"  예측 샘플 5건: {list(preds[:5])}")

    # joblib 으로 모델 저장 후 재로딩하여 동일 성능 확인
    joblib.dump(pipe, model_path)
    loaded = joblib.load(model_path)
    acc_reloaded = loaded.score(x_test, y_test)
    print(f"  모델 저장 → {model_path.name}")
    print(f"  재로딩 모델 정확도 = {acc_reloaded:.4f} (동일 여부: {acc == acc_reloaded})")


# =========================================================================
# 4) Plotly 인터랙티브 막대차트 저장
# =========================================================================
def task4_plotly(df: pd.DataFrame, html_path: Path) -> None:
    """지역·카테고리별 총매출을 Plotly Express 막대차트로 만들어 html 로 저장한다."""
    agg = (
        df.groupby(["region", "category"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total"})
    )
    fig = px.bar(
        agg,
        x="region",
        y="total",
        color="category",
        barmode="group",
        title="지역·카테고리별 총매출",
    )
    fig.write_html(html_path)  # fig.show() 가 아니라 파일로 저장
    print(f"[Plotly] 인터랙티브 차트 저장 → {html_path.name}")


# =========================================================================
# main
# =========================================================================
def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = load_and_clean(CSV_PATH)
    print(f"정제 후 데이터: {len(df):,}행\n")

    try:
        print("=== 1) EDA 시각화 4종 (2×2 서브플롯) ===")
        task1_visualize(df, PNG_PATH)
        print(f"2×2 차트 저장 → {PNG_PATH.name}\n")

        print("=== 2) 통계 검정 (t-test + 카이제곱) ===")
        task2_stat_tests(df)

        print("\n=== 3) sklearn Pipeline ===")
        task3_pipeline(df, MODEL_PATH)

        print("\n=== 4) Plotly 인터랙티브 차트 ===")
        task4_plotly(df, HTML_PATH)
    except (KeyError, ValueError) as e:
        raise SystemExit(f"[오류] 분석 처리 중 문제가 발생했습니다: {e}")

    print("\n✅ 실습 4 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
