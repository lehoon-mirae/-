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

st.set_page_config(page_title="자산운용일보", page_icon="📊", layout="wide")

# 미래에셋생명 프리미엄 브랜드 컬러 셋
BRAND_NAVY = "#004B93"
BRAND_ORANGE = "#EC6608"
BRAND_BEIGE = "#FFF8F2"

POS, NEG, BRAND = "#DC2626", "#2563EB", BRAND_NAVY
PREMIUM_COLORS = ["#004B93", "#EC6608", "#0284C7", "#F97316", "#0EA5E9", "#3B82F6", "#F59E0B"]

# ===================================================================
# Session State for Login Authentication
# ===================================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# ===================================================================
# Login Screen Gate
# ===================================================================
if not st.session_state["logged_in"]:
    # Style and render login screen
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
            
            /* Global typography & background */
            html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, .block-container {
                font-family: 'Plus Jakarta Sans', 'Noto Sans KR', sans-serif;
                background: linear-gradient(135deg, #FAF6F0 0%, #FFFFFF 50%, #F5EFE6 100%) !important;
                color: #1E293B !important;
            }
            
            /* Hide sidebar entirely on login page */
            [data-testid="stSidebar"] {
                display: none !important;
            }
            
            /* Premium form design */
            div[data-testid="stForm"] {
                background: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-left: 6px solid #EC6608 !important;
                border-radius: 16px !important;
                padding: 40px !important;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04) !important;
                margin-top: 50px;
            }
            
            /* Force dark text and clean border styling on form inputs and labels */
            div[data-testid="stForm"] input {
                border-radius: 8px !important;
                border-color: #E2E8F0 !important;
                color: #1E293B !important;
                background-color: #FFFFFF !important;
            }
            div[data-testid="stForm"] label p {
                color: #1E293B !important;
                font-weight: 600 !important;
            }
            
            /* Form submit button styling with brand colors & hover animation */
            div[data-testid="stForm"] button[type="submit"] {
                background-color: #004B93 !important;
                color: #FFFFFF !important;
                border: none !important;
                font-weight: 700 !important;
                padding: 12px 24px !important;
                border-radius: 8px !important;
                box-shadow: 0 4px 12px rgba(0, 75, 147, 0.15) !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }
            div[data-testid="stForm"] button[type="submit"]:hover {
                background-color: #EC6608 !important;
                box-shadow: 0 6px 18px rgba(236, 102, 8, 0.25) !important;
                transform: translateY(-2px) !important;
            }
            div[data-testid="stForm"] button[type="submit"]:active {
                transform: translateY(0) !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.write("")
        st.write("")
        with st.form("login_form", clear_on_submit=False):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 25px;">
                    <div style="display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="color: #004B93; font-weight: 900; font-size: 1.0rem; letter-spacing: -0.03em;">MIRAE ASSET</span>
                        <span style="color: #EC6608; font-weight: 500; font-size: 0.9rem; border-left: 1px solid #E2E8F0; padding-left: 10px;">미래에셋생명</span>
                    </div>
                    <h2 style="color: #004B93; font-size: 1.9rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">📊 자산운용일보</h2>
                    <p style="color: #64748B; font-size: 0.95rem; margin-top: 6px; font-weight: 500;">자산운용본부 인가 인원 전용 시스템</p>
                    <div style="background-color: #FFF5EB; border: 1px solid #FDE8D0; border-left: 5px solid #004B93; border-radius: 8px; padding: 12px; margin-top: 18px; color: #C2410C; font-weight: 600; font-size: 0.82rem; text-align: center; line-height: 1.4;">
                        🔒 본 화면은 자산운용본부의 인가된 인원만 접속이 가능합니다.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            username = st.text_input("👤 사용자 ID", placeholder="아이디를 입력하세요", key="login_username")
            password = st.text_input("🔑 비밀번호", placeholder="비밀번호를 입력하세요", type="password", key="login_password")
            
            submit_button = st.form_submit_button("로그인", use_container_width=True)
            
            st.markdown(
                """
                <div style="text-align: center; margin-top: 15px;">
                    <p style="font-size: 0.8rem; color: #94A3B8; margin: 0;">※ 테스트 계정: <b>admin</b> / <b>1234</b></p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            if submit_button:
                if username == "admin" and password == "1234":
                    st.session_state["logged_in"] = True
                    st.success("🎯 로그인 성공! 대시보드로 진입합니다.")
                    st.rerun()
                else:
                    st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
                    
    st.stop()

# ===================================================================
# Premium CSS Injection for Mirae Asset Light Design System
# ===================================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
        
        /* Global typography & background */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, .block-container {
            font-family: 'Plus Jakarta Sans', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #FAF6F0 0%, #FFFFFF 50%, #F5EFE6 100%) !important;
            color: #1E293B !important;
        }
        
        /* Force light theme colors on all standard Streamlit markdown texts */
        div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] span {
            color: #1E293B !important;
        }
        
        /* Sidebar styling - robust light theme */
        section[data-testid="stSidebar"], [data-testid="stSidebarUserContent"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #334155 !important;
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p {
            color: #0F172A !important;
        }
        
        /* Form & Selectbox & Inputs styling to completely prevent dark-mode blending */
        div[data-baseweb="select"] *, div[data-baseweb="input"] *, input, select, textarea {
            color: #1E293B !important;
        }
        div[data-baseweb="select"] > div, div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border-color: #E2E8F0 !important;
        }
        label[data-testid="stWidgetLabel"] p {
            color: #1E293B !important;
            font-weight: 600 !important;
        }
        ul[role="listbox"] * {
            color: #1E293B !important;
            background-color: #FFFFFF !important;
        }
        ul[role="listbox"] li:hover {
            background-color: #FFF8F2 !important;
            color: #EC6608 !important;
        }
        
        /* Header Banner Card */
        .header-container {
            background: linear-gradient(90deg, #FFF5EB 0%, #FFFFFF 100%);
            border: 1px solid #FDE8D0; /* Soft warm border */
            border-left: 6px solid #EC6608; /* Warm brand orange line */
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 28px;
            box-shadow: 0 4px 20px rgba(236, 102, 8, 0.05);
        }
        
        .header-title {
            color: #004B93 !important;
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.025em;
        }
        
        .header-subtitle {
            color: #475569;
            margin-top: 6px;
            margin-bottom: 0;
            font-size: 0.95rem;
            font-weight: 500;
        }
        
        /* Premium Light Metric Cards with Warm Beige touches */
        .metric-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            margin-bottom: 12px;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
            border-color: #EC6608;
            box-shadow: 0 12px 25px rgba(236, 102, 8, 0.1);
            background: #FFF8F2; /* Stable Light Beige touch */
        }
        
        .metric-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0F172A;
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
            color: #DC2626; /* Crimson Red for increase */
        }
        
        .delta-down {
            color: #2563EB; /* Blue for decrease */
        }
        
        /* Premium Tabs styling */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
            color: #64748B !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            margin-right: 8px;
        }
        
        button[data-baseweb="tab"]:hover {
            color: #EC6608 !important;
            background: rgba(236, 102, 8, 0.05) !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            background: #004B93 !important;
            color: #ffffff !important;
            border: 1px solid #004B93 !important;
            box-shadow: 0 4px 15px rgba(0, 75, 147, 0.15) !important;
        }
        
        /* Custom Premium Table with Sticky Headers for Light Mode */
        .premium-table {
            width: max-content !important;
            table-layout: fixed !important;
            border-collapse: separate !important;
            border-spacing: 0 !important;
            border-top: 1px solid #E2E8F0 !important;
            border-left: 1px solid #E2E8F0 !important;
            font-size: 0.85rem;
            background: #FFFFFF;
            color: #334155;
        }
        .premium-table th {
            position: sticky !important;
            top: 0 !important;
            z-index: 10 !important;
            background-color: #004B93 !important; /* Brand Navy Header */
            color: #ffffff !important;
            font-weight: 600;
            text-align: center;
            padding: 11px 14px;
            border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
            font-size: 0.85rem;
            white-space: nowrap;
            box-shadow: inset 0 -2px 0 #EC6608; /* Brand Orange Bottom Border inside th */
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .premium-table td {
            padding: 8px 12px;
            border-right: 1px solid #E2E8F0 !important;
            border-bottom: 1px solid #E2E8F0 !important;
            vertical-align: middle;
            white-space: nowrap !important; /* 글자가 절대 줄바꿈되거나 잘리지 않도록 설정 */
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .premium-table tr:hover {
            background-color: #F8FAFC !important;
        }
        
        /* Divider color adjustment */
        hr {
            border-color: #E2E8F0 !important;
        }
        
        /* Chart containers styling */
        .chart-box {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);
        }
        
        /* PDF 인쇄 시 불필요한 요소 자동 은폐 및 여백 최적화 */
        @media print {
            [data-testid="stSidebar"], [data-testid="stHeader"], .no-print, iframe {
                display: none !important;
            }
            html, body, [data-testid="stAppViewContainer"], .main, .block-container {
                background: #FFFFFF !important;
                color: #000000 !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            .premium-table {
                box-shadow: none !important;
                border: 1px solid #000000 !important;
            }
            .premium-table th {
                background-color: #004B93 !important;
                color: #FFFFFF !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .premium-table td {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Header Banner HTML
st.markdown(
    """
    <div class="header-container">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <span style="color: #004B93; font-weight: 900; font-size: 1.1rem; letter-spacing: -0.03em;">MIRAE ASSET</span>
            <span style="color: #EC6608; font-weight: 500; font-size: 1.0rem; border-left: 1px solid #E2E8F0; padding-left: 12px;">미래에셋생명</span>
        </div>
        <h1 class="header-title">📊 자산운용일보</h1>
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

# ===================================================================
# Sidebar Logout Button & Custom Styling
# ===================================================================
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <style>
        /* Sidebar button custom styling */
        section[data-testid="stSidebar"] button {
            background-color: transparent !important;
            border: 1px solid #E2E8F0 !important;
            color: #475569 !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
        }
        section[data-testid="stSidebar"] button:hover {
            color: #DC2626 !important;
            border-color: #FCA5A5 !important;
            background-color: #FEF2F2 !important;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.08) !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

if st.sidebar.button("🔓 로그아웃", use_container_width=True):
    st.session_state["logged_in"] = False
    st.success("로그아웃 되었습니다.")
    st.rerun()

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
    """Plotly 차트에 프리미엄 파이낸셜 디자인 테마 입히기 (미래에셋 라이트 모드)"""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Noto Sans KR, sans-serif", color="#334155"),
        title_font=dict(size=16, color="#0F172A", family="Plus Jakarta Sans, Noto Sans KR, sans-serif"),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#E2E8F0",
            font=dict(color="#475569")
        ),
    )
    if hasattr(fig, "layout") and fig.layout:
        if "xaxis" in fig.layout and fig.layout.xaxis:
            fig.update_xaxes(
                gridcolor="#F1F5F9",
                linecolor="#E2E8F0",
                tickfont=dict(color="#64748B"),
                title_font=dict(color="#334155")
            )
        if "yaxis" in fig.layout and fig.layout.yaxis:
            fig.update_yaxes(
                gridcolor="#F1F5F9",
                linecolor="#E2E8F0",
                tickfont=dict(color="#64748B"),
                title_font=dict(color="#334155")
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
            return "background-color: #FDF2E9 !important; color: #C2410C !important; font-weight: 800; border-top: 2px solid #EC6608; border-bottom: 2px solid #EC6608;"
        if t == "대분류합계":
            return "background-color: #EBF3FC !important; color: #004B93 !important; font-weight: 700; border-bottom: 1.5px solid #004B93;"
        if t in ("중분류소계", "소계"):
            return "background-color: #F4EFE6 !important; color: #1E293B !important; font-weight: 600; border-bottom: 1px solid #D5CFC6;"
        return "background-color: #FFFFFF !important; color: #475569 !important;"

    num_cols = [c for c in MEASURE_COLS if c not in PCT_COLS]
    
    # 스크롤 영역 지정을 위한 wrapper div 추가 및 테이블 마진 제거
    html = '<div style="width: 100% !important; max-width: 100% !important; max-height: 780px; overflow-y: auto; overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 12px; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06); display: block !important;"><table class="premium-table" style="margin:0; border:none;">'
    
    # 헤더 생성
    visible_cols = [col for col in df.columns if col not in ("행구분", "자산대분류")]
    sticky_cols = {
        "구분": {"left": "0px", "width": "60px"},
        "자산_대": {"left": "60px", "width": "85px"},
        "자산_중": {"left": "145px", "width": "110px"},
        "자산_소": {"left": "255px", "width": "125px"}
    }
    
    # colgroup 추가
    html += '<colgroup>'
    for col in visible_cols:
        if col in sticky_cols:
            w = sticky_cols[col]["width"]
            html += f'<col style="width: {w}; min-width: {w}; max-width: {w};">'
        else:
            html += '<col style="width: 120px; min-width: 120px; max-width: 120px;">'
    html += '</colgroup><thead><tr>'
    
    for idx, col in enumerate(visible_cols):
        if col in sticky_cols:
            left_val = sticky_cols[col]["left"]
            width_val = sticky_cols[col]["width"]
            shadow = "4px 0 8px rgba(0,0,0,0.12)" if col == "자산_소" else "2px 0 4px rgba(0,0,0,0.06)"
            html += (
                f'<th class="sticky-col-{idx}" style="position: sticky !important; left: {left_val} !important; '
                f'top: 0 !important; z-index: 15 !important; '
                f'min-width: {width_val} !important; max-width: {width_val} !important; '
                f'width: {width_val} !important; background-color: #004B93 !important; '
                f'border-right: 1px solid rgba(255, 255, 255, 0.15) !important; '
                f'box-shadow: inset 0 -2px 0 #EC6608, {shadow}; '
                f'white-space: normal !important; word-break: break-all !important; '
                f'line-height: 1.2 !important; padding: 6px 4px !important;">{col}</th>'
            )
        else:
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
                    cell_style = f"color: {POS} !important; font-weight: 600;"
                elif val < 0:
                    cell_style = f"color: {NEG} !important; font-weight: 600;"
            
            # 자산 소카테고리까지 고정(Sticky Left) 적용
            if col in sticky_cols:
                idx = visible_cols.index(col)
                class_attr = f' class="sticky-col-{idx}"'
                left_val = sticky_cols[col]["left"]
                width_val = sticky_cols[col]["width"]
                shadow = "4px 0 8px rgba(0,0,0,0.06)" if col == "자산_소" else "2px 0 4px rgba(0,0,0,0.03)"
                
                # 행구분에 따른 명확한 고정 셀 배경색 매핑 (상속 버그 방지 및 강제 불투명 채우기)
                row_type = row.get("행구분", "")
                if row_type == "총합계":
                    bg_col = "#FDF2E9"
                elif row_type == "대분류합계":
                    bg_col = "#EBF3FC"
                elif row_type in ("중분류소계", "소계"):
                    bg_col = "#F4EFE6"
                else:
                    bg_col = "#FFFFFF"
                
                sticky_style = (
                    f"position: sticky !important; left: {left_val} !important; "
                    f"z-index: 5 !important; background-color: {bg_col} !important; "
                    f"min-width: {width_val} !important; max-width: {width_val} !important; "
                    f"width: {width_val} !important; box-shadow: {shadow}; "
                    f"border-right: 1px solid #E2E8F0 !important; "
                    f"white-space: normal !important; word-break: break-all !important; "
                    f"line-height: 1.25 !important; padding: 6px 8px !important;"
                )
                cell_style += f" {sticky_style}"
            else:
                class_attr = ''
            
            html += f'<td{rowspan_attr}{class_attr} style="{align_style} {cell_style}">{val_str}</td>'
    
    # JavaScript column resizer injection via hidden image onerror hack
    js_code = """<img src="x" onerror="(function(){const tables=document.querySelectorAll('table.premium-table');tables.forEach(table=>{if(table.dataset.resizable)return;table.dataset.resizable='true';table.style.position='relative';const ths=table.querySelectorAll('th');const cols=table.querySelectorAll('col');ths.forEach((th,i)=>{if(window.getComputedStyle(th).position==='static'){th.style.position='relative';}const resizer=document.createElement('div');resizer.style.position='absolute';resizer.style.top='0';resizer.style.right='0';resizer.style.width='6px';resizer.style.height='100%';resizer.style.cursor='col-resize';resizer.style.userSelect='none';resizer.style.zIndex='30';resizer.style.backgroundColor='transparent';resizer.addEventListener('mouseover',()=>{resizer.style.backgroundColor='#EC6608';resizer.style.width='4px';});resizer.addEventListener('mouseout',()=>{resizer.style.backgroundColor='transparent';resizer.style.width='6px';});th.appendChild(resizer);resizer.addEventListener('mousedown',e=>{const startX=e.clientX;const startWidths=[];for(let idx=0;idx<4;idx++){startWidths.push(ths[idx]?ths[idx].offsetWidth:0);}document.body.style.cursor='col-resize';document.body.style.userSelect='none';const onMouseMove=ev=>{const diff=ev.clientX-startX;const newWidth=Math.max(30,startWidths[i]+diff);if(cols[i]){cols[i].style.width=newWidth+'px';cols[i].style.minWidth=newWidth+'px';cols[i].style.maxWidth=newWidth+'px';}th.style.width=newWidth+'px';th.style.minWidth=newWidth+'px';th.style.maxWidth=newWidth+'px';if(i<4){const cells=table.querySelectorAll('.sticky-col-'+i);cells.forEach(cell=>{cell.style.width=newWidth+'px';cell.style.minWidth=newWidth+'px';cell.style.maxWidth=newWidth+'px'});}let currentLeft=0;for(let idx=0;idx<4;idx++){if(idx<ths.length){const w=(idx===i)?newWidth:startWidths[idx];const stickyTh=ths[idx];stickyTh.style.left=currentLeft+'px';const cells=table.querySelectorAll('.sticky-col-'+idx);cells.forEach(cell=>{cell.style.left=currentLeft+'px'});currentLeft+=w;}}};const onMouseUp=()=>{document.body.style.cursor='';document.body.style.userSelect='';document.removeEventListener('mousemove',onMouseMove);document.removeEventListener('mouseup',onMouseUp);};document.addEventListener('mousemove',onMouseMove);document.addEventListener('mouseup',onMouseUp);e.preventDefault();});});});})()" style="display:none;">"""
    html += '</tbody></table>'
    html += js_code
    html += '</div>'
    return html


def comparison_table_to_html(df, m_prev, m_curr):
    """전월대비 비교 표를 프리미엄 HTML 테이블로 렌더링."""
    html = '<div style="border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.02);"><table class="premium-table" style="margin:0; width:100%;"><thead><tr>'
    
    headers = ["자산대분류", f"{m_prev} (억원)", f"{m_curr} (억원)", "전월대비 증감", "증감률"]
    for h in headers:
        html += f'<th>{h}</th>'
    html += '</tr></thead><tbody>'
    
    for i, (idx, row) in enumerate(df.iterrows()):
        is_total = row["자산대분류"] == "합계"
        bg_color = "#FFF0E0" if is_total else ("#FAF6F0" if i % 2 == 1 else "#FFFFFF")
        font_weight = "bold" if is_total else "normal"
        color_style = "color: #004B93; font-weight: 700;" if is_total else "color: #334155;"
        
        html += f'<tr style="background-color: {bg_color} !important; {color_style}">'
        
        # 자산대분류
        html += f'<td style="text-align: left; font-weight: {font_weight};">{row["자산대분류"]}</td>'
        
        # m_prev
        v_prev = row[m_prev]
        val_prev = f"{v_prev:,.1f}" if pd.notna(v_prev) else "-"
        html += f'<td style="text-align: right; font-weight: {font_weight};">{val_prev}</td>'
        
        # m_curr
        v_curr = row[m_curr]
        val_curr = f"{v_curr:,.1f}" if pd.notna(v_curr) else "-"
        html += f'<td style="text-align: right; font-weight: {font_weight};">{val_curr}</td>'
        
        # 전월대비 증감
        v_diff = row["전월대비 증감"]
        if pd.isna(v_diff):
            val_diff = "-"
            diff_style = ""
        else:
            val_diff = f"{v_diff:+,.1f}"
            diff_style = f"color: {POS} !important; font-weight: 600;" if v_diff > 0 else (f"color: {NEG} !important; font-weight: 600;" if v_diff < 0 else "")
            
        html += f'<td style="text-align: right; {diff_style}">{val_diff}</td>'
        
        # 증감률
        v_pct = row["증감률(%)"]
        if pd.isna(v_pct) or str(v_pct).strip().lower() in ('nan', 'none', '<na>', ''):
            val_pct = "-"
            pct_style = ""
        else:
            val_pct = f"{v_pct:+.1f}%"
            pct_style = f"color: {POS} !important; font-weight: 600;" if v_pct > 0 else (f"color: {NEG} !important; font-weight: 600;" if v_pct < 0 else "")
            
        html += f'<td style="text-align: right; {pct_style}">{val_pct}</td>'
        html += '</tr>'
        
    html += '</tbody></table></div>'
    return html


# ===================================================================
# 3. 탭 구성
# ===================================================================
tab1, tab2, tab3 = st.tabs(["📄 원본 일보", "📊 요약 대시보드", "📈 월별 추이 및 비교"])

# ---- 탭 1: 원본 일보 그대로 (세로 셀 병합 HTML 렌더링 + 다차원 계층 필터) ----
with tab1:
    # 보안 안내 문구 추가
    st.markdown(
        """
        <div style="background-color: #FFF5EB; border: 1px solid #FDE8D0; border-left: 5px solid #004B93; border-radius: 8px; padding: 12px 18px; margin-bottom: 24px; color: #C2410C; font-weight: 600; font-size: 0.88rem; display: flex; align-items: center; gap: 8px;">
            <span>🔒 본 화면은 자산운용본부의 인가된 인원만 접속이 가능합니다.</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    c1, c2, c3, c4 = st.columns([1, 1.2, 1.3, 1.5])
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
            
    with c4:
        st.write("")
        import streamlit.components.v1 as components
        components.html(
            """
            <button onclick="window.parent.print()" style="
                background-color: #004B93; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 8px; 
                font-weight: 700; 
                cursor: pointer;
                width: 100%;
                height: 42px;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0, 75, 147, 0.15);
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
            " onmouseover="this.style.backgroundColor='#EC6608'" onmouseout="this.style.backgroundColor='#004B93'">
                📄 PDF 출력 / 인쇄
            </button>
            """,
            height=45
        )

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
        trend_metrics = ["당기손익_당월", "BS자본조정_당월"]
        metric = st.selectbox(
            "비교 지표", 
            trend_metrics,
            index=0,
            format_func=lambda x: "당기손익 (당월)" if x == "당기손익_당월" else "BS자본조정 (당월)"
        )

        # 자산대분류 × 기준일 피벗
        series = {d.strftime("%Y-%m-%d"): agg_by_asset(reports[d], metric) for d in dates}
        pivot = pd.DataFrame(series).sort_index()
        cols = list(pivot.columns)

        c1, c2 = st.columns(2)
        m_curr = c1.selectbox("기준일", cols, index=len(cols) - 1, key="compare_base_date")
        m_prev = c2.selectbox("비교일", cols, index=len(cols) - 2, key="compare_target_date")

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

        # 3개월 월별 손익추이 값 연산
        idx_curr = cols.index(m_curr)
        
        # 당월 값
        val_curr = pivot[m_curr].sum()
        
        # 직전월 값
        if idx_curr >= 1:
            m_prev_val = cols[idx_curr - 1]
            val_prev = pivot[m_prev_val].sum()
            label_prev = f"직전월 ({m_prev_val})"
            val_prev_str = f"{val_prev:,.1f}"
        else:
            val_prev_str = "-"
            label_prev = "직전월 (데이터 없음)"
            
        # 전전월 값
        if idx_curr >= 2:
            m_prev2_val = cols[idx_curr - 2]
            val_prev2 = pivot[m_prev2_val].sum()
            label_prev2 = f"전전월 ({m_prev2_val})"
            val_prev2_str = f"{val_prev2:,.1f}"
        else:
            val_prev2_str = "-"
            label_prev2 = "전전월 (데이터 없음)"

        # 프리미엄 HTML 메트릭 카드 배치 (억원 표기) - 증감/증감률 삭제 및 3개월 단위 월별 추이로 대체
        kk1, kk2, kk3 = st.columns(3)
        with kk1:
            premium_metric_card(f"당월 ({m_curr}, 억원)", f"{val_curr:,.1f}")
        with kk2:
            premium_metric_card(f"{label_prev} (억원)", val_prev_str)
        with kk3:
            premium_metric_card(f"{label_prev2} (억원)", val_prev2_str)

        st.divider()
        st.subheader(f"자산구분 대분류별 {metric} — {m_prev} → {m_curr} (단위: 억원)")

        # Append Total Row for display
        tbl = cmp.reset_index().rename(columns={"index": "자산대분류"})
        total_row = {
            "자산대분류": "합계",
            m_prev: cmp[m_prev].sum(),
            m_curr: cmp[m_curr].sum(),
            "전월대비 증감": cmp["전월대비 증감"].sum(),
            "증감률(%)": (cmp["전월대비 증감"].sum() / cmp[m_prev].sum() * 100) if cmp[m_prev].sum() != 0 else 0.0
        }
        tbl = pd.concat([tbl, pd.DataFrame([total_row])], ignore_index=True)
        
        st.markdown(comparison_table_to_html(tbl, m_prev, m_curr), unsafe_allow_html=True)

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
            # 누적 세로 막대형 BAR 차트로 변경 및 마우스 오버(Hover) 시 세부 데이터 연합 노출
            fig = px.bar(trend, x="기준일", y=metric, color="자산대분류", 
                         color_discrete_sequence=PREMIUM_COLORS, barmode="stack")
            fig.update_layout(
                height=420, 
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(font=dict(size=10)),
                hovermode="x unified"
            )
            fig.update_traces(
                hovertemplate="<b>%{y:,.1f} 억원</b>"
            )
            apply_premium_chart_theme(fig)
            st.plotly_chart(fig, width='stretch')
            st.markdown('</div>', unsafe_allow_html=True)

st.caption("ⓘ 화면과 데이터가 분리되어 있어, 같은 양식의 일보를 올리면 자동으로 갱신·비교됩니다.")
