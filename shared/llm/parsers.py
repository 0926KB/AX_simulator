"""
shared/llm/parsers.py
LLM 응답 파싱 + 수치 생성 방지 필터
"""

from __future__ import annotations
import re


# 수치 생성 패턴 — LLM이 스스로 계산한 것으로 의심되는 패턴
_NUMERIC_GENERATION_PATTERNS = [
    # "계산하면 X.XX", "산출하면 X", "추정치 X"
    r"계산[하하면결]\s*[:：]?\s*[\d.,]+",
    r"추정[치값]\s*[:：]?\s*[\d.,]+",
    r"산출[하면]\s*[:：]?\s*[\d.,]+",
    r"따라서\s+[αβγτηλ]?\s*[=≈]\s*[\d.,]+",
    r"[αβγτηλ]\s*[=≈]\s*[\d.,]+\s*(?:억원|%|만원)",
    # "the value is X.XX" style
    r"the\s+(?:value|result|answer)\s+is\s+[\d.,]+",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _NUMERIC_GENERATION_PATTERNS]


def check_numeric_hallucination(text: str) -> list[str]:
    """
    LLM이 수치를 직접 생성(hallucination)했는지 검사.
    의심 패턴 발견 시 해당 문구 목록 반환 (빈 리스트 = 이상 없음).
    """
    hits = []
    for pattern in _COMPILED:
        for match in pattern.finditer(text):
            hits.append(match.group(0))
    return hits


def clean_response(text: str) -> str:
    """
    LLM 응답에서 불필요한 서론 구문 제거.
    예: "물론입니다!", "분석 결과를 말씀드리겠습니다." 등
    """
    filler_phrases = [
        r"^물론입니다[!.]?\s*",
        r"^네[,.]?\s*",
        r"^안녕하세요[!.]?\s*",
        r"^분석\s*결과를\s*(?:말씀드리겠습니다|설명드리겠습니다)[!.]\s*",
        r"^아래에?\s*(?:정리|요약|설명)해\s*드리겠습니다[!.]\s*",
        r"^주어진\s*데이터를\s*바탕으로\s*",
    ]
    result = text.strip()
    for phrase in filler_phrases:
        result = re.sub(phrase, "", result, flags=re.MULTILINE | re.IGNORECASE)
    return result.strip()


def format_for_display(text: str, warn_on_hallucination: bool = True) -> str:
    """
    파싱·정제 후 Streamlit 표시용 텍스트 반환.
    수치 hallucination 감지 시 경고 문구 추가.
    """
    cleaned = clean_response(text)

    if warn_on_hallucination:
        hits = check_numeric_hallucination(cleaned)
        if hits:
            warning_block = (
                "\n\n> ⚠️ **[시스템 경고]** LLM이 수치를 직접 생성했을 가능성이 있습니다. "
                "아래 구문을 확인하세요:\n"
                + "\n".join(f"> - `{h}`" for h in hits[:5])
            )
            cleaned += warning_block

    return cleaned
