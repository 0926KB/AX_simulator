"""section1/ui/s1_tab1_profile.py — 기업 프로파일"""
import streamlit as st
from shared.data.presets import (
    DEPARTMENT_TYPES, DEPARTMENT_PRESETS, INDUSTRY_LABOR_RATIO,
    estimate_capex, estimate_opex, compute_k, READINESS_DIMENSIONS,
)


def render():
    st.subheader("S1-1 기업 프로파일")
    ctx = st.session_state.get("context", {})
    currency = ctx.get("currency", "억원")

    # ── 1-A 재무 현황 ─────────────────────────────────────
    st.markdown("#### 재무 현황")
    industry = ctx.get("industry", "IT소프트웨어")
    labor_ratio = INDUSTRY_LABOR_RATIO.get(industry, {}).get("labor_to_revenue", 0.28)

    col1, col2, col3 = st.columns(3)
    with col1:
        revenue = st.number_input(f"연간 매출 ({currency})", min_value=0.0, value=100.0, step=1.0)
        op_margin = st.slider("영업이익률 (%)", 0.0, 50.0, 10.0, 0.5) / 100
    with col2:
        default_labor = revenue * labor_ratio
        total_labor = st.number_input(
            f"총 인건비 ({currency})", min_value=0.0,
            value=float(round(default_labor, 1)), step=1.0,
            help=f"미입력 시 매출 × 산업 기준({labor_ratio*100:.0f}%) 자동 계산",
        )
        ai_budget = st.number_input(f"AI 투자 예산 상한 ({currency})", min_value=0.0, value=10.0, step=0.5)
    with col3:
        N = st.number_input("시장 내 경쟁사 수 N", min_value=1, value=7, step=1)
        A = st.number_input(f"자율수요 A ({currency})", min_value=0.0, value=float(round(revenue * 0.1, 1)), step=1.0)

    col4, col5, col6 = st.columns(3)
    with col4:
        biz_type = st.selectbox("기업 유형", ["B2C", "B2B", "혼합"])
    with col5:
        is_listed = st.toggle("상장 기업")
        ticker = st.text_input("종목 코드 (선택)", placeholder="예: 005930.KS") if is_listed else ""
    with col6:
        avg_tenure = st.number_input("평균 근속년수 (년)", min_value=0.5, value=5.0, step=0.5)

    st.session_state["company_profile"] = {
        "annual_revenue": revenue, "op_margin": op_margin,
        "total_labor": total_labor, "ai_budget": ai_budget,
        "N": N, "A": A, "biz_type": biz_type,
        "is_listed": is_listed, "ticker": ticker,
        "avg_tenure_years": avg_tenure,
        "currency": currency,
    }

    # ── 1-B 부서 구성 ─────────────────────────────────────
    st.markdown("#### 부서 구성")
    if "departments" not in st.session_state:
        st.session_state["departments"] = []

    with st.expander("부서 추가", expanded=len(st.session_state["departments"]) == 0):
        d_col1, d_col2, d_col3 = st.columns(3)
        with d_col1:
            dept_name = st.text_input("부서명", placeholder="예: CS팀")
            dept_type = st.selectbox("부서 유형", DEPARTMENT_TYPES)
        with d_col2:
            headcount = st.number_input("헤드카운트 (명)", min_value=1, value=20, step=1)
            preset    = DEPARTMENT_PRESETS[dept_type]
            avg_mult  = preset["avg_salary_multiplier"]
            avg_sal_default = (total_labor / max(headcount, 1)) if total_labor > 0 else 0.5
            avg_salary = st.number_input(
                f"평균 연봉 ({currency})", min_value=0.01,
                value=float(round(avg_sal_default, 2)), step=0.01,
            )
        with d_col3:
            frac_lo, frac_hi = preset["auto_fraction_range"]
            alpha = st.slider(
                "자동화 가능 비율 (automatable fraction)",
                0.0, 1.0, float(round((frac_lo + frac_hi) / 2, 2)), 0.01,
                help=f"프리셋 범위: {frac_lo:.0%}~{frac_hi:.0%} ({preset['source']})",
            )
            description = st.text_area("업무 설명 (LLM 자동 파싱)", height=80, placeholder="주요 업무를 자유롭게 입력하세요...")

        if st.button("부서 추가", use_container_width=True):
            if dept_name:
                # 준비도 미입력 시 기본 3점으로 k 계산
                default_scores = {dim: 3.0 for dim in READINESS_DIMENSIONS}
                k = compute_k(default_scores, dept_type)
                capex_info = estimate_capex(
                    {"headcount": headcount, "type": dept_type}, 3.0
                )
                opex_info = estimate_opex(
                    {"headcount": headcount, "type": dept_type,
                     "capex_total": capex_info["total_capex"], "avg_salary": avg_salary},
                    alpha,
                )
                dept = {
                    "name": dept_name, "type": dept_type,
                    "headcount": headcount, "avg_salary": avg_salary,
                    "alpha": alpha, "description": description,
                    "k": k,
                    "capex_total": capex_info["total_capex"],
                    "annual_opex": opex_info["total_opex"],
                    "readiness_scores": default_scores,
                }
                st.session_state["departments"].append(dept)
                st.success(f"'{dept_name}' 추가됨")
                st.rerun()
            else:
                st.error("부서명을 입력하세요.")

    # 부서 목록 표시
    depts = st.session_state.get("departments", [])
    if depts:
        st.markdown(f"**등록된 부서 ({len(depts)}개)**")
        import pandas as pd
        df = pd.DataFrame([{
            "부서명": d["name"], "유형": d["type"],
            "인원": d["headcount"], f"평균연봉({currency})": d["avg_salary"],
            "자동화율": f"{d['alpha']:.0%}", "k(마찰)": d["k"],
        } for d in depts])
        st.dataframe(df, use_container_width=True, hide_index=True)

        total_headcount = sum(d["headcount"] for d in depts)
        st.session_state["company_profile"]["total_headcount"] = total_headcount
