-- ============================================================================
-- SKALA 4기 2주차 day_5 : 종합실습 4 (E-Commerce 성능 튜닝)
-- 파일: 02_tuning_Q01-Q11.sql
-- DB: skala_db / Schema: ecom / User: skala_user
-- PostgreSQL 18.4 기준
--
-- [사용법]
--   본 스크립트는 문항별로 "튜닝 전 → 튜닝 후" 순서로 배치되어 있습니다.
--   위에서 아래로 실행하면서 각 EXPLAIN (ANALYZE) 결과를 캡처하면
--   튜닝 전/후 실행계획 대비를 그대로 스크린샷으로 남길 수 있습니다.
--
--   - 각 문항은 자기완결적입니다(필요한 DROP/CREATE INDEX 포함).
--   - EXPLAIN (ANALYZE, BUFFERS): 추정치가 아닌 '실측' 실행시간/버퍼를 봅니다.
--   - now() 기준 상대 시각 데이터이므로, seed 적재 직후 실행을 권장합니다.
--
-- [이 데이터셋의 튜닝 3원칙 - 실측으로 도출]
--   1) 기간 필터가 있는 조회(Q1/Q10) → 부분 인덱스로 Seq→Bitmap 전환, 실측 2배↑ 개선
--   2) 기간 필터 없는 전체 집계 리포트(Q2/Q4/Q5/Q9)
--      → order_status IN(...) 이 전체의 76%라 인덱스가 무의미.
--        인덱스가 아니라 '쿼리 재작성' 또는 'Materialized View(03번 파일)'가 정답.
--   3) 작은 차원 테이블(Q7 inventory 600행 / Q8 reviews 2065행)
--      → Seq Scan이 최적이라 옵티마이저가 인덱스를 '거부'.
--        무조건 인덱스가 아니라, 규모가 커질 때를 대비한 설계가 핵심.
-- ============================================================================
SET search_path = ecom, public;
\timing on

-- 튜닝 실습을 처음부터 재현하기 위해, 본 실습에서 추가하는 인덱스를 먼저 제거
DROP INDEX IF EXISTS idx_orders_revts;
DROP INDEX IF EXISTS idx_orders_cust_revts;
DROP INDEX IF EXISTS idx_inv_low;
DROP INDEX IF EXISTS idx_reviews_prod_cov;
DROP INDEX IF EXISTS idx_oi_order_covering;
ANALYZE;


-- ############################################################################
-- Q1) 지난 한 달간 실제 팔린 총 금액 (paid + shipped + delivered)
--     튜닝 포인트: order_ts 기간 필터가 저선택도(약 20%)인데
--                  order_ts 단독/부분 인덱스가 없어 orders 전체 Seq Scan 발생.
-- ############################################################################

-- ---- [Q1 튜닝 전] orders를 Seq Scan (Rows Removed by Filter 다수) ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT COALESCE(SUM(oi.line_total), 0) AS net_sales
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')   -- 실매출 상태만
  AND o.order_ts >= now() - interval '1 month';           -- 지난 한 달

-- ---- [튜닝] 매출 상태 주문의 order_ts 부분 인덱스 ----
-- 부분 인덱스(WHERE 절)로 인덱스 크기를 줄이고, 상태 필터까지 인덱스가 커버.
CREATE INDEX idx_orders_revts
  ON orders(order_ts)
  WHERE order_status IN ('paid','shipped','delivered');
ANALYZE orders;

-- ---- [Q1 튜닝 후] orders가 Bitmap Index Scan(idx_orders_revts)으로 전환 ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT COALESCE(SUM(oi.line_total), 0) AS net_sales
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
  AND o.order_ts >= now() - interval '1 month';

-- 실제 결과 값 확인용
SELECT COALESCE(SUM(oi.line_total), 0) AS net_sales
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
  AND o.order_ts >= now() - interval '1 month';
-- 개선 요약: orders Seq Scan(cost≈302) → Bitmap Index Scan(cost≈178),
--            실행시간 약 8.9ms → 4.5ms (실측, 환경별 상이)


-- ############################################################################
-- Q2) 월별 주문 수 / 매출 / 주문당 평균금액(AOV)
--     튜닝 포인트: orders×order_items를 직접 조인 후 GROUP BY 하면
--                  주문당 아이템이 여러 개라 count(DISTINCT order_id)가 필요 →
--                  DISTINCT 집계는 비싸고 정확도/성능 모두 불리.
--     튜닝 전략(재작성): "주문 단위 사전 집계" 후 월 단위로 다시 집계.
-- ############################################################################

-- ---- [Q2 튜닝 전] JOIN 후 count(DISTINCT) 사용 ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT to_char(date_trunc('month', o.order_ts), 'YYYY-MM') AS ym,
       count(DISTINCT o.order_id)                          AS orders,
       SUM(oi.line_total)                                  AS revenue,
       round(safe_div(SUM(oi.line_total),
                      count(DISTINCT o.order_id)), 2)      AS aov
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
GROUP BY 1
ORDER BY 1;

-- ---- [Q2 튜닝 후] 주문 단위 사전집계 → DISTINCT 제거, count(*)/avg 사용 ----
EXPLAIN (ANALYZE, BUFFERS)
WITH order_amt AS (   -- 주문 1건당 금액을 먼저 만든다(아이템 → 주문 롤업)
  SELECT o.order_id,
         date_trunc('month', o.order_ts) AS ym,
         SUM(oi.line_total)              AS order_total
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, date_trunc('month', o.order_ts)
)
SELECT to_char(ym, 'YYYY-MM')               AS ym,
       count(*)                             AS orders,     -- 이미 주문 단위라 DISTINCT 불필요
       SUM(order_total)                     AS revenue,
       round(AVG(order_total), 2)           AS aov          -- AVG = AOV
FROM order_amt
GROUP BY ym
ORDER BY ym;

-- 결과 확인
WITH order_amt AS (
  SELECT o.order_id, date_trunc('month', o.order_ts) AS ym, SUM(oi.line_total) AS order_total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, date_trunc('month', o.order_ts)
)
SELECT to_char(ym,'YYYY-MM') ym, count(*) orders, SUM(order_total) revenue, round(AVG(order_total),2) aov
FROM order_amt GROUP BY ym ORDER BY ym;
-- 개선 포인트: HashAggregate 시 DISTINCT 키 관리 비용 제거 →
--             집계 단순화. AOV도 f_safe_div 없이 AVG로 자연 표현.


-- ############################################################################
-- Q3) 최근 90일 카테고리 Top10
--     관찰: 90일 필터는 전체의 약 58%가 통과(고선택도) → order_ts 인덱스를
--           만들어도 옵티마이저가 Seq Scan을 선택(인덱스가 정답이 아님).
--     튜닝 전략(재작성): 큰 사실 테이블(order_items) 스캔은 불가피하지만,
--           카테고리 트리 조인/집계 키를 category_id로 최소화하고
--           불필요한 컬럼 선택을 제거해 조인 폭을 줄인다.
-- ############################################################################

-- ---- [Q3 튜닝 전] categories까지 4중 조인, 넓은 GROUP BY ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.category_id, c.category_name, SUM(oi.line_total) AS sales
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products   p  ON p.product_id = oi.product_id
JOIN categories c  ON c.category_id = p.category_id
WHERE o.order_status IN ('paid','shipped','delivered')
  AND o.order_ts >= now() - interval '90 days'
GROUP BY c.category_id, c.category_name
ORDER BY sales DESC
LIMIT 10;

-- ---- [Q3 튜닝 후] 매출을 category_id 로 먼저 집계한 뒤, 이름은 마지막에 1회 조인 ----
-- categories 조인을 집계 이후로 미뤄(카디널리티 축소 후 조인),
-- GROUP BY 키를 category_id 단일 컬럼으로 좁힘.
EXPLAIN (ANALYZE, BUFFERS)
WITH cat_sales AS (
  SELECT p.category_id, SUM(oi.line_total) AS sales
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  JOIN products   p  ON p.product_id = oi.product_id
  WHERE o.order_status IN ('paid','shipped','delivered')
    AND o.order_ts >= now() - interval '90 days'
  GROUP BY p.category_id
)
SELECT cs.category_id, c.category_name, cs.sales
FROM cat_sales cs
JOIN categories c ON c.category_id = cs.category_id   -- 14행짜리 차원과 1회만 조인
ORDER BY cs.sales DESC
LIMIT 10;
-- 메모: 90일=고선택도이므로 "인덱스 추가"가 오답인 대표 사례.
--       옵티마이저 판단(Seq Scan+Hash Join)이 합리적임을 EXPLAIN으로 설명.


-- ############################################################################
-- Q4) 제품별 누적매출 RANK() Top20
--     관찰: 기간 필터가 없는 '전체 누적' 집계 → order_items 전량 스캔 불가피,
--           status IN(...) 도 76% 통과라 인덱스 무의미. Seq Scan+Hash Join이 최적.
--     튜닝 전략: 커버링 인덱스로 order_items의 힙 접근을 줄여보고(효과 측정),
--                근본적으로는 반복 조회 시 Materialized View(03번)가 정답.
-- ############################################################################

-- ---- [Q4 튜닝 전] ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM (
  SELECT p.product_id, p.product_name,
         SUM(oi.line_total)                              AS revenue,
         RANK() OVER (ORDER BY SUM(oi.line_total) DESC)  AS rnk
  FROM order_items oi
  JOIN orders   o ON o.order_id = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY p.product_id, p.product_name
) t
WHERE rnk <= 20
ORDER BY rnk;

-- ---- [튜닝] order_items 커버링 인덱스 (order_id, product_id, line_total) ----
-- 조인키 + 집계 대상 컬럼을 인덱스에 모두 담아 힙 접근(랜덤 I/O)을 축소.
CREATE INDEX idx_oi_order_covering
  ON order_items(order_id) INCLUDE (product_id, line_total);
ANALYZE order_items;

-- ---- [Q4 튜닝 후] ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM (
  SELECT p.product_id, p.product_name,
         SUM(oi.line_total)                              AS revenue,
         RANK() OVER (ORDER BY SUM(oi.line_total) DESC)  AS rnk
  FROM order_items oi
  JOIN orders   o ON o.order_id = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY p.product_id, p.product_name
) t
WHERE rnk <= 20
ORDER BY rnk;
-- 메모: 소규모(26k행)에선 커버링 인덱스 이득이 작을 수 있음.
--       "전체 누적 리포트"는 인덱스보다 Materialized View가 근본 해법(03번 파일).


-- ############################################################################
-- Q5) RFM (Recency / Frequency / Monetary)
--     고객이 얼마나 최근에 / 자주 / 많이 샀는지.
--     튜닝 포인트: 고객별 집계 → orders(customer_id) 접근 최적화.
-- ############################################################################

-- ---- [Q5 튜닝 전] ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.customer_id,
       (CURRENT_DATE - max(o.order_ts)::date) AS recency_days,   -- 최근성
       count(DISTINCT o.order_id)             AS frequency,      -- 빈도
       SUM(oi.line_total)                     AS monetary        -- 금액
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
GROUP BY o.customer_id
ORDER BY monetary DESC
LIMIT 20;

-- ---- [튜닝] (customer_id, order_ts) 부분 인덱스로 고객별 접근/최근성 계산 지원 ----
CREATE INDEX idx_orders_cust_revts
  ON orders(customer_id, order_ts)
  WHERE order_status IN ('paid','shipped','delivered');
ANALYZE orders;

-- ---- [Q5 튜닝 후] ----
-- 주문 단위 사전집계로 DISTINCT 제거 + 부분 인덱스로 orders 접근 축소.
EXPLAIN (ANALYZE, BUFFERS)
WITH order_amt AS (
  SELECT o.order_id, o.customer_id, o.order_ts, SUM(oi.line_total) AS order_total
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, o.customer_id, o.order_ts
)
SELECT customer_id,
       (CURRENT_DATE - max(order_ts)::date) AS recency_days,
       count(*)                             AS frequency,
       SUM(order_total)                     AS monetary
FROM order_amt
GROUP BY customer_id
ORDER BY monetary DESC
LIMIT 20;


-- ############################################################################
-- Q6) 첫 구매 후 30일 내 재구매율
--     튜닝 포인트: 고객별 '첫 주문'을 구해 30일 내 다음 주문 존재 여부 판정.
--     튜닝 전략(재작성): self-join(O(n^2) 위험) 대신 윈도우 함수 1-pass.
-- ############################################################################

-- ---- [Q6 튜닝 전] 상관 서브쿼리(고객마다 재조회) 방식 ----
EXPLAIN (ANALYZE, BUFFERS)
WITH firsts AS (
  SELECT customer_id, min(order_ts) AS first_ts
  FROM orders
  WHERE order_status IN ('paid','shipped','delivered')
  GROUP BY customer_id
)
SELECT
  count(*) AS buyers,
  count(*) FILTER (
    WHERE EXISTS (                         -- 고객마다 orders 재조회(상관 서브쿼리)
      SELECT 1 FROM orders o2
      WHERE o2.customer_id = f.customer_id
        AND o2.order_status IN ('paid','shipped','delivered')
        AND o2.order_ts >  f.first_ts
        AND o2.order_ts <= f.first_ts + interval '30 days'
    )
  ) AS repeat_30d,
  round(100.0 * count(*) FILTER (
    WHERE EXISTS (
      SELECT 1 FROM orders o2
      WHERE o2.customer_id = f.customer_id
        AND o2.order_status IN ('paid','shipped','delivered')
        AND o2.order_ts >  f.first_ts
        AND o2.order_ts <= f.first_ts + interval '30 days'
    )
  ) / count(*), 2) AS repeat_rate_pct
FROM firsts f;

-- ---- [Q6 튜닝 후] 윈도우 함수로 첫 주문시각을 붙여 단일 스캔 처리 ----
EXPLAIN (ANALYZE, BUFFERS)
WITH paid AS (
  SELECT customer_id, order_ts,
         min(order_ts) OVER (PARTITION BY customer_id) AS first_ts   -- 첫 주문시각을 한 번에
  FROM orders
  WHERE order_status IN ('paid','shipped','delivered')
)
SELECT
  count(DISTINCT customer_id) AS buyers,
  count(DISTINCT customer_id) FILTER (
    WHERE order_ts > first_ts AND order_ts <= first_ts + interval '30 days'
  ) AS repeat_30d,
  round(100.0 * count(DISTINCT customer_id) FILTER (
    WHERE order_ts > first_ts AND order_ts <= first_ts + interval '30 days'
  ) / count(DISTINCT customer_id), 2) AS repeat_rate_pct
FROM paid;
-- 개선 포인트: 상관 서브쿼리(고객 수만큼 반복 조회) → 윈도우 함수 1회 스캔.


-- ############################################################################
-- Q7) 재고가 임계치보다 낮은 상품 (곧 품절 위험)
--     관찰: inventory 600행 → Seq Scan(cost≈12)이 최적. 부분 인덱스를 만들어도
--           옵티마이저가 '거부'. 이는 오답이 아니라 소규모 테이블의 정상 동작.
--     학습: 인덱스는 규모가 커질 때 효과. enable_seqscan=off로 강제 시연 가능.
-- ############################################################################

-- ---- [Q7 튜닝 전] Seq Scan + Filter (qty_on_hand < reorder_point) ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT i.product_id, p.product_name, i.qty_on_hand, i.reorder_point
FROM inventory i
JOIN products p ON p.product_id = i.product_id
WHERE i.qty_on_hand < i.reorder_point
ORDER BY i.qty_on_hand;

-- ---- [튜닝] "품절 위험 행만" 담는 부분 인덱스(50여 행) ----
CREATE INDEX idx_inv_low
  ON inventory(qty_on_hand)
  WHERE qty_on_hand < reorder_point;
ANALYZE inventory;

-- ---- [Q7 튜닝 후] 소규모라 옵티마이저는 여전히 Seq Scan 선택(정상) ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT i.product_id, p.product_name, i.qty_on_hand, i.reorder_point
FROM inventory i
JOIN products p ON p.product_id = i.product_id
WHERE i.qty_on_hand < i.reorder_point
ORDER BY i.qty_on_hand;

-- ---- [Q7 참고] 인덱스가 '실제로' 쓰이면 어떤 계획인지 강제 시연 ----
SET enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT i.product_id, i.qty_on_hand, i.reorder_point
FROM inventory i
WHERE i.qty_on_hand < i.reorder_point
ORDER BY i.qty_on_hand;
SET enable_seqscan = on;
-- 메모: 강제 시 idx_inv_low(부분 인덱스)를 타지만, 데이터가 작아 실측은
--       Seq Scan이 더 빠름 → "튜닝의 정답은 데이터 규모/분포에 의존".


-- ############################################################################
-- Q8) 리뷰 4.5↑ & 50개↑ 효자상품
--     관찰: reviews 2065행 → HashAggregate + Seq Scan이 최적.
--           커버링 인덱스(product_id INCLUDE rating)도 소규모라 미채택(정상).
-- ############################################################################

-- ---- [Q8 튜닝 전] ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT p.product_id, p.product_name,
       count(*)            AS review_cnt,
       round(avg(r.rating), 2) AS avg_rating
FROM reviews r
JOIN products p ON p.product_id = r.product_id
GROUP BY p.product_id, p.product_name
HAVING avg(r.rating) >= 4.5 AND count(*) >= 50
ORDER BY avg_rating DESC, review_cnt DESC;

-- ---- [튜닝] 집계 커버링 인덱스(index-only scan 후보) ----
CREATE INDEX idx_reviews_prod_cov
  ON reviews(product_id) INCLUDE (rating);
ANALYZE reviews;

-- ---- [Q8 튜닝 후] 소규모라 계획 유지될 수 있음(규모↑ 시 index-only로 이득) ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT p.product_id, p.product_name,
       count(*)            AS review_cnt,
       round(avg(r.rating), 2) AS avg_rating
FROM reviews r
JOIN products p ON p.product_id = r.product_id
GROUP BY p.product_id, p.product_name
HAVING avg(r.rating) >= 4.5 AND count(*) >= 50
ORDER BY avg_rating DESC, review_cnt DESC;


-- ############################################################################
-- Q9) 쿠폰 사용 영향 (쿠폰 주문 vs 미사용 주문의 평균 주문금액 비교)
--     튜닝 포인트: 주문 단위 금액을 먼저 만든 뒤 쿠폰 사용여부로 그룹.
--     튜닝 전략(재작성): JOIN 후 곧바로 그룹하지 말고 주문 롤업을 선행.
-- ############################################################################

-- ---- [Q9 튜닝 전] ----
EXPLAIN (ANALYZE, BUFFERS)
SELECT (o.coupon_code IS NOT NULL)  AS used_coupon,
       count(DISTINCT o.order_id)   AS orders,
       round(AVG(oi.line_total), 2) AS avg_line          -- 라인 단위 평균(부정확 소지)
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
GROUP BY (o.coupon_code IS NOT NULL);

-- ---- [Q9 튜닝 후] 주문 단위 금액 롤업 후 AOV 비교(정확 + 단순) ----
EXPLAIN (ANALYZE, BUFFERS)
WITH ord AS (
  SELECT o.order_id,
         (o.coupon_code IS NOT NULL) AS used_coupon,
         SUM(oi.line_total)          AS order_amt
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, (o.coupon_code IS NOT NULL)
)
SELECT used_coupon,
       count(*)                AS orders,
       round(AVG(order_amt), 2) AS aov
FROM ord
GROUP BY used_coupon
ORDER BY used_coupon;
-- 결과: 쿠폰 사용 주문의 AOV가 미사용 대비 크게 높음(고가 상품 유도 효과).


-- ############################################################################
-- Q10) 상위 1% 고객의 최근 60일 매출
--      튜닝 포인트: 60일 기간 필터(약 39%) → 부분 인덱스로 Bitmap Scan 전환.
-- ############################################################################

-- (idx_orders_revts 는 Q1에서 이미 생성됨: 60일 필터에도 사용됨)

-- ---- [Q10 튜닝 전] 아래는 인덱스 없는 계획을 보려면 먼저 DROP 후 실행 ----
-- DROP INDEX IF EXISTS idx_orders_revts;   -- (튜닝 전 계획을 재현하고 싶을 때만)
-- ANALYZE orders;

-- ---- [Q10 실행/튜닝 후] 최근 60일 orders를 Bitmap Index Scan 으로 접근 ----
EXPLAIN (ANALYZE, BUFFERS)
WITH cust_rev AS (                         -- 고객별 전체 누적매출
  SELECT o.customer_id, SUM(oi.line_total) AS total_rev
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.customer_id
),
top1 AS (                                  -- 상위 1% 컷 (99 백분위)
  SELECT customer_id
  FROM cust_rev
  WHERE total_rev >= (
    SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY total_rev) FROM cust_rev
  )
)
SELECT count(DISTINCT t.customer_id) AS top1pct_customers,
       SUM(oi.line_total)            AS recent60d_revenue
FROM top1 t
JOIN orders o     ON o.customer_id = t.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
  AND o.order_ts >= now() - interval '60 days';   -- 이 조건에서 부분 인덱스 사용
-- 개선 요약: orders Seq Scan(cost≈302) → Bitmap Index Scan(idx_orders_revts),
--            실행시간 약 17.5ms → 9.9ms (실측).


-- ############################################################################
-- Q11) 0으로 나누어도 에러 안 나는 나눗셈 함수 → 안전 평균(AOV) 계산
--      seed에 정의된 두 함수를 사용 (파일 00_schema / 01_seed 에 포함).
--        - ecom.safe_div(n,d)  : d=0 이면 NULL 반환 (SQL 함수)
--        - ecom.f_safe_div(a,b): d=0 이면 0 반환 (PL/pgSQL 함수)
-- ############################################################################

-- 0으로 나눠도 에러 없이 처리됨을 확인
SELECT safe_div(100, 0)   AS safediv_zero,     -- NULL
       safe_div(100, 4)   AS safediv_normal,   -- 25
       f_safe_div(100, 0) AS udf_zero,         -- 0
       f_safe_div(100, 4) AS udf_normal;       -- 25

-- 활용: 주문이 0건인 채널이 있어도 AOV 계산이 깨지지 않음
SELECT o.channel,
       count(DISTINCT o.order_id)                       AS orders,
       round(safe_div(SUM(oi.line_total),
                      count(DISTINCT o.order_id)), 2)    AS aov_safe
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.order_id
     AND o.order_status IN ('paid','shipped','delivered')
GROUP BY o.channel
ORDER BY o.channel;

\timing off
-- ============================================================================
-- [끝] 각 문항의 EXPLAIN (ANALYZE) 튜닝 전/후 스크린샷과 결과값을 캡처하세요.
--      전체 집계형(Q2/Q4/Q5/Q9)의 근본 해법은 03_materialized_view.sql 참고.
-- ============================================================================
