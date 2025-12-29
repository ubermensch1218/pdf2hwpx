"""HWPX 콘텐츠 검색 및 쿼리"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from lxml import etree


NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
}


@dataclass
class PageBreakInfo:
    """페이지 브레이크 정보"""
    paragraph_index: int  # 몇 번째 단락 뒤에서 페이지가 바뀌는지
    paragraph_id: str  # 단락 ID
    break_type: str  # "explicit" (명시적) 또는 "column" (열 브레이크)
    text_preview: str  # 해당 단락의 텍스트 미리보기


@dataclass
class ParagraphInfo:
    """단락 정보"""
    index: int  # 0-based 인덱스
    paragraph_id: str
    text: str
    char_pr_ids: List[int]  # 사용된 문자 스타일 ID들
    para_pr_id: int  # 단락 스타일 ID
    has_table: bool
    has_image: bool
    page_estimate: int  # 추정 페이지 번호 (명시적 브레이크 기준)


@dataclass
class SearchResult:
    """검색 결과"""
    paragraph_index: int
    paragraph_id: str
    text: str  # 전체 단락 텍스트
    match_start: int  # 매칭 시작 위치
    match_end: int  # 매칭 끝 위치
    context: str  # 매칭 주변 컨텍스트
    page_estimate: int  # 추정 페이지


class HwpxSearcher:
    """HWPX 콘텐츠 검색기"""

    def __init__(self, section_xml: bytes):
        """
        Args:
            section_xml: section0.xml 바이트
        """
        self.root = etree.fromstring(section_xml)
        self._paragraphs: List[etree._Element] = []
        self._page_breaks: List[int] = []  # 페이지 브레이크가 있는 단락 인덱스
        self._parse()

    def _parse(self):
        """섹션 파싱하여 단락 목록과 페이지 브레이크 수집"""
        # 모든 단락 수집 (중첩된 것 포함)
        self._paragraphs = self.root.xpath(".//hp:p", namespaces=NS)

        # 페이지 브레이크 탐지
        for i, p in enumerate(self._paragraphs):
            if p.get("pageBreak") == "1":
                self._page_breaks.append(i)
            if p.get("columnBreak") == "1":
                self._page_breaks.append(i)

    def _get_paragraph_text(self, p: etree._Element) -> str:
        """단락에서 텍스트 추출"""
        texts = []
        for t in p.xpath(".//hp:t", namespaces=NS):
            if t.text:
                texts.append(t.text)
            if t.tail:
                texts.append(t.tail)
        return "".join(texts)

    def _estimate_page(self, para_index: int) -> int:
        """단락 인덱스로 페이지 번호 추정 (명시적 브레이크 기준)"""
        page = 1
        for break_idx in self._page_breaks:
            if break_idx < para_index:
                page += 1
            else:
                break
        return page

    # ============================================================
    # 1. 페이지 브레이크 탐지
    # ============================================================

    def find_page_breaks(self) -> List[PageBreakInfo]:
        """모든 명시적 페이지/열 브레이크 찾기"""
        results = []

        for i, p in enumerate(self._paragraphs):
            page_break = p.get("pageBreak") == "1"
            col_break = p.get("columnBreak") == "1"

            if page_break or col_break:
                text = self._get_paragraph_text(p)
                results.append(PageBreakInfo(
                    paragraph_index=i,
                    paragraph_id=p.get("id", ""),
                    break_type="explicit" if page_break else "column",
                    text_preview=text[:100] + "..." if len(text) > 100 else text,
                ))

        return results

    def get_page_count_estimate(self) -> int:
        """추정 페이지 수 (명시적 브레이크 기준)"""
        return len(self._page_breaks) + 1

    # ============================================================
    # 2. N번째 단락 가져오기
    # ============================================================

    def get_paragraph_count(self) -> int:
        """전체 단락 수"""
        return len(self._paragraphs)

    def get_paragraph(self, index: int) -> Optional[ParagraphInfo]:
        """N번째 단락 가져오기 (0-based)"""
        if index < 0 or index >= len(self._paragraphs):
            return None

        p = self._paragraphs[index]
        text = self._get_paragraph_text(p)

        # 문자 스타일 ID 수집
        char_pr_ids = []
        for run in p.xpath("./hp:run", namespaces=NS):
            char_id = run.get("charPrIDRef")
            if char_id:
                char_pr_ids.append(int(char_id))

        # 테이블/이미지 존재 여부
        has_table = len(p.xpath(".//hp:tbl", namespaces=NS)) > 0
        has_image = len(p.xpath(".//hp:pic", namespaces=NS)) > 0

        return ParagraphInfo(
            index=index,
            paragraph_id=p.get("id", ""),
            text=text,
            char_pr_ids=char_pr_ids,
            para_pr_id=int(p.get("paraPrIDRef", "0")),
            has_table=has_table,
            has_image=has_image,
            page_estimate=self._estimate_page(index),
        )

    def get_paragraphs_range(self, start: int, end: int) -> List[ParagraphInfo]:
        """범위 내 단락들 가져오기"""
        results = []
        for i in range(max(0, start), min(end, len(self._paragraphs))):
            para = self.get_paragraph(i)
            if para:
                results.append(para)
        return results

    def get_paragraphs_by_page(self, page: int) -> List[ParagraphInfo]:
        """특정 페이지의 단락들 가져오기 (추정)"""
        results = []
        for i in range(len(self._paragraphs)):
            para = self.get_paragraph(i)
            if para and para.page_estimate == page:
                results.append(para)
        return results

    # ============================================================
    # 3. 텍스트 검색
    # ============================================================

    def search(self, query: str, case_sensitive: bool = False) -> List[SearchResult]:
        """텍스트 검색"""
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)

        for i, p in enumerate(self._paragraphs):
            text = self._get_paragraph_text(p)

            for match in pattern.finditer(text):
                # 컨텍스트 추출 (매칭 전후 50자)
                ctx_start = max(0, match.start() - 50)
                ctx_end = min(len(text), match.end() + 50)
                context = text[ctx_start:ctx_end]
                if ctx_start > 0:
                    context = "..." + context
                if ctx_end < len(text):
                    context = context + "..."

                results.append(SearchResult(
                    paragraph_index=i,
                    paragraph_id=p.get("id", ""),
                    text=text,
                    match_start=match.start(),
                    match_end=match.end(),
                    context=context,
                    page_estimate=self._estimate_page(i),
                ))

        return results

    def search_regex(self, pattern: str, flags: int = 0) -> List[SearchResult]:
        """정규식 검색"""
        results = []
        regex = re.compile(pattern, flags)

        for i, p in enumerate(self._paragraphs):
            text = self._get_paragraph_text(p)

            for match in regex.finditer(text):
                ctx_start = max(0, match.start() - 50)
                ctx_end = min(len(text), match.end() + 50)
                context = text[ctx_start:ctx_end]
                if ctx_start > 0:
                    context = "..." + context
                if ctx_end < len(text):
                    context = context + "..."

                results.append(SearchResult(
                    paragraph_index=i,
                    paragraph_id=p.get("id", ""),
                    text=text,
                    match_start=match.start(),
                    match_end=match.end(),
                    context=context,
                    page_estimate=self._estimate_page(i),
                ))

        return results

    # ============================================================
    # 유틸리티
    # ============================================================

    def get_all_text(self) -> str:
        """전체 텍스트 추출"""
        texts = []
        for p in self._paragraphs:
            text = self._get_paragraph_text(p)
            if text.strip():
                texts.append(text)
        return "\n".join(texts)

    def get_text_by_page(self, page: int) -> str:
        """특정 페이지의 텍스트 추출 (추정)"""
        paragraphs = self.get_paragraphs_by_page(page)
        return "\n".join(p.text for p in paragraphs if p.text.strip())

    def get_tables_info(self) -> List[dict]:
        """모든 테이블 정보"""
        tables = []
        for i, tbl in enumerate(self.root.xpath(".//hp:tbl", namespaces=NS)):
            row_cnt = tbl.get("rowCnt", "0")
            col_cnt = tbl.get("colCnt", "0")

            # 테이블 내 텍스트
            texts = []
            for t in tbl.xpath(".//hp:t", namespaces=NS):
                if t.text:
                    texts.append(t.text)

            tables.append({
                "index": i,
                "rows": int(row_cnt),
                "cols": int(col_cnt),
                "text_preview": " ".join(texts)[:200],
            })
        return tables

    def get_images_info(self) -> List[dict]:
        """모든 이미지 정보"""
        images = []
        for i, pic in enumerate(self.root.xpath(".//hp:pic", namespaces=NS)):
            img = pic.xpath(".//hc:img", namespaces=NS)
            binary_ref = img[0].get("binaryItemIDRef") if img else ""

            # 크기
            cur_sz = pic.xpath("./hp:curSz", namespaces=NS)
            width = cur_sz[0].get("width") if cur_sz else "0"
            height = cur_sz[0].get("height") if cur_sz else "0"

            images.append({
                "index": i,
                "binary_ref": binary_ref,
                "width": int(width),
                "height": int(height),
            })
        return images
