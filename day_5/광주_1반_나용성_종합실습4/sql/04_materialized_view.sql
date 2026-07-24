-- ============================================================================
-- SKALA day_5 종합실습 4 : Materialized View (일별 GMV 리포트 가속)
-- 파일: 04_materialized_view.sql
-- 시나리오: "매일매일 총 판매금액"을 조회. 매번 JOIN+SUM은 느리므로
--           결과를 미리 계산해 두는 Materialized View(mv_daily_gmv)를 사용.
-- (갱신전략 설명은 docs/MV_갱신전략.md 참고)
-- ============================================================================
SET search_path = ecom, public;
\timing on

-- ############################################################################
-- 1) MV 미사용: 매번 원본 조인 + 집계 (리포트마다 반복 수행 → 비용 누적)
-- ############################################################################
EXPLAIN (ANALYZE, BUFFERS)
SELECT date_trunc('day', o.order_ts) AS day,
       SUM(oi.line_total)            AS gmv
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
GROUP BY 1
ORDER BY 1;

-- ############################################################################
-- 2) Materialized View 생성 (스키마 00_schema.sql 에 이미 정의됨)
--    여기서는 재현/재정의 스크립트를 함께 둠.
-- ############################################################################
DROP MATERIALIZED VIEW IF EXISTS mv_daily_gmv CASCADE;
CREATE MATERIALIZED VIEW mv_daily_gmv AS
SELECT date_trunc('day', o.order_ts) AS day,
       SUM(oi.line_total)            AS gmv
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
GROUP BY 1;

-- CONCURRENTLY 갱신(무중단 REFRESH)을 위해 UNIQUE 인덱스 필수
CREATE UNIQUE INDEX ux_mv_daily_gmv_day ON mv_daily_gmv(day);

-- ############################################################################
-- 3) MV 사용: 미리 계산된 결과를 그냥 읽음 (조인/집계 없음)
-- ############################################################################
EXPLAIN (ANALYZE, BUFFERS)
SELECT day, gmv
FROM mv_daily_gmv
ORDER BY day;
-- 관찰: 원본 Hash Join+집계(수만 행 스캔) → MV는 결과 테이블 Seq/Index Scan 1회.
--       리포트 반복 조회 시 매번 드는 집계 비용을 '갱신 시점 1회'로 이전.

-- 결과 확인(상위 5일)
SELECT day::date, gmv FROM mv_daily_gmv ORDER BY day LIMIT 5;

-- ############################################################################
-- 4) 갱신(REFRESH) 방법
-- ############################################################################
-- (a) 일반 갱신: 갱신 동안 해당 MV에 대한 조회가 잠깐 잠김(ACCESS EXCLUSIVE)
REFRESH MATERIALIZED VIEW mv_daily_gmv;

-- (b) 무중단 갱신: UNIQUE 인덱스가 있어야 사용 가능. 조회를 막지 않고 갱신.
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_gmv;

-- ############################################################################
-- 5) 갱신 주기 설계 (요구사항: 매일 오후 3시 기준)
--    - 데이터가 자주 바뀌지 않는 리포트성 지표이므로 실시간 대신 배치 갱신.
--    - OS cron 예시 (매일 15:00):
--        0 15 * * *  PGPASSWORD=**** psql -h localhost -U skala_user -d skala_db \
--          -c "REFRESH MATERIALIZED VIEW CONCURRENTLY ecom.mv_daily_gmv;"
--    - DB내 스케줄러 pg_cron 예시:
--        SELECT cron.schedule('refresh_mv_daily_gmv', '0 15 * * *',
--          $$REFRESH MATERIALIZED VIEW CONCURRENTLY ecom.mv_daily_gmv$$);
--    자세한 트레이드오프는 docs/MV_갱신전략.md 참고.

\timing off
