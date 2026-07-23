-- ============================================================
-- SKALA 4기 2주차 day_4 : 종합실습 2 (CampusHub 복합 쿼리)
-- [심화] 문항 23 ~ 25  (Window Function)
-- DB: skala_db / Schema: lab / User: skala_user
-- ============================================================
SET search_path TO lab, public;

-- ------------------------------------------------------------
-- 23. 학과(major)별 GPA 상위 3명 추출 (Window Function)
--     - ROW_NUMBER: 학과 내 순위 (동점 시 student_id 오름차순 2차 기준)
--     - RANK / DENSE_RANK 를 함께 계산해 동점 처리 방식 차이 비교
--     - total_in_major: COUNT() OVER(PARTITION BY major)
--     ▶ (23-A) CTE 방식 / (23-B) 서브쿼리 방식 — 두 가지 모두 작성
-- ------------------------------------------------------------

-- (23-A) CTE 방식
WITH ranked AS (
    SELECT student_id, name, major, gpa,
           ROW_NUMBER() OVER (PARTITION BY major ORDER BY gpa DESC, student_id) AS rn,
           RANK()       OVER (PARTITION BY major ORDER BY gpa DESC)             AS rnk,
           DENSE_RANK() OVER (PARTITION BY major ORDER BY gpa DESC)             AS drk,
           COUNT(*)     OVER (PARTITION BY major)                              AS total_in_major
    FROM student
)
SELECT * FROM ranked
WHERE rn <= 3
ORDER BY major, rn
LIMIT 5;

-- (23-B) 서브쿼리(인라인 뷰) 방식 — CTE 없이 동일 결과
SELECT *
FROM (
    SELECT student_id, name, major, gpa,
           ROW_NUMBER() OVER (PARTITION BY major ORDER BY gpa DESC, student_id) AS rn,
           RANK()       OVER (PARTITION BY major ORDER BY gpa DESC)             AS rnk,
           DENSE_RANK() OVER (PARTITION BY major ORDER BY gpa DESC)             AS drk,
           COUNT(*)     OVER (PARTITION BY major)                              AS total_in_major
    FROM student
) r
WHERE rn <= 3
ORDER BY major, rn
LIMIT 5;

-- (23-C) [보조] RANK vs DENSE_RANK 동점 처리 차이 관찰
--   상위 3명은 GPA 동점이라 rnk/drk 가 모두 1 → 차이가 안 보이므로,
--   동점 경계 구간(BIO 학과 rn 32~34)을 보면 차이가 명확:
--     rn=32 GPA 4.90 (동점 32명 마지막) → rnk=1,  drk=1
--     rn=33 GPA 4.40                    → rnk=33 (앞 동점 수만큼 건너뜀), drk=2
SELECT * FROM (
    SELECT student_id, major, gpa,
           ROW_NUMBER() OVER (PARTITION BY major ORDER BY gpa DESC, student_id) AS rn,
           RANK()       OVER (PARTITION BY major ORDER BY gpa DESC)             AS rnk,
           DENSE_RANK() OVER (PARTITION BY major ORDER BY gpa DESC)             AS drk
    FROM student WHERE major = 'BIO'
) t
WHERE rn BETWEEN 32 AND 34
ORDER BY rn;

-- ------------------------------------------------------------
-- 24. enroll 을 student_id 기준 정렬, 이전 수강 과목 대비 성적 변화 추적
--     - grade → 점수 변환 CASE (A=4,B=3,C=2,D=1)
--     - LAG(score) OVER(PARTITION BY student_id ORDER BY course) 로 이전 점수
--     - diff = 현재 - 이전, trend = 상승/유지/하락
--     - score_range = 학생별 MAX(score)-MIN(score) (Window)
-- ------------------------------------------------------------
WITH scored AS (
    SELECT student_id, course, grade,
           CASE grade WHEN 'A' THEN 4 WHEN 'B' THEN 3 WHEN 'C' THEN 2 ELSE 1 END AS score
    FROM enroll
),
lagged AS (
    SELECT student_id, course, grade, score,
           LAG(score) OVER (PARTITION BY student_id ORDER BY course) AS prev_score,
           MAX(score) OVER (PARTITION BY student_id)
             - MIN(score) OVER (PARTITION BY student_id)             AS score_range
    FROM scored
)
SELECT student_id, course, grade, score, prev_score,
       score - prev_score AS diff,
       CASE WHEN prev_score IS NULL   THEN '-'       -- 첫 과목(이전 없음)
            WHEN score > prev_score   THEN '상승'
            WHEN score = prev_score   THEN '유지'
            ELSE '하락' END           AS trend,
       score_range
FROM lagged
ORDER BY student_id, course
LIMIT 5;

-- ------------------------------------------------------------
-- 25. orders 를 order_id 순 정렬, 누적 주문액 + 3개 주문 이동평균 (ROWS BETWEEN)
--     - cum_total   : SUM OVER(ORDER BY order_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
--     - moving_avg_3: AVG OVER(ORDER BY order_id ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
--     - cust_cum    : 고객별 PARTITION 누적 구매액
-- ------------------------------------------------------------
SELECT order_id, customer_id, amount,
       SUM(amount) OVER (ORDER BY order_id
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_total,
       ROUND(AVG(amount) OVER (ORDER BY order_id
                         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)     AS moving_avg_3,
       SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_id
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cust_cum
FROM orders
ORDER BY order_id
LIMIT 5;

-- ------------------------------------------------------------
-- 25-b. 누적합(cum_total)이 전체 합계의 50% 를 처음 초과하는 order_id 찾기
--       - CTE 로 전체 합 대비 누적 비율을 구한 뒤 첫 초과 지점 1건
-- ------------------------------------------------------------
WITH cum AS (
    SELECT order_id, amount,
           SUM(amount) OVER (ORDER BY order_id
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_total,
           SUM(amount) OVER () AS total_sum
    FROM orders
)
SELECT order_id, cum_total, total_sum,
       ROUND(cum_total / total_sum * 100, 2) AS cum_pct
FROM cum
WHERE cum_total >= total_sum * 0.5
ORDER BY order_id
LIMIT 1;
