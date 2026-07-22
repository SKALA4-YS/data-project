-- Step 6. COALESCE / CASE WHEN / 날짜 함수 활용
SET search_path TO academy_schema;

-- Q4. 연락처/이메일 미등록 학생을 COALESCE로 대체 표시
SELECT student_name,
       COALESCE(phone, '연락처 미등록') AS phone,
       COALESCE(email, '이메일 미등록') AS email
FROM student
ORDER BY student_id;

-- Q5. 수강신청 성적을 CASE WHEN으로 등급 분류 (진행중 학기는 NULL)
SELECT e.enrollment_id,
       s.student_name,
       c.course_name,
       e.semester,
       e.grade,
       CASE
           WHEN e.grade IN ('A+', 'A')          THEN '우수'
           WHEN e.grade IN ('B+', 'B')          THEN '보통'
           WHEN e.grade IN ('C+', 'C', 'D+', 'D') THEN '미흡'
           WHEN e.grade = 'F'                   THEN '낙제'
           ELSE '진행중(성적 미입력)'
       END AS grade_level
FROM enrollment e
JOIN student s ON s.student_id = e.student_id
JOIN course  c ON c.course_id = e.course_id
ORDER BY e.semester DESC, s.student_name;

-- Q6. 날짜 함수 활용: 학생의 만 나이, 재학 개월 수 계산
SELECT student_name,
       birth_date,
       EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_date)) AS age,
       admission_date,
       EXTRACT(YEAR FROM AGE(CURRENT_DATE, admission_date)) * 12
         + EXTRACT(MONTH FROM AGE(CURRENT_DATE, admission_date)) AS months_enrolled
FROM student
ORDER BY age DESC;
