# -*- coding: utf-8 -*-
"""
report_parser.py
보험사 자산운용 일보 양식(2단 헤더 · 계층형 행) 전용 파서.
업로드된 엑셀을 일관된 형태의 DataFrame으로 변환한다.
"""
import re
import pandas as pd

# 양식의 32개 컬럼을 정리된 이름으로 매핑 (2단 헤더 결합 결과)
CLEAN_COLS = [
    "구분코드", "구분", "자산_대", "자산_중", "자산_소",
    "투자금액", "장부가_FY25말", "NAV_당일", "NAV_전일비", "NAV_비중",
    "당기손익_전일비", "당기손익_당월", "당기손익_FY26",
    "BS자본조정_전일비", "BS자본조정_당월", "BS자본조정_FY26", "BS자본조정_누적",
    "FVPL누적평가손익", "YTM_헤지포함", "YTM_현물", "PL수익률", "BS수익률", "ED", "평잔",
    "상세_이자", "상세_배당", "상세_환차파생", "상세_평가손익",
    "상세_매매이익", "상세_매매손실", "상세_신용손실충당금", "민감도_100bp당일",
]
ID_COLS = CLEAN_COLS[:5]
MEASURE_COLS = CLEAN_COLS[5:]

# 비율(%) 성격 컬럼 — 합산하면 안 되는 항목
PCT_COLS = ["NAV_비중", "YTM_헤지포함", "YTM_현물", "PL수익률", "BS수익률"]
# 금액 성격 컬럼 — 소계/합계는 하위 명세의 합
SUM_COLS = [c for c in MEASURE_COLS if c not in PCT_COLS]


def _row_type(r):
    """각 행을 명세 / 소계 / 합계 / 총합계로 분류."""
    c1, c2, c3, c4 = (str(r["구분"]), str(r["자산_대"]),
                      str(r["자산_중"]), str(r["자산_소"]))
    if "총합계" in c1:
        return "총합계"
    if c2.endswith("합계"):
        return "대분류합계"
    if c3.endswith("소계"):
        return "중분류소계"
    if c4.endswith("소계") or c4.endswith("합계"):
        return "소계"
    return "명세"


def parse_report(src):
    """엑셀 파일(경로 또는 업로드 객체) → 정리된 DataFrame."""
    raw = pd.read_excel(src, header=None)
    data = raw.iloc[2:].copy()                       # 0~1행은 헤더
    data.columns = CLEAN_COLS[:data.shape[1]]
    data = data.dropna(subset=["구분코드"]).reset_index(drop=True)

    for c in MEASURE_COLS:
        if c in data.columns:
            data[c] = pd.to_numeric(data[c], errors="coerce")

    data["행구분"] = data.apply(_row_type, axis=1)
    # 소계/합계 접미사를 제거한 순수 자산 대분류명
    data["자산대분류"] = (data["자산_대"].astype(str)
                       .str.replace(r"\s*(합계|소계)$", "", regex=True))
    return data


def date_from_filename(name):
    """파일명에서 YYYYMMDD를 찾아 날짜로 변환 (예: 일보_20260520.xlsx)."""
    m = re.search(r"(20\d{6})", str(name))
    return pd.to_datetime(m.group(1), format="%Y%m%d") if m else None
