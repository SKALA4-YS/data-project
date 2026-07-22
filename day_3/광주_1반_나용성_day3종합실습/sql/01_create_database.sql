-- 종합실습 1: 학사관리시스템 DB 설계 -> 구축 -> 조회
-- Step 1. 데이터베이스 / 스키마 생성

DROP DATABASE IF EXISTS academy;
CREATE DATABASE academy
    WITH ENCODING = 'UTF8';

-- 이후 명령은 academy DB에 접속한 상태에서 실행 (psql: \c academy)
