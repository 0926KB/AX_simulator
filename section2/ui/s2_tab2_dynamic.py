"""section2/ui/s2_tab2_dynamic.py — η(t) 동적 경로 시뮬레이션"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from section2.core.paper_model import ModelParams
from section2.core.dynamic_model import compute_dynamic_paths, SCENARIOS


SCENARIO_LABELS = {
    "optimistic":  "낙관 (Acemoglu & Restrepo 2019)",
    "baseline":    "기준 (표준 S커브)",
    "pessimistic": "비관 (Jacobson et al. 1993)",
}
SCENARIO_COLORS = {
    "optimistic":  "#2ecc71",
    "baseline":    "#3498db",
    "pessimistic": "#e74c3c",
}


def render():
    st.subheader("S2-2 η(t) 동적 회복 경로")
    st.caption(
        "피고용인 소득 대체율 η의 3단계 회복 모델 "
        "(Phase 1: 충격 → Phase 2: S커브 회복 → Phase 3: 신균형)"
    )

    ctx     = st.session_state.get("context", {})
    profile = st.session_state.get("company_profile", {})
    depts   = st.session_state.get("departments", [])
    currency = profile.get("currency", "억원") if profile else "억원"

    # ── 파라미터 입력 ─────────────────────────────────────
    st.markdown("#### 초기 파라미터")
    col1, col2, col3 = st.columns(3)
    with col1:
        eta_0  = st.slider("초기 소득 대체율 η₀", 0.0, 1.0,
                           value=float(ctx.get("eta", 0.35)), step=0.01)
        lam    = st.number_input("소비성향 λ", 0.0, 1.0,
                                 value=float(ctx.get("lambda_", 0.48)), step=0.01)
    with col2:
        w      = st.number_input(f"태스크당 임금 w ({currency})", 0.01, value=0.5, step=0.01)
        c      = st.number_input(f"태스크당 AI 비용 c ({currency})", 0.001, value=0.1, step=0.01)
    with col3:
        k      = st.number_input("마찰 계수 k", 0.1, 5.0,
                                 value=float(round(
                                     sum(d["k"] for d in depts) / len(depts), 2
                                 )) if depts else 1.0, step=0.05)
        N      = st.number_input("경쟁사 수 N", 1,
                                 value=int(profile.get("N", 7)) if profile else 7, step=1)
        L      = st.number_input("총 노동자 수 L", 1.0,
                                 value=float(sum(d["headcount"] for d in depts)) if depts else 100.0,
                                 step=1.0)
        A      = float(profile.get("A", 10.0)) if profile else 10.0

    col4, col5 = st.columns(2)
    with col4:
        sim_years = st.slider("시뮬레이션 기간 (년)", 3, 20, 10)
    with col5:
        selected_scenarios = st.multiselect(
            "시나리오 선택",
            SCENARIOS,
            default=SCENARIOS,
            format_func=lambda s: SCENARIO_LABELS[s],
        )

    if not selected_scenarios:
        st.warning("최소 1개 시나리오를 선택해주세요.")
        return

    base_params = ModelParams(lambda_=lam, eta=eta_0, w=w, c=c, k=k, N=N, A=A, L=L)
    years       = np.linspace(0, sim_years, sim_years * 10 + 1)
    paths       = compute_dynamic_paths(years, eta_0, base_params, selected_scenarios)

    # ── η(t) 경로 차트 ────────────────────────────────────
    st.markdown("#### η(t) 소득 대체율 회복 경로")
    fig_eta = go.Figure()
    for sc in selected_scenarios:
        fig_eta.add_trace(go.Scatter(
            x=list(years), y=paths[sc]["eta"],
            mode="lines", name=SCENARIO_LABELS[sc],
            line=dict(color=SCENARIO_COLORS[sc]),
        ))
    fig_eta.add_hline(y=eta_0, line_dash="dot", annotation_text=f"초기 η₀={eta_0:.2f}", line_color="gray")
    fig_eta.add_vrect(x0=0, x1=1, fillcolor="orange", opacity=0.05, annotation_text="충격기")
    fig_eta.add_vrect(x0=1, x1=4, fillcolor="blue", opacity=0.05, annotation_text="적응기")
    fig_eta.update_layout(xaxis_title="시간 (년)", yaxis_title="소득 대체율 η",
                          legend=dict(orientation="h"))
    st.plotly_chart(fig_eta, use_container_width=True)

    # ── αNE(t) / αCO(t) / wedge(t) 차트 ─────────────────
    st.markdown("#### 자동화율 동적 경로 — αNE(t), αCO(t), wedge(t)")

    tab1, tab2, tab3 = st.tabs(["αNE vs αCO", "wedge (격차)", "τ*(t) 피구세 경로"])

    with tab1:
        fig_alpha = go.Figure()
        for sc in selected_scenarios:
            fig_alpha.add_trace(go.Scatter(
                x=list(years), y=paths[sc]["alpha_NE"],
                mode="lines", name=f"αNE — {SCENARIO_LABELS[sc]}",
                line=dict(color=SCENARIO_COLORS[sc]),
            ))
            fig_alpha.add_trace(go.Scatter(
                x=list(years), y=paths[sc]["alpha_CO"],
                mode="lines", name=f"αCO — {SCENARIO_LABELS[sc]}",
                line=dict(color=SCENARIO_COLORS[sc], dash="dash"),
            ))
        fig_alpha.update_layout(xaxis_title="시간 (년)", yaxis_title="자동화율",
                                legend=dict(orientation="h"))
        st.plotly_chart(fig_alpha, use_container_width=True)

    with tab2:
        fig_wedge = go.Figure()
        for sc in selected_scenarios:
            fig_wedge.add_trace(go.Scatter(
                x=list(years), y=paths[sc]["wedge"],
                mode="lines", name=SCENARIO_LABELS[sc],
                line=dict(color=SCENARIO_COLORS[sc]),
                fill="tozeroy", fillcolor=SCENARIO_COLORS[sc].replace(")", ", 0.1)").replace("rgb", "rgba") if "rgb" in SCENARIO_COLORS[sc] else SCENARIO_COLORS[sc],
            ))
        fig_wedge.add_hline(y=0.20, line_dash="dot",
                            annotation_text="경고 임계치 0.20", line_color="red")
        fig_wedge.update_layout(xaxis_title="시간 (년)", yaxis_title="격차 wedge = αNE − αCO",
                                legend=dict(orientation="h"))
        st.plotly_chart(fig_wedge, use_container_width=True)

    with tab3:
        fig_tau = go.Figure()
        for sc in selected_scenarios:
            fig_tau.add_trace(go.Scatter(
                x=list(years), y=paths[sc]["tau_star"],
                mode="lines", name=SCENARIO_LABELS[sc],
                line=dict(color=SCENARIO_COLORS[sc]),
            ))
        fig_tau.update_layout(
            xaxis_title="시간 (년)",
            yaxis_title=f"최적 피구세 τ* ({currency}/태스크)",
            legend=dict(orientation="h"),
        )
        st.caption("η 상승 → ℓ 감소 → τ* 자기소멸 경로 (논문 Section 4.6)")
        st.plotly_chart(fig_tau, use_container_width=True)

    # ── t=1 / t=5 / t=10 스냅샷 ──────────────────────────
    st.markdown("#### 주요 시점 스냅샷")
    snap_years = [1, 3, 5, min(10, sim_years)]
    snap_years = sorted(set(snap_years))

    for sc in selected_scenarios:
        st.markdown(f"**{SCENARIO_LABELS[sc]}**")
        rows = []
        for sy in snap_years:
            idx = min(int(sy * 10), len(years) - 1)
            rows.append({
                "시점 (년)": sy,
                "η(t)":      round(paths[sc]["eta"][idx], 3),
                "αNE(t)":    round(paths[sc]["alpha_NE"][idx], 3),
                "αCO(t)":    round(paths[sc]["alpha_CO"][idx], 3),
                "wedge(t)":  round(paths[sc]["wedge"][idx], 3),
                f"τ*(t) ({currency})": round(paths[sc]["tau_star"][idx], 5),
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # LLM 버튼
    if st.button("동적 경로 분석 해석 (LLM)", use_container_width=True):
        try:
            from shared.llm.client import call_llm
            snap_data = {}
            for sc in selected_scenarios:
                snap_data[sc] = {
                    "t1":  {"eta": paths[sc]["eta"][10], "wedge": paths[sc]["wedge"][10]},
                    "t5":  {"eta": paths[sc]["eta"][min(50, len(years)-1)],
                            "wedge": paths[sc]["wedge"][min(50, len(years)-1)]},
                    "t10": {"eta": paths[sc]["eta"][min(100, len(years)-1)],
                            "wedge": paths[sc]["wedge"][min(100, len(years)-1)]},
                }
            st.markdown(call_llm("dynamic_analysis", {"eta_0": eta_0, "snapshots": snap_data}))
        except Exception as e:
            st.info(f"LLM 준비 중입니다. ({e})")
