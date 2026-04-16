"""
shared/data/regulatory.py
국가별 규제 컨텍스트 테이블 (Layer 3 채널 4)

출처: OECD EPL Index, 각국 노동법, World Bank Doing Business
"""

from __future__ import annotations

REGULATORY_CONTEXT: dict[str, dict] = {
    "KR": {
        "severance_notice_days": 50,
        "severance_pay_months": 1,
        "union_coverage_pct": 14.0,
        "ai_regulation": "AI 기본법 (2024)",
        "data_regulation": "개인정보보호법 (PIPA)",
        "labor_flexibility": "낮음",
        "firing_cost_multiplier": 1.8,
        "epl_score": 2.2,
        "outplacement_rate": 0.10,
        "source": "OECD EPL Index 2024, 근로기준법 제24조",
    },
    "US": {
        "severance_notice_days": 60,
        "severance_pay_months": 0,
        "union_coverage_pct": 10.0,
        "ai_regulation": "EO 14110 (2023)",
        "data_regulation": "CCPA / state laws",
        "labor_flexibility": "높음",
        "firing_cost_multiplier": 1.2,
        "epl_score": 1.1,
        "outplacement_rate": 0.10,
        "source": "OECD EPL Index 2024, WARN Act",
    },
    "DE": {
        "severance_notice_days": 90,
        "severance_pay_months": 0.5,
        "union_coverage_pct": 63.0,
        "ai_regulation": "EU AI Act (2024)",
        "data_regulation": "GDPR",
        "labor_flexibility": "매우 낮음",
        "firing_cost_multiplier": 2.5,
        "epl_score": 2.8,
        "outplacement_rate": 0.12,
        "source": "OECD EPL Index 2024, Kündigungsschutzgesetz",
    },
    "JP": {
        "severance_notice_days": 30,
        "severance_pay_months": 1,
        "union_coverage_pct": 16.5,
        "ai_regulation": "AI 가이드라인 (2023)",
        "data_regulation": "APPI",
        "labor_flexibility": "낮음",
        "firing_cost_multiplier": 1.6,
        "epl_score": 2.1,
        "outplacement_rate": 0.10,
        "source": "OECD EPL Index 2024, 労働契約法",
    },
    "GB": {
        "severance_notice_days": 45,
        "severance_pay_months": 0.5,
        "union_coverage_pct": 23.0,
        "ai_regulation": "AI Safety Institute (2024)",
        "data_regulation": "UK GDPR",
        "labor_flexibility": "중간",
        "firing_cost_multiplier": 1.4,
        "epl_score": 1.6,
        "outplacement_rate": 0.10,
        "source": "OECD EPL Index 2024, Employment Rights Act 1996",
    },
    "FR": {
        "severance_notice_days": 60,
        "severance_pay_months": 1,
        "union_coverage_pct": 11.0,
        "ai_regulation": "EU AI Act (2024)",
        "data_regulation": "GDPR / CNIL",
        "labor_flexibility": "낮음",
        "firing_cost_multiplier": 2.2,
        "epl_score": 2.6,
        "outplacement_rate": 0.12,
        "source": "OECD EPL Index 2024, Code du travail",
    },
}


def adjust_for_regulatory_cost(
    labor_saving: float,
    country: str,
    displaced_headcount: float,
    avg_salary: float,
    avg_tenure_years: float = 5.0,
) -> dict:
    """
    국가별 규제 비용 반영 → 실질 순절감액 산출

    Returns:
        gross_saving, severance_cost, outplacement_cost, net_saving,
        regulatory_burden_pct
    """
    reg = REGULATORY_CONTEXT.get(country, REGULATORY_CONTEXT["US"])

    # 퇴직금 (근속년수 비례)
    severance = (
        displaced_headcount
        * avg_salary
        * reg["severance_pay_months"]
        / 12.0
        * avg_tenure_years
    )

    # 재취업 지원 비용
    outplacement = displaced_headcount * avg_salary * reg["outplacement_rate"]

    net_saving = labor_saving - severance - outplacement
    burden_pct = (
        (severance + outplacement) / labor_saving * 100.0
        if labor_saving > 0
        else 0.0
    )

    return {
        "gross_saving":          round(labor_saving, 3),
        "severance_cost":        round(severance, 3),
        "outplacement_cost":     round(outplacement, 3),
        "net_saving":            round(net_saving, 3),
        "regulatory_burden_pct": round(burden_pct, 1),
        "epl_score":             reg["epl_score"],
        "source":                reg["source"],
    }
