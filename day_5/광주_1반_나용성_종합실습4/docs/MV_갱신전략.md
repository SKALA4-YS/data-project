# Materialized View 활용 & 갱신 전략 — `mv_daily_gmv`

> SKALA day_5 종합실습 4 · PostgreSQL 18.4 · schema `ecom`
> 실행 스크립트: `sql/04_materialized_view.sql`

## 1. 왜 Materialized View 인가

"매일매일 총 판매금액(GMV)"은 리포트에서 **반복적으로 조회**된다.
그런데 매번 아래처럼 `orders × order_items`를 JOIN + SUM 하면, 조회할 때마다
수만 행을 스캔·집계하는 비용이 발생한다.

- **일반 View**: 이름만 저장, 조회 시 매번 원본 쿼리를 다시 실행(비용 그대로).
- **Materialized View**: 쿼리 **결과 자체를 물리적으로 저장**. 조회 시 그 결과를 읽음.
  → 집계 비용을 "조회 시점"에서 "갱신 시점 1회"로 이전한다.

## 2. 성능 비교 (실측)

| 구분 | 실행계획 | 실행시간(실측) |
|------|----------|----------------|
| MV 미사용 (원본 JOIN+SUM) | Hash Join + HashAggregate, order_items 26k행 스캔 | 약 **15.9 ms** |
| MV 사용 (`SELECT * FROM mv_daily_gmv`) | mv_daily_gmv 결과(122행) 1회 스캔 | 약 **0.02 ms** |

> 리포트 반복 조회 환경에서 조회 비용이 사실상 무시할 수준으로 줄어든다
> (환경별 수치는 다르나, 수백 배 이상 차이). 데이터가 커질수록 격차는 더 벌어진다.

## 3. 생성 스크립트

```sql
CREATE MATERIALIZED VIEW mv_daily_gmv AS
SELECT date_trunc('day', o.order_ts) AS day,
       SUM(oi.line_total)            AS gmv
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
GROUP BY 1;

-- CONCURRENTLY(무중단) 갱신을 쓰려면 UNIQUE 인덱스가 반드시 필요
CREATE UNIQUE INDEX ux_mv_daily_gmv_day ON mv_daily_gmv(day);
```

## 4. 갱신(REFRESH) 방법과 트레이드오프

Materialized View는 **자동 갱신되지 않는다.** 원본이 바뀌어도 명시적으로 갱신해야 한다.

| 방식 | 명령 | 특징 |
|------|------|------|
| 일반 갱신 | `REFRESH MATERIALIZED VIEW mv_daily_gmv;` | 갱신 중 해당 MV 조회가 잠김(ACCESS EXCLUSIVE lock). 빠르지만 순간 조회 차단 |
| 무중단 갱신 | `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_gmv;` | 조회를 막지 않음. **UNIQUE 인덱스 필수**. 상대적으로 느리고 리소스 더 사용 |

- 운영(리포트를 항상 조회 가능해야 함)에서는 **CONCURRENTLY** 를 권장.

## 5. 갱신 주기 설계 — 요구사항: "매일 오후 3시 기준"

GMV는 실시간성이 낮은 리포트성 지표이므로, 실시간 트리거 대신 **배치 갱신**이 적절하다.
데이터가 얼마나 자주/얼마나 늦게 반영돼도 되는지(허용 지연)에 맞춰 주기를 정한다.

### (a) OS cron — 매일 15:00

```bash
0 15 * * *  PGPASSWORD=**** psql -h localhost -U skala_user -d skala_db \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY ecom.mv_daily_gmv;"
```

### (b) DB내 스케줄러 pg_cron

```sql
-- 확장 설치 후
SELECT cron.schedule(
  'refresh_mv_daily_gmv',
  '0 15 * * *',                         -- 매일 오후 3시
  $$REFRESH MATERIALIZED VIEW CONCURRENTLY ecom.mv_daily_gmv$$
);
```

### 설계 고려사항
- **허용 지연(Staleness)**: 오후 3시 갱신이면 그 이후 발생한 주문은 다음 날 반영.
  일 단위 GMV 리포트에는 충분(마감 성격).
- **갱신 시각 선정**: 트래픽이 낮은 시간대 권장(여기선 업무 흐름상 15:00 지정).
- **더 낮은 지연이 필요하면**: 주기를 좁히거나(예: 1시간마다), 증분 갱신(트리거+요약
  테이블) 또는 로그 기반 파이프라인으로 확장.
- **비용**: 갱신은 결국 원본 집계를 1회 수행하므로, 주기를 너무 촘촘히 하면
  갱신 비용이 조회 절감분을 상쇄할 수 있다 → "조회 빈도 ≫ 갱신 빈도"일 때 이득.
