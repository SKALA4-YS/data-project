-- ============================================================
-- SKALA 4기 2주차 day_4 : 종합실습 2 (CampusHub 복합 쿼리)
-- [심화] 문항 11 ~ 13  (ANTI JOIN / 매핑 리포트 / CROSS JOIN)
-- DB: skala_db / Schema: lab / User: skala_user
-- ============================================================
SET search_path TO lab, public;

-- ------------------------------------------------------------
-- 11. DB 과목을 듣지 않은 모든 학생을 나열  → ANTI JOIN
--     (student 중, course='DB' 수강 기록이 없는 학생 = 893명)
--     NOT EXISTS 로 상관 서브쿼리 부정 → NULL 안전
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major
FROM student s
WHERE NOT EXISTS (
    SELECT 1 FROM enroll e
    WHERE e.student_id = s.student_id
      AND e.course = 'DB'
)
ORDER BY s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 12. course_owner(course, manager_id) 매핑 테이블을 만들고,
--     과목별 [수강 인원 + 책임 매니저 이름] 리포트 작성
--     - 매니저(emp_id 2~11, 'Mgr_'로 시작)를 과목에 임의(rotation) 매핑
-- ------------------------------------------------------------
DROP TABLE IF EXISTS course_owner;
CREATE TABLE course_owner (
    course     VARCHAR(50) PRIMARY KEY,
    manager_id INT            -- emp(emp_id) 논리적 참조. (skala_user는 emp에
);                           --   REFERENCES 권한이 없어 물리 FK는 생략)

-- 과목(enroll의 distinct course)을 매니저 10명에 순환 배정
INSERT INTO course_owner (course, manager_id)
SELECT course,
       2 + ((ROW_NUMBER() OVER (ORDER BY course) - 1) % 10) AS manager_id
FROM (SELECT DISTINCT course FROM enroll) c;

-- 리포트: 과목 × 수강 인원 × 책임 매니저 이름
SELECT co.course,
       COUNT(e.student_id) AS enroll_cnt,
       m.name              AS manager_name
FROM course_owner co
JOIN emp m           ON m.emp_id = co.manager_id
LEFT JOIN enroll e   ON e.course = co.course
GROUP BY co.course, m.name
ORDER BY enroll_cnt DESC, co.course
LIMIT 5;

-- ------------------------------------------------------------
-- 13. 학생 × 과목 전체 조합(CROSS JOIN)으로 "학생별 과목 추천 후보"
--     생성, 단 샘플 100건만 확인
--     (과목 목록은 enroll의 distinct course 사용)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, c.course
FROM student s
CROSS JOIN (SELECT DISTINCT course FROM enroll) c
ORDER BY s.student_id, c.course
LIMIT 100;
