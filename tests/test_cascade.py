"""
tests/test_cascade.py
D-015 — 부서간 연쇄 효과 테스트
"""
import pytest
from shared.data.cascade_survey import survey_to_coefficient, label_to_values
from shared.data.cascade_engine import compute_cascade_effects, cascade_summary


# ─────────────────────────────────────────────────────────
# 테스트 픽스처
# ─────────────────────────────────────────────────────────

DEPARTMENTS = [
    {"dept_name": "고객서비스(CS)", "headcount": 50, "alpha": 0.65, "avg_salary": 0.4},
    {"dept_name": "HR",             "headcount": 20, "alpha": 0.0,  "avg_salary": 0.5},
    {"dept_name": "엔지니어링/개발","headcount": 80, "alpha": 0.3,  "avg_salary": 0.8},
]

PAIRS_NORMAL = [
    {"from_dept": "고객서비스(CS)", "to_dept": "HR",
     "coefficient": -0.10, "annual_factor": 0.50},
    {"from_dept": "고객서비스(CS)", "to_dept": "엔지니어링/개발",
     "coefficient": +0.08, "annual_factor": 1.00},
]


# ─────────────────────────────────────────────────────────
# 설문 계수 변환 테스트
# ─────────────────────────────────────────────────────────

class TestSurveyToCoefficient:
    def test_decrease_basic(self):
        coeff = survey_to_coefficient(0.10, "decrease", 0.50)
        assert coeff["coefficient"] == -0.10
        assert coeff["annual_factor"] == 0.50
        assert coeff["is_estimated"] is True

    def test_increase_basic(self):
        coeff = survey_to_coefficient(0.22, "increase", 1.00)
        assert coeff["coefficient"] == 0.22
        assert coeff["annual_factor"] == 1.00

    def test_neutral_returns_zero(self):
        coeff = survey_to_coefficient(0.10, "neutral", 1.00)
        assert coeff["coefficient"] == 0.0
        assert coeff["annual_factor"] == 0.0

    def test_zero_support_returns_zero(self):
        coeff = survey_to_coefficient(0.0, "decrease", 0.50)
        assert coeff["coefficient"] == 0.0

    def test_transition_capped_at_1(self):
        # transition_period=1.50 → annual_factor=1.0 (cap)
        coeff = survey_to_coefficient(0.10, "decrease", 1.50)
        assert coeff["annual_factor"] == 1.0

    def test_label_to_values_roundtrip(self):
        sr, direction, tp = label_to_values("5~15%", "감소 (지원 수요 줄어듦)", "단기 (3~6개월)")
        assert sr == 0.10
        assert direction == "decrease"
        assert tp == 0.50


# ─────────────────────────────────────────────────────────
# 연쇄 효과 계산 테스트
# ─────────────────────────────────────────────────────────

class TestCascadeEngine:
    def test_hr_decreases(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        hr = next(r for r in results if r["dept_name"] == "HR")
        assert hr["cascade_change"] < 0, "HR 인원은 감소해야 함"

    def test_hr_direct_displaced_zero(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        hr = next(r for r in results if r["dept_name"] == "HR")
        assert hr["direct_displaced"] == 0.0, "HR은 직접 자동화 없음"

    def test_engineering_increases(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        eng = next(r for r in results if r["dept_name"] == "엔지니어링/개발")
        assert eng["cascade_change"] > 0, "IT 인원은 증가해야 함"

    def test_cascade_cap_30pct(self):
        """상한: to_dept 인원의 30% 초과 불가"""
        extreme_pair = [{"from_dept": "고객서비스(CS)", "to_dept": "HR",
                         "coefficient": -0.99, "annual_factor": 1.0}]
        results = compute_cascade_effects(DEPARTMENTS, extreme_pair)
        hr = next(r for r in results if r["dept_name"] == "HR")
        # HR 20명의 30% = 6명
        assert abs(hr["cascade_change"]) <= 20 * 0.30 + 1e-6

    def test_cs_has_no_cascade_from_itself(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        cs = next(r for r in results if r["dept_name"] == "고객서비스(CS)")
        assert cs["cascade_change"] == 0.0

    def test_net_headcount_equals_direct_plus_cascade(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        for r in results:
            expected = round(r["direct_displaced"] + r["cascade_change"], 2)
            assert abs(r["net_headcount_change"] - expected) < 1e-6

    def test_labor_cost_change_sign(self):
        """인건비 변화: 인원 감소 → 음수 (절감)"""
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        hr = next(r for r in results if r["dept_name"] == "HR")
        # HR cascade < 0 → net_headcount_change < 0 → net_labor_cost_change < 0
        assert hr["net_labor_cost_change"] < 0

    def test_empty_pairs(self):
        """부서 쌍 없으면 연쇄 효과 없음"""
        results = compute_cascade_effects(DEPARTMENTS, [])
        for r in results:
            assert r["cascade_change"] == 0.0

    def test_unknown_dept_ignored(self):
        """존재하지 않는 부서 쌍은 조용히 무시"""
        bad_pair = [{"from_dept": "없는부서", "to_dept": "HR",
                     "coefficient": -0.10, "annual_factor": 1.0}]
        results = compute_cascade_effects(DEPARTMENTS, bad_pair)
        hr = next(r for r in results if r["dept_name"] == "HR")
        assert hr["cascade_change"] == 0.0

    def test_cascade_value_correctness(self):
        """CS 65% 자동화 → 32.5명 해고 → HR 연쇄 = 32.5 × -0.10 × 0.50 = -1.625명
        cascade_change는 round(..., 2) 저장이므로 허용 오차 0.005"""
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        hr = next(r for r in results if r["dept_name"] == "HR")
        expected = 50 * 0.65 * (-0.10) * 0.50  # = -1.625
        assert abs(hr["cascade_change"] - expected) < 0.005


# ─────────────────────────────────────────────────────────
# 연쇄 효과 요약 테스트
# ─────────────────────────────────────────────────────────

class TestCascadeSummary:
    def test_summary_fields_exist(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        summary = cascade_summary(results, DEPARTMENTS)
        for key in ("total_direct_displaced", "total_cascade_change",
                    "total_net_change", "total_additional_labor_cost", "affected_depts"):
            assert key in summary

    def test_affected_depts_nonempty(self):
        results = compute_cascade_effects(DEPARTMENTS, PAIRS_NORMAL)
        summary = cascade_summary(results, DEPARTMENTS)
        assert len(summary["affected_depts"]) >= 2  # HR, 엔지니어링 영향
