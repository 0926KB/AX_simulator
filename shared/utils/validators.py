"""shared/utils/validators.py — 입력값 검증"""
from __future__ import annotations


def validate_alpha(alpha: float) -> float:
    """자동화율은 0~1 사이"""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"자동화율 alpha={alpha}는 [0, 1] 범위를 벗어났습니다.")
    return alpha


def validate_positive(value: float, name: str) -> float:
    if value <= 0:
        raise ValueError(f"{name}={value}은 양수여야 합니다.")
    return value


def validate_params(params: dict) -> list[str]:
    """
    ModelParams 딕셔너리 검증.
    오류 메시지 리스트 반환 (빈 리스트 = 이상 없음).
    """
    errors = []
    for key in ("lambda_", "eta"):
        v = params.get(key, -1)
        if not 0.0 <= v <= 1.0:
            errors.append(f"{key}={v}은 [0, 1] 범위여야 합니다.")
    for key in ("w", "c", "k", "L", "A"):
        v = params.get(key, -1)
        if v <= 0:
            errors.append(f"{key}={v}은 양수여야 합니다.")
    if params.get("N", 0) < 1:
        errors.append("N은 1 이상이어야 합니다.")
    if params.get("c", 0) >= params.get("w", 1):
        errors.append("AI 비용 c가 임금 w 이상입니다. 자동화 유인이 없습니다.")
    return errors
