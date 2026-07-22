-- Step 5. SELECT + WHERE + ORDER BY 기초 조회
SET search_path TO academy_schema;

-- Q1. 컴퓨터공학과(dept_id=1) 소속 학생을 입학일 내림차순으로 조회
SELECT student_id, student_name, admission_date, status
FROM student
WHERE dept_id = 1
ORDER BY admission_date DESC;

-- Q2. 3학점 과목을 과목명 오름차순으로 조회
SELECT course_id, course_name, credit, semester_offered
FROM course
WHERE credit = 3
ORDER BY course_name ASC;

-- Q3. 2022년 이후 입학했고 현재 '재학' 상태인 학생을 입학일 오름차순으로 조회
SELECT student_id, student_name, admission_date, status
FROM student
WHERE status = '재학'
  AND admission_date >= '2022-01-01'
ORDER BY admission_date ASC;
