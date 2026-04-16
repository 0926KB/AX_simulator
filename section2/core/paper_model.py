"""
section2/core/paper_model.py
Hemenway Falk & Tsoukalas (2026), "The AI Layoff Trap" — 논문 수식 계산 엔진

LLM 없음. 알고리즘 전용.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class ModelParams:
    """논문 모델 파라미터"""
    lambda_: float      # 소비성향 (0~1)
    eta: float          # 소득 대체율 (0~1)
    w: float            # 태스크당 임금 (억원)
    c: float            # 태스크당 AI 비용 (억원)
    k: float            # 마찰 계수
    N: int              # 시장 내 경쟁사 수
    A: float            # 자율 수요 (억원)
    L: float            # 기업당 총 노동자 수
    alpha_bar: float = 0.0  # 시장 평균 자동화율


@dataclass
class ExternalityResult:
    ell: float            # 태스크당 실효 수요 손실 = λ(1−η)w
    s: float              # 태스크당 절약액 = w − c
    N_star: float         # 자동화 임계 경쟁사 수 = ℓ/s
    alpha_NE: float       # Nash 균형 자동화율
    alpha_CO: float       # 협력 최적 자동화율
    wedge: float          # 과잉 자동화 격차 = αNE − αCO
    tau_star: float       # 피구세 최적값 = ℓ(1−1/N)
    D_current: float      # 현재 총수요
    D_baseline: float     # 자동화 없을 때 총수요
    demand_loss: float    # 수요 손실
    demand_loss_pct: float


def compute_externality(alpha_bar: float, params: ModelParams) -> ExternalityResult:
    """
    논문 Section 2~3 핵심 수식

    ℓ = λ(1−η)w
    s = w − c
    αNE = (s − ℓ/N) / k      N > N* 일 때
    αCO = (s − ℓ) / k
    wedge = αNE − αCO = ℓ(1−1/N)/k
    D(ᾱ) = A + λwLN[1 − (1−η)ᾱ]
    """
    lam = params.lambda_
    eta = params.eta
    w, c, k = params.w, params.c, params.k
    N, A, L = params.N, params.A, params.L

    s = w - c
    ell = lam * (1.0 - eta) * w
    N_star = ell / s if s > 0 else float("inf")

    alpha_NE = (
        max(0.0, min(1.0, (s - ell / N) / k))
        if N > N_star and s > 0
        else 0.0
    )
    alpha_CO = max(0.0, min(1.0, (s - ell) / k)) if s > ell else 0.0
    wedge = max(0.0, alpha_NE - alpha_CO)
    tau_star = ell * (1.0 - 1.0 / N) if N > 0 else 0.0

    D_baseline = A + lam * w * L * N
    D_current = A + lam * w * L * N * (1.0 - (1.0 - eta) * alpha_bar)
    demand_loss = D_baseline - D_current
    demand_loss_pct = demand_loss / D_baseline * 100.0 if D_baseline > 0 else 0.0

    return ExternalityResult(
        ell=round(ell, 6),
        s=round(s, 6),
        N_star=round(N_star, 4),
        alpha_NE=round(alpha_NE, 6),
        alpha_CO=round(alpha_CO, 6),
        wedge=round(wedge, 6),
        tau_star=round(tau_star, 6),
        D_current=round(D_current, 4),
        D_baseline=round(D_baseline, 4),
        demand_loss=round(demand_loss, 4),
        demand_loss_pct=round(demand_loss_pct, 4),
    )


def scenario_comparison(company_alpha: float, params: ModelParams) -> dict:
    """
    시나리오 A (이 기업만 도입) vs B (업계 전체 동시 도입)
    자사 매출 영향 범위(range) 반환
    """
    # A: 시장 평균 = company_alpha / N (이 기업만)
    p_A = ModelParams(**{**params.__dict__, "alpha_bar": company_alpha / max(params.N, 1)})
    r_A = compute_externality(company_alpha / max(params.N, 1), p_A)

    # B: 시장 평균 = company_alpha (업계 전체 동시)
    p_B = ModelParams(**{**params.__dict__, "alpha_bar": company_alpha})
    r_B = compute_externality(company_alpha, p_B)

    rev_optimistic  = r_A.demand_loss / params.N
    rev_pessimistic = r_B.demand_loss / params.N

    return {
        "scenario_A": r_A,
        "scenario_B": r_B,
        "revenue_impact_optimistic":  round(rev_optimistic, 4),
        "revenue_impact_pessimistic": round(rev_pessimistic, 4),
        "revenue_impact_range":       (round(rev_optimistic, 4), round(rev_pessimistic, 4)),
    }


def compute_pigouvian_tax(
    tau: float,
    params: ModelParams,
    total_automated_tasks: float,
) -> dict:
    """
    논문 Proposition 5: τ* = ℓ(1−1/N)
    세금 부과 후 Nash 균형 자동화율 및 격차 변화
    """
    ext = compute_externality(params.alpha_bar, params)
    k, ell, N = params.k, ext.ell, params.N

    alpha_NE_taxed = max(0.0, min(1.0,
        (ext.s - tau - ell / N) / k if k > 0 else 0.0
    ))
    wedge_after = max(0.0, alpha_NE_taxed - ext.alpha_CO)
    gap_closed_pct = (
        (1.0 - wedge_after / ext.wedge) * 100.0
        if ext.wedge > 1e-9 else 100.0
    )

    return {
        "tau_star":           round(ext.tau_star, 6),
        "tau_applied":        round(tau, 6),
        "tax_burden_annual":  round(tau * total_automated_tasks, 4),
        "alpha_NE_original":  round(ext.alpha_NE, 6),
        "alpha_NE_taxed":     round(alpha_NE_taxed, 6),
        "alpha_CO":           round(ext.alpha_CO, 6),
        "wedge_original":     round(ext.wedge, 6),
        "wedge_after":        round(wedge_after, 6),
        "gap_closed_pct":     round(gap_closed_pct, 2),
    }


def check_externality_alerts(result: ExternalityResult, params: ModelParams) -> list[dict]:
    """외부효과 경보 시스템"""
    alerts = []

    if result.wedge > 0.20:
        alerts.append({
            "level":   "WARNING",
            "message": f"과잉 자동화 격차 {result.wedge:.3f} > 임계치 0.20",
            "detail":  f"협력 최적 대비 {result.wedge / max(result.alpha_CO, 0.001) * 100:.0f}% 초과 자동화",
        })

    if params.N > result.N_star:
        alerts.append({
            "level":   "INFO",
            "message": f"N={params.N} > N*={result.N_star:.1f}: 자동화 게임 활성",
            "detail":  "경쟁사 수가 임계치 초과. 과잉 자동화 압력 존재.",
        })

    if result.demand_loss_pct > 5.0:
        alerts.append({
            "level":   "DANGER",
            "message": f"수요 파괴 {result.demand_loss_pct:.1f}% — 피구세 도입 검토 필요",
            "detail":  "업계 전체 동시 도입 시 자사 매출 역풍 주의",
        })

    return alerts
