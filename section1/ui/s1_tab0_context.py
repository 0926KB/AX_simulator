"""section1/ui/s1_tab0_context.py — 컨텍스트 설정"""
import streamlit as st
from shared.data.api_client import load_country_params
from shared.data.presets import COUNTRY_CODES, COUNTRY_DEFAULTS, INDUSTRY_TYPES


def render():
    st.subheader("S1-0 컨텍스트 설정")
    st.caption("국가·산업 파라미터를 로드해 이후 모든 계산의 기반을 설정합니다.")

    col1, col2 = st.columns(2)
    with col1:
        country = st.selectbox(
            "국가", COUNTRY_CODES,
            format_func=lambda c: f"{c} — {COUNTRY_DEFAULTS[c]['name']}",
            index=0,
        )
    with col2:
        industry = st.selectbox("산업", INDUSTRY_TYPES, index=2)

    if st.button("파라미터 로드", type="primary", use_container_width=True):
        with st.spinner("OECD / World Bank API 조회 중..."):
            params = load_country_params(country, industry)

        st.session_state["context"] = {"country": country, "industry": industry, **params}
        st.success("컨텍스트 로드 완료")

        if params["warnings"]:
            for w in params["warnings"]:
                st.warning(w)

    ctx = st.session_state.get("context")
    if ctx:
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("소득 대체율 η", f"{ctx['eta']:.2f}")
        col2.metric("소비성향 λ", f"{ctx['lambda_']:.3f}")
        col3.metric("실업률", f"{ctx['unemployment_rate']:.1f}%")
        col4.metric("EPL 고용보호지수", f"{ctx['epl_score']:.1f}")

        st.caption(f"통화: {ctx['currency']} | 법체계: {ctx['legal_system']}")

        if st.button("국가/산업 컨텍스트 분석 (LLM)", use_container_width=True):
            _llm_context_analysis(ctx, country, industry)


def _llm_context_analysis(ctx: dict, country: str, industry: str):
    try:
        from shared.llm.client import call_llm
        from shared.llm.prompts import PROMPTS
        payload = {
            "country": country, "industry": industry,
            "unemployment_rate": ctx["unemployment_rate"],
            "eta": ctx["eta"], "lambda": ctx["lambda_"],
            "epl_score": ctx["epl_score"],
        }
        result = call_llm("context_analysis", payload)
        st.markdown("**AI 컨텍스트 분석**")
        st.markdown(result)
    except Exception as e:
        st.info(f"LLM 분석 준비 중입니다. ({e})")
