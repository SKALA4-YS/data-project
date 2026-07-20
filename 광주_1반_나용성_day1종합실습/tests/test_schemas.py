"""
Pydantic 스키마 검증 테스트 (pytest).

정상 데이터는 통과하고, 타입·범위를 벗어난 데이터는 ValidationError 가
발생하는지 확인한다.
"""

import pytest
from pydantic import ValidationError

from schemas import CountryInfo, IpInfo, WeatherHourly


def test_weather_valid():
    """정상 날씨 데이터는 검증을 통과한다."""
    record = WeatherHourly(
        time="2026-07-20T00:00",
        temperature_2m=23.2,
        precipitation_probability=6,
    )
    assert record.precipitation_probability == 6


def test_weather_precipitation_out_of_range():
    """강수확률이 0~100 범위를 벗어나면 ValidationError."""
    with pytest.raises(ValidationError):
        WeatherHourly(
            time="2026-07-20T00:00",
            temperature_2m=23.2,
            precipitation_probability=150,
        )


def test_weather_type_error():
    """기온에 숫자가 아닌 값이 오면 ValidationError."""
    with pytest.raises(ValidationError):
        WeatherHourly(
            time="2026-07-20T00:00",
            temperature_2m="더움",
            precipitation_probability=6,
        )


def test_country_population_must_be_positive():
    """인구가 0 이하이면 ValidationError."""
    with pytest.raises(ValidationError):
        CountryInfo(name="Korea", capital="Seoul", region="Asia", population=-1, area=100210)


def test_ip_valid():
    """정상 IP 데이터는 검증을 통과한다."""
    record = IpInfo(
        query="8.8.8.8",
        country="United States",
        city="Ashburn",
        lat=39.03,
        lon=-77.5,
        isp="Google LLC",
    )
    assert record.query == "8.8.8.8"
