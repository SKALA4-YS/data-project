-- ============================================================
-- SKALA 4기 2주차 day_4 : 종합실습 2 (CampusHub 복합 쿼리)
-- [심화] 문항 21 ~ 22  (ROLLUP·GROUPING / WITH RECURSIVE)
-- DB: skala_db / Schema: lab / User: skala_user
-- ============================================================
SET search_path TO lab, public;

-- ------------------------------------------------------------
-- 21. 학과별·GPA 구간별 인원 집계 + 소계(소계 행) + 총계 를 한 쿼리로
--     - GPA 구간(파생 컬럼): 3.0 미만 / 3.0~3.5 / 3.5 초과
--     - GROUP BY ROLLUP(major, gpa_tier) 로 학과별·전체 소계 동시 조회
--     - GROUPING(major) 로 총계 행에 '전체' 라벨, GROUPING(gpa_tier) 로 소계 라벨
--     - 정렬: major, gpa_tier 순 + 소계/총계 행은 각 그룹 하단
-- ------------------------------------------------------------
SELECT
    CASE GROUPING(major)    WHEN 1 THEN '전체' ELSE major    END AS major,
    CASE GROUPING(gpa_tier) WHEN 1 THEN '소계' ELSE gpa_tier END AS gpa_tier,
    COUNT(*)               AS cnt,
    ROUND(AVG(gpa), 2)     AS avg_gpa
FROM (
    SELECT major, gpa,
           CASE WHEN gpa < 3.0 THEN '3.0미만'
                WHEN gpa <= 3.5 THEN '3.0-3.5'
                ELSE '3.5초과' END AS gpa_tier
    FROM student
) t
GROUP BY ROLLUP(major, gpa_tier)
ORDER BY GROUPING(major), major, GROUPING(gpa_tier), gpa_tier;

-- ------------------------------------------------------------
-- 22. emp 3단계 계층(CEO→매니저10→개발자300)을 WITH RECURSIVE 로 탐색
--     - 각 행: depth(0=CEO), path (예: 'CEO > Mgr_2 > Dev_15')
-- ------------------------------------------------------------
WITH RECURSIVE org AS (
    -- Anchor: CEO (manager_id IS NULL)
    SELECT emp_id, name, manager_id,
           0            AS depth,
           name::TEXT   AS path
    FROM emp
    WHERE manager_id IS NULL
    UNION ALL
    -- Recursive: 상위(org)에 연결된 하위 직원
    SELECT e.emp_id, e.name, e.manager_id,
           o.depth + 1,
           o.path || ' > ' || e.name
    FROM emp e
    JOIN org o ON e.manager_id = o.emp_id
)
SELECT emp_id, name, depth, path
FROM org
ORDER BY path
LIMIT 5;

-- ------------------------------------------------------------
-- 22-b. 매니저별 "직속 부하 직원 수" 집계 (별도 쿼리, 컬럼명 direct_reports)
--       - 직속(=manager_id 가 자신인) 부하만 셈 (재귀 아님)
--       - CEO=10, 각 매니저=30, 개발자=0
-- ------------------------------------------------------------
SELECT m.emp_id, m.name,
       COUNT(e.emp_id) AS direct_reports
FROM emp m
LEFT JOIN emp e ON e.manager_id = m.emp_id
GROUP BY m.emp_id, m.name
ORDER BY direct_reports DESC, m.emp_id
LIMIT 5;
