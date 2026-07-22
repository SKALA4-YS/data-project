-- =====================================================================
-- Step 2. 스키마 생성 (university DB 접속 후 실행)
-- 실행: psql -p 5433 university -f sql/02_create_schema.sql
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS academy;

COMMENT ON SCHEMA academy IS '학사관리 도메인 오브젝트 모음 스키마';

-- 이후 세션에서 academy 스키마를 우선 탐색하도록 설정
SET search_path TO academy, public;
