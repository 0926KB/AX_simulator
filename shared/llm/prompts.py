"""
shared/llm/prompts.py
AX Simulator — LLM 프롬프트 7개 트리거 포인트

규칙:
  - LLM은 해석·설명만. 수치 계산 절대 금지.
  - 모든 수치는 payload에서 주입됨.
  - 한국어로 출력.
  - 출력 길이: 400~600자 권장 (Streamlit 가독성).
"""

from __future__ import annotations
import json

# ─────────────────────────────────────────────────────────────────────────────
# 시스템 프롬프트 (공통)
# ─────────────────────────────────────────────────────────────────────────────
_SYSTEM = """당신은 AI 자동화 경제학 분석 어시스턴트입니다.
Hemenway Falk & Tsoukalas (2026) "The AI Layoff Trap" 논문의 분석 결과를 해석합니다.

엄격한 규칙:
1. 수치를 직접 계산하거나 추정하지 마세요. 모든 수치는 이미 계산된 결과로 주입됩니다.
2. 주어진 수치를 인용하며 경영/정책적 의미를 설명하세요.
3. 한국어로 간결하게 (400~600자) 작성하세요.
4. 불필요한 서론("물론입니다", "분석 결과를 말씀드리겠습니다" 등) 없이 바로 본론으로 시작하세요.
5. Markdown 형식 사용 가능 (bullet, bold 등).
"""

# ─────────────────────────────────────────────────────────────────────────────
# 7개 트리거 포인트 프롬프트 빌더
# ─────────────────────────────────────────────────────────────────────────────

PROMPTS: dict[str, callable] = {}


def _reg(name: str):
    def decorator(fn):
        PROMPTS[name] = fn
        return fn
    return decorator


@_reg("context_analysis")
def context_analysis(payload: dict) -> str:
    return (
        f"다음 국가·산업 컨텍스트 파라미터를 해석해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "이 파라미터들이 AI 자동화 외부효과 크기에 어떤 영향을 미치는지 설명하세요. "
        "특히 η(소득 대체율)과 λ(소비성향)의 조합이 수요 파괴 위험에 미치는 영향에 집중하세요."
    )


@_reg("readiness_analysis")
def readiness_analysis(payload: dict) -> str:
    return (
        f"부서 '{payload['dept_name']}' ({payload['dept_type']})의 AI 준비도 진단 결과를 해석해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "마찰 계수 k 값의 의미, 가장 취약한 준비도 차원, "
        "McKinsey Rewired / BCG 10-20-70 관점에서의 핵심 권고사항을 제시하세요."
    )


@_reg("impact_analysis")
def impact_analysis(payload: dict) -> str:
    return (
        "다음 기업 파급효과 5채널 분석 결과를 해석해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "각 채널(CAR 주가 반응, 생존자 신드롬, 브랜드/고객, 규제 비용, ESG)별 핵심 리스크를 짚고, "
        "순편익/직접절감 비율이 경영 의사결정에 주는 시사점을 설명하세요."
    )


@_reg("strategy_report")
def strategy_report(payload: dict) -> str:
    return (
        "다음 피구세 시나리오 분석 결과를 바탕으로 기업 전략을 제안해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "적용 피구세 τ 수준에서의 ROI 변화, 격차 해소율, "
        "단계적 도입 전략(1년차/3년차/5년차) 권고를 포함하세요."
    )


@_reg("externality_analysis")
def externality_analysis(payload: dict) -> str:
    return (
        "다음 시장 외부효과 분석 결과를 해석해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "Nash 균형 vs 협력 최적 간 격차(wedge)의 의미, "
        "N* 임계치와 현재 경쟁 구조가 시사하는 바, "
        "수요 파괴율이 업계 전반에 미치는 영향을 설명하세요."
    )


@_reg("dynamic_analysis")
def dynamic_analysis(payload: dict) -> str:
    return (
        "다음 η(t) 동적 회복 경로 시뮬레이션 결과를 해석해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "3가지 시나리오(낙관/기준/비관)별로 t=1, t=5, t=10 시점의 "
        "격차(wedge) 변화 추이와 피구세 자기소멸 가능성을 평가하고, "
        "정책 입안자에게 주는 시사점을 제시하세요."
    )


@_reg("policy_analysis")
def policy_analysis(payload: dict) -> str:
    return (
        "다음 6가지 정책 수단 비교 분석 결과를 해석해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "피구세(Proposition 5)가 다른 수단 대비 우월한 이유를 논문 근거와 함께 설명하고, "
        "각 정책 수단의 현실적 한계(정치적 실현 가능성, 집행 비용 등)도 언급하세요."
    )


@_reg("comprehensive_report")
def comprehensive_report(payload: dict) -> str:
    return (
        "다음 AX Simulator 전체 분석 결과를 종합 요약 보고서 형식으로 작성해주세요.\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        "다음 구조로 작성하세요:\n"
        "1. **핵심 발견사항** (3줄 이내)\n"
        "2. **리스크 요약** — 과잉 자동화 격차 / 수요 파괴 / 숨겨진 비용\n"
        "3. **단계별 권고** — 즉시 / 6개월 / 1년\n"
        "4. **정책 시사점** — 피구세 필요성 및 규모\n"
        "수치는 제공된 값만 인용하고 한국어로 작성하세요."
    )
