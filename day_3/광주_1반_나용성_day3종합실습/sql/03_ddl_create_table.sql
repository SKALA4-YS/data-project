-- Step 3. DDL 작성 (제약조건 포함) — academy DB, academy_schema 스키마
SET search_path TO academy_schema;

DROP TABLE IF EXISTS enrollment CASCADE;
DROP TABLE IF EXISTS course CASCADE;
DROP TABLE IF EXISTS student CASCADE;
DROP TABLE IF EXISTS professor CASCADE;
DROP TABLE IF EXISTS department CASCADE;

-- 1. 학과
CREATE TABLE department (
    dept_id         SERIAL PRIMARY KEY,
    dept_name       VARCHAR(50) NOT NULL,
    dept_code       VARCHAR(10) NOT NULL UNIQUE,
    office_location VARCHAR(50)
);

-- 2. 교수
CREATE TABLE professor (
    prof_id     SERIAL PRIMARY KEY,
    prof_name   VARCHAR(30) NOT NULL,
    dept_id     INT NOT NULL REFERENCES department(dept_id),
    email       VARCHAR(100) NOT NULL UNIQUE,
    hire_date   DATE NOT NULL DEFAULT CURRENT_DATE
);

-- 3. 학생
CREATE TABLE student (
    student_id      SERIAL PRIMARY KEY,
    student_name    VARCHAR(30) NOT NULL,
    dept_id         INT NOT NULL REFERENCES department(dept_id),
    birth_date      DATE,
    gender          CHAR(1) CHECK (gender IN ('M', 'F')),
    phone           VARCHAR(20),
    email           VARCHAR(100) UNIQUE,
    admission_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(10) NOT NULL DEFAULT '재학'
                        CHECK (status IN ('재학', '휴학', '졸업', '자퇴'))
);

-- 4. 과목 (개설학과 + 담당교수)
CREATE TABLE course (
    course_id           SERIAL PRIMARY KEY,
    course_name         VARCHAR(50) NOT NULL,
    credit              INT NOT NULL CHECK (credit BETWEEN 1 AND 6),
    dept_id             INT NOT NULL REFERENCES department(dept_id),
    prof_id             INT REFERENCES professor(prof_id),
    semester_offered    VARCHAR(20)
);

-- 5. 수강신청 (학생-과목 교차 테이블, N:M 구현)
CREATE TABLE enrollment (
    enrollment_id   SERIAL PRIMARY KEY,
    student_id      INT NOT NULL REFERENCES student(student_id),
    course_id       INT NOT NULL REFERENCES course(course_id),
    semester        VARCHAR(20) NOT NULL,
    enroll_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    grade           VARCHAR(2) CHECK (grade IN ('A+','A','B+','B','C+','C','D+','D','F')),
    UNIQUE (student_id, course_id, semester)
);
