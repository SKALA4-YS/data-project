# SKALA day_5 · 종합실습 4 — E-Commerce 성능 튜닝

> 광주 · 1반 · 나용성 · PostgreSQL 18.4 (schema `ecom`)

전자상거래 데이터의 리포트 쿼리(Q1~Q11)를 작성하고, **EXPLAIN (ANALYZE)로 병목을
파악해 인덱스 추가·쿼리 재작성으로 튜닝**한 결과를 정리한다. 3가지 조인 비교,
Materialized View, (옵션) 엔진별 옵티마이저 조사를 포함한다.

## 폴더 구조

```
광주_1반_나용성_종합실습4/
├── README.md                     ← (이 파일) 실행 순서 & 제출 안내
├── sql/
│   ├── 00_schema.sql             ← 스키마 생성 (제공본)
│   ├── 01_seed.sql               ← 데이터 적재 (제공본)
│   ├── 02_tuning_Q01-Q11.sql     ← ★ 문항별 튜닝 전/후 쿼리 + EXPLAIN
│   ├── 03_join_3types.sql        ← 조인 3종(NLJ/Hash/Merge) 유도
│   ├── 04_materialized_view.sql  ← MV 생성/성능비교/갱신
│   └── 99_cleanup.sql            ← 실습 인덱스 원복(재현용)
└── docs/
    ├── 조인_3종_비교.md
    ├── MV_갱신전략.md
    └── 옵티마이저_엔진별_비교.md
```

## 실행 순서

```bash
# 0) 스키마 + 데이터 (관리자 계정으로 최초 1회. 이미 적재했다면 생략)
PGPASSWORD=0000 psql -h localhost -U postgres  -d skala_db -f sql/00_schema.sql
PGPASSWORD=0000 psql -h localhost -U postgres  -d skala_db -f sql/01_seed.sql

# 1) 문항별 튜닝 (스크린샷 대상) — 위→아래로 실행하며 EXPLAIN 캡처
PGPASSWORD=0000 psql -h localhost -U skala_user -d skala_db -f sql/02_tuning_Q01-Q11.sql

# 2) 조인 3종
PGPASSWORD=0000 psql -h localhost -U skala_user -d skala_db -f sql/03_join_3types.sql

# 3) Materialized View
PGPASSWORD=0000 psql -h localhost -U skala_user -d skala_db -f sql/04_materialized_view.sql
```

> GUI(DBeaver/pgAdmin)에서 문항별로 실행하며 결과 그리드와 실행계획을 캡처하는 것을
> 권장한다. `now()` 기준 상대시간 데이터라, **seed 적재 직후** 실행하면 결과가 안정적.

## 문항별 튜닝 요약 (Q1~Q11)

| 문항 | 내용 | 튜닝 유형 | 핵심 |
|------|------|-----------|------|
| Q1 | 지난 한 달 실매출 | **부분 인덱스** | order_ts 부분 인덱스 → Seq→**Bitmap** (약 8.9→4.5ms) |
| Q2 | 월별 주문/매출/AOV | **쿼리 재작성** | 주문 사전집계로 `count(DISTINCT)` 제거 (약 13→6ms) |
| Q3 | 최근 90일 카테고리 Top10 | 재작성 | 90일=고선택도라 인덱스 무용 → 집계 후 차원 조인 |
| Q4 | 제품별 누적매출 RANK Top20 | 커버링/MV | 전체집계라 인덱스 한계 → 반복조회는 MV가 정답 |
| Q5 | RFM(최근성/빈도/금액) | 인덱스+재작성 | (customer_id,order_ts) 부분 인덱스 + DISTINCT 제거 |
| Q6 | 첫구매 30일내 재구매율 | **재작성** | 상관 서브쿼리(SubPlan) → **윈도우 함수 1-pass** |
| Q7 | 재고 임계치 미달 | 부분 인덱스 | 소규모(600행)라 Seq Scan 최적(옵티마이저가 인덱스 거부) |
| Q8 | 리뷰 4.5↑ & 50↑ 효자상품 | 커버링 인덱스 | 소규모(2k행)라 계획 유지 — 규모↑ 시 index-only 이득 |
| Q9 | 쿠폰 사용/미사용 AOV | 재작성 | 주문 롤업 후 AOV 비교(라인 평균 → 정확한 주문 평균) |
| Q10 | 상위1% 고객 최근60일 매출 | **부분 인덱스** | 60일 필터 → Seq→**Bitmap** (약 17.5→9.9ms) |
| Q11 | 안전 나눗셈 함수 | 함수 | `safe_div`/`f_safe_div` — 0으로 나눠도 에러 없음 |

### 이 데이터셋의 튜닝 3원칙 (실측으로 도출)
1. **기간 필터 조회(Q1/Q10)** → 부분 인덱스로 `Seq Scan → Bitmap Index Scan` 전환, 실측 2배↑.
2. **기간 필터 없는 전체 집계(Q2/Q4/Q5/Q9)** → `order_status IN(...)`이 전체의 76%라
   인덱스가 무의미. 정답은 **쿼리 재작성** 또는 **Materialized View**.
3. **작은 차원 테이블(Q7/Q8)** → Seq Scan이 최적이라 옵티마이저가 인덱스를 **거부**.
   무조건 인덱스가 아니라, 규모 증가에 대비한 설계가 핵심.

## 제출물 체크리스트

- [ ] Q1~Q10(+Q11) 문항별 **튜닝 전 쿼리+결과화면 / 튜닝 후 쿼리+결과화면** 스크린샷
- [ ] 3가지 조인 차이점 정리 (`docs/조인_3종_비교.md` + `03_join_3types.sql` 실행계획)
- [ ] Materialized View 생성 스크립트 + 실행 결과 (`04_materialized_view.sql`)
- [ ] (Option) 엔진별 옵티마이저 조사 (`docs/옵티마이저_엔진별_비교.md`)
- [ ] PDF 제출: **`광주_1반_나용성.PDF`** (쿼리가 길면 SQL은 별도 제출 가능,
      단 파일명에 `광주_1반_나용성` 포함)
