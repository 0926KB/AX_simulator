"""
section2/core/policy_engine.py
논문 Table 1 — 6가지 정책 수단 효과 비교 + 피구세 최적화
"""

from __future__ import annotations
import numpy as np
from section2.core.paper_model import ModelParams, compute_externality, compute_pigouvian_tax


# 논문 Table 1 정책 수단 정의
POLICY_INSTRUMENTS: list[dict] = [
    {
        "id":           "upskilling",
        "name":         "업스킬링/재훈련 (η↑)",
        "N_star_change": True,
        "wedge_change":  "부분 감소",
        "externality":   "부분 해소",
        "mechanism":     "η 상승 → ℓ 감소 → N* 상승 → 자동화 압력 완화",
        "paper_section": "Proposition 7",
    },
    {
        "id":           "ubi",
        "name":         "UBI (A↑)",
        "N_star_change": False,
        "wedge_change":  "불변",
        "externality":   "미해소",
        "mechanism":     "수요 증가하나 격차 구조 변화 없음",
        "paper_section": "Proposition 6",
    },
    {
        "id":           "capital_tax",
        "name":         "자본소득세 (t)",
        "N_star_change": False,
        "wedge_change":  "불변",
        "externality":   "미해소",
        "mechanism":     "s 감소하나 ℓ/s 비율 불변 → 격차 그대로",
        "paper_section": "Proposition 8",
    },
    {
        "id":           "worker_equity",
        "name":         "노동자 지분 (ε)",
        "N_star_change": True,
        "wedge_change":  "부분 감소",
        "externality":   "부분 해소",
        "mechanism":     "노동자가 이익 일부 수취 → 수요 손실 내재화",
        "paper_section": "Proposition 9",
    },
    {
        "id":           "coase_coalition",
        "name":         "코즈 연합 (M<N)",
        "N_star_change": False,
        "wedge_change":  "부분 감소",
        "externality":   "미해소",
        "mechanism":     "카르텔 수준으로 자동화 억제, 사회적 최적 미달",
        "paper_section": "Proposition 4",
    },
    {
        "id":           "pigouvian_tax",
        "name":         "피구세 (τ*) ★",
        "N_star_change": True,
        "wedge_change":  "완전 제거",
        "externality":   "완전 해소",
        "mechanism":     "τ* = ℓ(1−1/N) → αNE = αCO → 사회적 최적 달성",
        "paper_section": "Proposition 5",
    },
]


def compare_policies(
    params: ModelParams,
    total_automated_tasks: float,
    eta_increase: float = 0.10,
    capital_tax_rate: float = 0.10,
    worker_equity_share: float = 0.20,
) -> list[dict]:
    """
    6가지 정책 수단 효과 비교

    각 정책별 αNE, αCO, wedge, demand_loss_pct 반환
    """
    baseline = compute_externality(params.alpha_bar, params)
    results  = []

    for policy in POLICY_INSTRUMENTS:
        p_mod = ModelParams(
            lambda_=params.lambda_,
            eta=params.eta,
            w=params.w,
            c=params.c,
            k=params.k,
            N=params.N,
            A=params.A,
            L=params.L,
            alpha_bar=params.alpha_bar,
        )

        if policy["id"] == "upskilling":
            p_mod.eta = min(params.eta + eta_increase, 0.95)

        elif policy["id"] == "ubi":
            p_mod.A = params.A * 1.20   # 20% 수요 증가 시나리오

        elif policy["id"] == "capital_tax":
            p_mod.c = params.c * (1 + capital_tax_rate)

        elif policy["id"] == "worker_equity":
            # 노동자 지분 ε → 실효 수요 손실 감소 (η 등가 상승)
            effective_eta = min(params.eta + worker_equity_share * (1 - params.eta), 0.95)
            p_mod.eta = effective_eta

        elif policy["id"] == "coase_coalition":
            # M=2 카르텔 (N을 유효 경쟁 수로 축소)
            p_mod.N = max(2, params.N // 2)

        elif policy["id"] == "pigouvian_tax":
            tau_result = compute_pigouvian_tax(baseline.tau_star, params, total_automated_tasks)
            results.append({
                **policy,
                "alpha_NE":       tau_result["alpha_NE_taxed"],
                "alpha_CO":       tau_result["alpha_CO"],
                "wedge":          tau_result["wedge_after"],
                "gap_closed_pct": tau_result["gap_closed_pct"],
                "demand_loss_pct": baseline.demand_loss_pct,  # 피구세는 수요 회복 별도
                "tau_burden":     tau_result["tax_burden_annual"],
            })
            continue

        ext = compute_externality(p_mod.alpha_bar, p_mod)
        gap_closed = (
            (1 - ext.wedge / baseline.wedge) * 100
            if baseline.wedge > 1e-9 else 100.0
        )

        results.append({
            **policy,
            "alpha_NE":       ext.alpha_NE,
            "alpha_CO":       ext.alpha_CO,
            "wedge":          ext.wedge,
            "gap_closed_pct": round(gap_closed, 1),
            "demand_loss_pct": ext.demand_loss_pct,
            "tau_burden":     0.0,
        })

    return results


def find_optimal_tau(
    params: ModelParams,
    total_automated_tasks: float,
    tolerance: float = 1e-4,
) -> dict:
    """
    피구세 최적값 τ* 도출 및 효과 요약
    """
    ext      = compute_externality(params.alpha_bar, params)
    tau_star = ext.tau_star
    result   = compute_pigouvian_tax(tau_star, params, total_automated_tasks)

    return {
        "tau_star":             round(tau_star, 6),
        "alpha_NE_before":      round(ext.alpha_NE, 6),
        "alpha_NE_after":       round(result["alpha_NE_taxed"], 6),
        "alpha_CO":             round(ext.alpha_CO, 6),
        "wedge_before":         round(ext.wedge, 6),
        "wedge_after":          round(result["wedge_after"], 6),
        "gap_closed_pct":       round(result["gap_closed_pct"], 1),
        "annual_tax_burden":    round(result["tax_burden_annual"], 3),
        "ell":                  round(ext.ell, 6),
        "N_star":               round(ext.N_star, 2),
        "paper_formula":        "τ* = ℓ(1−1/N) = λ(1−η)w × (1−1/N)",
        "source":               "Hemenway Falk & Tsoukalas 2026, Proposition 5",
    }
