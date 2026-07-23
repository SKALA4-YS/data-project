-- ============================================================
-- SKALA 4기 2주차 day_4 : 종합실습 2 (CampusHub 복합 쿼리)
-- [기본] 문항 1 ~ 10  (JOIN 중심)
-- DB: skala_db / Schema: lab / User: skala_user
-- 출력 규칙: Postgres → LIMIT 5 (문항 8만 상위 10명 → LIMIT 10)
-- ============================================================
SET search_path TO lab, public;

-- ------------------------------------------------------------
-- 1. 학생과 수강을 INNER JOIN 하여, 수강 존재 학생의 과목/성적 조회
--    → 양쪽 모두 매칭되는 행만 (고아 수강/미수강 학생 제외)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, e.course, e.grade
FROM student s
INNER JOIN enroll e ON e.student_id = s.student_id
ORDER BY s.student_id, e.course
LIMIT 5;

-- ------------------------------------------------------------
-- 2. 모든 학생 기준으로 수강을 붙이고, 과목(없으면 NULL)까지 보이기
--    → LEFT JOIN (student 전부 유지, 미수강 학생은 course NULL)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, e.course, e.grade
FROM student s
LEFT JOIN enroll e ON e.student_id = s.student_id
ORDER BY s.student_id, e.course
LIMIT 5;

-- ------------------------------------------------------------
-- 3. 수강이 기준. 학생이 없으면(고아 수강) 학생 정보가 NULL
--    → RIGHT JOIN (enroll 전부 유지, student 없으면 NULL)
--    확인 포인트: 고아 수강 1001/1010 은 학생정보가 NULL 로 나옴
-- ------------------------------------------------------------
SELECT s.student_id AS s_id, s.name, e.student_id AS e_id, e.course, e.grade
FROM student s
RIGHT JOIN enroll e ON e.student_id = s.student_id
ORDER BY s.student_id NULLS FIRST, e.course   -- 고아(NULL)부터 보이도록
LIMIT 5;

-- ------------------------------------------------------------
-- 4. 학생 / 수강 모두 포함  → FULL OUTER JOIN
--    (미수강 학생 + 고아 수강 양쪽 다 NULL 채워서 표시)
-- ------------------------------------------------------------
SELECT s.student_id AS s_id, s.name, e.student_id AS e_id, e.course, e.grade
FROM student s
FULL OUTER JOIN enroll e ON e.student_id = s.student_id
ORDER BY s.student_id NULLS FIRST, e.course
LIMIT 5;

-- ------------------------------------------------------------
-- 5. 한 번도 수강하지 않은 학생 목록  → ANTI JOIN
--    (LEFT JOIN 후 enroll 쪽 NULL 인 학생 = 미수강)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major
FROM student s
LEFT JOIN enroll e ON e.student_id = s.student_id
WHERE e.student_id IS NULL
ORDER BY s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 6. 한 과목 이상 수강한 학생 목록(중복 제거)  → SEMI JOIN
--    (EXISTS 로 수강 존재 여부만 확인, 중복 없이 학생 1행)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major
FROM student s
WHERE EXISTS (SELECT 1 FROM enroll e WHERE e.student_id = s.student_id)
ORDER BY s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 7. 고객별 주문건수 / 총액  → INNER JOIN + GROUP BY
-- ------------------------------------------------------------
SELECT c.customer_id, c.customer_name,
       COUNT(o.order_id)      AS order_cnt,
       SUM(o.amount)          AS total_amount
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id
LIMIT 5;

-- ------------------------------------------------------------
-- 8. 총액 상위 10명과 금액  → GROUP BY + ORDER BY DESC + LIMIT 10
-- ------------------------------------------------------------
SELECT c.customer_id, c.customer_name,
       SUM(o.amount) AS total_amount
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_amount DESC
LIMIT 10;

-- ------------------------------------------------------------
-- 9. 모든 직원과 그 매니저 이름  → SELF JOIN
--    (CEO 는 매니저가 없으므로 LEFT JOIN 으로 유지, 매니저명 NULL)
-- ------------------------------------------------------------
SELECT e.emp_id, e.name AS emp_name, m.name AS manager_name
FROM emp e
LEFT JOIN emp m ON m.emp_id = e.manager_id
ORDER BY e.emp_id
LIMIT 5;

-- ------------------------------------------------------------
-- 10. "모든 학생 기준"으로 과목 분포  → LEFT JOIN + 집계
--     (미수강 학생도 포함해서 과목별 수강 인원 집계)
--     미수강 학생 그룹은 course = NULL 로 묶여 나타남
-- ------------------------------------------------------------
SELECT COALESCE(e.course, '(미수강)') AS course,
       COUNT(e.student_id)            AS enroll_cnt   -- 수강 건수(미수강 그룹은 0)
FROM student s
LEFT JOIN enroll e ON e.student_id = s.student_id
GROUP BY e.course
ORDER BY enroll_cnt ASC, course   -- 소수 그룹부터 → 미수강(0)/DB 등 LEFT JOIN 효과 확인
LIMIT 5;
