"""
section1/core/impact_engine.py
Layer 3 — 기업 파급효과 5채널 통합 엔진

채널 1: 투자자/주가 반응 (CAR)
채널 2: Survivor Syndrome
채널 3: 고객/브랜드 반응
채널 4: 규제 비용
채널 5: ESG/공급망 (정성 체크리스트)
"""

from __future__ import annotations
from shared.data.impact_coefficients import (
    compute_car,
    compute_survivor_impact,
    compute_brand_impact,
    get_esg_alerts,
)
from shared.data.regulatory import adjust_for_regulatory_cost
from shared.data.presets import INDUSTRY_IS_TECH


def compute_total_enterprise_impact(
    internal_roi: dict,
    company_profile: dict,
    country: str,
    industry: str,
    layoff_config: dict,
    market_cap: float | None = None,
) -> dict:
    """
    5채널 기업 파급효과 통합 계산

    Args:
        internal_roi:    Layer 1 결과 (total_saving_annual, displaced_headcount 포함)
        company_profile: {annual_revenue, biz_type, is_listed, avg_tenure_years,
                          total_headcount, disclosure_style}
        country:         국가 코드
        industry:        산업 유형
        layoff_config:   {layoff_reason: "proactive"|"reactive", ai_branding: bool}
        market_cap:      시가총액 (상장사, 억원 기준)

    Returns:
        channel 1~5 결과 + 순영향 통합
    """
    gross           = internal_roi["total_saving_annual"]
    displaced       = internal_roi["displaced_headcount"]
    total_headcount = company_profile["total_headcount"]
    layoff_pct      = displaced / max(total_headcount, 1)
    avg_salary      = gross / max(displaced, 0.001)
    is_tech         = INDUSTRY_IS_TECH.get(industry, False)

    # ── 채널 1: 투자자/주가 반응 ──────────────────────────
    ch1 = None
    stock_impact = None
    if company_profile.get("is_listed"):
        ch1 = compute_car(
            layoff_reason=layoff_config.get("layoff_reason", "proactive"),
            is_tech=is_tech,
            country=country,
            layoff_pct=layoff_pct,
            ai_branding=layoff_config.get("ai_branding", False),
        )
        if market_cap:
            stock_impact = market_cap * ch1["car_pct"] / 100.0

    # ── 채널 2: Survivor Syndrome ─────────────────────────
    remaining = total_headcount - displaced
    ch2 = compute_survivor_impact(
        remaining_headcount=remaining,
        avg_salary=avg_salary,
        layoff_pct=layoff_pct,
        industry=industry,
        tenure_years=company_profile.get("avg_tenure_years", 5.0),
    )

    # ── 채널 3: 고객/브랜드 반응 ─────────────────────────
    ch3 = compute_brand_impact(
        annual_revenue=company_profile["annual_revenue"],
        biz_type=company_profile.get("biz_type", "B2C"),
        industry=industry,
        disclosure_style=company_profile.get("disclosure_style", "restructuring"),
        is_tech=is_tech,
    )

    # ── 채널 4: 규제 비용 ─────────────────────────────────
    ch4 = adjust_for_regulatory_cost(
        labor_saving=gross,
        country=country,
        displaced_headcount=displaced,
        avg_salary=avg_salary,
        avg_tenure_years=company_profile.get("avg_tenure_years", 5.0),
    )

    # ── 채널 5: ESG 체크리스트 ────────────────────────────
    ch5_alerts = get_esg_alerts(
        layoff_pct=layoff_pct,
        country=country,
        biz_type=company_profile.get("biz_type", "B2C"),
    )

    # ── 순영향 통합 ───────────────────────────────────────
    regulatory_cost = ch4["severance_cost"] + ch4["outplacement_cost"]
    survivor_cost   = ch2["total_hidden_cost"]
    brand_impact    = ch3["revenue_impact_annual"]   # 음수 = 비용

    net_annual = gross - regulatory_cost - survivor_cost + brand_impact

    return {
        "gross_saving_annual":   round(gross, 3),
        "channel1_car":          ch1,
        "channel2_survivor":     ch2,
        "channel3_brand":        ch3,
        "channel4_regulatory":   ch4,
        "channel5_esg_alerts":   ch5_alerts,
        "regulatory_cost":       round(regulatory_cost, 3),
        "survivor_cost":         round(survivor_cost, 3),
        "brand_impact":          round(brand_impact, 3),
        "net_saving_annual":     round(net_annual, 3),
        "stock_impact_estimate": round(stock_impact, 3) if stock_impact is not None else None,
        "net_vs_gross_ratio":    round(net_annual / gross, 3) if gross > 0 else None,
        "layoff_pct":            round(layoff_pct, 4),
    }
