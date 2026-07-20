# Day 1 종합 실습 — 데이터 수집 미니 파이프라인

3개 외부 API를 **비동기로 동시 수집** → **Pydantic v2 검증** → **CSV/Parquet 저장 및 성능 비교**하는 미니 데이터 파이프라인.

## 구성

| 파일 | 역할 |
|------|------|
| `collectors.py` | `asyncio` + `httpx` 로 3개 API를 `asyncio.gather()`로 동시 수집 |
| `schemas.py` | Pydantic v2 모델 (타입·범위 검증) |
| `storage.py` | CSV/Parquet 저장 + 읽기/쓰기 성능 측정 |
| `main.py` | 전체 파이프라인 실행 진입점 |
| `tests/test_schemas.py` | 스키마 검증 pytest |

## 사용 API

- **Open-Meteo**: 서울 3일 시간대별 기온·강수확률
- **countries.dev**: 한국 국가 정보
- **ip-api**: IP(8.8.8.8) 기반 지역 정보

## 실행 방법

```bash
# 1) 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2) 패키지 설치
pip install -r requirements.txt

# 3) 파이프라인 실행
python main.py

# 4) 테스트 / 스타일 검사
pytest -v
ruff check .
```

## 결과물

- `data/weather.csv`, `data/weather.parquet` — 검증 통과 날씨 데이터
- 실행 시 CSV vs Parquet 쓰기/읽기 시간 및 파일 용량 비교 출력
