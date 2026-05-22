# -*- coding: utf-8 -*-
"""
make_samples.py
업로드된 양식 파일을 기반으로 동작 확인용 월말 샘플 일보를 생성한다.
명세 행에 임의 수치를 채우고, 소계·합계·총합계는 명세 합으로 계산해
양식 레이아웃(헤더·병합셀)을 그대로 유지한 채 저장한다.
"""
import numpy as np
from openpyxl import load_workbook
from report_parser import parse_report, MEASURE_COLS, SUM_COLS

TEMPLATE = "일보_20260520.xlsx"
FIRST_DATA_ROW = 3        # 엑셀 1-indexed, 데이터 시작 행
FIRST_MEASURE_COL = 6     # F열 = 첫 측정 컬럼(투자금액)

# 생성할 월말 기준일과 성장 계수
MONTHS = {"20260331": 1.00, "20260430": 1.018, "20260520": 1.035}


def build_values(struct, scale, seed):
    """구조 정보를 받아 측정값 행렬을 생성."""
    rng = np.random.default_rng(seed)
    n = len(struct)
    vals = {c: np.full(n, np.nan) for c in MEASURE_COLS}
    is_detail = struct["행구분"].values == "명세"

    # --- 명세 행 채우기 ---
    for i in np.where(is_detail)[0]:
        nav = rng.uniform(400, 42000) * scale
        vals["투자금액"][i]      = nav * rng.uniform(0.95, 1.05)
        vals["장부가_FY25말"][i] = nav * rng.uniform(0.9, 1.0)
        vals["NAV_당일"][i]      = nav
        vals["NAV_전일비"][i]    = nav * rng.uniform(-0.012, 0.013)
        vals["당기손익_당월"][i] = nav * rng.uniform(-0.006, 0.011)
        vals["당기손익_전일비"][i] = vals["당기손익_당월"][i] * rng.uniform(0.04, 0.12)
        vals["당기손익_FY26"][i] = vals["당기손익_당월"][i] * rng.uniform(2.5, 5.5)
        vals["BS자본조정_당월"][i] = nav * rng.uniform(-0.004, 0.005)
        vals["BS자본조정_전일비"][i] = vals["BS자본조정_당월"][i] * rng.uniform(0.05, 0.15)
        vals["BS자본조정_FY26"][i] = vals["BS자본조정_당월"][i] * rng.uniform(2, 4)
        vals["BS자본조정_누적"][i] = vals["BS자본조정_FY26"][i] * rng.uniform(1.0, 1.4)
        vals["FVPL누적평가손익"][i] = nav * rng.uniform(-0.02, 0.03)
        vals["ED"][i]   = nav * rng.uniform(0.5, 4.0)
        vals["평잔"][i] = nav * rng.uniform(0.95, 1.02)
        for k in ["상세_이자", "상세_배당", "상세_환차파생", "상세_평가손익",
                  "상세_매매이익", "상세_매매손실", "상세_신용손실충당금"]:
            vals[k][i] = nav * rng.uniform(-0.003, 0.004)
        vals["민감도_100bp당일"][i] = nav * rng.uniform(-0.05, 0.05)
        # 비율 항목
        vals["YTM_헤지포함"][i] = rng.uniform(2.5, 6.0)
        vals["YTM_현물"][i]    = vals["YTM_헤지포함"][i] + rng.uniform(-0.4, 0.4)
        vals["PL수익률"][i]    = rng.uniform(-1.5, 7.5)
        vals["BS수익률"][i]    = vals["PL수익률"][i] + rng.uniform(-1.0, 1.0)

    # --- 소계/합계/총합계 = 명세 합 ---
    code = struct["구분코드"].values
    a_dae, a_jung = struct["자산_대"].values, struct["자산_중"].values
    rtype = struct["행구분"].values
    detail_idx = np.where(is_detail)[0]

    def detail_sum(mask, col):
        return np.nansum([vals[col][j] for j in detail_idx if mask(j)])

    for i in range(n):
        if rtype[i] == "명세":
            continue
        if rtype[i] == "대분류합계":
            name = str(a_dae[i]).replace(" 합계", "")
            mask = lambda j, nm=name, cd=code[i]: a_dae[j] == nm and code[j] == cd
        elif rtype[i] in ("중분류소계", "소계"):
            name = str(a_jung[i]).replace(" 소계", "")
            mask = lambda j, nm=name, cd=code[i]: a_jung[j] == nm and code[j] == cd
        elif rtype[i] == "총합계":
            cd = code[i]
            if cd == "AAZ":
                mask = lambda j: code[j] == "AA"
            elif cd == "APZ":
                mask = lambda j: code[j] == "AP"
            elif cd == "AZ2":   # 채권선도 제외
                mask = lambda j: "채권선도" not in str(a_jung[j])
            else:               # AZ1 일반계정 총합계
                mask = lambda j: True
        else:
            continue
        for col in SUM_COLS:
            vals[col][i] = detail_sum(mask, col)
        # 비율 항목은 NAV 가중평균
        navs = np.array([vals["NAV_당일"][j] for j in detail_idx if mask(j)])
        for col in ["YTM_헤지포함", "YTM_현물", "PL수익률", "BS수익률"]:
            comp = np.array([vals[col][j] for j in detail_idx if mask(j)])
            vals[col][i] = np.nansum(navs * comp) / np.nansum(navs) if navs.sum() else np.nan

    # --- NAV_비중: 일반계정 총합계(AZ1) 대비 ---
    total_nav = np.nansum([vals["NAV_당일"][j] for j in detail_idx])
    for i in range(n):
        if np.isfinite(vals["NAV_당일"][i]):
            vals["NAV_비중"][i] = vals["NAV_당일"][i] / total_nav * 100
    return vals


def write_file(date_str, vals, struct):
    wb = load_workbook(TEMPLATE)
    ws = wb.active
    for i in range(len(struct)):
        for j, col in enumerate(MEASURE_COLS):
            v = vals[col][i]
            if np.isfinite(v):
                ws.cell(row=FIRST_DATA_ROW + i,
                        column=FIRST_MEASURE_COL + j).value = round(float(v), 1)
    out = f"일보_{date_str}.xlsx"
    wb.save(out)
    print("생성:", out)


if __name__ == "__main__":
    struct = parse_report(TEMPLATE)        # 행 구조만 사용 (값은 비어있음)
    for seed, (date_str, scale) in enumerate(MONTHS.items()):
        write_file(date_str, build_values(struct, scale, seed + 1), struct)
    print("샘플 생성 완료 - 명세 행 수:", int((struct['행구분'] == '명세').sum()))
