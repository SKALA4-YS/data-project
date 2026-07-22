-- =====================================================================
-- Step 6. 함수 활용 — COALESCE / CASE WHEN / 날짜 함수
-- 실행: psql -p 5433 university -f sql/06_query_functions.sql
-- =====================================================================
SET search_path TO academy, public;

\echo '=== Q5. COALESCE — 학생 연락처/이메일 미등록 항목을 대체 문자열로 표시 ==='
SELECT student_name,
       COALESCE(phone, '(연락처 미등록)') AS phone,
       COALESCE(email, '(이메일 미등록)') AS email
FROM student
ORDER BY student_id;

\echo '=== Q6. CASE WHEN — 수강신청 성적을 등급 구간으로 분류 (NULL=진행중) ==='
SELECT s.student_name,
       c.course_name,
       e.grade,
       CASE
           WHEN e.grade IN ('A+','A')          THEN '우수'
           WHEN e.grade IN ('B+','B')          THEN '양호'
           WHEN e.grade IN ('C+','C','D+','D') THEN '미흡'
           WHEN e.grade = 'F'                  THEN '낙제'
           ELSE '진행중'
       END AS grade_group
FROM enrollment e
JOIN student s ON s.student_id = e.student_id
JOIN course  c ON c.course_id  = e.course_id
ORDER BY e.grade NULLS LAST, s.student_name;

\echo '=== Q7. 날짜 함수 — 학생 만 나이 / 재학 개월 수 계산 (AGE, EXTRACT) ==='
SELECT student_name,
       birth_date,
       DATE_PART('year', AGE(CURRENT_DATE, birth_date))::INT AS age,
       admission_date,
       (DATE_PART('year',  AGE(CURRENT_DATE, admission_date)) * 12
      + DATE_PART('month', AGE(CURRENT_DATE, admission_date)))::INT AS months_enrolled
FROM student
WHERE birth_date IS NOT NULL
ORDER BY age DESC;

\echo '=== Q8. CASE WHEN — 교수 근속연수 기준 시니어/주니어 구분 ==='
SELECT prof_name,
       position,
       hire_date,
       DATE_PART('year', AGE(CURRENT_DATE, hire_date))::INT AS years_of_service,
       CASE
           WHEN DATE_PART('year', AGE(CURRENT_DATE, hire_date)) >= 15 THEN '시니어'
           WHEN DATE_PART('year', AGE(CURRENT_DATE, hire_date)) >= 8  THEN '미드'
           ELSE '주니어'
       END AS seniority
FROM professor
ORDER BY years_of_service DESC;
