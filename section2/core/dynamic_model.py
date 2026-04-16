"""
section2/core/dynamic_model.py
η(t) 3단계 회복 경로 + 동적 파생 변수
논문 Section 4.6: η 상승 → ℓ 감소 → 격차 축소 → 피구세 자기소멸
"""

from __future__ import annotations
import numpy as np
from section2.core.paper_model import ModelParams, compute_externality

SCENARIOS = ["optimistic", "baseline", "pessimistic"]

SHOCK_FACTOR   = {"optimistic": 0.5, "baseline": 1.0, "pessimistic": 1.5}
RECOVERY_SPEED = {"optimistic": 0.8, "baseline": 0.4, "pessimistic": 0.15}
ETA_INF_RATIO  = {"optimistic": 1.3, "baseline": 1.1, "pessimistic": 0.9}


def dynamic_eta(t: float, eta_0: float, scenario: str) -> float:
    """
    3단계 η(t) 회복 경로

    Phase 1 (0~1년):  충격기 — 해고 발생, η 일시 하락
    Phase 2 (1~4년):  적응기 — 재교육/재취업, S커브 회복
    Phase 3 (4년~):   신균형 — 새 직종 정착, η 수렴

    시나리오별:
    - optimistic:  빠른 회복 (Acemoglu & Restrepo 2019 역사적 사례)
    - baseline:    표준 S커브
    - pessimistic: 더딘 회복 (Jacobson et al. 1993: 지속적 임금 손실)
    """
    shock = SHOCK_FACTOR[scenario]
    speed = RECOVERY_SPEED[scenario]
    ratio = ETA_INF_RATIO[scenario]
    eta_inf = min(eta_0 * ratio, 0.8)

    if t <= 1.0:
        return max(0.0, eta_0 - 0.05 * shock * t)
    elif t <= 4.0:
        return eta_0 + (eta_inf - eta_0) * (1 - np.exp(-speed * (t - 1.0)))
    else:
        return eta_inf


def compute_dynamic_paths(
    years: np.ndarray,
    eta_0: float,
    base_params: ModelParams,
    scenarios: list[str] | None = None,
) -> dict[str, dict]:
    """
    η(t) → ℓ(t) → αNE(t) → αCO(t) → wedge(t) → τ*(t) 전체 경로

    Args:
        years:       시간 배열 (예: np.linspace(0, 10, 100))
        eta_0:       초기 소득 대체율
        base_params: 고정 파라미터 (eta는 덮어씀)
        scenarios:   계산할 시나리오 목록 (기본: 전체 3개)

    Returns:
        {scenario: {eta, ell, alpha_NE, alpha_CO, wedge, tau_star, D_ratio}}
    """
    if scenarios is None:
        scenarios = SCENARIOS

    results: dict[str, dict] = {}
    for sc in scenarios:
        eta_path  = [dynamic_eta(t, eta_0, sc) for t in years]
        ell_path  = [base_params.lambda_ * (1 - eta) * base_params.w for eta in eta_path]

        alpha_NE_path, alpha_CO_path, tau_path, D_ratio_path = [], [], [], []
        for eta, ell in zip(eta_path, ell_path):
            p = ModelParams(
                lambda_=base_params.lambda_,
                eta=eta,
                w=base_params.w,
                c=base_params.c,
                k=base_params.k,
                N=base_params.N,
                A=base_params.A,
                L=base_params.L,
                alpha_bar=base_params.alpha_bar,
            )
            ext = compute_externality(base_params.alpha_bar, p)
            alpha_NE_path.append(ext.alpha_NE)
            alpha_CO_path.append(ext.alpha_CO)
            tau_path.append(ext.tau_star)
            D_ratio_path.append(ext.D_current / ext.D_baseline if ext.D_baseline > 0 else 1.0)

        results[sc] = {
            "eta":       eta_path,
            "ell":       ell_path,
            "alpha_NE":  alpha_NE_path,
            "alpha_CO":  alpha_CO_path,
            "wedge":     [ne - co for ne, co in zip(alpha_NE_path, alpha_CO_path)],
            "tau_star":  tau_path,
            "D_ratio":   D_ratio_path,   # D(t) / D_baseline
        }

    return results
