-- ============================================================================
-- SKALA day_5 종합실습 4 : 실습 인덱스 원복(초기 상태로)
-- 파일: 99_cleanup.sql
-- 용도: 02번에서 추가한 튜닝 인덱스를 제거해 "튜닝 전" 상태로 재현하고 싶을 때.
--       (제공 스키마 00_schema.sql 의 기본 인덱스는 건드리지 않음)
-- ============================================================================
SET search_path = ecom, public;

DROP INDEX IF EXISTS idx_orders_revts;        -- Q1/Q10 부분 인덱스
DROP INDEX IF EXISTS idx_orders_cust_revts;   -- Q5 부분 복합 인덱스
DROP INDEX IF EXISTS idx_inv_low;             -- Q7 부분 인덱스
DROP INDEX IF EXISTS idx_reviews_prod_cov;    -- Q8 커버링 인덱스
DROP INDEX IF EXISTS idx_oi_order_covering;   -- Q4 커버링 인덱스
ANALYZE;

-- 확인: 남아있는 인덱스 목록
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'ecom'
ORDER BY tablename, indexname;
