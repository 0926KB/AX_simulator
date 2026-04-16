"""
section1/core/roi_engine.py
Layer 1: 부서별 내부 ROI / NPV
Layer 2: 선형 P&L 프로젝션 (3년/5년)
"""

from __future__ import annotations
import pandas as pd
from shared.data.presets import estimate_opex


# ─────────────────────────────────────────────────────────
# Layer 1 — 부서별 내부 ROI
# ─────────────────────────────────────────────────────────

def compute_internal_roi(dept: dict, alpha: float, phi: float = 1.0) -> dict:
    """
    논문 Section 2 + 5.1 기반

    Args:
        dept:  {headcount, avg_salary, capex_total, annual_opex, type}
        alpha: 자동화율 (0~1)
        phi:   AI 생산성 배수 (1.0 = 생산성 이득 없음)

    Returns:
        displaced_headcount, labor_saving_annual, productivity_gain,
        total_saving_annual, npv_5yr, payback_years, roi_pct
    """
    headcount  = dept["headcount"]
    avg_salary = dept["avg_salary"]

    displaced       = headcount * alpha
    labor_saving    = displaced * avg_salary

    if phi > 1.0:
        remaining = headcount * (1 - alpha)
        # 생산성 이득의 30%만 비용 절감으로 전환 (실증 보수 추정)
        productivity_gain = remaining * avg_salary * (phi - 1.0) * 0.3
    else:
        productivity_gain = 0.0

    total_saving = labor_saving + productivity_gain
    capex        = dept.get("capex_total", 0.0)
    opex         = dept.get("annual_opex", 0.0)

    net_annual = total_saving - opex
    discount_rate = 0.10
    npv = sum(
        net_annual / (1 + discount_rate) ** t for t in range(1, 6)
    ) - capex

    payback = capex / net_annual if net_annual > 0 else float("inf")
    roi_pct = npv / capex * 100 if capex > 0 else 0.0

    return {
        "displaced_headcount":   round(displaced, 1),
        "labor_saving_annual":   round(labor_saving, 3),
        "productivity_gain":     round(productivity_gain, 3),
        "total_saving_annual":   round(total_saving, 3),
        "capex":                 round(capex, 3),
        "annual_opex":           round(opex, 3),
        "net_annual":            round(net_annual, 3),
        "npv_5yr":               round(npv, 3),
        "payback_years":         round(payback, 2),
        "roi_pct":               round(roi_pct, 1),
    }


# ─────────────────────────────────────────────────────────
# Layer 2 — 선형 P&L 프로젝션
# ─────────────────────────────────────────────────────────

def linear_projection(
    base_financials: dict,
    dept_results: list[dict],
    adoption_schedule: dict[int, float],
) -> pd.DataFrame:
    """
    연도별 P&L 프로젝션

    Args:
        base_financials: {revenue, op_margin}
        dept_results:    부서 목록 [{headcount, avg_salary, capex_total, type, ...}]
        adoption_schedule: {year: alpha} 예) {1: 0.3, 2: 0.6, 3: 0.8}

    Returns:
        DataFrame: year, alpha, labor_saving, ai_opex, net_cost_saving,
                   operating_profit (외부효과 역풍 미포함 — Section 2에서 별도 계산)
    """
    rows = []
    for year, alpha_year in sorted(adoption_schedule.items()):
        total_saving = sum(
            d["avg_salary"] * d["headcount"] * alpha_year
            for d in dept_results
        )
        total_opex = sum(
            estimate_opex(d, alpha_year)["total_opex"]
            for d in dept_results
        )
        net_saving = total_saving - total_opex
        base_op_profit = base_financials["revenue"] * base_financials["op_margin"]

        rows.append({
            "year":             year,
            "alpha":            alpha_year,
            "labor_saving":     round(total_saving, 3),
            "ai_opex":          round(total_opex, 3),
            "net_cost_saving":  round(net_saving, 3),
            "operating_profit": round(base_op_profit + net_saving, 3),
        })

    return pd.DataFrame(rows)


def compute_internal_roi_with_cascade(
    dept: dict,
    alpha: float,
    cascade_result: dict | None = None,
    phi: float = 1.0,
) -> dict:
    """
    기존 compute_internal_roi()에 연쇄 효과 추가 반영.

    cascade_result가 None이면 기존 방식과 동일 (하위 호환).

    Args:
        dept:           부서 딕셔너리
        alpha:          자동화율
        cascade_result: compute_cascade_effects() 출력 중 해당 부서 항목
        phi:            AI 생산성 배수

    Returns:
        compute_internal_roi() 결과 + cascade 관련 필드
    """
    base = compute_internal_roi(dept, alpha, phi)

    if cascade_result is None:
        return {**base, "cascade_applied": False}

    cascade_labor   = cascade_result.get("net_labor_cost_change", 0.0)
    cascade_hdcount = cascade_result.get("cascade_change", 0.0)

    # 연쇄 효과로 인한 순 절감 조정
    # cascade_labor: 양수 = 추가 인원(비용 증가), 음수 = 추가 절감
    adjusted_saving = base["total_saving_annual"] - cascade_labor

    # cascade 적용 NPV 재계산
    capex         = base["capex"]
    opex          = base["annual_opex"]
    discount_rate = 0.10
    net_annual_c  = adjusted_saving - opex
    npv_cascade   = sum(
        net_annual_c / (1 + discount_rate) ** t for t in range(1, 6)
    ) - capex

    return {
        **base,
        "cascade_headcount_change":   round(cascade_hdcount, 2),
        "cascade_labor_impact":       round(cascade_labor, 3),
        "total_saving_with_cascade":  round(adjusted_saving, 3),
        "npv_5yr_with_cascade":       round(npv_cascade, 3),
        "cascade_applied":            True,
    }


def priority_matrix(dept_roi_list: list[dict]) -> list[dict]:
    """
    부서별 우선순위 매트릭스 분류
    x축: AI 준비도 (1-k 역수), y축: NPV 기준 ROI

    Returns:
        각 부서에 quadrant 필드 추가된 리스트
    """
    if not dept_roi_list:
        return []

    npv_values = [d["roi"]["npv_5yr"] for d in dept_roi_list]
    k_values   = [d["k"] for d in dept_roi_list]

    npv_median = sorted(npv_values)[len(npv_values) // 2]
    k_median   = sorted(k_values)[len(k_values) // 2]

    result = []
    for d in dept_roi_list:
        npv_high = d["roi"]["npv_5yr"] >= npv_median
        k_low    = d["k"] <= k_median

        if npv_high and k_low:
            quadrant = "즉시 도입"
        elif npv_high and not k_low:
            quadrant = "전략적 도입"
        elif not npv_high and k_low:
            quadrant = "준비 후 도입"
        else:
            quadrant = "재고 필요"

        result.append({**d, "quadrant": quadrant})

    return result
