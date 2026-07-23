-- ============================================================
-- SKALA 4기 2주차 day_4 : 종합실습 2 (CampusHub 복합 쿼리)
-- [심화] 문항 14 ~ 20  (서브쿼리 / 집합 연산)
-- DB: skala_db / Schema: lab / User: skala_user
-- ============================================================
SET search_path TO lab, public;

-- ------------------------------------------------------------
-- 14. 스칼라 서브쿼리(SELECT 절)로 학생 + 소속 학과 정보 붙이기
--     - 각 학생 행에 "학과 평균 GPA", "학과 인원"을 스칼라 서브쿼리로 부착
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major AS dept,
       (SELECT ROUND(AVG(x.gpa), 2) FROM student x WHERE x.major = s.major) AS dept_avg_gpa,
       (SELECT COUNT(*)             FROM student x WHERE x.major = s.major) AS dept_size
FROM student s
ORDER BY s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 15. 전체 평균 GPA 보다 높은 학생  → WHERE 절 (비상관) 서브쿼리
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major, s.gpa
FROM student s
WHERE s.gpa > (SELECT AVG(gpa) FROM student)
ORDER BY s.gpa DESC, s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 16. 자신의 학과 평균 GPA 보다 높은 학생  → 상관(Correlated) 서브쿼리
--     (서브쿼리가 바깥 행의 s.major 를 참조)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major, s.gpa
FROM student s
WHERE s.gpa > (SELECT AVG(x.gpa) FROM student x WHERE x.major = s.major)
ORDER BY s.major, s.gpa DESC
LIMIT 5;

-- ------------------------------------------------------------
-- 17. 수강(enroll) 기록이 있는 학생만  → SEMI JOIN (EXISTS)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major
FROM student s
WHERE EXISTS (SELECT 1 FROM enroll e WHERE e.student_id = s.student_id)
ORDER BY s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 18. 한 번도 수강하지 않은 학생  → NOT IN vs NOT EXISTS 실행계획 비교
--     ⚠ enroll 에는 고아 레코드(1001,1010)가 있으나 student_id 컬럼 자체엔
--       NULL 이 없다. 다만 NOT IN 은 서브쿼리 결과에 NULL 이 섞이면
--       전체가 UNKNOWN 이 되어 0행이 나올 위험이 있으므로 IS NOT NULL 로 방어.
-- ------------------------------------------------------------
-- (18-a) NOT IN 방식 (NULL 위험 → IS NOT NULL 로 방어)
SELECT s.student_id, s.name, s.major
FROM student s
WHERE s.student_id NOT IN (SELECT student_id FROM enroll WHERE student_id IS NOT NULL)
ORDER BY s.student_id
LIMIT 5;

-- (18-b) NOT EXISTS 방식 (권장 · NULL 안전)
SELECT s.student_id, s.name, s.major
FROM student s
WHERE NOT EXISTS (SELECT 1 FROM enroll e WHERE e.student_id = s.student_id)
ORDER BY s.student_id
LIMIT 5;

-- (18-c) 실행계획 비교 : Hash Anti Join vs SubPlan 확인
--   ※ 아래 두 EXPLAIN 을 각각 실행해 계획 노드를 캡처
--   [실측 결과 요약]
--     NOT IN     → Seq Scan on student + Filter (hashed SubPlan)
--                  : Anti Join 으로 변환되지 못하고 SubPlan 으로 처리됨
--                    (서브쿼리 결과에 NULL 이 있을 수 있어 플래너가 보수적으로 동작)
--     NOT EXISTS → Hash Anti Join
--                  : 전용 안티조인 노드로 최적화 → 일반적으로 더 효율적/안전
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM student s
WHERE s.student_id NOT IN (SELECT student_id FROM enroll WHERE student_id IS NOT NULL);
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM student s
WHERE NOT EXISTS (SELECT 1 FROM enroll e WHERE e.student_id = s.student_id);

-- ------------------------------------------------------------
-- 19. HR 학과 학생 "일부"와의 비교 데모  → ANY 서브쿼리
--     gpa > ANY(HR 학생 GPA 목록) = HR 최저 GPA 보다 높은 학생
--     (참고: > ALL 이면 HR 최고 GPA 보다 높은 학생)
-- ------------------------------------------------------------
SELECT s.student_id, s.name, s.major, s.gpa
FROM student s
WHERE s.major <> 'HR'
  AND s.gpa > ANY (SELECT gpa FROM student WHERE major = 'HR')
ORDER BY s.gpa DESC, s.student_id
LIMIT 5;

-- ------------------------------------------------------------
-- 20. CS 학과 학생 "또는" DB 과목 수강 학생 목록  → 합집합(UNION)
--     (UNION 은 중복 학생 자동 제거)
-- ------------------------------------------------------------
SELECT student_id, name, major
FROM student
WHERE major = 'CS'
UNION
SELECT s.student_id, s.name, s.major
FROM student s
JOIN enroll e ON e.student_id = s.student_id
WHERE e.course = 'DB'
ORDER BY student_id
LIMIT 5;
