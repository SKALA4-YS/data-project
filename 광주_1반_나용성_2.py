"""
================================================================================
[실습 2] 파일 I/O · 예외 처리 · Pydantic 검증 파이프라인
--------------------------------------------------------------------------------
프로그램 설명
  Sales 데이터(CSV)를 안전하게 읽고, Pydantic v2 모델(SalesRecord)로 검증하여
  정상(valid) / 오류(errors) 레코드를 분리한다. 이후 valid 는 CSV, errors 는
  JSON 으로 저장하고 다시 읽어 건수를 검증한다.

처리 흐름
  1) safe_load_csv()     : try/except/finally 로 CSV 안전 로딩 (없으면 None)
  2) SalesRecord         : Pydantic v2 스키마 (region/month 필수, amount>0, category 선택)
  3) validate_records()  : raw_data 순회 → valid / errors 분리
  4) 저장 + 재로딩        : valid→CSV(model_dump), errors→JSON(ensure_ascii=False)

데이터
  sales_records.csv (검증 파이프라인 시연용 7행: 정상 4 + 불량 3)
    - 불량 사유: region 빈값 / amount 0(=0초과 위반) / month 빈값

변경내역 (Change History)
  2026-07-20  v1.0  최초 작성 - safe_load_csv, SalesRecord, 검증 파이프라인, 저장/재로딩

작성자 : 광주_1반_나용성
================================================================================
"""

import csv
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

# 로깅 설정 (logger.info / logger.error 출력용)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

INPUT_CSV = "sales_records.csv"
VALID_CSV = "valid_records.csv"
ERRORS_JSON = "error_records.json"


# =========================================================================
# 1) 예외 처리 + 파일 읽기
# =========================================================================
def safe_load_csv(path):
    """CSV 를 안전하게 읽어 dict 리스트를 반환한다.

    - 파일이 없으면 None 반환 + logger.error
    - 성공하면 dict 리스트 반환 + logger.info
    - 성공/실패와 무관하게 finally 에서 '로딩 종료' 출력
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        logger.info(f"CSV 로딩 성공: {path} ({len(rows)}건)")
        return rows
    except FileNotFoundError:
        logger.error(f"파일을 찾을 수 없습니다: {path}")
        return None
    finally:
        print("로딩 종료")


# =========================================================================
# 2) Pydantic v2 스키마 정의
# =========================================================================
class SalesRecord(BaseModel):
    """판매 레코드 스키마.

    - region, month : 비어 있으면 안 됨 (min_length=1)
    - amount        : 0 초과 (gt=0)
    - category      : 없어도 됨 (Optional)
    """

    region: str = Field(min_length=1)
    month: str = Field(min_length=1)
    amount: float = Field(gt=0)
    category: Optional[str] = None


# =========================================================================
# 3) 검증 파이프라인 (valid / errors 분리)
# =========================================================================
def validate_records(raw_data):
    """raw_data 를 순회하며 SalesRecord 로 변환. 성공은 valid, 실패는 errors 로 분리."""
    valid = []
    errors = []
    for row in raw_data:
        try:
            record = SalesRecord(**row)
            valid.append(record)
        except ValidationError as e:
            # ValidationError 만 잡아 오류 내용을 함께 기록
            errors.append({"row": row, "error": str(e)})
            logger.error(f"검증 실패: {row}\n{e}")
    return valid, errors


# =========================================================================
# 4) 결과 파일 저장 + 재로딩
# =========================================================================
def save_valid_csv(valid, path):
    """valid 레코드를 CSV 로 저장 (model_dump 사용)."""
    fieldnames = list(SalesRecord.model_fields.keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in valid:
            writer.writerow(record.model_dump())  # dict 직접 구성 대신 model_dump()


def save_errors_json(errors, path):
    """errors 를 JSON 으로 저장 (한글 깨짐 방지 ensure_ascii=False)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)


# =========================================================================
# main
# =========================================================================
def main():
    # 1) CSV 로딩
    raw_data = safe_load_csv(INPUT_CSV)
    if raw_data is None:
        return 1

    # 3) 검증 파이프라인
    valid, errors = validate_records(raw_data)
    print(f"\n[검증 결과] valid: {len(valid)}건 / errors: {len(errors)}건")

    # 4) 저장
    save_valid_csv(valid, VALID_CSV)
    save_errors_json(errors, ERRORS_JSON)

    # 재로딩 확인
    reloaded = safe_load_csv(VALID_CSV)

    # ---------------------------------------------------------------
    # Checkpoint (assert 검증)
    # ---------------------------------------------------------------
    assert safe_load_csv("no_such_file.csv") is None      # 없는 파일 → None
    assert len(valid) == 4                                 # valid 4건
    assert len(errors) == 3                                # errors 3건
    assert len(reloaded) == 4                              # 재로딩 후 4건

    print("\n✅ 모든 checkpoint assert 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
