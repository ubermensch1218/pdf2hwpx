"""북마크 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS
from pdf2hwpx.hwpx_ir.models import IrBookmark


class BookmarkReader:
    """북마크 파싱"""

    def parse(self, ctrl: etree._Element) -> Optional[IrBookmark]:
        """hp:ctrl 내 북마크 요소 파싱"""
        bookmark = ctrl.xpath(".//hp:bookmark", namespaces=NS)
        if not bookmark:
            return None

        bm = bookmark[0]
        name = bm.get("name", "")

        if not name:
            return None

        # 북마크 텍스트 추출
        text_parts = []
        for t in ctrl.xpath(".//hp:t", namespaces=NS):
            if t.text:
                text_parts.append(t.text)
        text = "".join(text_parts) if text_parts else None

        return IrBookmark(
            name=name,
            text=text,
        )

    def is_bookmark(self, ctrl: etree._Element) -> bool:
        """요소가 북마크인지 확인"""
        return len(ctrl.xpath(".//hp:bookmark", namespaces=NS)) > 0
