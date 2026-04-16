"""section1/ui/s1_tab4_strategy.py — 기업 전략 시나리오 (피구세 기업 영향)"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from section2.core.paper_model import ModelParams, compute_externality, compute_pigouvian_tax


def render():
    st.subheader("S1-4 전략 시나리오")
    st.caption("피구세 부과 시 기업 ROI 변화 및 단계적 도입 전략")

    ctx     = st.session_state.get("context", {})
    profile = st.session_state.get("company_profile", {})
    depts   = st.session_state.get("departments", [])

    if not ctx or not profile or not depts:
        st.warning("S1-0 ~ S1-2 먼저 완료해주세요.")
        return

    currency = profile.get("currency", "억원")
    N        = profile.get("N", 7)
    revenue  = profile.get("annual_revenue", 100.0)
    A        = profile.get("A", revenue * 0.1)

    st.markdown("#### 피구세 시나리오")
    st.caption("피구세 τ*가 부과될 경우 기업의 자동화율 및 ROI 변화를 보여줍니다.")

    # 파라미터 설정
    col1, col2, col3 = st.columns(3)
    with col1:
        w = st.number_input(f"태스크당 평균 임금 w ({currency})", 0.01, value=0.5, step=0.01)
        c = st.number_input(f"태스크당 AI 비용 c ({currency})", 0.001, value=0.1, step=0.01)
    with col2:
        k_avg = st.number_input("평균 마찰 계수 k", 0.1, 3.0,
                                value=float(round(sum(d["k"] for d in depts)/len(depts), 2)), step=0.05)
        L = st.number_input("총 태스크 수 L (노동자 수)", 1.0,
                             value=float(sum(d["headcount"] for d in depts)), step=1.0)
    with col3:
        eta  = ctx.get("eta", 0.35)
        lam  = ctx.get("lambda_", 0.48)
        st.metric("η (소득 대체율)", f"{eta:.2f}")
        st.metric("λ (소비성향)", f"{lam:.3f}")

    params = ModelParams(lambda_=lam, eta=eta, w=w, c=c, k=k_avg, N=N, A=A, L=L)
    ext    = compute_externality(0.0, params)

    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Nash 균형 자동화율 αNE", f"{ext.alpha_NE:.3f}")
    col2.metric("협력 최적 자동화율 αCO", f"{ext.alpha_CO:.3f}")
    col3.metric("과잉 자동화 격차 wedge", f"{ext.wedge:.3f}")
    col4.metric(f"최적 피구세 τ* ({currency})", f"{ext.tau_star:.4f}")

    # 피구세 슬라이더
    tau = st.slider(
        f"적용 피구세 τ ({currency}/태스크)",
        0.0, float(max(ext.tau_star * 2, 0.01)),
        float(round(ext.tau_star, 4)), float(round(ext.tau_star / 20, 5)),
        format="%.4f",
    )

    total_tasks = sum(d["headcount"] * d["alpha"] for d in depts)
    tax_result  = compute_pigouvian_tax(tau, params, total_tasks)

    col1, col2, col3 = st.columns(3)
    col1.metric("세금 부과 후 αNE", f"{tax_result['alpha_NE_taxed']:.3f}",
                delta=f"{tax_result['alpha_NE_taxed'] - ext.alpha_NE:+.3f}")
    col2.metric("격차 해소율", f"{tax_result['gap_closed_pct']:.1f}%")
    col3.metric(f"연간 세금 부담 ({currency})", f"{tax_result['tax_burden_annual']:.3f}")

    # 세율별 영향 차트
    st.markdown("#### 피구세율별 자동화율 변화")
    tau_range = [i * ext.tau_star / 10 for i in range(21)]
    chart_data = []
    for t in tau_range:
        r = compute_pigouvian_tax(t, params, total_tasks)
        chart_data.append({"τ (피구세)": round(t, 4),
                           "αNE (세후)": r["alpha_NE_taxed"],
                           "αCO (협력 최적)": ext.alpha_CO})
    df = pd.DataFrame(chart_data)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["τ (피구세)"], y=df["αNE (세후)"],
                             mode="lines", name="αNE (세후)", line=dict(color="#e74c3c")))
    fig.add_trace(go.Scatter(x=df["τ (피구세)"], y=df["αCO (협력 최적)"],
                             mode="lines", name="αCO (협력 최적)",
                             line=dict(color="#2ecc71", dash="dash")))
    fig.add_vline(x=ext.tau_star, line_dash="dot", annotation_text=f"τ*={ext.tau_star:.4f}")
    fig.update_layout(xaxis_title=f"피구세 τ ({currency})", yaxis_title="자동화율",
                      legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("전략 시나리오 리포트 생성 (LLM)", use_container_width=True):
        try:
            from shared.llm.client import call_llm
            payload = {"ext": ext.__dict__, "tax_result": tax_result,
                       "tau_applied": tau, "tau_star": ext.tau_star}
            st.markdown(call_llm("strategy_report", payload))
        except Exception as e:
            st.info(f"LLM 준비 중입니다. ({e})")
