#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKALA day_5 종합실습 4 제출 PDF 생성
- 스크린샷(docs/screenshots) + 설명을 묶어 '광주_1반_나용성.PDF' 생성
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, Preformatted
)
from PIL import Image as PILImage

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "docs", "screenshots")
OUT = os.path.join(BASE, "광주_1반_나용성.pdf")

# ---- 한글 폰트 등록 ----
pdfmetrics.registerFont(TTFont("KR", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"))
KR = "KR"

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName=KR, fontSize=18, leading=24, spaceBefore=6, spaceAfter=10, textColor=colors.HexColor("#1a3d6d"))
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName=KR, fontSize=13, leading=18, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#22508a"), keepWithNext=True)
BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontName=KR, fontSize=9.5, leading=14, spaceAfter=4)
CAP = ParagraphStyle("CAP", parent=styles["Normal"], fontName=KR, fontSize=8.5, leading=12, textColor=colors.HexColor("#555555"), spaceBefore=2, spaceAfter=2, keepWithNext=True)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=14, bulletIndent=3, spaceAfter=3, spaceBefore=1)
LEAD = ParagraphStyle("LEAD", parent=BODY, fontSize=10, leading=15, textColor=colors.HexColor("#22508a"), spaceBefore=4, spaceAfter=3)
CELL = ParagraphStyle("CELL", parent=styles["Normal"], fontName=KR, fontSize=8.3, leading=11)
CELLH = ParagraphStyle("CELLH", parent=styles["Normal"], fontName=KR, fontSize=8.6, leading=11, textColor=colors.white)


def cellize(data):
    """표 데이터의 각 셀 문자열을 Paragraph로 감싸 자동 줄바꿈되게 한다(첫 행=헤더)."""
    out = []
    for i, row in enumerate(data):
        out.append([Paragraph(str(c), CELLH if i == 0 else CELL) for c in row])
    return out
TITLE = ParagraphStyle("TITLE", parent=styles["Title"], fontName=KR, fontSize=26, leading=34, alignment=TA_CENTER, textColor=colors.HexColor("#1a3d6d"))
SUB = ParagraphStyle("SUB", parent=styles["Normal"], fontName=KR, fontSize=12, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#444444"))
MONO = ParagraphStyle("MONO", parent=styles["Code"], fontName="Courier", fontSize=6.8, leading=8.4)

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def img(path, max_w=CONTENT_W, max_h=170 * mm):
    """이미지 비율 유지하며 페이지에 맞게 축소"""
    with PILImage.open(path) as im:
        w, h = im.size
    ratio = min(max_w / w, max_h / h)
    return Image(path, width=w * ratio, height=h * ratio)


def shot(name):
    return os.path.join(SHOTS, name)


story = []

# ===== 표지 =====
story.append(Spacer(1, 55 * mm))
story.append(Paragraph("종합실습 4", TITLE))
story.append(Paragraph("E-Commerce 데이터 성능 튜닝", TITLE))
story.append(Spacer(1, 12 * mm))
story.append(Paragraph("SQL 실행계획 비교 &amp; 성능 개선", SUB))
story.append(Spacer(1, 30 * mm))
story.append(Paragraph("광주 · 1반 · 나용성", SUB))
story.append(Paragraph("PostgreSQL 18.4 · schema ecom · 2026-07-24", SUB))
story.append(PageBreak())

# ===== 개요 =====
story.append(Paragraph("0. 개요 &amp; 튜닝 3원칙", H1))
story.append(Paragraph(
    "전자상거래 데이터의 리포트 쿼리(Q1~Q11)를 작성하고, <b>EXPLAIN (ANALYZE, BUFFERS)</b>로 "
    "병목을 파악해 인덱스 추가 · 쿼리 재작성으로 튜닝하였다. 각 문항은 튜닝 전/후 실행계획을 "
    "실측(actual time)으로 비교하고, 실제 실행 결과값도 함께 수록한다. 데이터 규모: "
    "customers 3,000 / orders 9,560 / order_items 26,083.", BODY))
story.append(Paragraph(
    "※ 결과값(행/집계값)은 인덱스·쿼리 재작성과 무관하게 튜닝 전/후가 동일하다. 튜닝은 '같은 결과를 더 빠르게' "
    "얻는 것이 목적이므로, 각 문항의 결과 화면은 대표로 1회만 수록한다.", CAP))
story.append(Spacer(1, 3 * mm))
principles = [
    ["원칙", "내용"],
    ["① 기간 필터 조회\n(Q1, Q10)", "order_ts 기간 필터가 저선택도 → 부분 인덱스로 Seq Scan을 Bitmap Index Scan으로 전환. 실측 약 2배 개선."],
    ["② 전체 집계 리포트\n(Q2, Q4, Q5, Q9)", "order_status IN(...)이 전체의 76% 통과 → 인덱스 무의미. 쿼리 재작성 또는 Materialized View가 정답."],
    ["③ 작은 차원 테이블\n(Q7, Q8)", "Seq Scan이 최적이라 옵티마이저가 인덱스를 거부. 무조건 인덱스가 아니라 규모 증가 대비 설계가 핵심."],
]
t = Table(cellize(principles), colWidths=[42 * mm, CONTENT_W - 42 * mm])
t.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), KR, 9),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22508a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f9")]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(t)
story.append(Spacer(1, 4 * mm))

# 문항 요약표
story.append(Paragraph("문항별 튜닝 요약", H2))
summary = [
    ["문항", "내용", "튜닝 유형", "핵심 결과"],
    ["Q1", "지난 한 달 실매출", "부분 인덱스", "Seq→Bitmap (8.9→4.5ms)"],
    ["Q2", "월별 주문/매출/AOV", "쿼리 재작성", "count(DISTINCT) 제거 (13→6ms)"],
    ["Q3", "최근 90일 카테고리 Top10", "재작성", "고선택도라 인덱스 무용, 집계후 조인"],
    ["Q4", "제품별 누적매출 RANK Top20", "커버링/MV", "전체집계→MV가 근본해법"],
    ["Q5", "RFM(최근성/빈도/금액)", "인덱스+재작성", "부분 인덱스 + DISTINCT 제거"],
    ["Q6", "첫구매 30일내 재구매율", "쿼리 재작성", "상관 서브쿼리→윈도우 1-pass"],
    ["Q7", "재고 임계치 미달", "부분 인덱스", "소규모라 Seq Scan 최적(인덱스 거부)"],
    ["Q8", "리뷰 4.5↑ &amp; 50↑ 효자상품", "커버링 인덱스", "소규모라 계획 유지(index-only 후보)"],
    ["Q9", "쿠폰 사용/미사용 AOV", "재작성", "주문 롤업 후 AOV 비교"],
    ["Q10", "상위1% 고객 최근60일 매출", "부분 인덱스", "Seq→Bitmap (17.5→9.9ms)"],
    ["Q11", "안전 나눗셈 함수", "함수", "0으로 나눠도 에러 없음"],
]
t2 = Table(cellize(summary), colWidths=[12 * mm, 52 * mm, 26 * mm, CONTENT_W - 90 * mm])
t2.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), KR, 8),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22508a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f9")]),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
]))
story.append(t2)
story.append(PageBreak())

# ===== Q1~Q11 =====
questions = [
    ("Q1) 지난 한 달간 실제 팔린 총 금액 (paid + shipped + delivered)",
     "튜닝 포인트: order_ts 기간 필터(약 20%)인데 부분 인덱스가 없어 orders 전체 Seq Scan. "
     "매출 상태 주문의 order_ts 부분 인덱스를 추가하면 Bitmap Index Scan으로 전환된다.",
     "Q01_before.png", "Q01_after.png",
     "튜닝 전: orders에 Seq Scan (Rows Removed by Filter 다수).",
     "튜닝 후: Bitmap Index Scan(idx_orders_revts)으로 전환. 실행시간 8.9→4.5ms."),
    ("Q2) 월별 주문 수 / 매출 / 주문당 평균금액(AOV)",
     "튜닝 포인트: JOIN 후 count(DISTINCT order_id)는 비싸다. 주문 단위 사전집계로 롤업하면 "
     "DISTINCT 없이 count(*)/AVG로 처리되어 집계가 단순해진다.",
     "Q02_before.png", "Q02_after.png",
     "튜닝 전: JOIN 후 count(DISTINCT) 사용. Execution 약 13~35ms.",
     "튜닝 후: 주문 사전집계 → DISTINCT 제거. Execution 약 6ms."),
    ("Q3) 최근 90일 카테고리 Top10",
     "관찰: 90일 필터는 전체의 약 58%가 통과(고선택도)라 order_ts 인덱스를 만들어도 옵티마이저가 "
     "Seq Scan을 선택한다(인덱스가 정답이 아닌 사례). 대신 매출을 category_id로 먼저 집계하고 "
     "카테고리 이름은 마지막에 1회만 조인해 조인 폭을 줄인다.",
     "Q03_before.png", "Q03_after.png",
     "튜닝 전: categories까지 4중 조인, 넓은 GROUP BY.",
     "튜닝 후: category_id로 선집계 후 14행 차원과 1회 조인."),
    ("Q4) 제품별 누적매출 RANK() Top20",
     "관찰: 기간 필터 없는 전체 누적 집계 → order_items 전량 스캔 불가피, status 필터도 76% 통과라 "
     "인덱스 무의미. 커버링 인덱스로 힙 접근을 줄여보되, 반복 조회의 근본 해법은 Materialized View다.",
     "Q04_before.png", "Q04_after.png",
     "튜닝 전: Hash Join + WindowAgg + Seq Scan.",
     "튜닝 후: order_items 커버링 인덱스(order_id INCLUDE …). 소규모라 이득은 제한적."),
    ("Q5) RFM (Recency / Frequency / Monetary)",
     "튜닝 포인트: 고객별 집계. (customer_id, order_ts) 부분 인덱스 + 주문 단위 사전집계로 "
     "DISTINCT를 제거한다.",
     "Q05_before.png", "Q05_after.png",
     "튜닝 전: orders Seq Scan + count(DISTINCT).",
     "튜닝 후: 부분 인덱스 + 사전집계로 재작성."),
    ("Q6) 첫 구매 후 30일 내 재구매율",
     "튜닝 포인트: 상관 서브쿼리(고객마다 orders 재조회, SubPlan)는 반복 비용이 크다. "
     "윈도우 함수 min() OVER(PARTITION BY customer_id)로 첫 주문시각을 한 번에 붙여 단일 스캔 처리한다.",
     "Q06_before.png", "Q06_after.png",
     "튜닝 전: 상관 서브쿼리(EXISTS) → Index Searches 2254회 반복.",
     "튜닝 후: WindowAgg 1-pass 처리."),
    ("Q7) 재고가 임계치보다 낮은 상품 (곧 품절 위험)",
     "관찰: inventory 600행 → Seq Scan(cost≈12)이 최적. 품절위험 행만 담는 부분 인덱스를 만들어도 "
     "옵티마이저가 거부한다. 이는 오답이 아니라 소규모 테이블의 정상 동작이며, 규모가 커질 때 인덱스가 효과를 낸다.",
     "Q07_before.png", "Q07_after.png",
     "튜닝 전: Seq Scan + Filter(qty_on_hand < reorder_point).",
     "튜닝 후: 부분 인덱스 추가에도 소규모라 Seq Scan 유지(정상)."),
    ("Q8) 리뷰 4.5↑ & 50개↑ 효자상품",
     "관찰: reviews 2,065행 → HashAggregate + Seq Scan이 최적. 커버링 인덱스(product_id INCLUDE rating)도 "
     "소규모라 미채택(정상). 효자상품 12개가 조건을 만족한다.",
     "Q08_before.png", "Q08_after.png",
     "튜닝 전: HashAggregate + HAVING 필터.",
     "튜닝 후: 커버링 인덱스 추가. 규모 증가 시 index-only scan 이득."),
    ("Q9) 쿠폰 사용 영향 (쿠폰 vs 미사용 주문의 평균 주문금액 비교)",
     "튜닝 포인트: JOIN 후 곧바로 그룹하면 라인 단위 평균이 되어 부정확. 주문 단위 금액을 먼저 롤업한 뒤 "
     "쿠폰 사용여부로 그룹하면 정확한 AOV가 된다. 결과: 쿠폰 사용 주문의 AOV가 크게 높음(고가 상품 유도).",
     "Q09_before.png", "Q09_after.png",
     "튜닝 전: 라인 단위 평균(AVG(line_total)).",
     "튜닝 후: 주문 롤업 후 AVG(order_amt) = 정확한 AOV."),
]

for idx, (title, desc, before, after, cap_b, cap_a) in enumerate(questions, start=1):
    story.append(Paragraph(title, H2))
    story.append(Paragraph(desc, BODY))
    story.append(KeepTogether([
        Paragraph("● 튜닝 전 (실행계획) — " + cap_b, CAP), img(shot(before), max_h=124 * mm)]))
    story.append(Spacer(1, 2 * mm))
    story.append(KeepTogether([
        Paragraph("● 튜닝 후 (실행계획) — " + cap_a, CAP), img(shot(after), max_h=124 * mm)]))
    rf = shot("Q%02d_result.png" % idx)
    if os.path.exists(rf):
        story.append(Spacer(1, 2 * mm))
        story.append(KeepTogether([
            Paragraph("● 실행 결과 (결과값은 튜닝 전/후 동일 — 인덱스·재작성은 성능에만 영향)", CAP), img(rf, max_h=150 * mm)]))
    story.append(PageBreak())

# ---- Q10 (before는 텍스트) ----
story.append(Paragraph("Q10) 상위 1% 고객의 최근 60일 매출", H2))
story.append(Paragraph(
    "튜닝 포인트: 60일 기간 필터(약 39%) → 부분 인덱스(idx_orders_revts)로 Bitmap Index Scan 전환. "
    "튜닝 전 계획은 인덱스가 없을 때 orders 전체 Seq Scan이며(아래 실행계획 텍스트), 튜닝 후 Bitmap으로 전환된다.", BODY))
story.append(Paragraph("● 튜닝 전 — orders Seq Scan (Rows Removed by Filter 5810), Execution 17.4ms (psql 실행계획)", CAP))
with open(os.path.join(BASE, "docs", "Q10_before_실행계획.txt"), encoding="utf-8") as f:
    q10_txt = f.read()
box = Table([[Preformatted(q10_txt, MONO)]], colWidths=[CONTENT_W])
box.setStyle(TableStyle([
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f7f7")),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
]))
story.append(box)
story.append(Spacer(1, 3 * mm))
story.append(KeepTogether([
    Paragraph("● 튜닝 후 (실행계획) — Bitmap Index Scan(idx_orders_revts), Execution 9.9ms", CAP),
    img(shot("Q10_after.png"), max_h=124 * mm)]))
_q10r = shot("Q10_result.png")
if os.path.exists(_q10r):
    story.append(Spacer(1, 2 * mm))
    story.append(KeepTogether([
        Paragraph("● 실행 결과 (결과값은 튜닝 전/후 동일 — 인덱스·재작성은 성능에만 영향)", CAP), img(_q10r, max_h=150 * mm)]))
story.append(PageBreak())

# ---- Q11 ----
story.append(Paragraph("Q11) 0으로 나누어도 에러 안 나는 나눗셈 함수 → 안전 평균(AOV) 계산", H2))
story.append(Paragraph(
    "seed에 정의된 안전 나눗셈 함수를 사용한다. safe_div(n,d): d=0이면 NULL, f_safe_div(a,b): d=0이면 0. "
    "주문이 0건인 채널이 있어도 AOV 계산이 깨지지 않는다.", BODY))
story.append(Paragraph("● 채널별 안전 AOV 계산 결과", CAP))
story.append(img(shot("Q11_safediv.png")))
story.append(PageBreak())

# ===== 조인 3종 =====
story.append(Paragraph("3가지 조인(Join) 방식 비교 — Nested Loop / Hash / Merge", H1))
story.append(Paragraph(
    "PostgreSQL 옵티마이저는 통계 · 인덱스 · 정렬 상태를 보고 비용이 최소인 조인 알고리즘을 자동 선택한다. "
    "각 조인이 실제로 나오는 사례를 EXPLAIN으로 확인했다.", BODY))
joins = [
    ("(1) Nested Loop Join", "join_1_nestedloop.png",
     "outer가 소량 + inner에 조인키 인덱스일 때 최적. 특정 고객(customer_id=7)의 주문 15건 각각에 대해 "
     "order_items를 인덱스로 조회(loops=15). Bitmap Index Scan + Index Scan."),
    ("(2) Hash Join", "join_2_hashjoin.png",
     "대량 등가조인의 기본값. 작은 orders(7,286행)로 해시테이블을 빌드하고 order_items(26,083행)를 "
     "훑으며 프로브. 집계성 쿼리 대부분이 여기 해당."),
    ("(3) Merge Join (Sort-Merge)", "join_3_mergejoin.png",
     "양쪽 입력이 조인키로 정렬돼 있을 때 유리. orders(PK Index Scan) × payments(FK 인덱스 Index Scan)를 "
     "order_id 순서로 병합. (학습용으로 hash/nestloop 비활성화하여 유도)"),
]
for jt, jf, jd in joins:
    story.append(KeepTogether([
        Paragraph(jt, H2), Paragraph(jd, BODY), img(shot(jf), max_h=140 * mm)]))
    story.append(PageBreak())

# ===== Materialized View =====
story.append(Paragraph("Materialized View — 일별 GMV 리포트 가속 (mv_daily_gmv)", H1))
story.append(Paragraph(
    "매일 총 판매금액(GMV)은 반복 조회된다. 매번 orders×order_items를 JOIN+SUM하면 비용이 누적되므로, "
    "결과를 미리 계산해 저장하는 Materialized View를 사용한다. 요구사항대로 매일 오후 3시 갱신을 설계한다.", BODY))
mv_perf = [
    ["구분", "실행계획", "실행시간(실측)"],
    ["MV 미사용 (원본 JOIN+SUM)", "Hash Join + HashAggregate, 26k행 스캔", "약 15.9 ms"],
    ["MV 사용 (SELECT * FROM mv)", "결과(122행) 1회 스캔", "약 0.02 ms"],
]
tm = Table(cellize(mv_perf), colWidths=[55 * mm, CONTENT_W - 90 * mm, 35 * mm])
tm.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), KR, 8.5),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22508a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3f9")]),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(tm)
story.append(Paragraph("→ 리포트 반복 조회 비용을 '갱신 시점 1회'로 이전. 약 수백 배 개선.", CAP))
story.append(Spacer(1, 2 * mm))
mv_shots = [
    ("① MV 미사용 — 원본 JOIN+SUM 실행계획", "mv_1_before.png"),
    ("② MV 생성 — CREATE MATERIALIZED VIEW + UNIQUE INDEX", "mv_2_create.png"),
    ("③ MV 사용 — 결과 조회(조인/집계 없음)", "mv_3_after.png"),
    ("④ REFRESH — 일반/CONCURRENTLY 갱신", "mv_4_refresh.png"),
]
for cap, f in mv_shots:
    story.append(Paragraph("● " + cap, CAP))
    story.append(img(shot(f), max_h=120 * mm))
    story.append(Spacer(1, 2 * mm))
story.append(Paragraph("갱신 주기 설계 (요구사항: 매일 오후 3시)", LEAD))
story.append(Paragraph("GMV는 실시간성이 낮은 리포트 지표이므로, 실시간 트리거 대신 배치 갱신으로 설계한다.", BULLET, bulletText="•"))
story.append(Paragraph("OS cron (매일 15:00): <font face='Courier' size=8>0 15 * * * psql -c \"REFRESH MATERIALIZED VIEW CONCURRENTLY ecom.mv_daily_gmv;\"</font>", BULLET, bulletText="•"))
story.append(Paragraph("DB내 스케줄러 pg_cron: <font face='Courier' size=8>cron.schedule('refresh_mv','0 15 * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY ecom.mv_daily_gmv$$)</font>", BULLET, bulletText="•"))
story.append(Paragraph("무중단 갱신(CONCURRENTLY)은 UNIQUE 인덱스가 필수이며, 조회를 막지 않아 운영에 적합하다.", BULLET, bulletText="•"))
story.append(PageBreak())

# ===== 옵티마이저 조사 (옵션) =====
story.append(Paragraph("(Option) DBMS 엔진별 옵티마이저 조사", H1))
story.append(Paragraph(
    "현대 상용/오픈소스 DB는 대부분 비용 기반 옵티마이저(CBO)를 사용한다. 통계를 바탕으로 조인 알고리즘 · "
    "조인 순서 · 스캔 방식을 자동 선택한다.", BODY))
opt = [
    ["항목", "PostgreSQL", "MySQL(InnoDB)", "Oracle", "SQL Server"],
    ["조인 알고리즘", "NL/Hash/Merge", "NL 중심, Hash(8.0.18+)", "NL/Hash/Sort-Merge", "NL/Hash/Merge"],
    ["실행계획 확인", "EXPLAIN (ANALYZE)", "EXPLAIN ANALYZE", "DBMS_XPLAN", "SHOWPLAN / SSMS"],
    ["통계 수집", "ANALYZE(autovacuum)", "ANALYZE TABLE", "DBMS_STATS", "UPDATE STATISTICS"],
    ["힌트", "없음(pg_hint_plan)", "/*+ ... */", "강력한 /*+ ... */", "OPTION (...)"],
    ["플랜 안정성", "(확장)", "-", "SQL Plan Baseline", "Query Store"],
    ["특이점", "Bitmap/부분·표현식 인덱스", "클러스터형 PK", "Adaptive Plans", "Adaptive Joins/컬럼스토어"],
]
to = Table(cellize(opt), colWidths=[26 * mm, (CONTENT_W - 26 * mm) / 4.0] + [(CONTENT_W - 26 * mm) / 4.0] * 3)
to.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), KR, 7.3),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22508a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#dce6f2")),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fb")]),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(to)
story.append(Spacer(1, 3 * mm))
story.append(Paragraph("실무 시사점 (엔진 공통)", LEAD))
story.append(Paragraph("<b>통계가 핵심</b> — 어떤 엔진이든 통계가 낡으면 오추정으로 이어져 나쁜 계획이 나온다. 대량 변경 후 통계를 갱신한다.", BULLET, bulletText="•"))
story.append(Paragraph("<b>인덱스는 만능이 아니다</b> — 소규모/고선택도(대부분 통과) 쿼리는 Full/Seq Scan이 최적. 옵티마이저의 인덱스 미사용이 정상일 수 있다.", BULLET, bulletText="•"))
story.append(Paragraph("<b>힌트는 최후 수단</b> — 먼저 통계·인덱스·쿼리 재작성으로 해결하고, 힌트는 데이터 변화에 취약하므로 신중히 쓴다.", BULLET, bulletText="•"))
story.append(Spacer(1, 1 * mm))
story.append(Paragraph(
    "<b>요약:</b> 네 엔진 모두 비용 기반 옵티마이저로 수렴했으나, 힌트/플랜관리 성숙도는 Oracle·SQL Server가 앞서고, "
    "인덱스 유연성(부분/표현식/Bitmap)은 PostgreSQL이, MySQL은 클러스터형 인덱스와 인덱스 설계 의존이 특징이다.", BODY))

# ===== 빌드 =====
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=15 * mm, bottomMargin=14 * mm,
    title="광주_1반_나용성_종합실습4", author="나용성",
)


def footer(canvas, doc_):
    canvas.saveState()
    canvas.setFont(KR, 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, "광주_1반_나용성 · 종합실습4 · %d" % doc_.page)
    canvas.restoreState()


doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("생성 완료:", OUT)
