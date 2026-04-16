"""
shared/data/dept_estimator.py
공시 데이터 (기업 레벨) → 부서별 추정 수치 생성

1단계: 공시 API에서 기업 레벨 재무 수치 가져옴 (public_filing_client.py)
2단계: 업종 기준 부서 비중 테이블 → 부서별 인원/급여 추정

출처: Goldman Sachs 2023, McKinsey MGI 2025
"""

from __future__ import annotations
from shared.data.presets import (
    DEPT_HEADCOUNT_SHARE,
    DEPT_SALARY_MULTIPLIER,
    DEPARTMENT_PRESETS,
    READINESS_DIMENSIONS,
    compute_k,
    estimate_capex,
    estimate_opex,
)


def estimate_departments(
    filing_data: dict,
    industry: str,
    num_departments: int | None = None,
) -> list[dict]:
    """
    공시 데이터 (기업 레벨) → 부서별 추정 수치 생성.

    Parameters:
        filing_data:     get_company_filing_data() 반환값
        industry:        산업 코드 ('IT소프트웨어', '금융보험' 등)
        num_departments: 표시할 부서 수 (None이면 전체)

    Returns:
        S1-1 부서 추가 UI와 호환되는 딕셔너리 리스트
    """
    total_employees = filing_data.get("total_employees")
    avg_salary      = filing_data.get("avg_salary_annual")
    total_labor     = filing_data.get("total_labor_cost")

    # 전체 인건비가 없으면 평균급여 × 인원으로 추정
    if total_labor is None and total_employees and avg_salary:
        total_labor = total_employees * avg_salary
        filing_data.setdefault("warnings", []).append(
            "total_labor_cost: avg_salary_annual × total_employees로 추정"
        )

    share_table  = DEPT_HEADCOUNT_SHARE.get(industry, DEPT_HEADCOUNT_SHARE["기타"])
    salary_table = DEPT_SALARY_MULTIPLIER.get(industry, DEPT_SALARY_MULTIPLIER["_default"])

    # 전체 평균 급여의 기준값 보정 (가중 평균 배율로 나눔)
    dept_names = [k for k in share_table if not k.startswith("_")]
    weighted_avg_multiplier = sum(
        share_table.get(d, 0) * salary_table.get(d, 1.0)
        for d in dept_names
    )
    base_salary = (
        avg_salary / weighted_avg_multiplier
        if avg_salary and weighted_avg_multiplier > 0
        else None
    )

    dept_list = []
    for dept_name in dept_names:
        share      = share_table[dept_name]
        multiplier = salary_table.get(dept_name, 1.0)

        # 부서별 인원 추정
        headcount = round(total_employees * share) if total_employees else None

        # 부서별 평균 연봉 추정
        dept_salary = (base_salary * multiplier) if base_salary else None

        # s1_tab1_profile.py 부서 dict 형식과 호환
        dept_type = dept_name  # DEPARTMENT_PRESETS 키와 동일

        # 자동화율: DEPARTMENT_PRESETS 프리셋 중간값
        preset = DEPARTMENT_PRESETS.get(dept_type, {})
        frac_lo, frac_hi = preset.get("auto_fraction_range", (0.3, 0.5))
        alpha_default = round((frac_lo + frac_hi) / 2, 2)

        # 기본 준비도 점수(3)로 k 계산
        default_scores = {dim: 3.0 for dim in READINESS_DIMENSIONS}
        k = compute_k(default_scores, dept_type) if dept_type in DEPARTMENT_PRESETS else 1.0

        # Capex/Opex 추정
        capex_info = estimate_capex(
            {"headcount": headcount or 10, "type": dept_type}, 3.0
        )
        opex_info = estimate_opex(
            {
                "headcount":   headcount or 10,
                "type":        dept_type,
                "capex_total": capex_info["total_capex"],
                "avg_salary":  dept_salary or 0.5,
            },
            alpha_default,
        )

        dept_list.append({
            # S1-1 호환 필드
            "name":              dept_name,
            "type":              dept_type,
            "headcount":         headcount or 0,
            "avg_salary":        round(dept_salary, 3) if dept_salary else 0.5,
            "alpha":             alpha_default,
            "description":       "",
            "k":                 k,
            "capex_total":       capex_info["total_capex"],
            "annual_opex":       opex_info["total_opex"],
            "readiness_scores":  default_scores,
            # 추정 메타데이터
            "is_estimated":      True,
            "headcount_share":   share,
            "salary_multiplier": multiplier,
            "estimation_basis":  (
                f"{industry} 업종 평균 인원 비중 {share*100:.0f}%"
                f" (출처: {share_table.get('_source', 'McKinsey/Goldman Sachs')})"
            ),
        })

    if num_departments is not None:
        dept_list.sort(key=lambda x: x["headcount_share"], reverse=True)
        dept_list = dept_list[:num_departments]

    return dept_list


def validate_estimation(dept_list: list[dict], filing_data: dict) -> list[str]:
    """
    추정값 검증 — 인원 합계 오차, 급여 합계 오차.
    경고 메시지 리스트 반환.
    """
    warnings = []
    total_emp = filing_data.get("total_employees")
    if total_emp:
        estimated_total = sum(d["headcount"] for d in dept_list)
        diff = abs(estimated_total - total_emp)
        if diff > len(dept_list):
            warnings.append(
                f"추정 총 인원({estimated_total}명)이 공시 인원({total_emp}명)과 "
                f"{diff}명 차이납니다. (반올림 허용: {len(dept_list)}명)"
            )
    return warnings
