"""
tests/test_paper_model.py
논문 수식 단위 테스트
정확도 요구: aNE - aCO == ell*(1-1/N)/k  오차 < 1e-6
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from section2.core.paper_model import (
    compute_externality, ModelParams, compute_pigouvian_tax, scenario_comparison
)


def base_params(**ov) -> ModelParams:
    d = dict(lambda_=0.48, eta=0.35, w=0.5, c=0.1, k=1.0,
             N=7, A=10.0, L=100.0, alpha_bar=0.0)
    d.update(ov)
    return ModelParams(**d)


class TestFormulas:
    def test_ell(self):
        p = base_params(lambda_=0.48, eta=0.35, w=0.5)
        r = compute_externality(0.0, p)
        assert abs(r.ell - 0.48 * 0.65 * 0.5) < 1e-9

    def test_s(self):
        p = base_params(w=0.5, c=0.1)
        r = compute_externality(0.0, p)
        assert abs(r.s - 0.4) < 1e-9

    def test_wedge_core(self):
        """핵심: wedge = ell*(1-1/N)/k, 오차 < 1e-6"""
        p = base_params(N=7, k=1.0)
        r = compute_externality(0.5, p)
        if p.N > r.N_star:
            expected = r.ell * (1.0 - 1.0 / 7) / p.k
            assert abs(r.wedge - expected) < 1e-6, f"wedge={r.wedge}, expected={expected}"

    def test_alpha_NE_clipped(self):
        p = base_params(k=0.01)
        r = compute_externality(0.0, p)
        assert 0.0 <= r.alpha_NE <= 1.0

    def test_alpha_CO_le_NE(self):
        p = base_params(N=10)
        r = compute_externality(0.0, p)
        assert r.alpha_CO <= r.alpha_NE + 1e-9

    def test_wedge_nonneg(self):
        assert compute_externality(0.0, base_params()).wedge >= 0.0

    def test_demand_drops_with_automation(self):
        p = base_params()
        assert compute_externality(0.5, p).D_current < compute_externality(0.0, p).D_current

    def test_demand_at_zero_automation(self):
        r = compute_externality(0.0, base_params())
        assert abs(r.D_current - r.D_baseline) < 1e-9

    def test_N_star(self):
        r = compute_externality(0.0, base_params())
        assert abs(r.N_star - r.ell / r.s) < 1e-9

    def test_tau_star(self):
        p = base_params(N=7)
        r = compute_externality(0.0, p)
        # ell은 round(6) 저장값이므로 허용 오차 1e-6 적용
        assert abs(r.tau_star - r.ell * (1.0 - 1.0 / 7)) < 1e-6

    def test_no_automation_below_N_star(self):
        p = base_params(lambda_=0.99, eta=0.01, w=0.5, c=0.1, N=1)
        r = compute_externality(0.0, p)
        if p.N <= r.N_star:
            assert r.alpha_NE == 0.0

    def test_demand_loss_pct_range(self):
        r = compute_externality(0.8, base_params())
        assert 0.0 <= r.demand_loss_pct <= 100.0


class TestPigouvianTax:
    def test_tax_reduces_alpha_NE(self):
        p = base_params()
        result = compute_pigouvian_tax(0.1, p, 100.0)
        assert result["alpha_NE_taxed"] <= result["alpha_NE_original"] + 1e-9

    def test_tau_star_closes_gap(self):
        p = base_params()
        from section2.core.paper_model import compute_externality
        ext = compute_externality(0.0, p)
        result = compute_pigouvian_tax(ext.tau_star, p, 100.0)
        assert result["gap_closed_pct"] >= 99.0

    def test_zero_tax_no_change(self):
        p = base_params()
        result = compute_pigouvian_tax(0.0, p, 100.0)
        assert abs(result["alpha_NE_original"] - result["alpha_NE_taxed"]) < 1e-9


class TestScenarioComparison:
    def test_pessimistic_ge_optimistic(self):
        p = base_params(N=7)
        result = scenario_comparison(0.5, p)
        assert result["revenue_impact_pessimistic"] >= result["revenue_impact_optimistic"] - 1e-9

    def test_range_nonneg(self):
        result = scenario_comparison(0.5, base_params())
        lo, hi = result["revenue_impact_range"]
        assert lo >= 0.0 and hi >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
