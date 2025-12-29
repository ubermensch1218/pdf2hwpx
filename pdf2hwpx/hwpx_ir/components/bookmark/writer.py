"""북마크 Writer"""

from __future__ import annotations

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrBookmark


class BookmarkWriter:
    """북마크 생성"""

    def build(self, bookmark: IrBookmark) -> etree._Element:
        """IrBookmark를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        # bookmark
        bm = etree.SubElement(ctrl, qname("hp", "bookmark"))
        bm.set("name", bookmark.name)
        bm.set("type", "START")  # START/END 쌍으로 사용

        # 텍스트가 있으면 추가
        if bookmark.text:
            run = etree.SubElement(ctrl, qname("hp", "run"))
            run.set("charPrIDRef", "0")
            t = etree.SubElement(run, qname("hp", "t"))
            t.text = bookmark.text

        return ctrl

    def build_end(self, bookmark_name: str) -> etree._Element:
        """북마크 종료 요소 생성"""
        ctrl = etree.Element(qname("hp", "ctrl"))
        bm = etree.SubElement(ctrl, qname("hp", "bookmark"))
        bm.set("name", bookmark_name)
        bm.set("type", "END")
        return ctrl
