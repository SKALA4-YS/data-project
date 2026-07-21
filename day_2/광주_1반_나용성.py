"""
================================================================================
[실습 3] Pandas EDA · Polars Lazy · DuckDB SQL 비교
--------------------------------------------------------------------------------
프로그램 설명
  sales_100k.csv(약 100만 행)를 대상으로 아래를 수행한다.
    1) Pandas EDA : info()/isnull() 확인 후 IQR 방법으로 amount 이상치 제거
    2) Pandas     : region·category별 total·mean·count (named aggregation)
    3) Polars Lazy: 동일 집계를 scan_csv→filter→group_by→agg→sort→collect 로 작성
    4) DuckDB SQL : 동일 집계를 SQL GROUP BY 로 작성 + timeit 세 도구 성능 비교

설계 원칙
  - IQR 정상 범위(Q1-1.5*IQR ~ Q3+1.5*IQR)를 한 번 계산해, 세 도구 모두
    같은 범위로 filter → 완전히 동일한 집계를 수행하므로 성능 비교가 공정하다.
  - timeit 반복 횟수(NUMBER)를 세 도구에 동일하게 적용한다.

변경내역 (Change History)
  2026-07-21  v1.0  최초 작성 - EDA/IQR + Pandas/Polars/DuckDB 집계 + timeit 비교
  2026-07-21  v1.1  timeit 측정 강화 - number×repeat 로 충분한 표본 확보, 최솟값 대표값화

작성자 : 광주_1반_나용성
================================================================================
"""

import timeit
from pathlib import Path

import duckdb
import pandas as pd
import polars as pl

CSV_PATH = Path(__file__).parent / "sales_100k.csv"
REQUIRED_COLS = {"region", "category", "amount"}
IQR_K = 1.5          # IQR 계수 (정상 범위 = Q1-K*IQR ~ Q3+K*IQR)
TIMEIT_NUMBER = 10   # 1회 측정당 실행 횟수 (세 도구 공통 — 공정 비교 필수)
TIMEIT_REPEAT = 5    # 측정 반복 횟수 (충분한 표본 확보 → 최솟값을 대표값으로)


# =========================================================================
# 데이터 로드 (예외/오류 처리)
# =========================================================================
def load_data(path: Path) -> pd.DataFrame:
    """CSV 를 읽어 DataFrame 을 반환한다. (utf-8-sig 로 BOM 제거)

    발생 가능한 오류를 명시적으로 처리한다.
    """
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except FileNotFoundError:
        raise SystemExit(f"[오류] 데이터 파일을 찾을 수 없습니다: {path}")
    except pd.errors.EmptyDataError:
        raise SystemExit(f"[오류] 데이터 파일이 비어 있습니다: {path}")

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise SystemExit(f"[오류] 필수 컬럼이 없습니다: {missing}")
    return df


# =========================================================================
# 1) Pandas EDA + IQR 이상치 처리
# =========================================================================
def compute_iqr_bounds(series: pd.Series) -> tuple[float, float]:
    """IQR 방법으로 정상 범위(하한, 상한)를 계산한다."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return q1 - IQR_K * iqr, q3 + IQR_K * iqr


def task1_eda_and_outlier(df: pd.DataFrame) -> tuple[float, float]:
    """기본 EDA 출력 후 IQR 로 이상치를 제거하고 전·후 행 수를 출력한다."""
    print("=== 1) Pandas EDA + IQR 이상치 처리 ===")
    print("[info]")
    df.info()
    print("\n[결측치 개수]")
    print(df.isnull().sum())

    lower, upper = compute_iqr_bounds(df["amount"])
    # between 은 IQR 기준 정상 범위(경계 포함)를 의미한다.
    clean = df[df["amount"].between(lower, upper)]
    print(f"\n[IQR] 정상 범위: {lower:,.1f} ~ {upper:,.1f}")
    print(f"이상치 제거 전 행 수: {len(df):,}")
    print(f"이상치 제거 후 행 수: {len(clean):,}")
    print(f"제거된 이상치 수     : {len(df) - len(clean):,}\n")
    return lower, upper


# =========================================================================
# 2) 3) 4) 세 도구의 동일 집계 파이프라인
#     - region·category별 total(sum)·mean·count, total 내림차순
# =========================================================================
def pandas_agg(df: pd.DataFrame, lower: float, upper: float) -> pd.DataFrame:
    """Pandas named aggregation 으로 집계한다. (결과 컬럼명 직접 지정)"""
    # 정상 범위(IQR) + 그룹 키(region·category) 결측 제외 → 세 도구 동일 조건
    clean = df[
        df["amount"].between(lower, upper)
        & df["region"].notna()
        & df["category"].notna()
    ]
    return (
        clean.groupby(["region", "category"])
        .agg(
            total=("amount", "sum"),
            mean=("amount", "mean"),
            count=("amount", "count"),
        )
        .sort_values("total", ascending=False)
        .reset_index()
    )


def pandas_pipeline(path: Path, lower: float, upper: float) -> pd.DataFrame:
    """파일 읽기부터 집계까지 Pandas 전체 파이프라인 (성능 측정용)."""
    return pandas_agg(pd.read_csv(path, encoding="utf-8-sig"), lower, upper)


def polars_pipeline(path: Path, lower: float, upper: float) -> pl.DataFrame:
    """Polars Lazy API: scan_csv→filter→group_by→agg→sort→collect."""
    return (
        pl.scan_csv(path)
        .filter(
            pl.col("amount").is_between(lower, upper)
            & pl.col("region").is_not_null()
            & pl.col("category").is_not_null()
        )
        .group_by(["region", "category"])
        .agg(
            total=pl.col("amount").sum(),
            mean=pl.col("amount").mean(),
            count=pl.col("amount").count(),
        )
        .sort("total", descending=True)
        .collect()  # LazyFrame → DataFrame (반드시 collect 로 실체화)
    )


def duckdb_pipeline(path: Path, lower: float, upper: float) -> pd.DataFrame:
    """DuckDB SQL GROUP BY 로 동일 집계 후 DataFrame 반환."""
    query = f"""
        SELECT region,
               category,
               SUM(amount)   AS total,
               AVG(amount)   AS mean,
               COUNT(amount) AS "count"
        FROM read_csv_auto('{path}')
        WHERE amount BETWEEN {lower} AND {upper}
          AND region IS NOT NULL
          AND category IS NOT NULL
        GROUP BY region, category
        ORDER BY total DESC
    """
    return duckdb.sql(query).df()


# =========================================================================
# 성능 비교 (timeit — 세 도구 동일 반복 횟수)
# =========================================================================
def benchmark(path: Path, lower: float, upper: float, number: int, repeat: int) -> None:
    """세 도구를 동일한 number·repeat 로 timeit 측정해 실행 시간을 비교한다.

    timeit.repeat 로 repeat 회 측정하고, 각 측정의 1회 실행 시간 중
    최솟값(min)을 대표값으로 삼는다. (외부 방해가 가장 적은 최선값)
    """
    tools = {
        "Pandas": lambda: pandas_pipeline(path, lower, upper),
        "Polars": lambda: polars_pipeline(path, lower, upper),
        "DuckDB": lambda: duckdb_pipeline(path, lower, upper),
    }
    print(f"=== 4) 성능 비교 (timeit number={number} × repeat={repeat}, 세 도구 동일) ===")
    print(f"{'도구':<10}{'최선(ms)':>12}{'평균(ms)':>12}")
    results = {}
    for name, fn in tools.items():
        per_run = [t / number for t in timeit.repeat(fn, number=number, repeat=repeat)]
        best, avg = min(per_run), sum(per_run) / len(per_run)
        results[name] = best
        print(f"{name:<10}{best * 1000:>12.2f}{avg * 1000:>12.2f}")
    fastest = min(results, key=results.get)
    print(f"→ 가장 빠른 도구(최선 기준): {fastest}")


# =========================================================================
# main
# =========================================================================
def main() -> int:
    df = load_data(CSV_PATH)

    # 1) EDA + IQR
    lower, upper = task1_eda_and_outlier(df)

    # 2~4) 세 도구 집계 (동일 조건) — 집계 단계 오류를 명시적으로 처리
    try:
        pdf = pandas_agg(df, lower, upper)
        pol = polars_pipeline(CSV_PATH, lower, upper)
        dk = duckdb_pipeline(CSV_PATH, lower, upper)
    except (KeyError, ValueError, pl.exceptions.PolarsError, duckdb.Error) as e:
        raise SystemExit(f"[오류] 집계 처리 중 문제가 발생했습니다: {e}")

    print("=== 2) Pandas groupby (named aggregation) ===")
    print(pdf.head(10).to_string(index=False), "\n")
    print("=== 3) Polars Lazy API 집계 ===")
    print(pol.head(10))
    print("\n=== 4) DuckDB SQL 집계 ===")
    print(dk.head(10).to_string(index=False))

    # 세 도구 결과 일치 검증 (그룹 수 + 총 건수는 정수라 정확 비교 가능)
    assert len(pdf) == len(pol) == len(dk), "세 도구의 그룹 수가 다릅니다."
    assert int(pdf["count"].sum()) == int(pol["count"].sum()) == int(dk["count"].sum())
    print(f"\n세 도구 집계 결과 일치 ✅ (그룹 {len(pdf)}개)\n")

    # 성능 비교
    benchmark(CSV_PATH, lower, upper, TIMEIT_NUMBER, TIMEIT_REPEAT)
    print("\n✅ 실습 3 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
