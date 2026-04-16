"""
app.py — AX Simulator 메인 진입점
Section 선택 라우터 + 탭 구조

실행: streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AX Simulator — AI Layoff Trap",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────
# 사이드바: 섹션 선택 + 세션 관리
# ─────────────────────────────────────────────────────────

with st.sidebar:
    st.title("AX Simulator")
    st.caption("AI Layoff Trap × 기업·시장 분석 도구")
    st.caption("Hemenway Falk & Tsoukalas (2026)")

    st.divider()

    section = st.radio(
        "섹션 선택",
        options=["Section 1 — 기업 의사결정", "Section 2 — 시장/정책 분석"],
        index=0,
        help=(
            "Section 1: CFO·전략기획팀용 — 부서별 ROI, 기업 파급효과\n"
            "Section 2: 정책연구자용 — 수요 파괴, 외부효과, 피구세"
        ),
    )

    st.divider()

    # 세션 관리 패널
    try:
        from shared.data.session_store import SessionStore, render_session_panel
        store = SessionStore()
        render_session_panel(store)
    except Exception:
        st.caption("세션 관리 로드 실패")

# ─────────────────────────────────────────────────────────
# Section 1 — 기업 의사결정 도구
# ─────────────────────────────────────────────────────────

if section == "Section 1 — 기업 의사결정":
    st.header("Section 1 — 기업 의사결정 도구")
    st.caption("CFO · 전략기획팀 · AX 컨설턴트 대상")

    tabs = st.tabs([
        "S1-0  컨텍스트",
        "S1-1  기업 프로파일",
        "S1-2  AI 준비도",
        "S1-3  내부 ROI + 기업 파급효과",
        "S1-4  전략 시나리오",
    ])

    with tabs[0]:
        try:
            from section1.ui.s1_tab0_context import render
            render()
        except Exception as e:
            st.info("🔧 S1-0 컨텍스트 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[1]:
        try:
            from section1.ui.s1_tab1_profile import render
            render()
        except Exception as e:
            st.info("🔧 S1-1 기업 프로파일 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[2]:
        try:
            from section1.ui.s1_tab2_readiness import render
            render()
        except Exception as e:
            st.info("🔧 S1-2 AI 준비도 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[3]:
        try:
            from section1.ui.s1_tab3_roi_impact import render
            render()
        except Exception as e:
            st.info("🔧 S1-3 내부 ROI + 기업 파급효과 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[4]:
        try:
            from section1.ui.s1_tab4_strategy import render
            render()
        except Exception as e:
            st.info("🔧 S1-4 전략 시나리오 탭 구현 중입니다.")
            st.caption(str(e))

# ─────────────────────────────────────────────────────────
# Section 2 — 시장/정책 분석 도구
# ─────────────────────────────────────────────────────────

else:
    st.header("Section 2 — 시장/정책 분석 도구")
    st.caption("국가기관 · 정책연구자 · 경제학자 대상")

    st.info(
        "Section 2는 Section 1 없이도 독립 실행 가능합니다. "
        "정책 연구자는 파라미터를 직접 입력하세요.",
        icon="ℹ️",
    )

    tabs = st.tabs([
        "S2-1  시장 외부효과",
        "S2-2  국가 경제 파급 (동적)",
        "S2-3  정책 처방",
        "S2-4  통합 리포트",
    ])

    with tabs[0]:
        try:
            from section2.ui.s2_tab1_externality import render
            render()
        except Exception as e:
            st.info("🔧 S2-1 시장 외부효과 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[1]:
        try:
            from section2.ui.s2_tab2_dynamic import render
            render()
        except Exception as e:
            st.info("🔧 S2-2 동적 모델 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[2]:
        try:
            from section2.ui.s2_tab3_policy import render
            render()
        except Exception as e:
            st.info("🔧 S2-3 정책 처방 탭 구현 중입니다.")
            st.caption(str(e))

    with tabs[3]:
        try:
            from section2.ui.s2_tab4_report import render
            render()
        except Exception as e:
            st.info("🔧 S2-4 통합 리포트 탭 구현 중입니다.")
            st.caption(str(e))
