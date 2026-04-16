"""
shared/data/cascade_engine.py
D-015 — 부서간 연쇄 효과 계산 엔진 (구조 2: 업무량 기반)

핵심 수식:
  B 연쇄 변화량 = A 해고 인원 × A→B 업무지원비율 × 연간반영비율
  상한: to_dept 현재 인원의 ±30%

LLM 관여 없음. 순수 알고리즘.
"""

from __future__ import annotations

_CASCADE_CAP_RATIO = 0.30   # to_dept 인원 대비 최대 변화 비율


def compute_cascade_effects(
    departments: list[dict],
    cascade_pairs: list[dict],
    year: int = 1,
) -> list[dict]:
    """
    부서별 자동화 결과 + 설문 계수 → 연쇄 효과 계산.

    Parameters:
        departments: 부서 목록
            [{"dept_name": str, "headcount": int, "alpha": float,
              "avg_salary": float}, ...]

        cascade_pairs: 사용자가 정의한 부서 쌍 + 계수
            [{"from_dept": str, "to_dept": str,
              "coefficient": float,    # 음수=감소, 양수=증가
              "annual_factor": float,  # 0~1
              "support_ratio": float,  # UI 표시용
              "direction": str,
              "transition_label": str,
             }, ...]

        year: 프로젝션 연도 (현재는 단일 연도, 추후 확장 가능)

    Returns:
        [{dept_name, direct_displaced, cascade_change,
          cascade_breakdown, net_headcount_change,
          net_labor_cost_change, is_estimated}]
    """
    dept_map = {d["dept_name"]: d for d in departments}

    # 초기화
    results: dict[str, dict] = {}
    for dept in departments:
        results[dept["dept_name"]] = {
            "dept_name":         dept["dept_name"],
            "direct_displaced":  round(dept["headcount"] * dept["alpha"], 2),
            "cascade_change":    0.0,
            "cascade_breakdown": [],
            "is_estimated":      True,
        }

    # 쌍별 연쇄 효과 계산
    for pair in cascade_pairs:
        from_name = pair["from_dept"]
        to_name   = pair["to_dept"]

        if from_name not in dept_map or to_name not in dept_map:
            continue

        from_dept   = dept_map[from_name]
        displaced   = from_dept["headcount"] * from_dept["alpha"]

        raw_change  = displaced * pair["coefficient"] * pair["annual_factor"]

        # 상한 적용: to_dept 인원의 ±30%
        to_dept     = dept_map[to_name]
        cap         = to_dept["headcount"] * _CASCADE_CAP_RATIO
        capped      = max(-cap, min(raw_change, cap))
        was_capped  = abs(raw_change) > abs(capped) + 1e-9

        results[to_name]["cascade_change"] += capped
        results[to_name]["cascade_breakdown"].append({
            "from_dept":  from_name,
            "change":     round(capped, 2),
            "direction":  "decrease" if capped < 0 else ("increase" if capped > 0 else "neutral"),
            "was_capped": was_capped,
            "raw_change": round(raw_change, 2),
        })

    # 최종 합산
    for dept_name, res in results.items():
        dept = dept_map[dept_name]
        res["cascade_change"]       = round(res["cascade_change"], 2)
        res["net_headcount_change"] = round(
            res["direct_displaced"] + res["cascade_change"], 2
        )
        res["net_labor_cost_change"] = round(
            res["net_headcount_change"] * dept.get("avg_salary", 0.5), 3
        )

    return list(results.values())


def cascade_summary(
    cascade_results: list[dict],
    departments: list[dict],
) -> dict:
    """
    연쇄 효과 전체 요약.

    Returns:
        {total_direct_displaced, total_cascade_change,
         total_net_change, total_additional_labor_cost,
         affected_depts}
    """
    dept_salary = {d["dept_name"]: d.get("avg_salary", 0.5) for d in departments}

    total_direct   = sum(r["direct_displaced"] for r in cascade_results)
    total_cascade  = sum(r["cascade_change"] for r in cascade_results)
    total_net      = sum(r["net_headcount_change"] for r in cascade_results)

    # 연쇄 효과로 인한 추가 비용 (음수 = 추가 절감, 양수 = 추가 비용)
    total_extra_labor = sum(
        r["cascade_change"] * dept_salary.get(r["dept_name"], 0.5)
        for r in cascade_results
    )

    affected = [
        r["dept_name"] for r in cascade_results
        if abs(r["cascade_change"]) > 0.01
    ]

    return {
        "total_direct_displaced":     round(total_direct, 2),
        "total_cascade_change":       round(total_cascade, 2),
        "total_net_change":           round(total_net, 2),
        "total_additional_labor_cost": round(total_extra_labor, 3),
        "affected_depts":             affected,
    }
