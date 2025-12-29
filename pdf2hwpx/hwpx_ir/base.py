"""HWPX IR 공통 유틸리티 및 네임스페이스 정의"""

from __future__ import annotations

from typing import List, Optional

from lxml import etree


# HWPX XML 네임스페이스
NS = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "opf": "http://www.idpf.org/2007/opf/",
}


def is_tag(elem: etree._Element, prefix: str, local: str) -> bool:
    """XML 요소의 태그 이름 확인"""
    return elem.tag == f"{{{NS[prefix]}}}{local}"


def qname(prefix: str, local: str) -> etree.QName:
    """네임스페이스 QName 생성"""
    return etree.QName(NS[prefix], local)


def first_int(values: List[str], default: Optional[int] = None) -> Optional[int]:
    """리스트에서 첫 번째 정수 추출"""
    if not values:
        return default
    try:
        return int(values[0])
    except (ValueError, TypeError):
        return default


def first_str(values: List[str], default: Optional[str] = None) -> Optional[str]:
    """리스트에서 첫 번째 문자열 추출"""
    if not values:
        return default
    return values[0]


def guess_media_type(filename: str) -> str:
    """파일 확장자로 미디어 타입 추측"""
    lower = filename.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".bmp"):
        return "image/bmp"
    return "application/octet-stream"


def hex_color_to_hwpx(color: str) -> str:
    """HEX 색상을 HWPX 형식으로 변환 (#RRGGBB)"""
    if color.startswith("#"):
        return color
    return f"#{color}"


def hwpx_color_to_hex(color: str) -> str:
    """HWPX 색상을 HEX 형식으로 변환"""
    if color.startswith("#"):
        return color
    return f"#{color}"


# HWPX 단위 변환 상수
HWPUNIT_PER_INCH = 1440
HWPUNIT_PER_MM = 56.7  # 약 56.7 (1440 / 25.4)
HWPUNIT_PER_PT = 20  # 1440 / 72

# A4 크기 (HWPUNIT)
A4_WIDTH = 59528   # 210mm
A4_HEIGHT = 84188  # 297mm


def mm_to_hwpunit(mm: float) -> int:
    """밀리미터를 HWPUNIT으로 변환"""
    return int(mm * HWPUNIT_PER_MM)


def hwpunit_to_mm(hwpunit: int) -> float:
    """HWPUNIT을 밀리미터로 변환"""
    return hwpunit / HWPUNIT_PER_MM


def pt_to_hwpunit(pt: float) -> int:
    """포인트를 HWPUNIT으로 변환"""
    return int(pt * HWPUNIT_PER_PT)


def hwpunit_to_pt(hwpunit: int) -> float:
    """HWPUNIT을 포인트로 변환"""
    return hwpunit / HWPUNIT_PER_PT
