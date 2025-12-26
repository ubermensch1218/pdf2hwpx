"""빌링 모듈 - API 키 검증 및 사용량 추적"""

import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum

import httpx


class Tier(str, Enum):
    """사용자 티어"""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"


@dataclass
class ApiKeyInfo:
    """API 키 정보"""
    api_key: str
    tier: Tier
    quota_limit: int  # 월 페이지 제한
    quota_used: int   #本月 사용량
    active: bool


@dataclass
class UsageRecord:
    """사용량 기록"""
    api_key: str
    pages: int
    timestamp: str


class BillingError(Exception):
    """빌링 에러"""
    pass


class QuotaExceededError(BillingError):
    """한도 초과"""
    pass


class InvalidApiKeyError(BillingError):
    """유효하지 않은 API 키"""
    pass


class BillingService:
    """빌링 서비스"""

    # 티어별 한도
    TIER_LIMITS = {
        Tier.FREE: 50,
        Tier.STARTER: 1_000,
        Tier.PRO: 10_000,
        Tier.BUSINESS: 100_000,
    }

    def __init__(self):
        self.db_url = os.getenv("BILLING_DB_URL")
        self.db_secret = os.getenv("BILLING_DB_SECRET")

    async def verify_api_key(self, api_key: str) -> ApiKeyInfo:
        """
        API 키 검증 및 사용량 조회

        Args:
            api_key: API 키 (pk_xxx 형식)

        Returns:
            ApiKeyInfo

        Raises:
            InvalidApiKeyError: 유효하지 않은 키
        """
        # TODO: 실제 DB 조회 (Firestore/PostgreSQL)
        # 지금은 mock으로 처리

        # 키 형식 검증
        if not api_key.startswith("pk_"):
            raise InvalidApiKeyError("Invalid API key format")

        # Mock 데이터 (실제로는 DB 조회)
        if api_key == "pk_test_free":
            return ApiKeyInfo(
                api_key=api_key,
                tier=Tier.FREE,
                quota_limit=self.TIER_LIMITS[Tier.FREE],
                quota_used=10,
                active=True,
            )
        elif api_key == "pk_test_starter":
            return ApiKeyInfo(
                api_key=api_key,
                tier=Tier.STARTER,
                quota_limit=self.TIER_LIMITS[Tier.STARTER],
                quota_used=500,
                active=True,
            )
        elif api_key == "pk_test_pro":
            return ApiKeyInfo(
                api_key=api_key,
                tier=Tier.PRO,
                quota_limit=self.TIER_LIMITS[Tier.PRO],
                quota_used=5_000,
                active=True,
            )

        # 실제 DB 조회
        return await self._fetch_api_key_info(api_key)

    async def _fetch_api_key_info(self, api_key: str) -> ApiKeyInfo:
        """DB에서 API 키 정보 조회"""
        # TODO: 실제 구현
        # - Firestore 또는 PostgreSQL 조회
        # - 월 사용량 집계
        raise InvalidApiKeyError("API key not found")

    async def check_quota(self, api_key_info: ApiKeyInfo, pages: int) -> None:
        """
        사용량 한도 체크

        Args:
            api_key_info: API 키 정보
            pages: 변환할 페이지 수

        Raises:
            QuotaExceededError: 한도 초과
        """
        if not api_key_info.active:
            raise QuotaExceededError("API key is inactive")

        new_usage = api_key_info.quota_used + pages
        if new_usage > api_key_info.quota_limit:
            raise QuotaExceededError(
                f"Quota exceeded: {api_key_info.quota_used}/{api_key_info.quota_limit} pages used. "
                f"Trying to add {pages} more pages."
            )

    async def record_usage(self, api_key: str, pages: int) -> None:
        """
        사용량 기록

        Args:
            api_key: API 키
            pages: 사용 페이지 수
        """
        # TODO: 실제 DB 기록
        # - 사용량 로그 테이블에 삽입
        # - 월 집계 테이블 업데이트
        pass

    def count_pdf_pages(self, pdf_bytes: bytes) -> int:
        """
        PDF 페이지 수 계산

        Args:
            pdf_bytes: PDF 바이트

        Returns:
            페이지 수
        """
        try:
            import pypdf
            from io import BytesIO

            reader = pypdf.PdfReader(BytesIO(pdf_bytes))
            return len(reader.pages)
        except Exception:
            # 실패 시 1 페이지로 간주
            return 1


# 전역 인스턴스
billing_service = BillingService()
