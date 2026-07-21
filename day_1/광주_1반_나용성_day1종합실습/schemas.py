"""
Pydantic v2 스키마 정의 모듈.

수집한 3개 API(JSON)에서 필요한 필드만 추출해 타입·범위를 검증한다.
검증 실패(타입 오류/범위 초과) 시 ValidationError 가 발생하며,
호출부(main.py)에서 이를 잡아 valid / errors 로 분리한다.
"""

from typing import Optional

from pydantic import BaseModel, Field


class WeatherHourly(BaseModel):
    """Open-Meteo 시간대별 날씨 1건.

    - time                      : 관측 시각 (빈 문자열 불가)
    - temperature_2m            : 기온(℃), 현실 범위 -60 ~ 60
    - precipitation_probability : 강수확률(%), 0 ~ 100
    """

    time: str = Field(min_length=1)
    temperature_2m: float = Field(ge=-60, le=60)
    precipitation_probability: int = Field(ge=0, le=100)


class CountryInfo(BaseModel):
    """countries.dev 국가 정보(필요 필드만).

    - population : 인구, 0 초과
    - area       : 면적(㎢), 0 초과
    """

    name: str = Field(min_length=1)
    capital: str = Field(min_length=1)
    region: str = Field(min_length=1)
    population: int = Field(gt=0)
    area: float = Field(gt=0)


class IpInfo(BaseModel):
    """ip-api IP 기반 지역 정보(필요 필드만).

    - query   : 조회한 IP
    - lat/lon : 위도(-90~90) / 경도(-180~180)
    - isp     : 통신사 (선택)
    """

    query: str = Field(min_length=1)
    country: str = Field(min_length=1)
    city: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    isp: Optional[str] = None
