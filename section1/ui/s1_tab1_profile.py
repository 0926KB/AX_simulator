"""section1/ui/s1_tab1_profile.py — 기업 프로파일"""
import streamlit as st
from shared.data.presets import (
    DEPARTMENT_TYPES, DEPARTMENT_PRESETS, INDUSTRY_LABOR_RATIO,
    estimate_capex, estimate_opex, compute_k, READINESS_DIMENSIONS,
)


def _render_filing_loader(ctx: dict, currency: str):
    """공시 데이터 자동 불러오기 섹션 (DART/SEC EDGAR)"""
    country = ctx.get("country", "KR")
    if country not in ("KR", "US"):
        return  # KR/US만 지원

    st.markdown("#### 공시 데이터 자동 불러오기")
    st.caption(
        "DART(한국) / SEC EDGAR(미국) 공시에서 기업 레벨 재무 수치를 자동으로 가져옵니다."
    )

    col_q, col_y, col_btn = st.columns([3, 1, 1])
    with col_q:
        label = "회사명 또는 종목코드" if country == "KR" else "티커 (예: MSFT)"
        query = st.text_input(label, key="filing_query",
                              placeholder="삼성전자 / 005930" if country == "KR" else "MSFT / AAPL")
    with col_y:
        import datetime
        default_year = datetime.datetime.now().year - 1
        filing_year = st.number_input("사업연도", min_value=2019,
                                      max_value=default_year, value=default_year,
                                      step=1, key="filing_year")
    with col_btn:
        st.markdown("<div style='margin-top:28px'/>", unsafe_allow_html=True)
        load_btn = st.button("불러오기", use_container_width=True, key="filing_load_btn")

    if load_btn and query:
        with st.spinner("공시 데이터 조회 중..."):
            try:
                from shared.data.public_filing_client import get_company_filing_data
                filing = get_company_filing_data(query.strip(), country, int(filing_year))
                st.session_state["filing_data"] = filing
            except Exception as e:
                st.error(f"공시 조회 실패: {e}")
                st.session_state["filing_data"] = None

    filing = st.session_state.get("filing_data")
    if not filing:
        return

    # 결과 표시
    st.markdown(f"**{filing.get('company_name', query)}** — {filing.get('source')} {filing_year}")
    items = [
        ("매출",        "revenue",             currency),
        ("영업이익",    "operating_income",    currency),
        ("총 인건비",   "total_labor_cost",    currency),
        ("전체 임직원", "total_employees",     "명"),
        ("평균 연봉",   "avg_salary_annual",   currency),
        ("시가총액",    "market_cap",          currency),
    ]
    missing = set(filing.get("missing_fields", []))
    row_cols = st.columns(3)
    for i, (label, key, unit) in enumerate(items):
        val = filing.get(key)
        with row_cols[i % 3]:
            if val is not None:
                src = "공시 자동" if key not in ["market_cap"] else "yfinance 실시간"
                st.metric(f"{label} ({unit})", f"{val:,.2f}" if isinstance(val, float) else f"{val:,}",
                          help=f"출처: {src}")
            else:
                st.metric(f"{label} ({unit})", "⚠️ 데이터 없음")

    if filing.get("warnings"):
        with st.expander("⚠️ 경고 및 보완 내역"):
            for w in filing["warnings"]:
                st.caption(f"• {w}")

    # 적용 버튼
    if st.button("재무 수치 적용", use_container_width=True, key="filing_apply_btn"):
        updates = {}
        if filing.get("revenue") is not None:
            updates["__revenue"] = filing["revenue"]
        if filing.get("operating_income") is not None and filing.get("revenue", 0) > 0:
            updates["__op_margin"] = filing["operating_income"] / filing["revenue"]
        if filing.get("total_labor_cost") is not None:
            updates["__total_labor"] = filing["total_labor_cost"]
        st.session_state["filing_prefill"] = updates
        st.success("재무 수치가 아래 입력에 자동 적용됩니다. 필요 시 수동 수정하세요.")
        st.rerun()

    # 부서 추정
    industry = ctx.get("industry", "기타")
    if st.button("부서 구성 자동 추정 (업종 기준값 적용)", use_container_width=True, key="dept_est_btn"):
        try:
            from shared.data.dept_estimator import estimate_departments, validate_estimation
            depts_est = estimate_departments(filing, industry)
            warnings_val = validate_estimation(depts_est, filing)
            st.session_state["departments"] = depts_est
            if warnings_val:
                for w in warnings_val:
                    st.warning(w)
            st.success(f"{len(depts_est)}개 부서 추정 완료. 아래 부서 목록을 확인하세요. (모든 값은 추정치)")
            st.rerun()
        except Exception as e:
            st.error(f"부서 추정 실패: {e}")


def render():
    st.subheader("S1-1 기업 프로파일")
    ctx = st.session_state.get("context", {})
    currency = ctx.get("currency", "억원")

    # ── 1-Z 공시 자동 불러오기 ────────────────────────────
    _render_filing_loader(ctx, currency)
    st.divider()

    # ── 1-A 재무 현황 ─────────────────────────────────────
    st.markdown("#### 재무 현황")
    industry = ctx.get("industry", "IT소프트웨어")
    labor_ratio = INDUSTRY_LABOR_RATIO.get(industry, {}).get("labor_to_revenue", 0.28)

    # 공시 프리필 값 적용
    prefill = st.session_state.pop("filing_prefill", {})

    col1, col2, col3 = st.columns(3)
    with col1:
        rev_default = float(prefill.get("__revenue", 100.0))
        revenue = st.number_input(
            f"연간 매출 ({currency})" + (" *(공시 자동)*" if "__revenue" in prefill else ""),
            min_value=0.0, value=rev_default, step=1.0,
        )
        om_default = float(round(prefill.get("__op_margin", 0.10) * 100, 1))
        op_margin = st.slider(
            "영업이익률 (%)" + (" *(공시 자동)*" if "__op_margin" in prefill else ""),
            0.0, 50.0, om_default, 0.5,
        ) / 100
    with col2:
        labor_default = float(round(prefill.get("__total_labor", revenue * labor_ratio), 1))
        total_labor = st.number_input(
            f"총 인건비 ({currency})" + (" *(공시 자동)*" if "__total_labor" in prefill else ""),
            min_value=0.0,
            value=labor_default, step=1.0,
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
