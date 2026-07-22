-- =====================================================================
-- Day3 종합실습 : 학사관리시스템 (University Academic Management System)
-- Step 1. 데이터베이스 생성
-- 실행: psql -p 5433 postgres -f sql/01_create_database.sql
-- =====================================================================

DROP DATABASE IF EXISTS university;

CREATE DATABASE university
    WITH ENCODING = 'UTF8'
         TEMPLATE = template0
         LC_COLLATE = 'C'
         LC_CTYPE = 'C';

COMMENT ON DATABASE university IS '학사관리시스템 실습 DB (Day3 종합실습)';

-- 이후 스크립트는 university DB에 접속하여 실행한다. (psql: \c university)
