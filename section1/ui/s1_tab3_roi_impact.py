"""section1/ui/s1_tab3_roi_impact.py — 내부 ROI + 기업 파급효과 (Layer 1~3)"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from section1.core.roi_engine import (
    compute_internal_roi, compute_internal_roi_with_cascade,
    linear_projection, priority_matrix,
)
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

    # ── Layer 1-B: 부서간 연쇄 효과 (선택사항) ───────────
    _render_cascade_section(depts, results, currency)

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


def _render_cascade_section(depts: list[dict], roi_results: list[dict], currency: str):
    """부서간 연쇄 효과 설정 및 계산 UI"""
    from shared.data.cascade_survey import (
        CASCADE_QUESTIONS, SUPPORT_RATIO_OPTIONS, DIRECTION_OPTIONS,
        TRANSITION_OPTIONS, label_to_values, survey_to_coefficient,
    )
    from shared.data.cascade_engine import compute_cascade_effects, cascade_summary

    st.markdown("#### Layer 1-B — 부서간 연쇄 효과 *(선택사항)*")
    st.caption(
        "A부서 자동화가 B부서 업무량에 주는 영향을 추가하면 순 절감액이 더 정확해집니다. "
        "설정하지 않으면 기존 ROI와 동일하게 동작합니다."
    )
    st.info(
        "⚠️ 모든 연쇄 효과 수치는 설문 기반 **추정값**입니다. "
        "계수는 실무자 답변에서 도출되며 LLM이 생성하지 않습니다.",
        icon="ℹ️",
    )

    dept_names = [d["name"] for d in depts]

    # 부서 쌍 관리
    if "cascade_pairs_raw" not in st.session_state:
        st.session_state["cascade_pairs_raw"] = []

    with st.expander("부서 쌍 추가", expanded=False):
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            from_dept = st.selectbox("A 부서 (자동화 발생)", dept_names, key="cas_from")
        with p_col2:
            to_options = [d for d in dept_names if d != from_dept]
            to_dept = st.selectbox("B 부서 (연쇄 영향)", to_options, key="cas_to") if to_options else None

        if to_dept:
            q1_label = st.select_slider(
                CASCADE_QUESTIONS["support_ratio"]["question"].format(
                    dept_A=from_dept, dept_B=to_dept
                ),
                options=SUPPORT_RATIO_OPTIONS,
                value="5~15%",
                help=CASCADE_QUESTIONS["support_ratio"]["help"],
            )
            q2_label = st.radio(
                CASCADE_QUESTIONS["direction"]["question"].format(
                    dept_A=from_dept, dept_B=to_dept
                ),
                DIRECTION_OPTIONS,
                horizontal=True,
                help=CASCADE_QUESTIONS["direction"]["help"],
            )
            q3_label = st.select_slider(
                CASCADE_QUESTIONS["transition_period"]["question"],
                options=TRANSITION_OPTIONS,
                value="단기 (3~6개월)",
                help=CASCADE_QUESTIONS["transition_period"]["help"],
            )

            # 미리 계산해서 표시
            sr, direction_str, tp = label_to_values(q1_label, q2_label, q3_label)
            coeff = survey_to_coefficient(sr, direction_str, tp)
            if coeff["coefficient"] != 0.0:
                from_roi = next((r for r in roi_results if r["dept"] == from_dept), None)
                if from_roi:
                    displaced = from_roi["roi"]["displaced_headcount"]
                    preview = displaced * coeff["coefficient"] * coeff["annual_factor"]
                    sign_str = "감소" if preview < 0 else "증가"
                    st.caption(
                        f"→ {to_dept} 연쇄 변화 예상: **{abs(preview):.1f}명 {sign_str}** (연간, 추정)"
                    )

            if st.button("쌍 추가", key="cas_add_btn"):
                sr2, direction_str2, tp2 = label_to_values(q1_label, q2_label, q3_label)
                coeff2 = survey_to_coefficient(sr2, direction_str2, tp2)
                st.session_state["cascade_pairs_raw"].append({
                    "from_dept":        from_dept,
                    "to_dept":          to_dept,
                    "support_label":    q1_label,
                    "direction_label":  q2_label,
                    "transition_label": q3_label,
                    "support_ratio":    sr2,
                    "direction":        direction_str2,
                    "transition_period": tp2,
                    "coefficient":      coeff2["coefficient"],
                    "annual_factor":    coeff2["annual_factor"],
                })
                st.success(f"'{from_dept} → {to_dept}' 쌍 추가됨")
                st.rerun()

    # 등록된 쌍 목록
    pairs_raw = st.session_state.get("cascade_pairs_raw", [])
    if pairs_raw:
        st.markdown(f"**등록된 부서 쌍 ({len(pairs_raw)}개)**")
        for i, pair in enumerate(pairs_raw):
            direction_emoji = "↓" if pair["direction"] == "decrease" else ("↑" if pair["direction"] == "increase" else "—")
            col_p, col_del = st.columns([8, 1])
            with col_p:
                st.markdown(
                    f"`{pair['from_dept']}` → `{pair['to_dept']}` "
                    f"| {pair['support_label']} | {direction_emoji} {pair['direction_label']} "
                    f"| {pair['transition_label']} "
                    f"| 계수: `{pair['coefficient']:+.3f}` × `{pair['annual_factor']:.2f}`"
                )
            with col_del:
                if st.button("삭제", key=f"cas_del_{i}"):
                    st.session_state["cascade_pairs_raw"].pop(i)
                    st.rerun()

        # 연쇄 효과 계산
        if st.button("연쇄 효과 계산 적용", type="secondary", use_container_width=True):
            cascade_results = compute_cascade_effects(depts, pairs_raw)
            st.session_state["cascade_results"] = cascade_results

            # cascade_data 저장 (Phase 2 서버 수집 대비 구조)
            ctx = st.session_state.get("context", {})
            st.session_state["cascade_data"] = {
                "industry":        ctx.get("industry", "기타"),
                "pairs":           pairs_raw,
                "respondent_type": None,   # Phase 2에서 수집
                "company_size":    None,   # Phase 2에서 수집
            }
            st.rerun()

    # 연쇄 효과 결과 표시
    cascade_results = st.session_state.get("cascade_results")
    if not cascade_results:
        return

    summary = cascade_summary(cascade_results, depts)

    st.markdown("##### 연쇄 효과 전/후 비교")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("직접 해고 인원", f"{summary['total_direct_displaced']:.1f}명")
    s2.metric("연쇄 인원 변화 *(추정)*",
              f"{summary['total_cascade_change']:+.1f}명",
              delta=f"{'↓절감' if summary['total_cascade_change'] < 0 else '↑비용'}",
              delta_color="normal" if summary["total_cascade_change"] < 0 else "inverse")
    s3.metric("순 인원 변화",        f"{summary['total_net_change']:.1f}명")
    s4.metric(f"연쇄 추가 비용 ({currency}) *(추정)*",
              f"{summary['total_additional_labor_cost']:+.3f}",
              delta_color="inverse" if summary["total_additional_labor_cost"] > 0 else "normal")

    # 부서별 비교 테이블
    rows = []
    roi_map = {r["dept"]: r["roi"] for r in roi_results}
    for cr in cascade_results:
        direct_saving = roi_map.get(cr["dept_name"], {}).get("total_saving_annual", 0.0)
        rows.append({
            "부서":               cr["dept_name"],
            "직접 해고 (명)":     cr["direct_displaced"],
            "연쇄 변화 (명)":     f"{cr['cascade_change']:+.1f} *(추정)*" if cr["cascade_change"] != 0 else "—",
            "순 변화 (명)":       cr["net_headcount_change"],
            f"연쇄 비용 ({currency})": f"{cr['net_labor_cost_change'] - direct_saving:+.3f}" if cr["cascade_change"] != 0 else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 연쇄 효과 ROI 재계산 비교
    st.markdown("##### ROI 재계산 (연쇄 효과 반영)")
    cr_map = {r["dept_name"]: r for r in cascade_results}
    dept_map = {d["name"]: d for d in depts}

    phi_cascade = st.slider("AI 생산성 배수 φ (연쇄 재계산용)", 1.0, 2.0, 1.0, 0.05,
                            key="cascade_phi")
    compare_rows = []
    for r in roi_results:
        dept = dept_map.get(r["dept"])
        if not dept:
            continue
        cr = cr_map.get(r["dept"])
        roi_c = compute_internal_roi_with_cascade(dept, dept["alpha"], cr, phi_cascade)
        compare_rows.append({
            "부서":                      r["dept"],
            f"기본 NPV ({currency})":    r["roi"]["npv_5yr"],
            f"연쇄 반영 NPV ({currency}) *(추정)*": roi_c.get("npv_5yr_with_cascade", roi_c["npv_5yr"]),
            f"연쇄 절감 차이 ({currency})":
                round(roi_c.get("total_saving_with_cascade", roi_c["total_saving_annual"])
                      - roi_c["total_saving_annual"], 3),
        })
    st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)


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
