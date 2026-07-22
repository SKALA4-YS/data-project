# Day 3 종합실습 — 학사관리시스템 DB 설계 → 구축 → 조회

PostgreSQL 위에 학사관리시스템(학과/교수/학생/과목/수강신청)을 **ERD 설계 → DDL → DML → 조회 쿼리**까지 직접 구축한 실습.

## 구성

| 경로 | 역할 |
|------|------|
| `erd/academic_system_erd.mmd`, `erd/academic_system_erd.png` | ERD (Mermaid, 범례 포함) |
| `sql/01_create_database.sql` | `academy` DB 생성 |
| `sql/02_create_schema.sql` | `academy_schema` 스키마 생성 |
| `sql/03_ddl_create_table.sql` | 5개 테이블 DDL (PK/FK/UNIQUE/CHECK/DEFAULT) |
| `sql/04_dml_insert.sql` | 샘플 데이터 INSERT (테이블당 10건 이상) |
| `sql/05_query_basic.sql` | SELECT + WHERE + ORDER BY 기초 조회 |
| `sql/06_query_functions.sql` | COALESCE / CASE WHEN / 날짜 함수(AGE, EXTRACT) |
| `sql/07_query_join.sql` | 수강신청 교차 테이블 JOIN 조회 |
| `results/*.txt` | 각 단계 실제 실행 결과 캡처 |
| `report.html`, `광주_1반_나용성_day3종합실습보고서.pdf` | 제출용 리포트 |

## ERD 요약

- DEPARTMENT 1:N STUDENT / PROFESSOR / COURSE
- PROFESSOR 1:N COURSE (담당)
- STUDENT N:M COURSE → ENROLLMENT 교차 테이블로 해소 (student_id, course_id, semester UNIQUE)

## 실행

```bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
brew services start postgresql@17   # 포트 5433 (시스템 기존 PostgreSQL 18과 충돌 방지)

psql -p 5433 postgres -f sql/01_create_database.sql
psql -p 5433 academy  -f sql/02_create_schema.sql
psql -p 5433 academy  -f sql/03_ddl_create_table.sql
psql -p 5433 academy  -f sql/04_dml_insert.sql
psql -p 5433 academy  -f sql/05_query_basic.sql
psql -p 5433 academy  -f sql/06_query_functions.sql
psql -p 5433 academy  -f sql/07_query_join.sql
```

## 환경 관련 참고

이 머신에는 이미 시스템 서비스로 등록된 PostgreSQL 18(`/Library/PostgreSQL/18`)이 포트 5432를 사용 중이라,
실습용 `postgresql@17`(Homebrew)은 **5433 포트**로 분리 설정했다 (`postgresql.conf`의 `port = 5433`).
기존 시스템 서비스는 건드리지 않았다.
