"""section1/ui/s1_tab3_roi_impact.py — 내부 ROI + 기업 파급효과 (Layer 1~3)"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from section1.core.roi_engine import compute_internal_roi, linear_projection, priority_matrix
from section1.core.impact_engine import compute_total_enterprise_impact


def render():
    st.subheader("S1-3 내부 ROI + 기업 파급효과")

    depts   = st.session_state.get("departments", [])
    profile = st.session_state.get("company_profile", {})
    ctx     = st.session_state.get("context", {})

    if not depts or not profile:
        st.warning("S1-1, S1-2에서 기업 프로파일과 부서 준비도를 먼저 입력하세요.")
        return

    currency = profile.get("currency", "억원")

    # ── φ (AI 생산성 배수) ─────────────────────────────────
    phi = st.slider("AI 생산성 배수 φ", 1.0, 2.0, 1.0, 0.05,
                    help="1.0 = 생산성 이득 없음, 1.3 = 남은 인원 30% 생산성 향상")

    if st.button("계산 실행", type="primary", use_container_width=True):
        results = []
        for dept in depts:
            roi = compute_internal_roi(dept, dept["alpha"], phi)
            results.append({"dept": dept["name"], "type": dept["type"],
                            "k": dept["k"], "roi": roi})

        st.session_state["roi_results"] = results

    results = st.session_state.get("roi_results", [])
    if not results:
        return

    # ── Layer 1: 부서별 ROI 테이블 ────────────────────────
    st.markdown("#### Layer 1 — 부서별 내부 ROI")
    df = pd.DataFrame([{
        "부서": r["dept"],
        f"인건비 절감/년({currency})": r["roi"]["labor_saving_annual"],
        f"NPV 5년({currency})":        r["roi"]["npv_5yr"],
        "ROI (%)":                     r["roi"]["roi_pct"],
        "회수기간 (년)":               r["roi"]["payback_years"],
        "해고 인원":                   r["roi"]["displaced_headcount"],
    } for r in results])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 우선순위 매트릭스
    pm = priority_matrix(results)
    if pm:
        st.markdown("#### 우선순위 매트릭스")
        fig = px.scatter(
            pd.DataFrame([{
                "부서": r["dept"],
                "준비도 (1-k)": round(1 - r["k"], 3),
                f"NPV ({currency})": r["roi"]["npv_5yr"],
                "사분면": r["quadrant"],
            } for r in pm]),
            x="준비도 (1-k)", y=f"NPV ({currency})",
            color="사분면", text="부서",
            color_discrete_map={
                "즉시 도입": "#2ecc71", "전략적 도입": "#3498db",
                "준비 후 도입": "#f39c12", "재고 필요": "#e74c3c",
            },
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)

    # ── Layer 2: P&L 프로젝션 ─────────────────────────────
    st.markdown("#### Layer 2 — P&L 프로젝션")
    col1, col2, col3 = st.columns(3)
    with col1:
        y1_alpha = st.slider("1년차 자동화율", 0.0, 1.0, 0.3, 0.05)
    with col2:
        y3_alpha = st.slider("3년차 자동화율", 0.0, 1.0, 0.6, 0.05)
    with col3:
        y5_alpha = st.slider("5년차 자동화율", 0.0, 1.0, 0.8, 0.05)

    proj = linear_projection(
        {"revenue": profile["annual_revenue"], "op_margin": profile["op_margin"]},
        depts, {1: y1_alpha, 3: y3_alpha, 5: y5_alpha},
    )
    st.dataframe(proj.rename(columns={
        "year": "연도", "alpha": "자동화율",
        "labor_saving": f"인건비절감({currency})", "ai_opex": f"AI운영비({currency})",
        "net_cost_saving": f"순절감({currency})", "operating_profit": f"영업이익({currency})",
    }), use_container_width=True, hide_index=True)

    # ── Layer 3: 기업 파급효과 ────────────────────────────
    st.markdown("#### Layer 3 — 기업 파급효과 5채널")

    country   = ctx.get("country", "KR")
    industry  = ctx.get("industry", "IT소프트웨어")

    col1, col2 = st.columns(2)
    with col1:
        layoff_reason  = st.selectbox("해고 명분", ["proactive", "reactive"],
                                      format_func=lambda x: "비용 절감(proactive)" if x == "proactive" else "수요 감소 대응(reactive)")
        ai_branding    = st.toggle("'AI 선도' 프레이밍 공시")
    with col2:
        disclosure     = st.selectbox("공시 방식",
                                      ["ai_explicit", "restructuring", "silent"],
                                      format_func=lambda x: {
                                          "ai_explicit": "AI 선도 공시",
                                          "restructuring": "구조조정 공시",
                                          "silent": "조용한 감축"}[x])
        market_cap     = st.number_input(f"시가총액 ({currency})", 0.0, value=0.0,
                                         help="상장사만 입력. 0이면 채널 1 생략.") if profile.get("is_listed") else 0.0

    if st.button("기업 파급효과 계산", type="secondary", use_container_width=True):
        total_roi = {
            "total_saving_annual": sum(r["roi"]["total_saving_annual"] for r in results),
            "displaced_headcount": sum(r["roi"]["displaced_headcount"] for r in results),
        }
        profile_full = {
            **profile,
            "total_headcount": sum(d["headcount"] for d in depts),
            "disclosure_style": disclosure,
        }
        impact = compute_total_enterprise_impact(
            total_roi, profile_full, country, industry,
            {"layoff_reason": layoff_reason, "ai_branding": ai_branding},
            market_cap if market_cap > 0 else None,
        )
        st.session_state["impact_result"] = impact

    impact = st.session_state.get("impact_result")
    if impact:
        _render_impact_summary(impact, currency)
        if st.button("기업 파급효과 채널 분석 (LLM)", use_container_width=True):
            try:
                from shared.llm.client import call_llm
                st.markdown(call_llm("impact_analysis", impact))
            except Exception as e:
                st.info(f"LLM 준비 중입니다. ({e})")


def _render_impact_summary(impact: dict, currency: str):
    st.divider()
    cols = st.columns(5)
    labels = ["총 절감(gross)", "규제 비용", "Survivor 비용", "브랜드 영향", "순 절감(net)"]
    values = [
        impact["gross_saving_annual"], -impact["regulatory_cost"],
        -impact["survivor_cost"], impact["brand_impact"], impact["net_saving_annual"],
    ]
    for col, label, val in zip(cols, labels, values):
        col.metric(f"{label}\n({currency})", f"{val:+.2f}")

    if impact.get("stock_impact_estimate") is not None:
        st.metric(f"주가 영향 추정 ({currency})", f"{impact['stock_impact_estimate']:+.2f}",
                  help="시가총액 × CAR% (단기 3~5일 추정)")

    if impact.get("net_vs_gross_ratio"):
        ratio = impact["net_vs_gross_ratio"]
        color = "normal" if ratio >= 0.6 else "inverse"
        st.metric("순편익 / 직접절감 비율", f"{ratio:.0%}",
                  delta=f"{'숨겨진 비용 낮음' if ratio >= 0.7 else '숨겨진 비용 높음'}", delta_color=color)

    if impact.get("channel5_esg_alerts"):
        st.markdown("**채널 5 — ESG 체크리스트**")
        for alert in impact["channel5_esg_alerts"]:
            st.warning(f"⚠️ {alert['item']}")
