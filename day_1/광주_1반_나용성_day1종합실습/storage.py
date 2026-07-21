"""
저장 및 성능 비교 모듈.

검증을 통과한 데이터(DataFrame)를 CSV 와 Parquet 두 형식으로 저장하고,
각 형식의 쓰기/읽기 시간과 파일 크기를 측정해 비교 결과를 반환한다.

공정한 비교를 위해:
  - 워밍업(warm-up)으로 pyarrow 엔진 최초 초기화 비용을 측정에서 제외한다.
  - 데이터가 작을 때의 노이즈를 줄이려고 여러 번 반복해 평균을 낸다.
"""

import os
import time

import pandas as pd


def _avg_seconds(func, iterations: int) -> float:
    """func 을 iterations 번 실행한 평균 소요 시간(초)을 반환한다."""
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    return (time.perf_counter() - start) / iterations


def save_and_benchmark(
    df: pd.DataFrame,
    csv_path: str,
    parquet_path: str,
    iterations: int = 100,
) -> dict:
    """DataFrame 을 CSV/Parquet 로 저장하며 쓰기·읽기 성능을 측정한다.

    반환: 쓰기/읽기 평균 시간(초), 파일 크기(bytes), 반복 횟수를 담은 dict
    """
    # 워밍업: pyarrow 엔진 최초 초기화 비용이 측정에 섞이지 않도록 한 번 실행
    df.to_parquet(parquet_path, index=False)
    pd.read_parquet(parquet_path)

    results = {
        "csv_write_sec": _avg_seconds(lambda: df.to_csv(csv_path, index=False), iterations),
        "parquet_write_sec": _avg_seconds(
            lambda: df.to_parquet(parquet_path, index=False), iterations
        ),
        "csv_read_sec": _avg_seconds(lambda: pd.read_csv(csv_path), iterations),
        "parquet_read_sec": _avg_seconds(lambda: pd.read_parquet(parquet_path), iterations),
        "csv_bytes": os.path.getsize(csv_path),
        "parquet_bytes": os.path.getsize(parquet_path),
        "iterations": iterations,
    }
    return results
