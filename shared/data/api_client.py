"""
shared/data/api_client.py
외부 데이터 레이어 — OECD, World Bank, Finnhub, BLS, yfinance + 7일 캐시

키 불필요: OECD SDMX, World Bank (wbgapi), yfinance
키 필요:   Finnhub (FINNHUB_API_KEY), BLS (BLS_API_KEY)
"""

from __future__ import annotations
import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache/api"))
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "7"))

OECD_BASE = "https://sdmx.oecd.org/public/rest/data"
BLS_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# BLS JOLTS 업종별 자발적 이직률 시리즈 ID (2024)
JOLTS_SERIES: dict[str, str] = {
    "IT소프트웨어": "JTS540099000000000QUR",
    "금융보험":     "JTS520000000000000QUR",
    "의료":         "JTS620000000000000QUR",
    "제조":         "JTS300000000000000QUR",
    "소매":         "JTS440000000000000QUR",
}


# ─────────────────────────────────────────────────────────
# 캐시 유틸리티
# ─────────────────────────────────────────────────────────

def _cache_key(source: str, country: str, indicator: str) -> str:
    week = datetime.now().strftime("%Y-W%W")
    raw = f"{source}_{country}_{indicator}_{week}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def _cache_get(key: str) -> Any | None:
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
        saved_at = datetime.fromisoformat(meta["saved_at"])
        if datetime.now() - saved_at > timedelta(days=CACHE_TTL_DAYS):
            return None
        return meta["data"]
    except Exception:
        return None


def _cache_set(key: str, data: Any) -> None:
    try:
        _cache_path(key).write_text(
            json.dumps({"saved_at": datetime.now().isoformat(), "data": data},
                       ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# OECD SDMX API
# ─────────────────────────────────────────────────────────

def _oecd_fetch(url: str, timeout: int = 10) -> dict | None:
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"Accept": "application/json"})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_unemployment_rate(country: str) -> tuple[float | None, str]:
    """
    OECD LFS 실업률 (최근 4개월 평균)
    반환: (값, 상태) — 상태: "api" | "cache" | "fallback"
    """
    key = _cache_key("oecd_unemployment", country, "UNE")
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"

    url = (
        f"{OECD_BASE}/OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/"
        f"{country}.M.UNE_LF..._Z.Y._T.?format=jsondata&lastNObservations=4"
    )
    raw = _oecd_fetch(url)
    if raw:
        try:
            obs = raw["dataSets"][0]["observations"]
            values = [v[0] for v in obs.values() if v[0] is not None]
            if values:
                rate = sum(values) / len(values)
                _cache_set(key, rate)
                return rate, "api"
        except Exception:
            pass
    return None, "fallback"


def get_epl_score(country: str) -> tuple[float | None, str]:
    """
    OECD EPL (고용보호지수) — 해고 비용 배수 근거
    """
    key = _cache_key("oecd_epl", country, "EPL")
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"

    url = (
        f"{OECD_BASE}/OECD.ELS.SAE,DSD_EPL@DF_EPL_OV/"
        f"{country}.A.EPRC_V1?format=jsondata&lastNObservations=1"
    )
    raw = _oecd_fetch(url)
    if raw:
        try:
            obs = raw["dataSets"][0]["observations"]
            values = [v[0] for v in obs.values() if v[0] is not None]
            if values:
                score = values[0]
                _cache_set(key, score)
                return score, "api"
        except Exception:
            pass
    return None, "fallback"


# ─────────────────────────────────────────────────────────
# World Bank API (wbgapi)
# ─────────────────────────────────────────────────────────

def get_household_consumption_ratio(country: str) -> tuple[float | None, str]:
    """
    World Bank NE.CON.PETC.ZS — 가계 최종 소비 지출/GDP (λ 프록시)
    최근 3년 평균
    """
    key = _cache_key("wb_consumption", country, "NE.CON.PETC.ZS")
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"
    try:
        import wbgapi as wb
        data = wb.data.get("NE.CON.PETC.ZS", country, mrv=3)
        values = [v for v in data.values() if v is not None]
        if values:
            ratio = sum(values) / len(values) / 100.0  # % → 비율
            _cache_set(key, ratio)
            return ratio, "api"
    except Exception:
        pass
    return None, "fallback"


def get_gdp_per_capita(country: str) -> tuple[float | None, str]:
    """World Bank NY.GDP.PCAP.CD — 1인당 GDP (USD)"""
    key = _cache_key("wb_gdp_pc", country, "NY.GDP.PCAP.CD")
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"
    try:
        import wbgapi as wb
        data = wb.data.get("NY.GDP.PCAP.CD", country, mrv=1)
        values = [v for v in data.values() if v is not None]
        if values:
            gdp = values[0]
            _cache_set(key, gdp)
            return gdp, "api"
    except Exception:
        pass
    return None, "fallback"


# ─────────────────────────────────────────────────────────
# BLS API (이직률 — 채널 2)
# ─────────────────────────────────────────────────────────

def get_voluntary_turnover_rate(industry: str) -> tuple[float | None, str]:
    """
    BLS JOLTS 연간 자발적 이직률 (미국 기준)
    국가가 미국이 아닐 경우 로컬 테이블 폴백 사용
    """
    series_id = JOLTS_SERIES.get(industry)
    if not series_id:
        return None, "fallback"

    key = _cache_key("bls_jolts", "US", industry)
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"

    api_key = os.getenv("BLS_API_KEY", "")
    try:
        payload = {
            "seriesid": [series_id],
            "startyear": str(datetime.now().year - 1),
            "endyear":   str(datetime.now().year),
        }
        if api_key:
            payload["registrationkey"] = api_key

        r = requests.post(BLS_BASE, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            series = data.get("Results", {}).get("series", [])
            if series:
                values = [
                    float(d["value"])
                    for d in series[0].get("data", [])
                    if d.get("value") != "-"
                ]
                if values:
                    rate = sum(values) / len(values) / 100.0
                    _cache_set(key, rate)
                    return rate, "api"
    except Exception:
        pass
    return None, "fallback"


# ─────────────────────────────────────────────────────────
# Finnhub API (주가 — 채널 1)
# ─────────────────────────────────────────────────────────

def get_stock_price(ticker: str) -> tuple[float | None, str]:
    """Finnhub 현재 주가 조회"""
    api_key = os.getenv("FINNHUB_API_KEY", "")
    if not api_key:
        return None, "no_key"

    key = _cache_key("finnhub_price", ticker, "quote")
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"

    try:
        import finnhub
        client = finnhub.Client(api_key=api_key)
        quote = client.quote(ticker)
        price = quote.get("c")
        if price:
            _cache_set(key, price)
            return price, "api"
    except Exception:
        pass
    return None, "fallback"


def get_market_cap(ticker: str) -> tuple[float | None, str]:
    """Finnhub 또는 yfinance 시가총액 조회"""
    api_key = os.getenv("FINNHUB_API_KEY", "")
    if api_key:
        key = _cache_key("finnhub_mcap", ticker, "profile")
        cached = _cache_get(key)
        if cached is not None:
            return cached, "cache"
        try:
            import finnhub
            client = finnhub.Client(api_key=api_key)
            profile = client.company_profile2(symbol=ticker)
            mcap = profile.get("marketCapitalization")
            if mcap:
                _cache_set(key, mcap)
                return mcap, "api"
        except Exception:
            pass

    # yfinance 폴백
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        mcap = info.get("marketCap")
        if mcap:
            return mcap / 1e8, "yfinance"  # USD → 억원 환산 아님, 원본 반환
    except Exception:
        pass
    return None, "fallback"


# ─────────────────────────────────────────────────────────
# 국가 파라미터 통합 로드
# ─────────────────────────────────────────────────────────

def load_country_params(country: str, industry: str) -> dict:
    """
    국가/산업 기반 파라미터 전체 로드
    API 실패 시 폴백값 사용 + warning_flags 반환

    Returns:
        {eta, lambda_, unemployment_rate, epl_score,
         gdp_per_capita, warnings: list[str]}
    """
    from shared.data.presets import COUNTRY_DEFAULTS, INDUSTRY_SECTOR_SHARE

    defaults = COUNTRY_DEFAULTS.get(country, COUNTRY_DEFAULTS["KR"])
    warnings: list[str] = []

    # 실업률
    unemp, unemp_src = get_unemployment_rate(country)
    if unemp is None:
        unemp = defaults["unemployment_rate"]
        warnings.append(f"실업률: OECD API 실패 → 기본값 {unemp}% 적용")

    # EPL 점수
    from shared.data.regulatory import REGULATORY_CONTEXT
    epl, epl_src = get_epl_score(country)
    if epl is None:
        epl = REGULATORY_CONTEXT.get(country, {}).get("epl_score", 2.0)
        warnings.append(f"EPL: OECD API 실패 → 기본값 {epl} 적용")

    # 가계 소비성향 (λ 프록시)
    hc_ratio, hc_src = get_household_consumption_ratio(country)
    sector_share = INDUSTRY_SECTOR_SHARE.get(industry, 0.10)
    if hc_ratio is not None:
        lambda_ = hc_ratio * sector_share
    else:
        lambda_ = defaults["lambda_"]
        warnings.append(f"λ: World Bank API 실패 → 기본값 {lambda_} 적용")

    # 1인당 GDP
    gdp_pc, _ = get_gdp_per_capita(country)
    if gdp_pc is None:
        warnings.append("1인당 GDP: World Bank API 실패")

    return {
        "eta":               defaults["eta"],        # η는 API 미확보 → 항상 기본값
        "lambda_":           round(lambda_, 4),
        "unemployment_rate": round(unemp, 2),
        "epl_score":         round(epl, 2),
        "gdp_per_capita":    gdp_pc,
        "currency":          defaults["currency"],
        "legal_system":      defaults["legal_system"],
        "warnings":          warnings,
        "sources": {
            "unemployment": unemp_src,
            "epl":          epl_src,
            "lambda":       hc_src,
        },
    }
