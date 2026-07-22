-- =====================================================================
-- Step 7. 수강신청 교차 테이블 JOIN 조회
-- 실행: psql -p 5433 university -f sql/07_query_join.sql
-- =====================================================================
SET search_path TO academy, public;

\echo '=== Q9. 수강신청 상세 현황 — 학생/학과/강의/담당교수 5개 테이블 JOIN ==='
SELECT s.student_name,
       d.dept_name,
       c.course_code,
       c.course_name,
       COALESCE(p.prof_name, '(미배정)') AS professor,
       c.credits,
       COALESCE(e.grade, '진행중')       AS grade
FROM enrollment e
JOIN student    s ON s.student_id = e.student_id
JOIN department d ON d.dept_id    = s.dept_id
JOIN course     c ON c.course_id  = e.course_id
LEFT JOIN professor p ON p.prof_id = c.prof_id
ORDER BY d.dept_name, s.student_name, c.course_code;

\echo '=== Q10. 강의별 수강 인원 집계 (LEFT JOIN + GROUP BY, 정원 대비 신청률) ==='
SELECT c.course_code,
       c.course_name,
       c.capacity,
       COUNT(e.enroll_id)                                        AS enrolled,
       ROUND(COUNT(e.enroll_id) * 100.0 / c.capacity, 1)         AS fill_rate_pct
FROM course c
LEFT JOIN enrollment e ON e.course_id = c.course_id
GROUP BY c.course_id, c.course_code, c.course_name, c.capacity
ORDER BY enrolled DESC, c.course_code;

\echo '=== Q11. 학생별 신청 과목 수 / 취득 학점 (성적 부여된 과목만 합산) ==='
SELECT s.student_name,
       COUNT(e.enroll_id)                                                 AS total_courses,
       SUM(CASE WHEN e.grade IS NOT NULL THEN c.credits ELSE 0 END)       AS earned_credits,
       SUM(CASE WHEN e.grade IS NULL     THEN 1 ELSE 0 END)               AS in_progress
FROM student s
JOIN enrollment e ON e.student_id = s.student_id
JOIN course     c ON c.course_id  = e.course_id
GROUP BY s.student_id, s.student_name
ORDER BY earned_credits DESC, total_courses DESC;

\echo '=== Q12. 학과별 개설 강의 수 및 소속 학생 수 (다중 집계) ==='
SELECT d.dept_name,
       d.college,
       (SELECT COUNT(*) FROM course  c WHERE c.dept_id = d.dept_id) AS course_count,
       (SELECT COUNT(*) FROM student s WHERE s.dept_id = d.dept_id) AS student_count
FROM department d
ORDER BY student_count DESC, d.dept_name;
