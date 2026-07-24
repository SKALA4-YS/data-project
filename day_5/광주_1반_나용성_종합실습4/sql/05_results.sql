-- ============================================================================
-- SKALA day_5 종합실습 4 : 문항별 "결과값" 조회 (EXPLAIN 없이 순수 SELECT)
-- 파일: 05_results.sql
-- 용도: 각 문항의 실제 실행결과 그리드를 캡처하기 위한 최종(튜닝 후) 쿼리 모음.
--       문항 쿼리 하나에 커서를 두고 Ctrl+Enter(단일 실행) → 결과 그리드를 캡처.
--       캡처 파일명: Q01_result.png ~ Q10_result.png (Q11은 Q11_safediv.png로 이미 있음)
-- ============================================================================
SET search_path = ecom, public;

-- ===== Q1) 지난 한 달 실매출 → 캡처: Q01_result.png =====
SELECT COALESCE(SUM(oi.line_total), 0) AS net_sales
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
  AND o.order_ts >= now() - interval '1 month';

-- ===== Q2) 월별 주문수/매출/AOV → 캡처: Q02_result.png =====
WITH order_amt AS (
  SELECT o.order_id, date_trunc('month', o.order_ts) AS ym, SUM(oi.line_total) AS order_total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, date_trunc('month', o.order_ts)
)
SELECT to_char(ym,'YYYY-MM') AS ym, count(*) AS orders,
       SUM(order_total) AS revenue, round(AVG(order_total),2) AS aov
FROM order_amt GROUP BY ym ORDER BY ym;

-- ===== Q3) 최근 90일 카테고리 Top10 → 캡처: Q03_result.png =====
WITH cat_sales AS (
  SELECT p.category_id, SUM(oi.line_total) AS sales
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.order_status IN ('paid','shipped','delivered')
    AND o.order_ts >= now() - interval '90 days'
  GROUP BY p.category_id
)
SELECT cs.category_id, c.category_name, cs.sales
FROM cat_sales cs JOIN categories c ON c.category_id = cs.category_id
ORDER BY cs.sales DESC LIMIT 10;

-- ===== Q4) 제품별 누적매출 RANK Top20 → 캡처: Q04_result.png =====
SELECT * FROM (
  SELECT p.product_id, p.product_name, SUM(oi.line_total) AS revenue,
         RANK() OVER (ORDER BY SUM(oi.line_total) DESC) AS rnk
  FROM order_items oi
  JOIN orders o ON o.order_id = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY p.product_id, p.product_name
) t WHERE rnk <= 20 ORDER BY rnk;

-- ===== Q5) RFM (Top20) → 캡처: Q05_result.png =====
WITH order_amt AS (
  SELECT o.order_id, o.customer_id, o.order_ts, SUM(oi.line_total) AS order_total
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, o.customer_id, o.order_ts
)
SELECT customer_id,
       (CURRENT_DATE - max(order_ts)::date) AS recency_days,
       count(*) AS frequency, SUM(order_total) AS monetary
FROM order_amt GROUP BY customer_id ORDER BY monetary DESC LIMIT 20;

-- ===== Q6) 첫구매 30일내 재구매율 → 캡처: Q06_result.png =====
WITH paid AS (
  SELECT customer_id, order_ts,
         min(order_ts) OVER (PARTITION BY customer_id) AS first_ts
  FROM orders WHERE order_status IN ('paid','shipped','delivered')
)
SELECT
  count(DISTINCT customer_id) AS buyers,
  count(DISTINCT customer_id) FILTER (
    WHERE order_ts > first_ts AND order_ts <= first_ts + interval '30 days') AS repeat_30d,
  round(100.0 * count(DISTINCT customer_id) FILTER (
    WHERE order_ts > first_ts AND order_ts <= first_ts + interval '30 days')
    / count(DISTINCT customer_id), 2) AS repeat_rate_pct
FROM paid;

-- ===== Q7) 재고 임계치 미달 → 캡처: Q07_result.png =====
SELECT i.product_id, p.product_name, i.qty_on_hand, i.reorder_point
FROM inventory i JOIN products p ON p.product_id = i.product_id
WHERE i.qty_on_hand < i.reorder_point
ORDER BY i.qty_on_hand
LIMIT 20;   -- (전체 63건 중 상위 20건. 전체를 보려면 LIMIT 제거)

-- ===== Q8) 리뷰 4.5↑ & 50↑ 효자상품 → 캡처: Q08_result.png =====
SELECT p.product_id, p.product_name,
       count(*) AS review_cnt, round(avg(r.rating),2) AS avg_rating
FROM reviews r JOIN products p ON p.product_id = r.product_id
GROUP BY p.product_id, p.product_name
HAVING avg(r.rating) >= 4.5 AND count(*) >= 50
ORDER BY avg_rating DESC, review_cnt DESC;

-- ===== Q9) 쿠폰 사용/미사용 AOV → 캡처: Q09_result.png =====
WITH ord AS (
  SELECT o.order_id, (o.coupon_code IS NOT NULL) AS used_coupon, SUM(oi.line_total) AS order_amt
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.order_id, (o.coupon_code IS NOT NULL)
)
SELECT used_coupon, count(*) AS orders, round(AVG(order_amt),2) AS aov
FROM ord GROUP BY used_coupon ORDER BY used_coupon;

-- ===== Q10) 상위 1% 고객 최근 60일 매출 → 캡처: Q10_result.png =====
WITH cust_rev AS (
  SELECT o.customer_id, SUM(oi.line_total) AS total_rev
  FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.order_status IN ('paid','shipped','delivered')
  GROUP BY o.customer_id
),
top1 AS (
  SELECT customer_id FROM cust_rev
  WHERE total_rev >= (SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY total_rev) FROM cust_rev)
)
SELECT count(DISTINCT t.customer_id) AS top1pct_customers,
       SUM(oi.line_total) AS recent60d_revenue
FROM top1 t
JOIN orders o ON o.customer_id = t.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('paid','shipped','delivered')
  AND o.order_ts >= now() - interval '60 days';

-- ===== Q11) 안전 나눗셈 → 이미 Q11_safediv.png 로 결과 캡처 완료 =====
-- (참고) 함수 자체 확인:
-- SELECT safe_div(100,0) AS d0, safe_div(100,4) AS dn, f_safe_div(100,0) AS u0, f_safe_div(100,4) AS un;
