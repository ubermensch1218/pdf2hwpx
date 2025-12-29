"""목차 Reader"""

from __future__ import annotations

from typing import List, Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int
from pdf2hwpx.hwpx_ir.models import IrTOC, IrTOCEntry


class TOCReader:
    """목차 파싱"""

    def parse(self, ctrl: etree._Element) -> Optional[IrTOC]:
        """hp:ctrl 내 목차 요소 파싱"""
        toc = ctrl.xpath(".//hp:toc", namespaces=NS)
        if not toc:
            return None

        t = toc[0]
        title = t.get("title", "목차")
        max_level = first_int([t.get("maxLevel", "3")], 3)
        show_page_numbers = t.get("showPageNumbers", "1") == "1"
        use_hyperlinks = t.get("useHyperlinks", "1") == "1"

        # 목차 항목 파싱
        entries: List[IrTOCEntry] = []
        for entry in t.xpath(".//hp:tocEntry", namespaces=NS):
            text = entry.get("text", "")
            level = first_int([entry.get("level", "1")], 1)
            page_number = first_int([entry.get("pageNumber")])
            bookmark_name = entry.get("bookmarkName")

            entries.append(IrTOCEntry(
                text=text,
                level=level,
                page_number=page_number,
                bookmark_name=bookmark_name,
            ))

        return IrTOC(
            entries=entries,
            title=title,
            max_level=max_level,
            show_page_numbers=show_page_numbers,
            use_hyperlinks=use_hyperlinks,
        )

    def is_toc(self, ctrl: etree._Element) -> bool:
        """요소가 목차인지 확인"""
        return len(ctrl.xpath(".//hp:toc", namespaces=NS)) > 0
