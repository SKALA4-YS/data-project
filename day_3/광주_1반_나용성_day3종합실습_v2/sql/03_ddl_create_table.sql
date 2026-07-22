-- =====================================================================
-- Step 3. DDL — 제약조건(PK/FK/UNIQUE/CHECK/DEFAULT/NOT NULL) 포함 테이블 생성
-- 실행: psql -p 5433 university -f sql/03_ddl_create_table.sql
-- 생성 순서: FK 참조 대상을 먼저 생성 (department → professor → student → course → enrollment)
-- =====================================================================
SET search_path TO academy, public;

DROP TABLE IF EXISTS enrollment CASCADE;
DROP TABLE IF EXISTS course     CASCADE;
DROP TABLE IF EXISTS student    CASCADE;
DROP TABLE IF EXISTS professor  CASCADE;
DROP TABLE IF EXISTS department CASCADE;

-- 1) 학과 -------------------------------------------------------------
CREATE TABLE department (
    dept_id       SERIAL       PRIMARY KEY,
    dept_name     VARCHAR(50)  NOT NULL UNIQUE,          -- 학과명 (고유)
    college       VARCHAR(50)  NOT NULL,                 -- 단과대학
    office_phone  VARCHAR(20)                            -- 학과 사무실 전화 (NULL 허용)
);
COMMENT ON TABLE department IS '학과';

-- 2) 교수 -------------------------------------------------------------
CREATE TABLE professor (
    prof_id    SERIAL        PRIMARY KEY,
    prof_name  VARCHAR(30)   NOT NULL,
    dept_id    INT           NOT NULL REFERENCES department(dept_id),
    position   VARCHAR(10)   NOT NULL DEFAULT '조교수'
                             CHECK (position IN ('정교수', '부교수', '조교수')),
    email      VARCHAR(100)  NOT NULL UNIQUE,
    hire_date  DATE          NOT NULL DEFAULT CURRENT_DATE
);
COMMENT ON TABLE professor IS '교수';

-- 3) 학생 -------------------------------------------------------------
CREATE TABLE student (
    student_id      SERIAL       PRIMARY KEY,             -- 학번
    student_name    VARCHAR(30)  NOT NULL,
    dept_id         INT          NOT NULL REFERENCES department(dept_id),
    gender          CHAR(1)      CHECK (gender IN ('M', 'F')),
    birth_date      DATE,
    phone           VARCHAR(20),                          -- NULL 허용 (COALESCE 실습용)
    email           VARCHAR(100) UNIQUE,                  -- NULL 허용
    admission_date  DATE         NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(10)  NOT NULL DEFAULT '재학'
                                 CHECK (status IN ('재학', '휴학', '졸업', '제적'))
);
COMMENT ON TABLE student IS '학생';

-- 4) 강의 -------------------------------------------------------------
CREATE TABLE course (
    course_id    SERIAL       PRIMARY KEY,
    course_code  VARCHAR(10)  NOT NULL UNIQUE,            -- 학수번호 (예: CSE101)
    course_name  VARCHAR(50)  NOT NULL,
    dept_id      INT          NOT NULL REFERENCES department(dept_id),
    prof_id      INT          REFERENCES professor(prof_id),  -- 담당교수 미배정 가능(NULL)
    credits      INT          NOT NULL DEFAULT 3
                              CHECK (credits BETWEEN 1 AND 4),
    semester     VARCHAR(20)  NOT NULL,                   -- 개설 학기 (예: 2026-1)
    capacity     INT          NOT NULL DEFAULT 40
                              CHECK (capacity > 0)
);
COMMENT ON TABLE course IS '강의(과목)';

-- 5) 수강신청 (STUDENT-COURSE N:M 교차 테이블) ------------------------
CREATE TABLE enrollment (
    enroll_id    SERIAL      PRIMARY KEY,
    student_id   INT         NOT NULL REFERENCES student(student_id),
    course_id    INT         NOT NULL REFERENCES course(course_id),
    enroll_date  DATE        NOT NULL DEFAULT CURRENT_DATE,
    grade        VARCHAR(2)  CHECK (grade IN ('A+','A','B+','B','C+','C','D+','D','F')),
                                                          -- grade NULL = 성적 미부여(진행중)
    CONSTRAINT uq_enroll_student_course UNIQUE (student_id, course_id)  -- 동일 강의 중복신청 방지
);
COMMENT ON TABLE enrollment IS '수강신청(학생-강의 교차 테이블)';

-- 생성 결과 확인
\dt academy.*
