-- =====================================================================
-- Step 5. 기초 조회 — SELECT + WHERE + ORDER BY
-- 실행: psql -p 5433 university -f sql/05_query_basic.sql
-- =====================================================================
SET search_path TO academy, public;

\echo '=== Q1. 공과대학 소속 학과 목록 (학과명 오름차순) ==='
SELECT dept_id, dept_name, college, office_phone
FROM department
WHERE college = '공과대학'
ORDER BY dept_name ASC;

\echo '=== Q2. 현재 재학 중인 학생을 입학일 최신순으로 조회 ==='
SELECT student_id, student_name, dept_id, admission_date, status
FROM student
WHERE status = '재학'
ORDER BY admission_date DESC, student_id ASC;

\echo '=== Q3. 정원이 40명 초과인 강의를 정원 내림차순으로 조회 ==='
SELECT course_code, course_name, credits, capacity, semester
FROM course
WHERE capacity > 40
ORDER BY capacity DESC;

\echo '=== Q4. 2015년 이후 임용된 교수를 임용일 오름차순으로 조회 ==='
SELECT prof_id, prof_name, position, hire_date
FROM professor
WHERE hire_date >= '2015-01-01'
ORDER BY hire_date ASC;
