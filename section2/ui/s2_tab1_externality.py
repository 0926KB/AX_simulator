"""section2/ui/s2_tab1_externality.py — 외부효과 분석 (Nash vs 협력 최적)"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from section2.core.paper_model import ModelParams, compute_externality, scenario_comparison, check_externality_alerts


def render():
    st.subheader("S2-1 외부효과 분석")
    st.caption(
        "Hemenway Falk & Tsoukalas (2026) — Nash 균형 vs 협력 최적 자동화율 격차 시각화"
    )

    ctx     = st.session_state.get("context", {})
    profile = st.session_state.get("company_profile", {})
    depts   = st.session_state.get("departments", [])

    currency = profile.get("currency", "억원") if profile else "억원"

    # ── 파라미터 입력 ─────────────────────────────────────
    st.markdown("#### 시장 파라미터")
    col1, col2, col3 = st.columns(3)
    with col1:
        lam = st.number_input("소비성향 λ", 0.0, 1.0,
                              value=float(ctx.get("lambda_", 0.48)), step=0.01)
        eta = st.number_input("소득 대체율 η", 0.0, 1.0,
                              value=float(ctx.get("eta", 0.35)), step=0.01)
    with col2:
        w   = st.number_input(f"태스크당 임금 w ({currency})", 0.01,
                              value=0.5, step=0.01)
        c   = st.number_input(f"태스크당 AI 비용 c ({currency})", 0.001,
                              value=0.1, step=0.01)
    with col3:
        k   = st.number_input("마찰 계수 k", 0.1, 5.0,
                              value=float(round(
                                  sum(d["k"] for d in depts) / len(depts), 2
                              )) if depts else 1.0, step=0.05)
        N   = st.number_input("시장 경쟁사 수 N", 1,
                              value=int(profile.get("N", 7)) if profile else 7, step=1)

    col4, col5 = st.columns(2)
    with col4:
        L   = st.number_input("총 노동자 수 L", 1.0,
                              value=float(sum(d["headcount"] for d in depts)) if depts else 100.0,
                              step=1.0)
    with col5:
        A   = st.number_input(f"자율 수요 A ({currency})", 0.0,
                              value=float(profile.get("A", 10.0)) if profile else 10.0,
                              step=1.0)

    params = ModelParams(lambda_=lam, eta=eta, w=w, c=c, k=k, N=N, A=A, L=L)

    # ── 결과 계산 ─────────────────────────────────────────
    ext = compute_externality(0.0, params)
    alerts = check_externality_alerts(ext, params)

    st.divider()
    st.markdown("#### 외부효과 핵심 지표")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ℓ (수요 손실/태스크)", f"{ext.ell:.4f}")
    c2.metric("s (절약액/태스크)", f"{ext.s:.4f}")
    c3.metric("N* (임계 경쟁사 수)", f"{ext.N_star:.2f}")
    c4.metric("αNE (Nash 균형)", f"{ext.alpha_NE:.3f}")
    c5.metric("αCO (협력 최적)", f"{ext.alpha_CO:.3f}")

    c6, c7, c8 = st.columns(3)
    c6.metric("과잉 자동화 격차 wedge", f"{ext.wedge:.3f}",
              delta=f"{'위험' if ext.wedge > 0.2 else '안전'}", delta_color="inverse" if ext.wedge > 0.2 else "off")
    c7.metric(f"최적 피구세 τ* ({currency})", f"{ext.tau_star:.5f}")
    c8.metric("수요 파괴율", f"{ext.demand_loss_pct:.2f}%",
              delta=f"{'⚠ 위험' if ext.demand_loss_pct > 5 else '정상'}", delta_color="inverse" if ext.demand_loss_pct > 5 else "off")

    # 경보
    for alert in alerts:
        level = alert["level"]
        if level == "DANGER":
            st.error(f"🚨 {alert['message']} — {alert['detail']}")
        elif level == "WARNING":
            st.warning(f"⚠️ {alert['message']} — {alert['detail']}")
        else:
            st.info(f"ℹ️ {alert['message']} — {alert['detail']}")

    # ── 시나리오 A vs B ───────────────────────────────────
    st.markdown("#### 시나리오 비교: 자사 단독 vs 업계 동시 도입")
    company_alpha_default = float(
        sum(d["alpha"] * d["headcount"] for d in depts) / max(sum(d["headcount"] for d in depts), 1)
    ) if depts else 0.5

    company_alpha = st.slider("자사 자동화율 ᾱ (company)", 0.0, 1.0,
                               float(round(company_alpha_default, 2)), 0.01)

    sc = scenario_comparison(company_alpha, params)
    sc_cols = st.columns(4)
    sc_cols[0].metric("시나리오A — 수요 손실 (최소)", f"{sc['scenario_A'].demand_loss:.3f}")
    sc_cols[1].metric("시나리오B — 수요 손실 (최대)", f"{sc['scenario_B'].demand_loss:.3f}")
    sc_cols[2].metric(f"자사 매출 영향 (낙관, {currency})", f"{sc['revenue_impact_optimistic']:+.4f}")
    sc_cols[3].metric(f"자사 매출 영향 (비관, {currency})", f"{sc['revenue_impact_pessimistic']:+.4f}")

    # ── αNE / αCO vs N 차트 ───────────────────────────────
    st.markdown("#### 경쟁사 수(N)에 따른 자동화율 변화")
    n_range = list(range(1, 31))
    alpha_NE_vals, alpha_CO_vals, wedge_vals = [], [], []
    for n_val in n_range:
        p_tmp = ModelParams(lambda_=lam, eta=eta, w=w, c=c, k=k, N=n_val, A=A, L=L)
        r_tmp = compute_externality(0.0, p_tmp)
        alpha_NE_vals.append(r_tmp.alpha_NE)
        alpha_CO_vals.append(r_tmp.alpha_CO)
        wedge_vals.append(r_tmp.wedge)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=n_range, y=alpha_NE_vals, mode="lines",
                             name="αNE (Nash 균형)", line=dict(color="#e74c3c")))
    fig.add_trace(go.Scatter(x=n_range, y=alpha_CO_vals, mode="lines",
                             name="αCO (협력 최적)", line=dict(color="#2ecc71", dash="dash")))
    fig.add_trace(go.Scatter(x=n_range, y=wedge_vals, mode="lines",
                             name="wedge (격차)", line=dict(color="#9b59b6", dash="dot")))
    fig.add_vline(x=ext.N_star, line_dash="dot",
                  annotation_text=f"N*={ext.N_star:.1f}", line_color="orange")
    fig.add_vline(x=N, line_dash="solid",
                  annotation_text=f"현재 N={N}", line_color="#3498db")
    fig.update_layout(
        xaxis_title="시장 경쟁사 수 N",
        yaxis_title="자동화율",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 수요 함수 D(ᾱ) 차트 ──────────────────────────────
    st.markdown("#### 수요 함수 D(ᾱ) — 시장 평균 자동화율에 따른 총수요")
    alpha_range = np.linspace(0, 1, 50)
    D_vals = []
    for ab in alpha_range:
        D_val = A + lam * w * L * N * (1.0 - (1.0 - eta) * ab)
        D_vals.append(D_val)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=list(alpha_range), y=D_vals, mode="lines",
                              name="D(ᾱ)", line=dict(color="#3498db")))
    fig2.add_vline(x=ext.alpha_NE, line_dash="dot",
                   annotation_text=f"αNE={ext.alpha_NE:.3f}", line_color="#e74c3c")
    fig2.add_vline(x=ext.alpha_CO, line_dash="dot",
                   annotation_text=f"αCO={ext.alpha_CO:.3f}", line_color="#2ecc71")
    fig2.update_layout(
        xaxis_title="시장 평균 자동화율 ᾱ",
        yaxis_title=f"총수요 D ({currency})",
    )
    st.plotly_chart(fig2, use_container_width=True)

    # LLM 버튼
    if st.button("외부효과 분석 해석 (LLM)", use_container_width=True):
        try:
            from shared.llm.client import call_llm
            payload = {
                "ext": ext.__dict__,
                "params": {"lam": lam, "eta": eta, "w": w, "c": c, "k": k, "N": N, "L": L},
                "alerts": alerts,
                "scenario": sc,
            }
            st.markdown(call_llm("externality_analysis", payload))
        except Exception as e:
            st.info(f"LLM 준비 중입니다. ({e})")
