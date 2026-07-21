"""
비동기 데이터 수집 모듈.

asyncio + httpx 로 3개 API 를 asyncio.gather() 를 통해 '동시에' 호출한다.
(순차 호출 대비 전체 대기 시간을 크게 줄일 수 있다.)
"""

import asyncio

import httpx

# 수집 대상 API URL
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia/Seoul"
)
COUNTRY_URL = "https://countries.dev/alpha/KOR"
IP_URL = "http://ip-api.com/json/8.8.8.8"


async def fetch_json(client: httpx.AsyncClient, url: str) -> dict:
    """단일 URL 을 비동기로 GET 하여 JSON(dict) 을 반환한다.

    HTTP 오류(4xx/5xx)는 raise_for_status() 로 예외 발생시킨다.
    """
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def collect_all() -> tuple[dict, dict, dict]:
    """3개 API 를 asyncio.gather() 로 동시에 수집한다.

    반환: (weather_raw, country_raw, ip_raw)
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        weather_raw, country_raw, ip_raw = await asyncio.gather(
            fetch_json(client, WEATHER_URL),
            fetch_json(client, COUNTRY_URL),
            fetch_json(client, IP_URL),
        )
    return weather_raw, country_raw, ip_raw
