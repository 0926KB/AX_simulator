"""section2/ui/s2_tab3_policy.py — 정책 수단 비교 (논문 Table 1)"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from section2.core.paper_model import ModelParams
from section2.core.policy_engine import compare_policies, find_optimal_tau, POLICY_INSTRUMENTS


EFFECTIVENESS_COLOR = {
    "완전 해소": "#2ecc71",
    "부분 해소": "#f39c12",
    "미해소":    "#e74c3c",
}


def render():
    st.subheader("S2-3 정책 수단 비교")
    st.caption(
        "논문 Table 1 — 6가지 정책 수단 외부효과 해소 효과 비교"
    )

    ctx     = st.session_state.get("context", {})
    profile = st.session_state.get("company_profile", {})
    depts   = st.session_state.get("departments", [])
    currency = profile.get("currency", "억원") if profile else "억원"

    # ── 파라미터 입력 ─────────────────────────────────────
    st.markdown("#### 기본 파라미터")
    col1, col2, col3 = st.columns(3)
    with col1:
        lam = st.number_input("소비성향 λ", 0.0, 1.0,
                              value=float(ctx.get("lambda_", 0.48)), step=0.01)
        eta = st.number_input("소득 대체율 η", 0.0, 1.0,
                              value=float(ctx.get("eta", 0.35)), step=0.01)
    with col2:
        w   = st.number_input(f"태스크당 임금 w ({currency})", 0.01, value=0.5, step=0.01)
        c   = st.number_input(f"태스크당 AI 비용 c ({currency})", 0.001, value=0.1, step=0.01)
    with col3:
        k   = st.number_input("마찰 계수 k", 0.1, 5.0,
                              value=float(round(
                                  sum(d["k"] for d in depts) / len(depts), 2
                              )) if depts else 1.0, step=0.05)
        N   = st.number_input("경쟁사 수 N", 1,
                              value=int(profile.get("N", 7)) if profile else 7, step=1)
        L   = st.number_input("총 노동자 수 L", 1.0,
                              value=float(sum(d["headcount"] for d in depts)) if depts else 100.0,
                              step=1.0)
        A   = float(profile.get("A", 10.0)) if profile else 10.0

    # ── 정책별 조절 파라미터 ──────────────────────────────
    st.markdown("#### 정책 시나리오 설정")
    col1, col2, col3 = st.columns(3)
    with col1:
        eta_increase      = st.slider("업스킬링 η 상승폭", 0.0, 0.30, 0.10, 0.01,
                                      help="Upskilling/재훈련 효과: η를 이만큼 올림")
    with col2:
        capital_tax_rate  = st.slider("자본소득세율", 0.0, 0.30, 0.10, 0.01,
                                      help="AI 도입 비용 c를 이 비율만큼 증가")
    with col3:
        worker_equity_share = st.slider("노동자 지분 ε", 0.0, 0.50, 0.20, 0.01,
                                        help="노동자가 이익의 ε만큼 수취 → η 등가 상승")

    total_tasks = (
        sum(d["headcount"] * d["alpha"] for d in depts) if depts else L * 0.5
    )

    params = ModelParams(lambda_=lam, eta=eta, w=w, c=c, k=k, N=N, A=A, L=L)

    if st.button("정책 효과 계산", type="primary", use_container_width=True):
        results = compare_policies(
            params, total_tasks,
            eta_increase=eta_increase,
            capital_tax_rate=capital_tax_rate,
            worker_equity_share=worker_equity_share,
        )
        optimal = find_optimal_tau(params, total_tasks)
        st.session_state["policy_results"] = results
        st.session_state["optimal_tau"]    = optimal

    results = st.session_state.get("policy_results")
    optimal = st.session_state.get("optimal_tau")
    if not results:
        return

    # ── 피구세 최적값 요약 ────────────────────────────────
    st.divider()
    st.markdown("#### 최적 피구세 τ* 요약")
    oc1, oc2, oc3, oc4 = st.columns(4)
    oc1.metric(f"τ* ({currency}/태스크)", f"{optimal['tau_star']:.5f}")
    oc2.metric("αNE → 세후 αNE", f"{optimal['alpha_NE_before']:.3f} → {optimal['alpha_NE_after']:.3f}",
               delta=f"{optimal['alpha_NE_after'] - optimal['alpha_NE_before']:+.3f}")
    oc3.metric("격차 해소율", f"{optimal['gap_closed_pct']:.1f}%")
    oc4.metric(f"연간 세금 부담 ({currency})", f"{optimal['annual_tax_burden']:.3f}")
    st.caption(f"수식: {optimal['paper_formula']}  |  출처: {optimal['source']}")

    # ── 6개 정책 비교 테이블 ──────────────────────────────
    st.markdown("#### 정책 수단 효과 비교 (논문 Table 1)")
    rows = []
    for r in results:
        rows.append({
            "정책": r["name"],
            "αNE (정책後)":   f"{r['alpha_NE']:.3f}",
            "αCO":            f"{r['alpha_CO']:.3f}",
            "격차 wedge":     f"{r['wedge']:.3f}",
            "격차 해소율 (%)": f"{r['gap_closed_pct']:.1f}",
            "수요 파괴율 (%)": f"{r['demand_loss_pct']:.2f}",
            "외부효과 해소":   r["externality"],
            "근거":            r["paper_section"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── 격차 해소율 막대 차트 ─────────────────────────────
    st.markdown("#### 격차 해소율 비교")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[r["name"] for r in results],
        y=[r["gap_closed_pct"] for r in results],
        marker_color=[
            EFFECTIVENESS_COLOR.get(r["externality"], "#95a5a6") for r in results
        ],
        text=[f"{r['gap_closed_pct']:.1f}%" for r in results],
        textposition="outside",
    ))
    fig.add_hline(y=100, line_dash="dot", annotation_text="완전 해소 기준 (100%)",
                  line_color="#2ecc71")
    fig.update_layout(
        yaxis_title="격차 해소율 (%)",
        yaxis_range=[0, 115],
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── αNE 수렴 레이더 차트 ─────────────────────────────
    st.markdown("#### αNE — 협력 최적(αCO) 대비 수렴도")
    alpha_CO_ref = results[0]["alpha_CO"] if results else 0.5
    policy_names = [r["name"] for r in results]
    distance_from_co = [abs(r["alpha_NE"] - alpha_CO_ref) for r in results]

    fig2 = go.Figure(go.Bar(
        x=policy_names,
        y=distance_from_co,
        marker_color="#3498db",
        text=[f"{v:.3f}" for v in distance_from_co],
        textposition="outside",
    ))
    fig2.update_layout(
        yaxis_title="|αNE − αCO| (0에 가까울수록 사회적 최적)",
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── 정책 카드 ─────────────────────────────────────────
    st.markdown("#### 정책 수단 메커니즘")
    for r in results:
        color = EFFECTIVENESS_COLOR.get(r["externality"], "#95a5a6")
        with st.expander(f"{r['name']} — {r['externality']} ({r['paper_section']})"):
            st.markdown(f"**메커니즘**: {r['mechanism']}")
            st.markdown(f"**wedge 변화**: {r['wedge_change']}")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("αNE (정책後)", f"{r['alpha_NE']:.3f}")
            mc2.metric("격차 해소율", f"{r['gap_closed_pct']:.1f}%")
            mc3.metric("수요 파괴율", f"{r['demand_loss_pct']:.2f}%")

    # LLM 버튼
    if st.button("정책 비교 분석 (LLM)", use_container_width=True):
        try:
            from shared.llm.client import call_llm
            payload = {
                "results": [{k: v for k, v in r.items()
                             if k not in ("N_star_change",)} for r in results],
                "optimal": optimal,
                "params":  {"lam": lam, "eta": eta, "w": w, "c": c, "k": k, "N": N},
            }
            st.markdown(call_llm("policy_analysis", payload))
        except Exception as e:
            st.info(f"LLM 준비 중입니다. ({e})")
