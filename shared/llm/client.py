"""
shared/llm/client.py
AX Simulator — OpenAI 호환 LLM 클라이언트

지원 백엔드:
  1. OpenAI GPT (OPENAI_API_KEY)
  2. Anthropic Claude (ANTHROPIC_API_KEY)  — openai 호환 엔드포인트 사용
  3. Ollama 로컬 (OLLAMA_BASE_URL)

LLM 역할: 해석만. 수치 계산 절대 금지.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv
from shared.llm.prompts import PROMPTS, _SYSTEM
from shared.llm.parsers import format_for_display

load_dotenv()

# 모델 우선순위 설정
_OPENAI_MODEL     = os.getenv("OPENAI_MODEL",     "gpt-4o-mini")
_ANTHROPIC_MODEL  = os.getenv("ANTHROPIC_MODEL",  "claude-haiku-4-5-20251001")
_OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL",      "llama3")
_OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL",  "http://localhost:11434/v1")

_MAX_TOKENS = 800
_TEMPERATURE = 0.3


def _call_openai(user_prompt: str) -> str:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(user_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=_ANTHROPIC_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=_TEMPERATURE,
    )
    return resp.content[0].text if resp.content else ""


def _call_ollama(user_prompt: str) -> str:
    import openai
    client = openai.OpenAI(
        api_key="ollama",
        base_url=_OLLAMA_BASE_URL,
    )
    resp = client.chat.completions.create(
        model=_OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def call_llm(trigger: str, payload: dict) -> str:
    """
    트리거 포인트에 대한 LLM 호출 진입점.

    우선순위: ANTHROPIC_API_KEY → OPENAI_API_KEY → OLLAMA_BASE_URL
    모두 없으면 NotImplementedError 발생 (UI에서 st.info로 처리).

    Args:
        trigger: PROMPTS 키 (예: "readiness_analysis")
        payload: 수치 데이터 딕셔너리

    Returns:
        정제된 LLM 응답 텍스트
    """
    if trigger not in PROMPTS:
        raise ValueError(f"알 수 없는 트리거: {trigger}. 사용 가능: {list(PROMPTS.keys())}")

    user_prompt = PROMPTS[trigger](payload)

    # 백엔드 선택
    if os.getenv("ANTHROPIC_API_KEY"):
        raw = _call_anthropic(user_prompt)
    elif os.getenv("OPENAI_API_KEY"):
        raw = _call_openai(user_prompt)
    elif os.getenv("OLLAMA_BASE_URL"):
        raw = _call_ollama(user_prompt)
    else:
        raise NotImplementedError(
            "LLM API 키가 설정되지 않았습니다. "
            ".env 파일에 ANTHROPIC_API_KEY 또는 OPENAI_API_KEY를 추가하세요."
        )

    return format_for_display(raw)
