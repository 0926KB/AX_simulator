"""
shared/data/presets.py
로컬 기준값 테이블 — 부서 프리셋, 산업, 국가, 준비도

출처: Goldman Sachs 2023, McKinsey MGI 2025, Deloitte, PWC, CloudZero 2025
LLM 없음. 순수 데이터 테이블.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────
# 부서별 프리셋
# ─────────────────────────────────────────────────────────

DEPARTMENT_PRESETS: dict[str, dict] = {
    "고객서비스(CS)": {
        "auto_fraction_range": (0.60, 0.75),
        "avg_salary_multiplier": 0.8,
        "k_base": 0.6,
        "capex_per_head": 0.015,   # 억원
        "source": "Goldman Sachs 2023, Gartner 2025",
    },
    "재무/회계": {
        "auto_fraction_range": (0.35, 0.45),
        "avg_salary_multiplier": 1.2,
        "k_base": 1.0,
        "capex_per_head": 0.025,
        "source": "Goldman Sachs 2023, McKinsey MGI 2025",
    },
    "법무/컴플라이언스": {
        "auto_fraction_range": (0.40, 0.50),
        "avg_salary_multiplier": 1.8,
        "k_base": 1.4,
        "capex_per_head": 0.035,
        "source": "Goldman Sachs 2023",
    },
    "엔지니어링/개발": {
        "auto_fraction_range": (0.30, 0.45),
        "avg_salary_multiplier": 1.6,
        "k_base": 1.2,
        "capex_per_head": 0.020,
        "source": "McKinsey MGI 2025, Brynjolfsson et al. 2025",
    },
    "HR": {
        "auto_fraction_range": (0.30, 0.40),
        "avg_salary_multiplier": 1.0,
        "k_base": 0.9,
        "capex_per_head": 0.018,
        "source": "McKinsey MGI 2025",
    },
    "영업/마케팅": {
        "auto_fraction_range": (0.25, 0.35),
        "avg_salary_multiplier": 1.1,
        "k_base": 1.1,
        "capex_per_head": 0.020,
        "source": "McKinsey MGI 2025",
    },
    "운영/물류": {
        "auto_fraction_range": (0.35, 0.50),
        "avg_salary_multiplier": 0.9,
        "k_base": 0.8,
        "capex_per_head": 0.022,
        "source": "McKinsey MGI 2025",
    },
    "경영/기획": {
        "auto_fraction_range": (0.20, 0.30),
        "avg_salary_multiplier": 1.5,
        "k_base": 1.5,
        "capex_per_head": 0.030,
        "source": "McKinsey MGI 2025",
    },
}

DEPARTMENT_TYPES = list(DEPARTMENT_PRESETS.keys())


# ─────────────────────────────────────────────────────────
# 산업별 기준값
# ─────────────────────────────────────────────────────────

INDUSTRY_LABOR_RATIO: dict[str, dict] = {
    "제조":         {"labor_to_revenue": 0.18, "source": "PWC/US Census"},
    "금융보험":     {"labor_to_revenue": 0.28, "source": "PWC/US Census"},
    "IT소프트웨어": {"labor_to_revenue": 0.28, "source": "Deloitte"},
    "소매":         {"labor_to_revenue": 0.20, "source": "NRF"},
    "의료":         {"labor_to_revenue": 0.45, "source": "PWC"},
    "컨설팅":       {"labor_to_revenue": 0.45, "source": "McKinsey"},
    "기타":         {"labor_to_revenue": 0.30, "source": "업종 평균"},
}

INDUSTRY_TYPES = list(INDUSTRY_LABOR_RATIO.keys())

# λ 산출에 사용하는 산업별 소비 집중도
INDUSTRY_SECTOR_SHARE: dict[str, float] = {
    "IT소프트웨어": 0.08,
    "제조":         0.12,
    "금융보험":     0.10,
    "소매":         0.25,
    "의료":         0.15,
    "컨설팅":       0.07,
    "기타":         0.10,
}

# 업종 → tech/non_tech 분류 (채널 1, 3에 사용)
INDUSTRY_IS_TECH: dict[str, bool] = {
    "IT소프트웨어": True,
    "엔지니어링":   True,
    "금융보험":     False,
    "제조":         False,
    "소매":         False,
    "의료":         False,
    "컨설팅":       False,
    "기타":         False,
}


# ─────────────────────────────────────────────────────────
# 국가별 기본값 (API 실패 시 폴백)
# ─────────────────────────────────────────────────────────

COUNTRY_DEFAULTS: dict[str, dict] = {
    "KR": {
        "name": "한국",
        "eta": 0.35,
        "lambda_": 0.48,
        "unemployment_rate": 2.8,
        "avg_wage_index": 100.0,
        "currency": "억원",
        "legal_system": "civil_law",
    },
    "US": {
        "name": "미국",
        "eta": 0.25,
        "lambda_": 0.52,
        "unemployment_rate": 3.9,
        "avg_wage_index": 100.0,
        "currency": "만달러",
        "legal_system": "common_law",
    },
    "JP": {
        "name": "일본",
        "eta": 0.40,
        "lambda_": 0.45,
        "unemployment_rate": 2.5,
        "avg_wage_index": 100.0,
        "currency": "억엔",
        "legal_system": "civil_law",
    },
    "DE": {
        "name": "독일",
        "eta": 0.55,
        "lambda_": 0.50,
        "unemployment_rate": 3.0,
        "avg_wage_index": 100.0,
        "currency": "만유로",
        "legal_system": "civil_law",
    },
    "GB": {
        "name": "영국",
        "eta": 0.45,
        "lambda_": 0.51,
        "unemployment_rate": 4.2,
        "avg_wage_index": 100.0,
        "currency": "만파운드",
        "legal_system": "common_law",
    },
    "FR": {
        "name": "프랑스",
        "eta": 0.60,
        "lambda_": 0.49,
        "unemployment_rate": 7.3,
        "avg_wage_index": 100.0,
        "currency": "만유로",
        "legal_system": "civil_law",
    },
    "CN": {
        "name": "중국",
        "eta": 0.20,
        "lambda_": 0.44,
        "unemployment_rate": 5.0,
        "avg_wage_index": 100.0,
        "currency": "억위안",
        "legal_system": "civil_law",
    },
    "IN": {
        "name": "인도",
        "eta": 0.15,
        "lambda_": 0.40,
        "unemployment_rate": 7.8,
        "avg_wage_index": 100.0,
        "currency": "억루피",
        "legal_system": "common_law",
    },
}

COUNTRY_CODES = list(COUNTRY_DEFAULTS.keys())


# ─────────────────────────────────────────────────────────
# AI 준비도 차원 (McKinsey Rewired + BCG 10-20-70)
# ─────────────────────────────────────────────────────────

READINESS_DIMENSIONS: dict[str, dict] = {
    "data_quality": {
        "label": "데이터 품질",
        "weight": 0.25,
        "description": "업무 데이터의 구조화 수준, 접근성, 일관성",
        "category": "data_tech",
    },
    "process_maturity": {
        "label": "프로세스 표준화",
        "weight": 0.20,
        "description": "업무 흐름의 문서화, 표준화, 반복 가능성",
        "category": "data_tech",
    },
    "change_readiness": {
        "label": "변화 수용성",
        "weight": 0.30,
        "description": "구성원의 AI 도입 수용도, 리더십 지원, 리스킬 의지",
        "category": "people",
    },
    "tech_infrastructure": {
        "label": "기술 인프라",
        "weight": 0.10,
        "description": "클라우드 환경, API 연동 가능성, IT 시스템 현대화 수준",
        "category": "tech",
    },
    "governance_constraint": {
        "label": "거버넌스/규제 제약",
        "weight": 0.15,
        "description": "데이터 규제(개인정보), 컴플라이언스, 노사 협약 제약",
        "category": "people",
    },
}

READINESS_SCALE: dict[int, str] = {
    1: "기반 없음 — 비정형 데이터, 업무 비표준화, AI 거부감 강함",
    2: "초기 단계 — 일부 구조화, 일부 표준화, 시범 도입 논의 중",
    3: "준비 중   — 대부분 구조화, 주요 프로세스 표준화, 파일럿 경험 일부",
    4: "준비 완료 — 고품질 데이터, 완전 표준화, 적극적 AI 도입 의지",
    5: "선도      — 실시간 파이프라인, 자동화 일부 가동, AI-first 문화",
}

K_INTERPRETATION: list[dict] = [
    {"range": (0.3, 0.7),  "label": "낮은 마찰",       "action": "즉시 도입 가능",         "pilot_success": "높음"},
    {"range": (0.7, 1.3),  "label": "중간 마찰",       "action": "6~12개월 준비",          "pilot_success": "중간"},
    {"range": (1.3, 2.0),  "label": "높은 마찰",       "action": "준비도 개선 우선",        "pilot_success": "낮음"},
    {"range": (2.0, 3.0),  "label": "매우 높은 마찰",  "action": "파일럿 진행 전 재검토",   "pilot_success": "5% (MIT 연구)"},
]


def compute_k(readiness_scores: dict[str, float], dept_type: str) -> float:
    """
    준비도 점수(1~5) → 마찰 계수 k
    k = k_base × (3.0 / weighted_score)
    클리핑: [0.3, 3.0]
    """
    weighted_score = sum(
        readiness_scores[dim] * READINESS_DIMENSIONS[dim]["weight"]
        for dim in readiness_scores
        if dim in READINESS_DIMENSIONS
    )
    k_base = DEPARTMENT_PRESETS[dept_type]["k_base"]
    k = k_base * (3.0 / max(weighted_score, 0.1))
    return round(max(0.3, min(k, 3.0)), 3)


def interpret_k(k: float) -> dict:
    for item in K_INTERPRETATION:
        lo, hi = item["range"]
        if lo <= k <= hi:
            return item
    return K_INTERPRETATION[-1]


def estimate_capex(dept: dict, readiness_score: float) -> dict:
    """
    CloudZero 2025 벤치마크 기반 Capex 추정
    readiness_score: 1~5 가중 평균 점수
    """
    headcount = dept["headcount"]
    preset = DEPARTMENT_PRESETS.get(dept["type"], {})
    per_head = preset.get("capex_per_head", 0.020)

    base = headcount * per_head
    readiness_multiplier = 2.0 - (readiness_score / 5.0)      # [1.0, 1.8]
    hidden_rate = 0.15 + (1 - readiness_score / 5.0) * 0.15   # [0.15, 0.30]
    total = base * readiness_multiplier * (1 + hidden_rate)

    return {
        "integration": round(base, 3),
        "total_capex": round(total, 3),
        "hidden_rate": round(hidden_rate, 3),
        "source": "CloudZero 2025",
    }


def estimate_opex(dept: dict, alpha: float) -> dict:
    """연간 Opex: API 비용 + 유지보수 + 감독 인력"""
    automated = dept["headcount"] * alpha
    api_cost = automated * 0.0003 * 250          # 연 250 영업일
    maintenance = dept.get("capex_total", 0) * 0.18
    oversight = automated * 0.15 * dept.get("avg_salary", 0.5)
    total = api_cost + maintenance + oversight
    return {"total_opex": round(total, 3), "api_cost": round(api_cost, 3),
            "maintenance": round(maintenance, 3), "oversight": round(oversight, 3)}
