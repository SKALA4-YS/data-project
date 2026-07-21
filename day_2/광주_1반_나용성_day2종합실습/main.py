"""
================================================================================
[Day 2 종합실습] End2End 데이터 분석 프로젝트 — Adult Census Income
--------------------------------------------------------------------------------
프로그램 설명
  UCI Adult Census Income 데이터를 대상으로 다음을 수행하고 report.md 를 자동 생성한다.
    1) 데이터 준비 : Pandas·Polars 양쪽 로딩 후 비교, 결측치·중복 처리, 기본 EDA
    2) 시각화      : Seaborn 정적(2×2 다중 패널) + Plotly 인터랙티브 2종
                     - 상관관계 / 성별·결혼상태·직업별 소득비율 / 연령 분포 등 다중 컬럼 활용
    3) 통계 분석   : 기술통계(평균·표준편차·분위수), 상관계수, t-test + p-value 해석
    4) ML Pipeline : ColumnTransformer+LogisticRegression 을 Pipeline 으로 구성,
                     정확도·F1 출력, joblib 로 모델 저장
    5) 자동화      : 위 결과와 핵심 인사이트를 report.md 로 자동 생성

데이터 주의
  원본은 결측을 '?' 로 표기한다. skipinitialspace 로 앞 공백을 제거하므로
  na_values='?' 로 지정해야 결측(4,262건)이 올바르게 인식된다. (' ?' 로 두면 0건)

변경내역 (Change History)
  2026-07-21  v1.0  최초 작성 - 데이터준비/시각화/통계/ML/report.md 자동생성
  2026-07-21  v1.1  시각화 다중 컬럼 확장(성별·연령·결혼·직업) + 핵심 인사이트 자동화

작성자 : 광주_1반_나용성
================================================================================
"""

import urllib.request
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib
import pandas as pd
import plotly.express as px
import polars as pl
import seaborn as sns
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

matplotlib.use("Agg")  # 파일 저장 전용 백엔드
import matplotlib.pyplot as plt  # noqa: E402

sns.set_theme(style="whitegrid", font="AppleGothic")  # 한글 폰트
plt.rcParams["axes.unicode_minus"] = False

# ---- 경로/상수 ----------------------------------------------------------
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_CACHE = OUTPUT_DIR / "adult_raw.data"
SEABORN_PNG = OUTPUT_DIR / "seaborn_overview.png"
PLOTLY_EDU = OUTPUT_DIR / "income_by_education.html"
PLOTLY_OCC = OUTPUT_DIR / "income_by_occupation.html"
MODEL_PATH = OUTPUT_DIR / "model.joblib"
REPORT_PATH = BASE_DIR / "report.md"

DATA_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
COLS = [
    "age", "workclass", "fnlwgt", "education", "education-num", "marital-status",
    "occupation", "relationship", "race", "sex", "capital-gain", "capital-loss",
    "hours-per-week", "native-country", "income",
]
NUMERIC = ["age", "education-num", "capital-gain", "capital-loss", "hours-per-week"]
TARGET = "income"
RANDOM_STATE = 42
# 소득 2범주 색상(색맹 안전 쌍) — 모든 차트에서 일관 사용
INCOME_PALETTE = {"<=50K": "#4C78A8", ">50K": "#F58518"}
LOW_COLOR, HIGH_COLOR = INCOME_PALETTE["<=50K"], INCOME_PALETTE[">50K"]


# =========================================================================
# 1) 데이터 준비 (다운로드 → Pandas·Polars 로딩 → 비교 → 결측·중복 처리)
# =========================================================================
def ensure_dataset(url: str, cache_path: Path) -> Path:
    """원본 데이터를 1회 다운로드해 로컬 캐시로 둔다 (두 라이브러리 공통 입력)."""
    if not cache_path.exists():
        try:
            urllib.request.urlretrieve(url, cache_path)
        except Exception as e:  # 네트워크/URL 오류
            raise SystemExit(f"[오류] 데이터 다운로드 실패: {e}")
    return cache_path


def load_pandas(path: Path) -> pd.DataFrame:
    """Pandas 로딩: 앞 공백 제거 + '?' 를 결측으로 인식."""
    return pd.read_csv(path, header=None, names=COLS, na_values="?", skipinitialspace=True)


def load_polars(path: Path) -> pl.DataFrame:
    """Polars 로딩: ' ?' 결측 처리 + 문자열 공백 제거 + 빈 행 제거."""
    df = pl.read_csv(path, has_header=False, new_columns=COLS, null_values=" ?")
    str_cols = [c for c, dt in zip(df.columns, df.dtypes) if dt == pl.String]
    df = df.with_columns([pl.col(c).str.strip_chars() for c in str_cols])
    return df.filter(~pl.all_horizontal(pl.all().is_null()))  # 원본 끝 빈 행 제거


def compare_loading(pdf: pd.DataFrame, pldf: pl.DataFrame) -> dict:
    """Pandas 와 Polars 로딩 결과(shape·결측 수)를 비교한다."""
    return {
        "pandas_shape": pdf.shape,
        "polars_shape": (pldf.height, pldf.width),
        "shape_match": pdf.shape == (pldf.height, pldf.width),
        "missing_match": int(pdf.isnull().sum().sum()) == int(pldf.null_count().to_numpy().sum()),
    }


def prepare(pdf: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """중복 제거 + 결측/EDA 요약을 반환한다. (결측은 ML 파이프라인에서 대치)"""
    dup = int(pdf.duplicated().sum())
    df = pdf.drop_duplicates().reset_index(drop=True)
    missing = pdf.isnull().sum()
    summary = {
        "n_rows": len(df),
        "duplicates_removed": dup,
        "missing": {k: int(v) for k, v in missing.items() if v > 0},
        "income_dist": df[TARGET].value_counts().to_dict(),
    }
    return df, summary


# =========================================================================
# 2) 시각화 (Seaborn 정적 2×2 + Plotly 인터랙티브 2종) — 다중 컬럼 활용
# =========================================================================
def high_income_rate(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """범주형 col 별 고소득(>50K) 비율(%)과 표본수를 내림차순으로 계산한다."""
    return (
        df.dropna(subset=[col])
        .assign(high=(df[TARGET] == ">50K").astype(int))
        .groupby(col, as_index=False)
        .agg(rate=("high", "mean"), n=("high", "size"))
        .assign(pct=lambda d: (d["rate"] * 100).round(1))
        .sort_values("pct", ascending=False)
    )


def make_seaborn_overview(df: pd.DataFrame, path: Path) -> None:
    """2×2 정적 패널: ①상관 히트맵 ②성별 ③연령분포 ④결혼상태 (다중 컬럼)."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))

    # ① 수치형 상관 히트맵 (상관관계)
    sns.heatmap(
        df[NUMERIC].corr(), annot=True, fmt=".2f", cmap="RdBu_r", center=0,
        vmin=-1, vmax=1, square=True, linewidths=0.5,
        cbar_kws={"label": "상관계수"}, ax=axes[0, 0],
    )
    axes[0, 0].set_title("① 수치형 변수 상관 히트맵")

    # ② 성별 고소득 비율 (그룹 비교)
    sx = high_income_rate(df, "sex")
    sns.barplot(data=sx, x="sex", y="pct", order=sx["sex"], color=HIGH_COLOR, ax=axes[0, 1])
    axes[0, 1].set_title("② 성별 고소득(>50K) 비율")
    axes[0, 1].set(xlabel="성별", ylabel=">50K 비율 (%)")
    for i, r in enumerate(sx.itertuples()):
        axes[0, 1].text(i, r.pct, f"{r.pct}%", ha="center", va="bottom")

    # ③ 연령 분포 (소득별) (분포)
    sns.histplot(
        data=df, x="age", hue=TARGET, kde=True, bins=30,
        palette=INCOME_PALETTE, ax=axes[1, 0],
    )
    axes[1, 0].set_title("③ 연령 분포 (소득 수준별)")
    axes[1, 0].set(xlabel="나이", ylabel="인원수")

    # ④ 결혼상태별 고소득 비율 (그룹 비교)
    ms = high_income_rate(df, "marital-status")
    sns.barplot(data=ms, x="pct", y="marital-status", order=ms["marital-status"],
                color=LOW_COLOR, ax=axes[1, 1])
    axes[1, 1].set_title("④ 결혼상태별 고소득(>50K) 비율")
    axes[1, 1].set(xlabel=">50K 비율 (%)", ylabel="결혼상태")

    fig.tight_layout()
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def _rate_bar_html(df: pd.DataFrame, col: str, title: str, xlabel: str, path: Path) -> None:
    """범주별 >50K 비율 가로 막대(Plotly, 인터랙티브)를 html 로 저장하는 공통 함수."""
    data = high_income_rate(df, col)
    fig = px.bar(
        data, x="pct", y=col, orientation="h", hover_data={"n": True},
        title=title, labels={"pct": ">50K 비율 (%)", col: xlabel},
    )
    fig.update_traces(marker_color=HIGH_COLOR)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.write_html(path)  # fig.show() 가 아니라 파일 저장


def make_plotly_charts(df: pd.DataFrame) -> None:
    """교육수준별·직업별 고소득 비율 인터랙티브 차트 2종을 저장한다."""
    _rate_bar_html(df, "education", "교육수준별 고소득(>50K) 비율", "교육수준", PLOTLY_EDU)
    _rate_bar_html(df, "occupation", "직업별 고소득(>50K) 비율", "직업", PLOTLY_OCC)


# =========================================================================
# 3) 통계 분석 (기술통계 + 상관계수 + t-test)
# =========================================================================
def descriptive_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """기술통계(평균·표준편차·분위수)와 상관계수 행렬을 반환한다."""
    desc = df[NUMERIC].describe().round(2)
    corr = df[NUMERIC].corr().round(3)
    return desc, corr


def run_ttest(df: pd.DataFrame) -> dict:
    """소득 그룹(>50K vs <=50K)의 주당 근무시간 평균 차이를 t-test 로 검정."""
    high = df.loc[df[TARGET] == ">50K", "hours-per-week"]
    low = df.loc[df[TARGET] == "<=50K", "hours-per-week"]
    t_stat, p_val = stats.ttest_ind(high, low, equal_var=False)  # Welch
    p_display = f"{p_val:.4g}" if p_val > 0 else "< 1e-308 (극소값)"
    return {
        "t": float(t_stat), "p": float(p_val), "p_display": p_display,
        "sig": p_val < 0.05,
        "mean_high": round(high.mean(), 2), "mean_low": round(low.mean(), 2),
    }


def compute_insights(df: pd.DataFrame) -> dict:
    """다중 컬럼(성별·결혼·직업·연령)에서 핵심 결론을 자동 추출한다."""
    sx = high_income_rate(df, "sex")
    ms = high_income_rate(df, "marital-status")
    occ = high_income_rate(df, "occupation")
    return {
        "sex_rate": dict(zip(sx["sex"], sx["pct"])),
        "marital_top": (ms.iloc[0]["marital-status"], float(ms.iloc[0]["pct"])),
        "occ_top": (occ.iloc[0]["occupation"], float(occ.iloc[0]["pct"])),
        "age_high": round(df.loc[df[TARGET] == ">50K", "age"].mean(), 1),
        "age_low": round(df.loc[df[TARGET] == "<=50K", "age"].mean(), 1),
    }


# =========================================================================
# 4) ML Pipeline (전처리 + 모델 → 평가 → 저장)
# =========================================================================
def build_and_evaluate(df: pd.DataFrame, model_path: Path) -> dict:
    """ColumnTransformer + LogisticRegression Pipeline 으로 income 을 예측한다.

    수치는 표준화, 범주는 최빈값 대치 후 원핫 인코딩한다. (결측 처리 = 파이프라인 내부)
    """
    x = df.drop(columns=[TARGET, "fnlwgt", "education"])  # 타깃·가중치·중복(education) 제외
    y = df[TARGET]
    cat_features = [c for c in x.columns if c not in NUMERIC]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC),
            ("cat", Pipeline([
                ("impute", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), cat_features),
        ]
    )
    pipe = Pipeline([("prep", preprocessor), ("model", LogisticRegression(max_iter=1000))])

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    pipe.fit(x_train, y_train)
    pred = pipe.predict(x_test)

    metrics = {
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "f1_macro": round(f1_score(y_test, pred, average="macro"), 4),
        "f1_high": round(f1_score(y_test, pred, pos_label=">50K"), 4),
    }
    joblib.dump(pipe, model_path)
    return metrics


# =========================================================================
# 5) report.md 자동 생성
# =========================================================================
def generate_report(ctx: dict, path: Path) -> None:
    """분석 결과(ctx)를 종합해 report.md 를 자동 생성한다."""
    load, prep, tt, metrics, ins = (
        ctx["load"], ctx["prep"], ctx["ttest"], ctx["metrics"], ctx["insights"]
    )
    sig_txt = "유의미한 차이가 있다" if tt["sig"] else "유의미하지 않다"
    sex_txt = ", ".join(f"{k} {v}%" for k, v in ins["sex_rate"].items())
    lines = [
        "# End2End 데이터 분석 리포트 — Adult Census Income",
        f"_자동 생성: {datetime.now():%Y-%m-%d %H:%M:%S}_",
        "",
        "## 1. 데이터 개요 (Pandas vs Polars)",
        f"- 원본: `{DATA_URL}`",
        f"- Pandas shape: `{load['pandas_shape']}` / Polars shape: `{load['polars_shape']}`",
        f"- shape 일치: **{load['shape_match']}** / 결측 수 일치: **{load['missing_match']}**",
        "",
        "## 2. 결측치·중복 처리",
        f"- 중복 제거: **{prep['duplicates_removed']}행**",
        f"- 결측(컬럼별): `{prep['missing']}`",
        "- 처리 방식: 중복 제거 후, 결측은 ML 파이프라인 내 `SimpleImputer(최빈값)`로 대치",
        f"- 최종 행 수: **{prep['n_rows']:,}** / income 분포: `{prep['income_dist']}`",
        "",
        "## 3. 기술통계 (수치형)",
        "```",
        ctx["desc"].to_string(),
        "```",
        "",
        "## 4. 상관계수",
        "```",
        ctx["corr"].to_string(),
        "```",
        "",
        "## 5. 통계 검정 (t-test)",
        "- 대상: 소득 그룹(>50K vs <=50K)의 주당 근무시간(hours-per-week) 평균 차이",
        f"- 평균: >50K = **{tt['mean_high']}h**, <=50K = **{tt['mean_low']}h**",
        f"- 결과: t = {tt['t']:.4f}, p = {tt['p_display']}",
        f"- **해석: p {'<' if tt['sig'] else '>='} 0.05 → 두 그룹의 근무시간 평균은 {sig_txt}.**",
        "",
        "## 6. 핵심 인사이트 (다중 컬럼 분석)",
        f"- **성별 격차**: 고소득(>50K) 비율 — {sex_txt}",
        f"- **결혼상태**: `{ins['marital_top'][0]}` 그룹이 {ins['marital_top'][1]}%로 가장 높음",
        f"- **직업**: `{ins['occ_top'][0]}` 이 {ins['occ_top'][1]}%로 가장 높음",
        f"- **연령**: 고소득 평균 {ins['age_high']}세 vs 저소득 평균 {ins['age_low']}세",
        "",
        "## 7. 시각화 산출물",
        f"- 정적(Seaborn 2×2): `{SEABORN_PNG.relative_to(BASE_DIR)}`",
        f"- 인터랙티브(Plotly): `{PLOTLY_EDU.relative_to(BASE_DIR)}`, "
        f"`{PLOTLY_OCC.relative_to(BASE_DIR)}`",
        "",
        "## 8. ML Pipeline 평가",
        "- 모델: `LogisticRegression` (ColumnTransformer 전처리 포함)",
        f"- 정확도(accuracy): **{metrics['accuracy']}**",
        f"- F1(macro): **{metrics['f1_macro']}** / F1(>50K): **{metrics['f1_high']}**",
        f"- 모델 저장: `{MODEL_PATH.relative_to(BASE_DIR)}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# =========================================================================
# main
# =========================================================================
def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1) 데이터 준비
    path = ensure_dataset(DATA_URL, DATA_CACHE)
    pdf, pldf = load_pandas(path), load_polars(path)
    load_info = compare_loading(pdf, pldf)
    df, prep = prepare(pdf)
    print("=== 1) 데이터 준비 ===")
    print(f"Pandas {load_info['pandas_shape']} / Polars {load_info['polars_shape']} "
          f"(일치: {load_info['shape_match']})")
    print(f"중복 {prep['duplicates_removed']}행 제거 / 결측: {prep['missing']}")

    try:
        # 2) 시각화 (다중 컬럼)
        make_seaborn_overview(df, SEABORN_PNG)
        make_plotly_charts(df)
        print(f"\n=== 2) 시각화 저장 ===\n{SEABORN_PNG.name} / "
              f"{PLOTLY_EDU.name} / {PLOTLY_OCC.name}")

        # 3) 통계 분석 + 인사이트
        desc, corr = descriptive_stats(df)
        tt = run_ttest(df)
        insights = compute_insights(df)
        print("\n=== 3) 통계 분석 ===")
        print(f"[t-test] 근무시간 >50K={tt['mean_high']}h vs <=50K={tt['mean_low']}h "
              f"→ p={tt['p_display']} ({'유의미' if tt['sig'] else '비유의'})")
        print(f"[인사이트] 성별 {insights['sex_rate']} / "
              f"결혼최고 {insights['marital_top']} / 직업최고 {insights['occ_top']}")

        # 4) ML Pipeline
        metrics = build_and_evaluate(df, MODEL_PATH)
        print("\n=== 4) ML Pipeline ===")
        print(f"정확도={metrics['accuracy']} / F1(macro)={metrics['f1_macro']} "
              f"/ F1(>50K)={metrics['f1_high']} → 모델 저장: {MODEL_PATH.name}")
    except (KeyError, ValueError) as e:
        raise SystemExit(f"[오류] 분석 처리 중 문제가 발생했습니다: {e}")

    # 5) report.md 자동 생성
    ctx = {"load": load_info, "prep": prep, "desc": desc, "corr": corr,
           "ttest": tt, "insights": insights, "metrics": metrics}
    generate_report(ctx, REPORT_PATH)
    print(f"\n=== 5) 자동화 ===\nreport.md 자동 생성 → {REPORT_PATH.name}")

    print("\n✅ End2End 분석 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
