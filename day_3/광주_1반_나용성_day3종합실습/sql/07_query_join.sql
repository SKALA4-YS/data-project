-- Step 7. 수강신청 교차 테이블 JOIN 조회
SET search_path TO academy_schema;

-- Q7. 2026-1학기 수강신청 현황: 학생명/학과, 과목명/담당교수, 학점 (4개 테이블 JOIN)
SELECT s.student_name,
       d.dept_name,
       c.course_name,
       p.prof_name AS professor,
       c.credit,
       e.semester
FROM enrollment e
JOIN student    s ON s.student_id = e.student_id
JOIN department d ON d.dept_id = s.dept_id
JOIN course     c ON c.course_id = e.course_id
JOIN professor  p ON p.prof_id = c.prof_id
WHERE e.semester = '2026-1'
ORDER BY d.dept_name, s.student_name;

-- Q8. 과목별 수강 인원수 집계 (교차 테이블 GROUP BY)
SELECT c.course_name,
       p.prof_name AS professor,
       COUNT(e.enrollment_id) AS enrolled_count
FROM course c
LEFT JOIN professor p ON p.prof_id = c.prof_id
LEFT JOIN enrollment e ON e.course_id = c.course_id
GROUP BY c.course_id, c.course_name, p.prof_name
ORDER BY enrolled_count DESC, c.course_name;

-- Q9. 학생별 취득 학점(성적이 부여된 과목의 credit 합계) 조회
SELECT s.student_name,
       COUNT(e.enrollment_id) AS total_enrollments,
       SUM(CASE WHEN e.grade IS NOT NULL THEN c.credit ELSE 0 END) AS earned_credits
FROM student s
JOIN enrollment e ON e.student_id = s.student_id
JOIN course c ON c.course_id = e.course_id
GROUP BY s.student_id, s.student_name
ORDER BY earned_credits DESC;
