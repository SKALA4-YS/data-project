-- ============================================================================
-- SKALA day_5 종합실습 4 : 3가지 조인 실행계획 비교
-- 파일: 03_join_3types.sql
-- 목적: Nested Loop / Hash Join / Merge Join 을 실제로 유도하고 EXPLAIN 캡처.
--       (개념 정리는 docs/조인_3종_비교.md 참고)
-- ============================================================================
SET search_path = ecom, public;
\timing on

-- ############################################################################
-- (1) NESTED LOOP JOIN
--     조건: 한쪽(outer)의 결과가 매우 적고, 다른 쪽(inner)에 조인키 인덱스 존재.
--     동작: outer 각 행마다 inner를 인덱스로 콕 집어 조회 (드라이빙 테이블 반복).
--     사례: 특정 고객 1명의 주문과 주문상세.
-- ############################################################################
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.order_id, o.order_ts, oi.product_id, oi.line_total
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.customer_id = 7;    -- outer(orders)가 15행 → 각 행마다 order_items 인덱스 조회
-- 관찰: Nested Loop + (orders) Bitmap/Index Scan + (order_items) Index Scan.
--       loops=N (outer 행수만큼 inner 반복)이 계획에 표시됨.


-- ############################################################################
-- (2) HASH JOIN
--     조건: 등가조인(=)이면서 양쪽 또는 한쪽이 대량. 인덱스로 콕 집기 비효율.
--     동작: 작은 쪽으로 해시테이블 빌드 → 큰 쪽을 훑으며 해시 프로브.
--     사례: 실매출 주문 전체 × 주문상세 (수만 행 집계).
-- ############################################################################
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) AS matched_rows, SUM(oi.line_total) AS gmv
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered');
-- 관찰: Hash Join. 작은 orders(7286행)로 Hash 빌드,
--       order_items(26083행) Seq Scan 하며 프로브. 대량 조인의 기본 전략.


-- ############################################################################
-- (3) MERGE JOIN (Sort-Merge Join)
--     조건: 양쪽 입력이 조인키로 '정렬'되어 있을 때(주로 PK/인덱스 순서) 유리.
--     동작: 정렬된 두 스트림을 지퍼처럼 맞물려 병합.
--     유도: 옵티마이저가 소규모에선 Hash를 선호 → 학습 목적상 Hash/NL 비활성화.
--     사례: orders × payments (둘 다 order_id 기준 인덱스 정렬 스트림).
-- ############################################################################
SET enable_hashjoin = off;   -- (학습용) 다른 조인 전략을 막아 Merge Join 유도
SET enable_nestloop = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.order_id, o.order_status, p.method, p.amount
FROM orders o
JOIN payments p ON p.order_id = o.order_id;
-- 관찰: Merge Join. 양쪽 모두 order_id 정렬 입력
--       (orders: Index Only Scan on PK, payments: Index Scan on FK 인덱스).
SET enable_hashjoin = on;    -- 원복 (중요)
SET enable_nestloop = on;

\timing off
-- ============================================================================
-- 요약(이 데이터셋 기준):
--   Nested Loop : outer 소량 + inner 인덱스 → 포인트 조회에 최적 (loops 확인)
--   Hash Join   : 대량 등가조인의 기본값 → GMV/집계성 쿼리 대부분 여기 해당
--   Merge Join  : 양쪽 정렬 입력/대량 정렬 조인에 유리(정렬 비용 상쇄 필요)
-- ============================================================================
