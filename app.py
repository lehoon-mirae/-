# -*- coding: utf-8 -*-
"""
자산운용부 일보 대시보드 (Streamlit) — 보험사 일보 양식 전용 (프리미엄 파이낸셜 디자인 에디션)
----------------------------------------------------------------------------------
· 업로드한 일보 엑셀(양식)을 그대로 화면에 표시
· 파일명(일보_YYYYMMDD)에서 기준일을 인식해 월말 스냅샷으로 적재
· 자산구분 대분류별 전월대비 손익 변동을 칼럼으로 구분해 비교 + 차트
실행:  pip install -r requirements.txt  →  streamlit run app.py
----------------------------------------------------------------------------------
"""
import os
import glob
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from report_parser import (parse_report, date_from_filename,
                           MEASURE_COLS, PCT_COLS)

st.set_page_config(page_title="자산운용부 일보 대시보드", page_icon="📊", layout="wide")

# 프리미엄 파이낸셜 컬러 셋
POS, NEG, BRAND = "#10b981", "#ef4444", "#6366f1"
PREMIUM_COLORS = ["#6366f1", "#10b981", "#3b82f6", "#ec4899", "#8b5cf6", "#f59e0b", "#ef4444"]

# ===================================================================
# Premium CSS Injection for Glassmorphism & High-End Financial Vibe
# ===================================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
        
        /* Global typography & background */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            font-family: 'Plus Jakarta Sans', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #070a13 100%) !important;
            color: #e5e7eb !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #080c14 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        
        /* Header Banner Card */
        .header-container {
            background: linear-gradient(90deg, rgba(31, 41, 55, 0.4) 0%, rgba(17, 24, 39, 0.4) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 28px;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }
        
        .header-title {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.025em;
        }
        
        .header-subtitle {
            color: #9ca3af;
            margin-top: 6px;
            margin-bottom: 0;
            font-size: 0.95rem;
            font-weight: 500;
        }
        
        /* Glassmorphic Metric Cards */
        .metric-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 14px;
            padding: 20px;
            backdrop-filter: blur(8px);
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            margin-bottom: 12px;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 12px 25px 0 rgba(99, 102, 241, 0.15);
            background: rgba(255, 255, 255, 0.05);
        }
        
        .metric-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            font-family: 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -0.02em;
        }
        
        .metric-delta {
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 6px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        
        .delta-up {
            color: #34d399;
        }
        
        .delta-down {
            color: #f87171;
        }
        
        /* Premium Tabs styling */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
            color: #9ca3af !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            margin-right: 8px;
        }
        
        button[data-baseweb="tab"]:hover {
            color: #ffffff !important;
            background: rgba(255, 255, 255, 0.05) !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(99, 102, 241, 0.3) !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.12) !important;
        }
        
        /* Custom Premium Table with Sticky Headers */
        .premium-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            background: rgba(255, 255, 255, 0.01);
            color: #d1d5db;
        }
        .premium-table th {
            position: sticky !important;
            top: 0 !important;
            z-index: 10 !important;
            background-color: #0b0f19 !important; /* Perfect opaque dark background to cover scroll items */
            box-shadow: inset 0 -2px 0 rgba(99, 102, 241, 0.4);
            color: #ffffff !important;
            font-weight: 600;
            text-align: center;
            padding: 11px 14px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 0.85rem;
            white-space: nowrap;
        }
        .premium-table td {
            padding: 8px 12px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            vertical-align: middle;
        }
        .premium-table tr:hover {
            background-color: rgba(255, 255, 255, 0.04) !important;
        }
        
        /* Divider color adjustment */
        hr {
            border-color: rgba(255, 255, 255, 0.08) !important;
        }
        
        /* Chart containers styling */
        .chart-box {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Header Banner HTML
st.markdown(
    """
    <div class="header-container">
        <h1 class="header-title">📊 자산운용부 일보 대시보드</h1>
        <p class="header-subtitle">일보 양식 기준 · 자산구분 대분류별 전월대비 손익 비교 (단위: 억원)</p>
    </div>
    """,
    unsafe_allow_html=True
)


# ===================================================================
# 1. 데이터 로드 — 여러 기준일의 일보를 함께 적재 (억원 단위로 변환)
# ===================================================================
@st.cache_data(show_spinner=False)
def load_one(file_bytes, name):
    import io
    df = parse_report(io.BytesIO(file_bytes))
    # 통화량 컬럼을 억원 기준으로 변환 (백만원 -> 억원: 100으로 나눔)
    for c in MEASURE_COLS:
        if c in df.columns and c not in PCT_COLS:
            df[c] = df[c] / 100.0
    return df

st.sidebar.header("① 일보 파일 불러오기")
st.sidebar.caption("월말 일보 여러 개를 함께 올리면 전월대비 비교가 됩니다.")
ups = st.sidebar.file_uploader("일보 엑셀 (.xlsx) — 복수 선택 가능",
                               type=["xlsx"], accept_multiple_files=True)

reports = {}   # {기준일(Timestamp): DataFrame}
if ups:
    for f in ups:
        d = date_from_filename(f.name) or pd.Timestamp.now().normalize()
        reports[d] = load_one(f.getvalue(), f.name)
else:
    for path in sorted(glob.glob("일보_2*.xlsx")):
        d = date_from_filename(path)
        if d is not None:
            with open(path, "rb") as fh:
                reports[d] = load_one(fh.read(), path)
    if reports:
        st.sidebar.info("샘플 일보를 표시 중입니다.\n실제 파일을 올리면 교체됩니다.")

if not reports:
    st.warning("왼쪽 사이드바에서 일보 엑셀 파일을 업로드하세요. "
               "파일명은 '일보_YYYYMMDD.xlsx' 형식을 권장합니다.")
    st.stop()

dates = sorted(reports.keys())
latest = dates[-1]


# ===================================================================
# 2. 공통 헬퍼 & 세로 셀 병합 테이블 렌더러
# ===================================================================
def agg_by_asset(df, metric):
    """대분류합계 행을 기준으로 자산대분류별 지표값 집계."""
    sub = df[df["행구분"] == "대분류합계"]
    return sub.groupby("자산대분류")[metric].sum()


def premium_metric_card(label, value, delta=None, delta_type="up"):
    """글래스모피즘 메트릭 카드를 HTML로 렌더링."""
    delta_html = ""
    if delta is not None:
        if delta_type == "up":
            delta_html = f'<div class="metric-delta delta-up">▲ {delta}</div>'
        else:
            delta_html = f'<div class="metric-delta delta-down">▼ {delta}</div>'
            
    card_html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def apply_premium_chart_theme(fig):
    """Plotly 차트에 프리미엄 파이낸셜 디자인 테마 입히기."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Noto Sans KR, sans-serif", color="#e5e7eb"),
        title_font=dict(size=16, color="#ffffff", family="Plus Jakarta Sans, Noto Sans KR, sans-serif"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.05)",
            font=dict(color="#9ca3af")
        ),
    )
    if hasattr(fig, "layout") and fig.layout:
        if "xaxis" in fig.layout and fig.layout.xaxis:
            fig.update_xaxes(
                gridcolor="rgba(255,255,255,0.06)",
                linecolor="rgba(255,255,255,0.1)",
                tickfont=dict(color="#9ca3af"),
                title_font=dict(color="#d1d5db")
            )
        if "yaxis" in fig.layout and fig.layout.yaxis:
            fig.update_yaxes(
                gridcolor="rgba(255,255,255,0.06)",
                linecolor="rgba(255,255,255,0.1)",
                tickfont=dict(color="#9ca3af"),
                title_font=dict(color="#d1d5db")
            )
    return fig


def df_to_merged_html(df):
    """계층형 텍스트 세로 셀 병합(rowspan)을 처리하고 스크롤 가능하며 헤더가 고정된 HTML 테이블 생성."""
    columns_to_merge = ["구분", "자산_대", "자산_중"]
    merge_cols = [c for c in columns_to_merge if c in df.columns]
    
    # Calculate rowspans for consecutive duplicate cells in hierarchical columns
    rowspans = {col: [1] * len(df) for col in merge_cols}
    for col in merge_cols:
        i = 0
        while i < len(df):
            val_i = df.iloc[i][col]
            # 빈 값(NaN 등)은 병합 대상에서 제외
            if pd.isna(val_i) or str(val_i).strip().lower() in ('nan', 'none', ''):
                rowspans[col][i] = 1
                i += 1
                continue
                
            j = i + 1
            parent_same = True
            while j < len(df):
                val_j = df.iloc[j][col]
                if pd.isna(val_j) or str(val_j).strip().lower() in ('nan', 'none', ''):
                    break
                if val_j != val_i:
                    break
                
                # 상위 계층 컬럼들도 모두 같은지 추가 확인
                col_idx = merge_cols.index(col)
                for p_col in merge_cols[:col_idx]:
                    if df.iloc[j][p_col] != df.iloc[i][p_col]:
                        parent_same = False
                        break
                if not parent_same:
                    break
                j += 1
                
            span = j - i
            rowspans[col][i] = span
            for k in range(i + 1, j):
                rowspans[col][k] = 0
            i = j

    # 행구분에 따른 CSS 스타일 매핑
    def get_row_style(row):
        t = row.get("행구분", "")
        if t == "총합계":
            return "background-color: rgba(99, 102, 241, 0.28); color: #ffffff; font-weight: 700; border-top: 2px solid rgba(99, 102, 241, 0.5); border-bottom: 2px solid rgba(99, 102, 241, 0.5);"
        if t == "대분류합계":
            return "background-color: rgba(59, 130, 246, 0.2); color: #ffffff; font-weight: 600;"
        if t in ("중분류소계", "소계"):
            return "background-color: rgba(255, 255, 255, 0.05); color: #e5e7eb;"
        return "color: #9ca3af;"

    num_cols = [c for c in MEASURE_COLS if c not in PCT_COLS]
    
    # 스크롤 영역 지정을 위한 wrapper div 추가 및 테이블 마진 제거
    html = '<div style="max-height: 520px; overflow-y: auto; overflow-x: auto; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);"><table class="premium-table" style="margin:0; border:none;"><thead><tr>'
    
    # 헤더 생성
    visible_cols = [col for col in df.columns if col not in ("행구분", "자산대분류")]
    for col in visible_cols:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    
    # 행 본문 생성
    for i, (idx, row) in enumerate(df.iterrows()):
        row_style = get_row_style(row)
        html += f'<tr style="{row_style}">'
        for col in visible_cols:
            # 셀 병합 여부 판단
            if col in merge_cols:
                span = rowspans[col][i]
                if span == 0:
                    # 상위 행과 병합된 셀이므로 패스
                    continue
                rowspan_attr = f' rowspan="{span}"' if span > 1 else ''
            else:
                rowspan_attr = ''
                
            val = row[col]
            
            # 포맷팅
            if pd.isna(val) or str(val).strip().lower() in ('nan', 'none', ''):
                val_str = "-"
            elif col in num_cols:
                val_str = f"{val:,.1f}"
            elif col in PCT_COLS:
                val_str = f"{val:,.2f}"
            else:
                val_str = str(val)
                
            # 수치 데이터 우측 정렬, 구분 텍스트 좌측 정렬
            is_num = isinstance(val, (int, float)) and col not in ("구분코드", "구분", "자산_대", "자산_중", "자산_소")
            align_style = "text-align: right;" if is_num else "text-align: left;"
            
            # 메트릭 열 중 증감값에 대한 색상 강조 추가
            cell_style = ""
            if col in ["전월대비 증감"] and isinstance(val, (int, float)):
                if val > 0:
                    cell_style = f"color: {POS}; font-weight: 600;"
                elif val < 0:
                    cell_style = f"color: {NEG}; font-weight: 600;"
            
            html += f'<td{rowspan_attr} style="{align_style} {cell_style}">{val_str}</td>'
        html += '</tr>'
        
    html += '</tbody></table></div>'
    return html


# ===================================================================
# 3. 탭 구성
# ===================================================================
tab1, tab2, tab3 = st.tabs(["📄 원본 일보", "📊 요약 대시보드", "📈 전월대비 비교"])

# ---- 탭 1: 원본 일보 그대로 (세로 셀 병합 HTML 렌더링 + 다차원 계층 필터) ----
with tab1:
    c1, c2, c3 = st.columns([1, 1.2, 1.8])
    sel_date = c1.selectbox("기준일", dates, index=len(dates) - 1,
                            format_func=lambda d: d.strftime("%Y-%m-%d"))
    df = reports[sel_date]
    
    # 2단계 다차원 필터 UI 적용
    filter_col = c2.selectbox("필터 기준 컬럼", ["전체", "구분", "자산_대", "자산_중", "자산_소"])
    
    if filter_col == "전체":
        view = df
        c3.empty()
    else:
        # 선택한 컬럼 기준 고유값 추출 (빈 문자열 제외)
        unique_vals = sorted(df[filter_col].dropna().astype(str).unique().tolist())
        unique_vals = [v for v in unique_vals if v.strip().lower() not in ('nan', 'none', '')]
        sel_val = c3.selectbox(f"필터 값 선택 ({filter_col})", ["전체"] + unique_vals)
        
        if sel_val == "전체":
            view = df
        else:
            view = df[df[filter_col] == sel_val]

    st.caption(f"{sel_date:%Y-%m-%d} 기준 · {len(view):,}개 행 "
               f"(명세 {int((view['행구분']=='명세').sum())} · "
               f"합계/소계 {int((view['행구분']!='명세').sum())}) · 단위: 억원")
    
    # 불필요한 자산대분류 임시컬럼 및 정보 없는 맨 앞의 "구분코드" 컬럼 완전 배제
    drop_cols = ["자산대분류"]
    if "구분코드" in view.columns:
        drop_cols.append("구분코드")
        
    show = view.drop(columns=drop_cols)
    st.markdown(df_to_merged_html(show), unsafe_allow_html=True)

# ---- 탭 2: 요약 대시보드 (최근 기준일) ----
with tab2:
    df = reports[latest]
    st.caption(f"기준일 {latest:%Y-%m-%d} · 단위: 억원")
    tot = df[df["구분코드"] == "AZ1"]
    tot = tot.iloc[0] if len(tot) else df[df["행구분"] == "총합계"].iloc[-1]

    # 프리미엄 HTML 메트릭 카드 배치 (억원 표기)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        premium_metric_card("총 NAV (억원)", f"{tot['NAV_당일']:,.1f}")
    with k2:
        val = tot['NAV_전일비']
        delta_str = f"{abs(val):,.1f}"
        delta_type = "up" if val >= 0 else "down"
        premium_metric_card("NAV 전일비 (억원)", f"{val:,.1f}", delta=delta_str, delta_type=delta_type)
    with k3:
        val = tot['당기손익_당월']
        delta_str = f"{abs(val):,.1f}"
        delta_type = "up" if val >= 0 else "down"
        premium_metric_card("당기손익 (당월, 억원)", f"{val:,.1f}", delta=delta_str, delta_type=delta_type)
    with k4:
        premium_metric_card("당기손익 (FY26, 억원)", f"{tot['당기손익_FY26']:,.1f}")

    st.divider()
    g1, g2 = st.columns([1, 1])

    with g1:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.subheader("자산구분 대분류별 NAV 비중")
        nav = agg_by_asset(df, "NAV_당일").sort_values(ascending=False)
        fig = px.pie(values=nav.values, names=nav.index, hole=0.5, color_discrete_sequence=PREMIUM_COLORS)
        fig.update_traces(textposition="outside", textinfo="label+percent")
        fig.update_layout(height=380, showlegend=False,
                          margin=dict(l=10, r=10, t=10, b=10))
        apply_premium_chart_theme(fig)
        st.plotly_chart(fig, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.subheader("당월 상세손익 구성")
        comp_cols = ["상세_이자", "상세_배당", "상세_환차파생", "상세_평가손익",
                     "상세_매매이익", "상세_매매손실", "상세_신용손실충당금"]
        comp = df[df["행구분"] == "대분류합계"][comp_cols].sum()
        comp.index = [c.replace("상세_", "") for c in comp.index]
        fig = go.Figure(go.Bar(
            x=comp.values, y=comp.index, orientation="h",
            marker_color=[POS if v >= 0 else NEG for v in comp.values],
            text=[f"{v:+,.1f}" for v in comp.values], textposition="outside"))
        fig.update_layout(height=380, margin=dict(l=10, r=40, t=10, b=10))
        apply_premium_chart_theme(fig)
        st.plotly_chart(fig, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.subheader("자산구분 대분류별 당월 당기손익")
    pnl = agg_by_asset(df, "당기손익_당월").sort_values()
    fig = go.Figure(go.Bar(
        x=pnl.values, y=pnl.index, orientation="h",
        marker_color=[POS if v >= 0 else NEG for v in pnl.values],
        text=[f"{v:+,.1f}" for v in pnl.values], textposition="outside"))
    fig.update_layout(height=360, margin=dict(l=10, r=40, t=10, b=10))
    apply_premium_chart_theme(fig)
    st.plotly_chart(fig, width='stretch')
    st.markdown('</div>', unsafe_allow_html=True)

# ---- 탭 3: 전월대비 비교 ----
with tab3:
    if len(dates) < 2:
        st.info("전월대비 비교를 하려면 기준일이 다른 일보 2개 이상이 필요합니다. "
                "사이드바에서 여러 파일을 함께 올려 주세요.")
    else:
        metric = st.selectbox("비교 지표", MEASURE_COLS,
                              index=MEASURE_COLS.index("당기손익_당월"))

        # 자산대분류 × 기준일 피벗
        series = {d.strftime("%Y-%m-%d"): agg_by_asset(reports[d], metric) for d in dates}
        pivot = pd.DataFrame(series).sort_index()
        cols = list(pivot.columns)

        c1, c2 = st.columns(2)
        m_curr = c1.selectbox("비교일 (당월)", cols, index=len(cols) - 1)
        m_prev = c2.selectbox("기준일 (전월)", cols, index=len(cols) - 2)

        if m_prev == m_curr:
            cmp = pd.DataFrame(index=pivot.index)
            cmp[m_prev] = pivot[m_prev].copy()
            cmp["전월대비 증감"] = 0.0
            cmp["증감률(%)"] = 0.0
        else:
            cmp = pivot[[m_prev, m_curr]].copy()
            cmp["전월대비 증감"] = cmp[m_curr] - cmp[m_prev]
            cmp["증감률(%)"] = (cmp["전월대비 증감"] /
                              cmp[m_prev].abs().replace(0, pd.NA) * 100)

        t = cmp.sum(numeric_only=True)
        
        # 프리미엄 HTML 메트릭 카드 배치 (억원 표기)
        kk1, kk2, kk3 = st.columns(3)
        with kk1:
            premium_metric_card(f"{m_curr} 합계 (억원)", f"{cmp[m_curr].sum():,.1f}")
        with kk2:
            val = t['전월대비 증감']
            delta_str = f"{abs(val):,.1f}"
            delta_type = "up" if val >= 0 else "down"
            premium_metric_card("전월대비 증감 (억원)", f"{val:,.1f}", delta=delta_str, delta_type=delta_type)
        with kk3:
            best = cmp["전월대비 증감"].idxmax()
            best_val = cmp.loc[best,'전월대비 증감']
            delta_str = f"{abs(best_val):,.1f}"
            delta_type = "up" if best_val >= 0 else "down"
            premium_metric_card(f"증가 1위 · {best} (억원)", f"{best_val:,.1f}", delta=delta_str, delta_type=delta_type)

        st.divider()
        st.subheader(f"자산구분 대분류별 {metric} — {m_prev} → {m_curr} (단위: 억원)")

        tbl = cmp.reset_index().rename(columns={"index": "자산대분류"})
        def color(v):
            if isinstance(v, (int, float)) and pd.notna(v):
                return f"color:{POS}" if v > 0 else (f"color:{NEG}" if v < 0 else "")
            return ""
        styled = (tbl.style
                  .map(color, subset=["전월대비 증감", "증감률(%)"])
                  .format({m_prev: "{:,.1f}", m_curr: "{:,.1f}",
                           "전월대비 증감": "{:+,.1f}", "증감률(%)": "{:+.1f}%"}, na_rep="-"))
        st.dataframe(styled, width='stretch', hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns([1, 1])
        with g1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown("##### 전월대비 증감")
            bar = cmp.sort_values("전월대비 증감")
            fig = go.Figure(go.Bar(
                x=bar["전월대비 증감"], y=bar.index, orientation="h",
                marker_color=[POS if v >= 0 else NEG for v in bar["전월대비 증감"]],
                text=[f"{v:+,.1f}" for v in bar["전월대비 증감"]], textposition="outside"))
            fig.update_layout(height=420, margin=dict(l=10, r=40, t=10, b=10))
            apply_premium_chart_theme(fig)
            st.plotly_chart(fig, width='stretch')
            st.markdown('</div>', unsafe_allow_html=True)
            
        with g2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown("##### 기준일별 추이")
            trend = pivot.T.reset_index().melt(id_vars="index",
                        var_name="자산대분류", value_name=metric).rename(columns={"index": "기준일"})
            fig = px.line(trend, x="기준일", y=metric, color="자산대분류", color_discrete_sequence=PREMIUM_COLORS, markers=True)
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(font=dict(size=10)))
            apply_premium_chart_theme(fig)
            st.plotly_chart(fig, width='stretch')
            st.markdown('</div>', unsafe_allow_html=True)

st.caption("ⓘ 화면과 데이터가 분리되어 있어, 같은 양식의 일보를 올리면 자동으로 갱신·비교됩니다.")
