"""
shared/data/impact_coefficients.py
Layer 3 기업 파급효과 계수 테이블

채널 1: CAR (투자자/주가)   — Eshghi & Astvansh 2024
채널 2: Survivor Syndrome   — LeadershipIQ n=4,172 / Work Institute 2023 / BLS JOLTS 2024
채널 3: 고객/브랜드 반응    — Twilio 2025 / Attest 2025 / Relyance 2025 / MindStudio 2026
채널 5: ESG 체크리스트      — MSCI / Sustainalytics 방법론 (정성)
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────
# 채널 1: 투자자/주가 반응 (CAR)
# Eshghi & Astvansh (2024), meta-analysis 34,594 layoff announcements
# ─────────────────────────────────────────────────────────

CAR_TABLE: dict[tuple, float] = {
    # (해고_명분, 업종_유형, 법체계) → 3~5일 CAR 추정값 (%)
    ("proactive", "tech",     "common_law"):  +0.5,
    ("proactive", "tech",     "civil_law"):   +0.2,
    ("proactive", "non_tech", "common_law"):   0.0,
    ("proactive", "non_tech", "civil_law"):   -0.3,
    ("reactive",  "tech",     "common_law"):  -1.0,
    ("reactive",  "tech",     "civil_law"):   -1.4,
    ("reactive",  "non_tech", "common_law"):  -1.4,
    ("reactive",  "non_tech", "civil_law"):   -1.8,
    # 전체 평균: -0.549%  (source: Eshghi & Astvansh 2024)
}

CAR_AI_BRANDING_BONUS = +0.8   # "AI 선도" 공시 시 보정값 (2024~2025 트렌드)
CAR_SIZE_PENALTY_RATE = 2.0    # 해고 비율 5% 초과분 × 2.0 페널티

LEGAL_SYSTEM: dict[str, str] = {
    "KR": "civil_law",
    "JP": "civil_law",
    "DE": "civil_law",
    "FR": "civil_law",
    "CN": "civil_law",
    "US": "common_law",
    "GB": "common_law",
    "IN": "common_law",
}


def compute_car(
    layoff_reason: str,
    is_tech: bool,
    country: str,
    layoff_pct: float,
    ai_branding: bool = False,
) -> dict:
    """
    CAR 추정 및 시가총액 영향 계산 (상장 기업 전용)

    Args:
        layoff_reason: "proactive" | "reactive"
        is_tech: 업종이 tech 계열인지
        country: 국가 코드
        layoff_pct: 전체 인력 대비 해고 비율 (0~1)
        ai_branding: "AI 선도" 프레이밍 여부

    Returns:
        car_pct (%), source, note
    """
    industry_type = "tech" if is_tech else "non_tech"
    legal = LEGAL_SYSTEM.get(country, "common_law")
    base_car = CAR_TABLE.get((layoff_reason, industry_type, legal), -0.5)

    if ai_branding:
        base_car += CAR_AI_BRANDING_BONUS

    size_penalty = max(0.0, (layoff_pct - 0.05) * CAR_SIZE_PENALTY_RATE)
    final_car = base_car - size_penalty

    return {
        "car_pct": round(final_car, 2),
        "base_car_pct": round(base_car, 2),
        "size_penalty_pct": round(size_penalty, 2),
        "source": "Eshghi & Astvansh 2024, meta-analysis n=34,594 / 78 studies",
        "note": "단기(3~5일) 누적 비정상 수익률 추정값. 장기(3년) 반응은 상반된 결과 존재.",
    }


# ─────────────────────────────────────────────────────────
# 채널 2: Survivor Syndrome
# LeadershipIQ n=4,172 / HBR meta-analysis / Work Institute 2023
# BLS JOLTS 2024 연간 자발적 이직률
# ─────────────────────────────────────────────────────────

VOLUNTARY_TURNOVER_BASELINE: dict[str, float] = {
    # BLS JOLTS 2024 연간 자발적 이직률
    "IT소프트웨어": 0.13,
    "금융보험":     0.11,
    "의료":         0.19,
    "제조":         0.14,
    "소매":         0.28,
    "컨설팅":       0.15,
    "기타":         0.15,
}

SURVIVOR_SYNDROME_COEFFICIENTS: dict[str, dict] = {
    # 해고 규모 구간 → 생산성/사기 하락률
    # source: LeadershipIQ n=4,172, HBR meta-analysis
    "small":  {"threshold": 0.05, "productivity_loss": 0.10, "morale_loss": 0.15},
    "medium": {"threshold": 0.15, "productivity_loss": 0.20, "morale_loss": 0.25},
    "large":  {"threshold": 1.00, "productivity_loss": 0.25, "morale_loss": 0.31},
}

TURNOVER_COST_RATE = 0.33       # 연봉의 33% — Work Institute 2023
TURNOVER_ELEVATION_FACTOR = 1.7 # 해고 후 1년 내 이직률 70% 상승


def compute_survivor_impact(
    remaining_headcount: float,
    avg_salary: float,
    layoff_pct: float,
    industry: str,
    tenure_years: float = 5.0,
) -> dict:
    """
    Survivor Syndrome 비용 계산

    Returns:
        productivity_loss_annual, turnover_risk_annual,
        total_hidden_cost, 각종 비율
    """
    if layoff_pct < 0.05:
        coeff = SURVIVOR_SYNDROME_COEFFICIENTS["small"]
    elif layoff_pct < 0.15:
        coeff = SURVIVOR_SYNDROME_COEFFICIENTS["medium"]
    else:
        coeff = SURVIVOR_SYNDROME_COEFFICIENTS["large"]

    productivity_loss_cost = remaining_headcount * avg_salary * coeff["productivity_loss"]

    base_turnover = VOLUNTARY_TURNOVER_BASELINE.get(industry, 0.15)
    elevated_turnover = base_turnover * TURNOVER_ELEVATION_FACTOR
    incremental_turnover = elevated_turnover - base_turnover
    turnover_risk_cost = (
        remaining_headcount * incremental_turnover * avg_salary * TURNOVER_COST_RATE
    )

    return {
        "productivity_loss_annual": round(productivity_loss_cost, 3),
        "productivity_loss_pct":    round(coeff["productivity_loss"] * 100, 1),
        "morale_loss_pct":          round(coeff["morale_loss"] * 100, 1),
        "turnover_risk_annual":     round(turnover_risk_cost, 3),
        "incremental_turnover_pct": round(incremental_turnover * 100, 1),
        "total_hidden_cost":        round(productivity_loss_cost + turnover_risk_cost, 3),
        "layoff_size_tier":         (
            "small" if layoff_pct < 0.05
            else "medium" if layoff_pct < 0.15
            else "large"
        ),
        "source": "LeadershipIQ n=4,172 / HBR meta-analysis / Work Institute 2023 / BLS JOLTS 2024",
    }


# ─────────────────────────────────────────────────────────
# 채널 3: 고객/브랜드 반응
# Twilio 2025, Attest 2025, Relyance 2025, MindStudio 2026
# ─────────────────────────────────────────────────────────

BRAND_IMPACT_TABLE: dict[tuple, float] = {
    # (기업_유형, 업종_유형, 공시_방식) → 연간 매출 대비 영향 비율
    ("B2C", "tech",     "ai_explicit"):  +0.005,
    ("B2C", "tech",     "silent"):       -0.005,
    ("B2C", "tech",     "restructuring"): -0.010,
    ("B2C", "non_tech", "ai_explicit"):  -0.015,
    ("B2C", "non_tech", "silent"):       -0.020,
    ("B2C", "non_tech", "restructuring"): -0.025,
    ("B2B", "tech",     "ai_explicit"):  +0.010,
    ("B2B", "tech",     "silent"):        0.000,
    ("B2B", "tech",     "restructuring"): -0.005,
    ("B2B", "non_tech", "ai_explicit"):  -0.005,
    ("B2B", "non_tech", "silent"):       -0.010,
    ("B2B", "non_tech", "restructuring"): -0.015,
}

BRAND_DISCLOSURE_OPTIONS = ["ai_explicit", "restructuring", "silent"]
BRAND_DISCLOSURE_LABELS = {
    "ai_explicit":   "AI 선도 공시 (AI 전환 명시)",
    "restructuring": "구조조정 공시 (일반적 발표)",
    "silent":        "조용한 감축 (공시 최소화)",
}


def compute_brand_impact(
    annual_revenue: float,
    biz_type: str,
    industry: str,
    disclosure_style: str,
    is_tech: bool,
) -> dict:
    """
    고객/브랜드 영향 계산

    Returns:
        revenue_impact_annual, impact_pct, direction, confidence
    """
    industry_type = "tech" if is_tech else "non_tech"
    bt = biz_type if biz_type in ("B2B", "B2C") else "B2C"
    key = (bt, industry_type, disclosure_style)
    coeff = BRAND_IMPACT_TABLE.get(key, -0.010)

    return {
        "revenue_impact_annual": round(annual_revenue * coeff, 3),
        "impact_pct":            round(coeff * 100, 2),
        "direction":             "positive" if coeff > 0 else ("neutral" if coeff == 0 else "negative"),
        "note":                  "1~3년 누적 영향 추정. 단기(6개월) 영향은 절반 적용 권장.",
        "source":                "Twilio 2025, Attest 2025, Relyance 2025, MindStudio 2026",
        "confidence":            "medium",
    }


# ─────────────────────────────────────────────────────────
# 채널 5: ESG / 공급망 반응 (정성적 체크리스트)
# MSCI, Sustainalytics 방법론 기반 — 무료 API 없어 정성 처리
# ─────────────────────────────────────────────────────────

ESG_RISK_CHECKLIST: list[dict] = [
    {
        "item":       "해고 인원 5% 초과 시 Sustainalytics S점수 하락 가능성",
        "threshold":  0.05,
        "applies_to": "global",
        "source":     "Sustainalytics ESG Risk Rating Methodology 2024",
    },
    {
        "item":       "AI 해고 공시 시 MSCI ESG Rating 재평가 트리거 가능",
        "threshold":  0.10,
        "applies_to": "global",
        "source":     "MSCI ESG Ratings Methodology 2024",
    },
    {
        "item":       "EU 공급망 ESG 실사 의무(CSDD) 해당 시 추가 보고 필요",
        "threshold":  None,
        "applies_to": ["DE", "FR"],
        "source":     "EU Corporate Sustainability Due Diligence Directive 2024",
    },
    {
        "item":       "SBTi/CDP 참여 기업은 인력 감축 공시 의무 검토 필요",
        "threshold":  None,
        "applies_to": "global",
        "source":     "SBTi Corporate Manual 2024",
    },
    {
        "item":       "B2B 고객사의 공급망 ESG 기준 충족 여부 사전 확인 필요",
        "threshold":  None,
        "applies_to": "B2B",
        "source":     "공급망 ESG 일반 관행",
    },
]


def get_esg_alerts(layoff_pct: float, country: str, biz_type: str) -> list[dict]:
    """해당 조건에 맞는 ESG 체크리스트 항목 반환"""
    alerts = []
    for item in ESG_RISK_CHECKLIST:
        applies = item["applies_to"]
        triggered = False

        if applies == "global":
            triggered = True
        elif applies == "B2B" and biz_type == "B2B":
            triggered = True
        elif isinstance(applies, list) and country in applies:
            triggered = True

        threshold = item.get("threshold")
        if threshold and layoff_pct < threshold:
            triggered = False

        if triggered:
            alerts.append(item)

    return alerts
