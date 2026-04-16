"""
shared/data/cascade_survey.py
D-015 — 부서간 연쇄 효과 설문 구조 및 계수 변환

설문 답변 → 연쇄 효과 계수 변환 (LLM 관여 없음, 순수 알고리즘)
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# 설문 질문 템플릿
# ─────────────────────────────────────────────────────────────────────────────

CASCADE_QUESTIONS: dict[str, dict] = {
    "support_ratio": {
        "question":  "{dept_A} 업무 중 {dept_B}팀이 지원하는 비율은?",
        "type":      "select",
        "options": {
            "없음":      0.00,
            "5% 미만":   0.03,
            "5~15%":     0.10,
            "15~30%":    0.22,
            "30% 이상":  0.40,
        },
        "help": "예: CS팀 업무 중 HR이 채용/퇴직 처리로 지원하는 비율",
    },
    "direction": {
        "question": "{dept_A} 인원이 줄면 {dept_B} 업무량은?",
        "type":     "select",
        "options": {
            "감소 (지원 수요 줄어듦)": "decrease",
            "증가 (새 업무 발생)":     "increase",
            "변화 없음":               "neutral",
        },
        "help": "예: CS 해고 → HR 채용 업무 감소 / CS AI 도입 → IT 운영 업무 증가",
    },
    "transition_period": {
        "question": "이 변화가 나타나는 데 걸리는 시간은?",
        "type":     "select",
        "options": {
            "즉시 (1~3개월)":  0.25,
            "단기 (3~6개월)":  0.50,
            "중기 (6~12개월)": 1.00,
            "장기 (1년 이상)": 1.50,
        },
        "help": "효과가 실제 인원 변화로 나타나기까지 걸리는 시간",
    },
}

# 지원 비율 옵션 레이블 순서 (Streamlit selectbox 순서 보장)
SUPPORT_RATIO_OPTIONS: list[str] = list(CASCADE_QUESTIONS["support_ratio"]["options"].keys())
DIRECTION_OPTIONS:     list[str] = list(CASCADE_QUESTIONS["direction"]["options"].keys())
TRANSITION_OPTIONS:    list[str] = list(CASCADE_QUESTIONS["transition_period"]["options"].keys())


# ─────────────────────────────────────────────────────────────────────────────
# 계수 변환
# ─────────────────────────────────────────────────────────────────────────────

def survey_to_coefficient(
    support_ratio: float,
    direction: str,
    transition_period: float,
) -> dict:
    """
    설문 답변 → 연쇄 효과 계수 변환.

    Parameters:
        support_ratio:     업무 지원 비율 (0~1, CASCADE_QUESTIONS options 값)
        direction:         "decrease" | "increase" | "neutral"
        transition_period: 연간 환산 계수 (0.25/0.50/1.00/1.50)

    Returns:
        {coefficient, annual_factor, is_estimated, source}
    """
    if direction == "neutral" or support_ratio == 0.0:
        return {
            "coefficient":   0.0,
            "annual_factor": 0.0,
            "is_estimated":  True,
            "source":        "사용자 설문 기반 추정",
        }

    coefficient   = -support_ratio if direction == "decrease" else +support_ratio
    annual_factor = min(transition_period, 1.0)   # 1.50 → cap 1.0

    return {
        "coefficient":   round(coefficient, 4),
        "annual_factor": round(annual_factor, 4),
        "is_estimated":  True,
        "source":        "사용자 설문 기반 추정",
    }


def label_to_values(
    support_label: str,
    direction_label: str,
    transition_label: str,
) -> tuple[float, str, float]:
    """
    Streamlit selectbox 레이블 → 수치 변환 헬퍼.

    Returns: (support_ratio, direction_str, transition_period)
    """
    support_ratio     = CASCADE_QUESTIONS["support_ratio"]["options"][support_label]
    direction_str     = CASCADE_QUESTIONS["direction"]["options"][direction_label]
    transition_period = CASCADE_QUESTIONS["transition_period"]["options"][transition_label]
    return support_ratio, direction_str, transition_period
