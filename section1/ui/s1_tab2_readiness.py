"""section1/ui/s1_tab2_readiness.py — AI 준비도 진단"""
import streamlit as st
from shared.data.presets import (
    READINESS_DIMENSIONS, READINESS_SCALE, compute_k, interpret_k,
    estimate_capex, estimate_opex,
)


def render():
    st.subheader("S1-2 AI 준비도 진단")
    st.caption("McKinsey Rewired + BCG 10-20-70 기반 부서별 마찰 계수 k 도출")

    depts = st.session_state.get("departments", [])
    if not depts:
        st.warning("S1-1에서 부서를 먼저 등록해주세요.")
        return

    dept_names = [d["name"] for d in depts]
    selected   = st.selectbox("진단할 부서 선택", dept_names)
    dept_idx   = dept_names.index(selected)
    dept       = depts[dept_idx]

    st.markdown("#### 준비도 5개 차원 (1~5점)")

    scores = {}
    cols = st.columns(len(READINESS_DIMENSIONS))
    for i, (dim_key, dim_info) in enumerate(READINESS_DIMENSIONS.items()):
        with cols[i]:
            score = st.slider(
                dim_info["label"],
                1, 5,
                int(dept.get("readiness_scores", {}).get(dim_key, 3)),
                help=f"{dim_info['description']}\n가중치: {dim_info['weight']:.0%}",
            )
            scores[dim_key] = float(score)
            st.caption(READINESS_SCALE[score][:30] + "...")

    k = compute_k(scores, dept["type"])
    interp = interpret_k(k)

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("마찰 계수 k", f"{k:.3f}", help="낮을수록 자동화 통합 용이")
    col2.metric("판정", interp["label"])
    col3.metric("권고 액션", interp["action"])

    weighted = sum(scores[d] * READINESS_DIMENSIONS[d]["weight"] for d in scores)
    st.progress(weighted / 5.0, text=f"종합 준비도 점수: {weighted:.2f} / 5.00")

    # Capex/Opex 업데이트
    capex_info = estimate_capex({"headcount": dept["headcount"], "type": dept["type"]}, weighted)
    opex_info  = estimate_opex(
        {"headcount": dept["headcount"], "type": dept["type"],
         "capex_total": capex_info["total_capex"], "avg_salary": dept["avg_salary"]},
        dept["alpha"],
    )

    currency = st.session_state.get("company_profile", {}).get("currency", "억원")
    st.markdown("#### AI 도입 비용 추정 (CloudZero 2025)")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"초기 Capex ({currency})", f"{capex_info['total_capex']:.2f}")
    c2.metric(f"연간 Opex ({currency})", f"{opex_info['total_opex']:.2f}")
    c3.metric("숨겨진 비용 비율", f"{capex_info['hidden_rate']:.0%}")

    if st.button("준비도 진단 결과 저장", type="primary", use_container_width=True):
        st.session_state["departments"][dept_idx]["readiness_scores"] = scores
        st.session_state["departments"][dept_idx]["k"]                = k
        st.session_state["departments"][dept_idx]["capex_total"]      = capex_info["total_capex"]
        st.session_state["departments"][dept_idx]["annual_opex"]      = opex_info["total_opex"]
        st.success(f"'{selected}' 준비도 저장 완료 (k={k:.3f})")

    if st.button("준비도 진단 해석 (LLM)", use_container_width=True):
        try:
            from shared.llm.client import call_llm
            payload = {"dept_name": selected, "dept_type": dept["type"],
                       "scores": scores, "k": k, "interpretation": interp}
            st.markdown(call_llm("readiness_analysis", payload))
        except Exception as e:
            st.info(f"LLM 준비 중입니다. ({e})")
