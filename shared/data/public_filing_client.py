"""
shared/data/public_filing_client.py
DART(한국) / SEC EDGAR(미국) 공시 API 클라이언트

기업 레벨 재무 수치 자동 추출:
  - 매출, 영업이익, 총 인건비, 임직원 수, 평균 연봉, 시가총액

캐시: .cache/api/ 디렉토리 (기존 api_client.py 캐시 레이어 활용)
"""

from __future__ import annotations
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 기존 캐시 레이어 재사용
from shared.data.api_client import _cache_key, _cache_get, _cache_set

_DART_API_KEY    = os.getenv("DART_API_KEY", "")
_EDGAR_UA        = "AX-Simulator kbpark0926@gmail.com"
_SEC_BASE        = "https://data.sec.gov"
_SEC_TICKERS_TTL = 30 * 24 * 3600  # 30일 (회사 목록 자주 안 바뀜)
_RATE_SLEEP      = 0.11             # SEC 10 req/s 제한


# ─────────────────────────────────────────────────────────────────────────────
# DART 클라이언트 (한국)
# ─────────────────────────────────────────────────────────────────────────────

def get_dart_company_data(query: str, year: int) -> dict:
    """
    DART 공시에서 기업 레벨 수치 자동 추출.

    Parameters:
        query: 회사명 ('삼성전자') 또는 종목코드 ('005930')
        year:  사업연도 (예: 2023)

    Returns:
        {company_name, corp_code, stock_code, fiscal_year,
         revenue, operating_income, operating_margin,
         total_labor_cost, total_employees, avg_salary_annual,
         market_cap, data_sources, missing_fields, warnings, source, currency}
    """
    try:
        import OpenDartReader
    except ImportError:
        raise ImportError("OpenDartReader 패키지가 필요합니다: pip install OpenDartReader")

    if not _DART_API_KEY:
        raise ValueError("DART_API_KEY가 설정되지 않았습니다. .env 파일에 추가해주세요.")

    cache_key = _cache_key(f"dart_{query}_{year}")
    cached = _cache_get(cache_key)
    if cached:
        return cached

    dart = OpenDartReader.OpenDartReader(_DART_API_KEY)
    result: dict = {
        "source":         "DART",
        "currency":       "억원",
        "fiscal_year":    year,
        "data_sources":   [],
        "missing_fields": [],
        "warnings":       [],
    }
    missing = result["missing_fields"]
    warnings = result["warnings"]

    # Step 1: 기업 고유번호 조회
    try:
        corp = dart.find_corp_code(query)
        if corp is None or (hasattr(corp, 'empty') and corp.empty):
            raise ValueError(f"'{query}' 기업을 DART에서 찾을 수 없습니다.")
        if hasattr(corp, 'iloc'):
            corp_row = corp.iloc[0]
            result["company_name"] = corp_row.get("corp_name", query)
            result["corp_code"]    = str(corp_row.get("corp_code", ""))
            result["stock_code"]   = str(corp_row.get("stock_code", ""))
        else:
            result["company_name"] = query
            result["corp_code"]    = str(corp)
            result["stock_code"]   = ""
    except Exception as e:
        raise ValueError(f"DART 기업 조회 실패: {e}")

    corp_code  = result["corp_code"]
    stock_code = result["stock_code"]

    # Step 2: 재무제표 (매출, 영업이익)
    rev_candidates  = ["매출액", "매출", "영업수익", "수익(매출액)", "Revenue"]
    oi_candidates   = ["영업이익", "영업이익(손실)", "Operating income"]

    try:
        fin = dart.finstate(corp_code, year, reprt_code="11011")  # 사업보고서
        if fin is not None and not (hasattr(fin, 'empty') and fin.empty):
            result["data_sources"].append(f"DART finstate {year}")
            fin_df = fin

            def _find_amount(df, candidates):
                for cand in candidates:
                    rows = df[df["account_nm"].str.contains(cand, na=False)]
                    if not rows.empty:
                        val_str = str(rows.iloc[0].get("thstrm_amount", "0")).replace(",", "")
                        try:
                            return float(val_str) / 1e8  # 원 → 억원
                        except ValueError:
                            continue
                return None

            rev = _find_amount(fin_df, rev_candidates)
            oi  = _find_amount(fin_df, oi_candidates)

            if rev is not None:
                result["revenue"] = round(rev, 2)
            else:
                missing.append("revenue")

            if oi is not None and rev is not None and rev > 0:
                result["operating_income"] = round(oi, 2)
                result["operating_margin"] = round(oi / rev, 4)
            else:
                missing.extend(["operating_income", "operating_margin"])
        else:
            missing.extend(["revenue", "operating_income", "operating_margin"])
            warnings.append("재무제표 데이터 없음 (사업보고서 미제출 또는 연도 불일치)")
    except Exception as e:
        missing.extend(["revenue", "operating_income", "operating_margin"])
        warnings.append(f"재무제표 조회 실패: {e}")

    # Step 3: 직원 현황 (인건비, 인원)
    try:
        emp = dart.report(corp_code, "직원", year)
        if emp is not None and not (hasattr(emp, 'empty') and emp.empty):
            result["data_sources"].append(f"DART 직원현황 {year}")

            def _to_int(val):
                try:
                    return int(str(val).replace(",", ""))
                except (ValueError, TypeError):
                    return 0

            def _to_float(val):
                try:
                    return float(str(val).replace(",", ""))
                except (ValueError, TypeError):
                    return 0.0

            total_emp = 0
            total_salary_m = 0.0  # 백만원

            for _, row in emp.iterrows():
                m = _to_int(row.get("reform_bfe_emp_cnt_m", 0))
                f = _to_int(row.get("reform_bfe_emp_cnt_f", 0))
                c = _to_int(row.get("cnt_cert", 0))
                s = _to_float(row.get("fyer_salary_totamt", 0))
                total_emp     += m + f + c
                total_salary_m += s

            if total_emp > 0:
                result["total_employees"]  = total_emp
                result["total_labor_cost"] = round(total_salary_m / 10, 2)  # 백만원 → 억원
                result["avg_salary_annual"]= round(total_salary_m / total_emp / 10, 4)  # 억원
            else:
                missing.extend(["total_employees", "total_labor_cost", "avg_salary_annual"])
                warnings.append("직원 현황 데이터에 인원 정보 없음")
        else:
            missing.extend(["total_employees", "total_labor_cost", "avg_salary_annual"])
            warnings.append("직원 현황 미제출")
    except Exception as e:
        missing.extend(["total_employees", "total_labor_cost", "avg_salary_annual"])
        warnings.append(f"직원 현황 조회 실패: {e}")

    # Step 4: 시가총액 (yfinance 보완)
    if stock_code:
        try:
            import yfinance as yf
            ticker_str = stock_code.strip() + ".KS"
            info = yf.Ticker(ticker_str).info
            mc = info.get("marketCap")
            if mc:
                result["market_cap"] = round(mc / 1e8, 2)  # 원 → 억원
                result["data_sources"].append("yfinance (실시간)")
            else:
                missing.append("market_cap")
        except Exception as e:
            missing.append("market_cap")
            warnings.append(f"시가총액 조회 실패: {e}")
    else:
        missing.append("market_cap")

    _cache_set(cache_key, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SEC EDGAR 클라이언트 (미국)
# ─────────────────────────────────────────────────────────────────────────────

def _get_sec_tickers() -> dict:
    """SEC 회사 목록 조회 (티커 → CIK 매핑). 30일 캐시."""
    import requests
    cache_key = _cache_key("sec_tickers_v1")
    cached = _cache_get(cache_key)
    if cached:
        return cached

    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers={"User-Agent": _EDGAR_UA}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # {str(i): {"cik_str": ..., "ticker": ..., "title": ...}}
    ticker_map = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    _cache_set(cache_key, ticker_map)
    return ticker_map


def _sec_get(path: str) -> dict:
    """SEC EDGAR GET with rate limiting."""
    import requests
    time.sleep(_RATE_SLEEP)
    resp = requests.get(
        f"{_SEC_BASE}{path}",
        headers={"User-Agent": _EDGAR_UA, "Accept-Encoding": "gzip, deflate"},
        timeout=60,
    )
    for attempt in range(3):
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            resp = requests.get(
                f"{_SEC_BASE}{path}",
                headers={"User-Agent": _EDGAR_UA},
                timeout=60,
            )
        else:
            break
    resp.raise_for_status()
    return resp.json()


def _extract_xbrl_value(facts: dict, tags: list[str], year: int) -> float | None:
    """XBRL Company Facts에서 지정 태그의 연간 값 추출."""
    us_gaap = facts.get("us-gaap", {})
    dei     = facts.get("dei", {})

    for tag in tags:
        namespace, _, tag_name = tag.partition(":")
        ns_data = us_gaap if namespace == "us-gaap" else dei
        tag_data = ns_data.get(tag_name, {})
        units = tag_data.get("units", {})
        usd_entries = units.get("USD", units.get("shares", []))

        # 10-K 중 해당 연도, 가장 최근 filed
        candidates = [
            e for e in usd_entries
            if e.get("form") == "10-K" and str(e.get("end", ""))[:4] == str(year)
        ]
        if not candidates and namespace == "dei":
            # dei 태그는 form 필드 없는 경우도 있음
            candidates = [
                e for e in usd_entries
                if str(e.get("end", ""))[:4] == str(year)
            ]

        if candidates:
            best = sorted(candidates, key=lambda x: x.get("filed", ""), reverse=True)[0]
            return float(best["val"])

    return None


def get_sec_company_data(query: str, year: int) -> dict:
    """
    SEC EDGAR에서 기업 레벨 수치 자동 추출.

    Parameters:
        query: 티커 ('MSFT') 또는 CIK ('0000789019')
        year:  회계연도 (예: 2023)

    Returns: DART와 동일한 구조 (currency=USD, 단위=백만달러)
    """
    cache_key = _cache_key(f"sec_{query}_{year}")
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result: dict = {
        "source":         "SEC_EDGAR",
        "currency":       "USD(백만달러)",
        "fiscal_year":    year,
        "data_sources":   [],
        "missing_fields": [],
        "warnings":       [],
    }
    missing  = result["missing_fields"]
    warnings = result["warnings"]

    # Step 1: CIK 조회
    try:
        if query.isdigit():
            cik = str(query).zfill(10)
        else:
            tickers = _get_sec_tickers()
            cik = tickers.get(query.upper())
            if not cik:
                raise ValueError(f"'{query}' 티커를 SEC EDGAR에서 찾을 수 없습니다.")
        result["cik"] = cik
    except Exception as e:
        raise ValueError(f"CIK 조회 실패: {e}")

    # Step 2: 회사 정보
    try:
        sub = _sec_get(f"/submissions/CIK{cik}.json")
        result["company_name"] = sub.get("name", query)
        result["stock_code"]   = sub.get("tickers", [query])[0] if sub.get("tickers") else query
        result["data_sources"].append("SEC EDGAR submissions")
    except Exception as e:
        result["company_name"] = query
        warnings.append(f"회사 정보 조회 실패: {e}")

    # Step 3: XBRL Company Facts
    try:
        facts_data = _sec_get(f"/api/xbrl/companyfacts/CIK{cik}.json")
        facts = facts_data.get("facts", {})
        result["data_sources"].append(f"SEC XBRL Company Facts {year}")

        # 매출
        rev_tags = [
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:Revenues",
            "us-gaap:SalesRevenueNet",
            "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
        ]
        rev = _extract_xbrl_value(facts, rev_tags, year)
        if rev is not None:
            result["revenue"] = round(rev / 1e6, 2)  # USD → 백만달러
        else:
            missing.append("revenue")

        # 영업이익
        oi = _extract_xbrl_value(facts, ["us-gaap:OperatingIncomeLoss"], year)
        if oi is not None:
            result["operating_income"] = round(oi / 1e6, 2)
            if result.get("revenue", 0) > 0:
                result["operating_margin"] = round(oi / (result["revenue"] * 1e6), 4)
            else:
                missing.append("operating_margin")
        else:
            missing.extend(["operating_income", "operating_margin"])

        # 인건비
        labor_tags = [
            "us-gaap:LaborAndRelatedExpense",
            "us-gaap:EmployeeBenefitsAndShareBasedCompensation",
        ]
        labor = _extract_xbrl_value(facts, labor_tags, year)
        if labor is not None:
            result["total_labor_cost"] = round(labor / 1e6, 2)
        else:
            missing.append("total_labor_cost")
            warnings.append("인건비 데이터 없음 (LaborAndRelatedExpense 미보고)")

        # 임직원 수
        emp = _extract_xbrl_value(facts, ["dei:EntityNumberOfEmployees"], year)
        if emp is not None:
            result["total_employees"] = int(emp)
            if result.get("total_labor_cost"):
                result["avg_salary_annual"] = round(
                    result["total_labor_cost"] / result["total_employees"], 4
                )
            else:
                missing.append("avg_salary_annual")
        else:
            missing.extend(["total_employees", "avg_salary_annual"])
            warnings.append("임직원 수 데이터 없음 (EntityNumberOfEmployees 미보고)")

    except Exception as e:
        missing.extend(["revenue", "operating_income", "operating_margin",
                        "total_labor_cost", "total_employees", "avg_salary_annual"])
        warnings.append(f"XBRL Company Facts 조회 실패: {e}")

    # Step 4: 시가총액 (yfinance)
    try:
        import yfinance as yf
        ticker_sym = result.get("stock_code", query)
        info = yf.Ticker(ticker_sym).info
        mc = info.get("marketCap")
        if mc:
            result["market_cap"] = round(mc / 1e6, 2)  # USD → 백만달러
            result["data_sources"].append("yfinance (실시간)")
        else:
            missing.append("market_cap")
    except Exception as e:
        missing.append("market_cap")
        warnings.append(f"시가총액 조회 실패: {e}")

    _cache_set(cache_key, result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 공통 래퍼
# ─────────────────────────────────────────────────────────────────────────────

def get_company_filing_data(query: str, country: str, year: int | None = None) -> dict:
    """
    국가에 따라 DART 또는 SEC EDGAR 자동 라우팅.
    year 미입력 시 직전 완료 사업연도 자동 선택.

    Parameters:
        query:   회사명, 종목코드(KR), 또는 티커(US)
        country: 'KR' 또는 'US'
        year:    사업연도 (None이면 최근 연도 자동)

    Returns:
        공통 구조 dict (source, company_name, fiscal_year, currency,
                       revenue, operating_income, operating_margin,
                       total_labor_cost, total_employees, avg_salary_annual,
                       market_cap, missing_fields, warnings)
    """
    if year is None:
        now = datetime.now()
        # 한국: 3월 말이 보고서 제출 기한, 4월 이후면 전년도 확인 가능
        year = now.year - 1 if now.month >= 4 else now.year - 2

    if country == "KR":
        return get_dart_company_data(query, year)
    elif country == "US":
        return get_sec_company_data(query, year)
    else:
        raise ValueError(f"지원 국가: KR, US. 입력값: {country}")
