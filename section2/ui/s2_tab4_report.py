"""section2/ui/s2_tab4_report.py — 종합 보고서 (Section 1 + Section 2 통합)"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
from datetime import datetime
from section2.core.paper_model import ModelParams, compute_externality
from section2.core.policy_engine import find_optimal_tau


def render():
    st.subheader("S2-4 종합 분석 보고서")
    st.caption("Section 1 (기업 의사결정) + Section 2 (시장/정책 분석) 통합 요약")

    ctx     = st.session_state.get("context", {})
    profile = st.session_state.get("company_profile", {})
    depts   = st.session_state.get("departments", [])

    if not ctx or not profile or not depts:
        st.warning("S1-0 ~ S1-2 먼저 완료해주세요.")
        return

    currency = profile.get("currency", "억원")

    # ── 1. 기업 요약 ──────────────────────────────────────
    st.markdown("### 1. 기업 프로파일 요약")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("연간 매출", f"{profile.get('annual_revenue', 0):.1f} {currency}")
    p2.metric("영업이익률", f"{profile.get('op_margin', 0)*100:.1f}%")
    p3.metric("총 부서 수", f"{len(depts)}개")
    p4.metric("총 헤드카운트", f"{profile.get('total_headcount', sum(d['headcount'] for d in depts))}명")

    # ── 2. AI 준비도 매트릭스 ─────────────────────────────
    st.markdown("### 2. 부서별 AI 준비도 매트릭스")
    if depts:
        df_depts = pd.DataFrame([{
            "부서명":     d["name"],
            "유형":       d["type"],
            "헤드카운트": d["headcount"],
            "자동화율":   f"{d['alpha']:.0%}",
            "k(마찰)":    round(d["k"], 3),
            f"초기Capex({currency})": round(d.get("capex_total", 0), 2),
            f"연간Opex({currency})":  round(d.get("annual_opex", 0), 2),
        } for d in depts])
        st.dataframe(df_depts, use_container_width=True, hide_index=True)

    # ── 3. ROI 결과 ───────────────────────────────────────
    roi_results = st.session_state.get("roi_results", [])
    if roi_results:
        st.markdown("### 3. 부서별 ROI 분석 (S1-3 결과)")
        df_roi = pd.DataFrame([{
            "부서":                       r["dept"],
            f"NPV 5년 ({currency})":      round(r["roi"]["npv_5yr"], 2),
            "ROI (%)":                    round(r["roi"]["roi_pct"], 1),
            "회수기간 (년)":              round(r["roi"]["payback_years"], 1),
            "해고 인원":                  r["roi"]["displaced_headcount"],
        } for r in roi_results])
        st.dataframe(df_roi, use_container_width=True, hide_index=True)

        total_npv       = sum(r["roi"]["npv_5yr"] for r in roi_results)
        total_displaced = sum(r["roi"]["displaced_headcount"] for r in roi_results)
        r1, r2 = st.columns(2)
        r1.metric(f"전사 NPV 합계 ({currency})", f"{total_npv:.2f}")
        r2.metric("전사 총 해고 인원", f"{total_displaced}명")
    else:
        st.info("S1-3에서 ROI 계산을 먼저 실행해주세요.")
        total_npv, total_displaced = 0.0, 0

    # ── 4. 기업 파급효과 ──────────────────────────────────
    impact = st.session_state.get("impact_result")
    if impact:
        st.markdown("### 4. 기업 파급효과 5채널 (S1-3 결과)")
        i1, i2, i3, i4, i5 = st.columns(5)
        i1.metric(f"총 절감 ({currency})", f"{impact.get('gross_saving_annual', 0):+.2f}")
        i2.metric(f"규제 비용 ({currency})", f"{-impact.get('regulatory_cost', 0):+.2f}")
        i3.metric(f"생존자 비용 ({currency})", f"{-impact.get('survivor_cost', 0):+.2f}")
        i4.metric(f"브랜드 영향 ({currency})", f"{impact.get('brand_impact', 0):+.2f}")
        i5.metric(f"순 절감 ({currency})", f"{impact.get('net_saving_annual', 0):+.2f}")

        if impact.get("net_vs_gross_ratio") is not None:
            st.progress(
                max(0.0, min(1.0, impact["net_vs_gross_ratio"])),
                text=f"순편익/직접절감 비율: {impact['net_vs_gross_ratio']:.0%}"
            )

    # ── 5. 시장 외부효과 분석 ─────────────────────────────
    st.markdown("### 5. 시장 외부효과 분석 (논문 수식)")

    lam   = ctx.get("lambda_", 0.48)
    eta   = ctx.get("eta", 0.35)
    w     = st.number_input(f"태스크당 임금 w ({currency})", 0.01, value=0.5, step=0.01, key="rep_w")
    c     = st.number_input(f"태스크당 AI 비용 c ({currency})", 0.001, value=0.1, step=0.01, key="rep_c")
    k_avg = float(round(sum(d["k"] for d in depts) / len(depts), 3)) if depts else 1.0
    L     = float(sum(d["headcount"] for d in depts)) if depts else 100.0
    N     = int(profile.get("N", 7))
    A     = float(profile.get("A", 10.0))

    params = ModelParams(lambda_=lam, eta=eta, w=w, c=c, k=k_avg, N=N, A=A, L=L)
    total_tasks = sum(d["headcount"] * d["alpha"] for d in depts) if depts else L * 0.5
    ext     = compute_externality(0.0, params)
    optimal = find_optimal_tau(params, total_tasks)

    e1, e2, e3, e4 = st.columns(4)
    e1.metric("αNE (Nash 균형)", f"{ext.alpha_NE:.3f}")
    e2.metric("αCO (협력 최적)", f"{ext.alpha_CO:.3f}")
    e3.metric("과잉 자동화 격차", f"{ext.wedge:.3f}",
              delta="위험" if ext.wedge > 0.2 else "정상",
              delta_color="inverse" if ext.wedge > 0.2 else "off")
    e4.metric(f"최적 피구세 τ* ({currency})", f"{ext.tau_star:.5f}")

    # ── 6. 통합 시각화 ────────────────────────────────────
    st.markdown("### 6. 통합 리스크 대시보드")
    _render_risk_dashboard(depts, ext, impact, currency)

    # ── 7. 정책 권고 ──────────────────────────────────────
    st.markdown("### 7. 핵심 권고사항")
    _render_recommendations(ext, optimal, impact, profile, currency)

    # ── LLM 종합 보고서 ───────────────────────────────────
    st.divider()
    if st.button("LLM 종합 보고서 생성", type="primary", use_container_width=True):
        try:
            from shared.llm.client import call_llm
            payload = {
                "profile":   {k: v for k, v in profile.items() if k not in ("ticker",)},
                "depts_cnt": len(depts),
                "total_npv": total_npv,
                "displaced": total_displaced,
                "ext":       ext.__dict__,
                "optimal":   optimal,
                "impact":    impact or {},
                "country":   ctx.get("country", "KR"),
                "industry":  ctx.get("industry", "IT소프트웨어"),
            }
            report = call_llm("comprehensive_report", payload)
            st.markdown("---")
            st.markdown("#### AI 종합 분석 보고서")
            st.markdown(report)
        except Exception as e:
            st.info(f"LLM 준비 중입니다. ({e})")

    # ── PDF / JSON 내보내기 ───────────────────────────────
    st.divider()
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "company_profile": {k: v for k, v in profile.items() if k not in ("ticker",)},
            "departments": [{k: v for k, v in d.items() if k != "readiness_scores"} for d in depts],
            "market_externality": ext.__dict__,
            "optimal_pigouvian_tax": optimal,
            "impact_result": impact or {},
        }
        st.download_button(
            "JSON 내보내기",
            data=json.dumps(export_data, ensure_ascii=False, indent=2),
            file_name=f"ax_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_exp2:
        if st.button("세션 저장", use_container_width=True):
            try:
                from shared.data.session_store import SessionStore
                store = SessionStore()
                sid = store.save(
                    name=f"Report_{datetime.now().strftime('%Y%m%d_%H%M')}",
                    data={
                        "context": ctx,
                        "company_profile": profile,
                        "departments": depts,
                        "roi_results": roi_results,
                        "impact_result": impact,
                    }
                )
                st.success(f"세션 저장 완료 (ID: {sid})")
            except Exception as e:
                st.error(f"세션 저장 실패: {e}")


def _render_risk_dashboard(depts, ext, impact, currency):
    """통합 리스크 레이더 차트"""
    # 지표 정규화 (0=최고 리스크, 1=최저 리스크)
    wedge_risk   = min(ext.wedge / 0.5, 1.0)        # 0.5가 최대라 가정
    demand_risk  = min(ext.demand_loss_pct / 20.0, 1.0)
    net_ratio    = impact.get("net_vs_gross_ratio", 0.7) if impact else 0.7
    k_avg_norm   = min(float(sum(d["k"] for d in depts) / len(depts)) / 3.0, 1.0) if depts else 0.5
    disp_ratio   = sum(d["headcount"] for d in depts)
    disp_risk    = min(
        (sum(r.get("displaced_headcount", 0) for r in
             [st.session_state.get("roi_results", [{}])[0]] if isinstance(r, dict)) /
         max(disp_ratio, 1)), 1.0
    ) if st.session_state.get("roi_results") else 0.5

    categories = ["과잉 자동화 격차", "수요 파괴 위험", "숨겨진 비용", "준비도 미흡", "해고 비율"]
    risk_values = [wedge_risk, demand_risk, 1 - net_ratio, k_avg_norm, disp_risk]

    fig = go.Figure(go.Scatterpolar(
        r=risk_values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(231,76,60,0.2)",
        line_color="#e74c3c",
        name="리스크 수준",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_recommendations(ext, optimal, impact, profile, currency):
    """조건별 핵심 권고"""
    recs = []

    if ext.wedge > 0.20:
        recs.append({
            "level": "danger",
            "title": "과잉 자동화 위험",
            "body":  f"격차 wedge={ext.wedge:.3f} > 임계치 0.20. "
                     f"최적 피구세 τ*={optimal['tau_star']:.5f} {currency}/태스크 도입 검토 필요.",
        })

    if ext.demand_loss_pct > 5.0:
        recs.append({
            "level": "warning",
            "title": "수요 파괴 경보",
            "body":  f"업계 동시 자동화 시 수요 {ext.demand_loss_pct:.1f}% 감소 예상. "
                     "단계적 도입 전략 권고.",
        })

    if impact and impact.get("net_vs_gross_ratio", 1.0) < 0.6:
        recs.append({
            "level": "warning",
            "title": "숨겨진 비용 높음",
            "body":  f"순편익/직접절감 = {impact['net_vs_gross_ratio']:.0%} < 60%. "
                     "규제·생존자·브랜드 비용이 절감 효과를 크게 잠식.",
        })

    if impact and impact.get("channel5_esg_alerts"):
        recs.append({
            "level": "warning",
            "title": "ESG 리스크",
            "body":  f"{len(impact['channel5_esg_alerts'])}개 ESG 체크리스트 항목 경고 발생. "
                     "공시 전략 및 아웃플레이스먼트 프로그램 수립 필요.",
        })

    if not recs:
        recs.append({
            "level": "success",
            "title": "전반적 안전 수준",
            "body":  "주요 리스크 지표가 임계치 이내입니다. 단계적 자동화 도입을 지속 모니터링하세요.",
        })

    for rec in recs:
        if rec["level"] == "danger":
            st.error(f"**{rec['title']}** — {rec['body']}")
        elif rec["level"] == "warning":
            st.warning(f"**{rec['title']}** — {rec['body']}")
        else:
            st.success(f"**{rec['title']}** — {rec['body']}")
