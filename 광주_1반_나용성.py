"""
================================================================================
[실습 1] 자료구조 집계 · 컴프리헨션 · 제너레이터
--------------------------------------------------------------------------------
프로그램 설명
  Sales 데이터(JSON)를 읽어 아래 4가지를 수행한다.
    1) 컴프리헨션        : amount>=1000 필터링 + 지역별 총매출 dict
    2) Counter/defaultdict: 지역별 거래 건수 + 카테고리별 amount 리스트
    3) 제너레이터        : amount>1000 만 yield 하고 list 와 메모리 크기 비교
    4) 종합             : (month, category) 기준 총매출 집계 및 top3

데이터
  Python_Practice2_Data.json 사용
  (Python_Practice1_Data.json 은 'sales = [...]' 형태의 파이썬 코드라 JSON 파싱 불가)

변경내역 (Change History)
  2026-07-20  v1.0  최초 작성 (4개 문제 + checkpoint assert)
  2026-07-20  v1.1  평가기준 반영 - 예외/오류 처리 추가, 머리말·docstring 보강

작성자 : 광주_1반_나용성
================================================================================
"""

import json
import sys
from collections import Counter, defaultdict

DATA_FILE = "Python_Practice2_Data.json"


# =========================================================================
# 데이터 로드 (예외/오류 처리)
# =========================================================================
def load_sales(path):
    """JSON 파일을 읽어 sales 리스트를 반환한다.

    발생 가능한 오류를 명시적으로 처리한다.
      - FileNotFoundError : 파일이 없을 때
      - JSONDecodeError   : JSON 형식이 아닐 때 (Practice1 파일이 해당)
      - 데이터 형식 오류   : 최상위가 리스트가 아닐 때
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"[오류] 데이터 파일을 찾을 수 없습니다: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"[오류] JSON 파싱 실패: {e}")

    if not isinstance(data, list):
        raise SystemExit("[오류] 데이터 최상위 구조가 리스트가 아닙니다.")
    return data


# =========================================================================
# 1) 리스트/딕셔너리 컴프리헨션
# =========================================================================
def part1_comprehension(sales):
    """① amount>=1000 필터링, ② 지역별 총매출 dict(컴프리헨션)."""
    high_sales = [s for s in sales if s["amount"] >= 1000]

    regions = {s["region"] for s in sales}
    region_total = {
        region: sum(s["amount"] for s in sales if s["region"] == region)
        for region in regions
    }
    return high_sales, region_total


# =========================================================================
# 2) Counter + defaultdict
# =========================================================================
def part2_counter_defaultdict(sales):
    """Counter: 지역별 거래 건수 / defaultdict: 카테고리별 amount 리스트."""
    region_count = Counter(s["region"] for s in sales)

    category_amounts = defaultdict(list)
    for s in sales:
        category_amounts[s["category"]].append(s["amount"])  # key 없어도 자동 []
    return region_count, category_amounts


# =========================================================================
# 3) 제너레이터 — 메모리 비교
# =========================================================================
def high_amount_gen(data):
    """amount > 1000 인 레코드만 하나씩 yield 하는 제너레이터."""
    for s in data:
        if s["amount"] > 1000:
            yield s


def part3_generator(sales):
    """제너레이터 객체와 list 버전의 메모리 크기를 비교한다."""
    gen = high_amount_gen(sales)                     # 제너레이터 객체 (실행 지연)
    lst = [s for s in sales if s["amount"] > 1000]   # 리스트 버전
    return sys.getsizeof(gen), sys.getsizeof(lst)    # gen 을 list 로 변환하지 않음


# =========================================================================
# 4) 종합 — 월별·카테고리 매출 집계
# =========================================================================
def part4_monthly_category(sales):
    """(month, category) 기준 총매출 집계(defaultdict) 후 top3 반환."""
    acc = defaultdict(int)
    for s in sales:
        acc[(s["month"], s["category"])] += s["amount"]

    month_cat_total = {key: total for key, total in acc.items()}  # 일반 dict 로 정리
    top3 = sorted(month_cat_total.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return month_cat_total, top3


# =========================================================================
# Checkpoint (assert 검증)
# =========================================================================
def run_checkpoints(sales, region_total, region_count, gen_size, lst_size, top3):
    """평가 checkpoint 를 assert 로 검증한다."""
    assert sum(region_total.values()) == sum(s["amount"] for s in sales)
    counts = [c for _, c in region_count.most_common()]
    assert counts == sorted(counts, reverse=True)
    assert gen_size < lst_size
    top3_amounts = [amt for _, amt in top3]
    assert top3_amounts == sorted(top3_amounts, reverse=True)


# =========================================================================
# main
# =========================================================================
def main():
    sales = load_sales(DATA_FILE)

    try:
        high_sales, region_total = part1_comprehension(sales)
        region_count, category_amounts = part2_counter_defaultdict(sales)
        gen_size, lst_size = part3_generator(sales)
        month_cat_total, top3 = part4_monthly_category(sales)
    except KeyError as e:
        # 레코드에 기대한 키(region/category/amount/month)가 없을 때
        raise SystemExit(f"[오류] 데이터에 필요한 키가 없습니다: {e}")

    print("=== 1) 컴프리헨션 ===")
    print("amount>=1000 거래 수:", len(high_sales))
    print("지역별 총매출:", region_total)

    print("\n=== 2) Counter + defaultdict ===")
    print("지역별 거래 건수 top3:", region_count.most_common(3))
    print("카테고리 목록:", list(category_amounts.keys()))
    print("전자 카테고리 amount 개수:", len(category_amounts["전자"]))

    print("\n=== 3) 제너레이터 메모리 비교 ===")
    print(f"generator 크기: {gen_size} bytes")
    print(f"list 크기     : {lst_size} bytes")
    print(f"generator < list ? {gen_size < lst_size}")

    print("\n=== 4) 월별·카테고리 매출 집계 ===")
    print("그룹 수:", len(month_cat_total))
    print("금액 top3:", top3)

    run_checkpoints(sales, region_total, region_count, gen_size, lst_size, top3)
    print("\n✅ 모든 checkpoint assert 통과")


if __name__ == "__main__":
    main()
