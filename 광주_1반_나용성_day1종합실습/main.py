"""
================================================================================
[Day 1 종합 실습] 데이터 수집 미니 파이프라인
--------------------------------------------------------------------------------
프로그램 설명
  3개 외부 API(Open-Meteo / countries.dev / ip-api)를 asyncio + httpx 로
  '동시에' 수집하고, Pydantic v2 모델로 타입·범위를 검증한 뒤,
  검증을 통과한 날씨 데이터를 CSV·Parquet 로 저장하며 읽기/쓰기 성능을 비교한다.

처리 흐름
  1) collect_all()      : asyncio.gather() 로 3개 API 동시 수집
  2) validate_*()       : Pydantic 모델로 검증 → valid / errors 분리
  3) save_and_benchmark : CSV/Parquet 저장 + 성능(시간/용량) 측정·출력

변경내역 (Change History)
  2026-07-20  v1.0  최초 작성 - 비동기 수집 + 검증 + 저장/성능비교 파이프라인

작성자 : 광주_1반_나용성
================================================================================
"""

import asyncio
import json
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from collectors import collect_all
from schemas import CountryInfo, IpInfo, WeatherHourly
from storage import save_and_benchmark

DATA_DIR = Path(__file__).parent / "data"


def validate_weather(weather_raw: dict) -> tuple[list[WeatherHourly], list[dict]]:
    """Open-Meteo hourly 데이터를 순회하며 WeatherHourly 로 검증한다.

    성공은 valid, 실패는 errors({row, error}) 로 분리해 반환한다.
    """
    hourly = weather_raw["hourly"]
    valid: list[WeatherHourly] = []
    errors: list[dict] = []
    for time_str, temp, pop in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
    ):
        row = {
            "time": time_str,
            "temperature_2m": temp,
            "precipitation_probability": pop,
        }
        try:
            valid.append(WeatherHourly(**row))
        except ValidationError as e:
            errors.append({"row": row, "error": str(e)})
    return valid, errors


def validate_country(country_raw: dict) -> CountryInfo | None:
    """국가 정보를 CountryInfo 로 검증한다. 실패 시 오류를 출력하고 None 반환."""
    try:
        return CountryInfo(**country_raw)
    except ValidationError as e:
        print(f"[국가 정보 검증 실패]\n{e}")
        return None


def validate_ip(ip_raw: dict) -> IpInfo | None:
    """IP 정보를 IpInfo 로 검증한다. 실패 시 오류를 출력하고 None 반환."""
    try:
        return IpInfo(**ip_raw)
    except ValidationError as e:
        print(f"[IP 정보 검증 실패]\n{e}")
        return None


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)

    # 1) 비동기 동시 수집
    weather_raw, country_raw, ip_raw = asyncio.run(collect_all())
    print("=== 1) 비동기 수집 완료 (asyncio.gather) ===")
    print(f"weather hourly 건수: {len(weather_raw['hourly']['time'])}")
    print(f"country: {country_raw.get('name')} / ip: {ip_raw.get('query')}\n")

    # 2) 스키마 검증
    weather_valid, weather_errors = validate_weather(weather_raw)
    country = validate_country(country_raw)
    ip_info = validate_ip(ip_raw)

    print("=== 2) 스키마 검증 결과 ===")
    print(f"날씨 valid: {len(weather_valid)}건 / errors: {len(weather_errors)}건")
    print(f"국가 검증: {'성공' if country else '실패'} / IP 검증: {'성공' if ip_info else '실패'}")
    if country:
        print(f"  - {country.name} | 수도 {country.capital} | 인구 {country.population:,}")
    if ip_info:
        print(f"  - IP {ip_info.query} | {ip_info.country} {ip_info.city}\n")

    # 검증 통과한 날씨 데이터를 DataFrame 으로 (model_dump 사용)
    df = pd.DataFrame([record.model_dump() for record in weather_valid])

    # 3) 저장 + 성능 비교
    csv_path = str(DATA_DIR / "weather.csv")
    parquet_path = str(DATA_DIR / "weather.parquet")
    perf = save_and_benchmark(df, csv_path, parquet_path)

    csv_w, pq_w = perf["csv_write_sec"] * 1000, perf["parquet_write_sec"] * 1000
    csv_r, pq_r = perf["csv_read_sec"] * 1000, perf["parquet_read_sec"] * 1000
    print(f"=== 3) CSV vs Parquet 성능 비교 (워밍업 후 {perf['iterations']}회 평균) ===")
    print(f"{'항목':<16}{'CSV':>14}{'Parquet':>14}")
    print(f"{'쓰기(ms)':<16}{csv_w:>14.3f}{pq_w:>14.3f}")
    print(f"{'읽기(ms)':<16}{csv_r:>14.3f}{pq_r:>14.3f}")
    print(f"{'용량(bytes)':<16}{perf['csv_bytes']:>14,}{perf['parquet_bytes']:>14,}")

    # errors 는 JSON 으로 저장 (한글 깨짐 방지 ensure_ascii=False)
    if weather_errors:
        with open(DATA_DIR / "weather_errors.json", "w", encoding="utf-8") as f:
            json.dump(weather_errors, f, ensure_ascii=False, indent=2)

    print("\n✅ 파이프라인 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
