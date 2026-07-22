# Day 3 종합실습 (v2) — 학사관리시스템 DB 설계 → 구축 → 조회

PostgreSQL 17 위에 학사관리시스템(학과·교수·학생·강의·수강신청)을
**ERD 설계 → CREATE DATABASE/SCHEMA → DDL → DML → 조회 쿼리**까지 직접 구축한 실습.
DB `university`, 스키마 `academy`.

## 폴더 구성

| 경로 | 역할 |
|------|------|
| `erd/university_erd.mmd`, `erd/university_erd.png` | ERD (Mermaid, 범례 포함·선 겹침 없음) |
| `sql/01_create_database.sql` | `university` DB 생성 |
| `sql/02_create_schema.sql` | `academy` 스키마 생성 |
| `sql/03_ddl_create_table.sql` | 5개 테이블 DDL (PK/FK/UNIQUE/CHECK/DEFAULT/NOT NULL) |
| `sql/04_dml_insert.sql` | 샘플 데이터 (테이블당 10건 이상, 총 75건) |
| `sql/05_query_basic.sql` | SELECT + WHERE + ORDER BY (Q1~Q4) |
| `sql/06_query_functions.sql` | COALESCE / CASE WHEN / 날짜 함수 (Q5~Q8) |
| `sql/07_query_join.sql` | 수강신청 교차 테이블 JOIN + 집계 (Q9~Q12) |
| `results/*.txt` | 접속 확인 + 각 쿼리 실제 실행 로그 |
| `report.html`, `광주_1반_나용성_day3종합실습보고서.pdf` | 제출용 리포트 |

## 데이터 모델 요약

- DEPARTMENT 1:N PROFESSOR / STUDENT / COURSE
- PROFESSOR 1:N COURSE (담당, 미배정 시 NULL)
- STUDENT N:M COURSE → **ENROLLMENT 교차 테이블**로 해소
  - `UNIQUE(student_id, course_id)` 로 동일 강의 중복 신청 차단
  - `grade` NULL = 성적 미부여(진행중)

## 실행 방법

```bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
brew services start postgresql@17          # 포트 5433

psql -p 5433 postgres    -f sql/01_create_database.sql
psql -p 5433 university  -f sql/02_create_schema.sql
psql -p 5433 university  -f sql/03_ddl_create_table.sql
psql -p 5433 university  -f sql/04_dml_insert.sql
psql -p 5433 university  -f sql/05_query_basic.sql
psql -p 5433 university  -f sql/06_query_functions.sql
psql -p 5433 university  -f sql/07_query_join.sql
```

## 환경 참고

이 머신에는 시스템 서비스로 등록된 PostgreSQL 18(`/Library/PostgreSQL/18`)이 이미
포트 **5432**를 점유 중이라, 실습용 Homebrew `postgresql@17` 은 `postgresql.conf`의
`port = 5433` 으로 분리 설정했다. 기존 시스템 서비스는 건드리지 않았다.

## PDF 재생성

```bash
CHROME="/Users/nys/.cache/puppeteer/chrome/mac_arm-150.0.7871.24/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="광주_1반_나용성_day3종합실습보고서.pdf" "$(pwd)/report.html"
```
