"""각주/미주 Reader"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int
from pdf2hwpx.hwpx_ir.models import IrFootnote, IrEndnote, IrParagraph

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.components.paragraph.reader import ParagraphReader


class FootnoteReader:
    """각주/미주 파싱"""

    def __init__(self, paragraph_reader: "ParagraphReader"):
        self.paragraph_reader = paragraph_reader

    def parse_footnote(self, ctrl: etree._Element) -> Optional[IrFootnote]:
        """hp:ctrl 내 각주 요소 파싱"""
        fn = ctrl.xpath(".//hp:footNote", namespaces=NS)
        if not fn:
            return None

        footnote = fn[0]
        number = first_int([footnote.get("number", "1")], 1)

        # 각주 내용 파싱
        content: List[IrParagraph] = []
        for p in footnote.xpath(".//hp:subList//hp:p", namespaces=NS):
            para = self.paragraph_reader.parse(p)
            content.append(para)

        return IrFootnote(
            number=number,
            content=content,
        )

    def parse_endnote(self, ctrl: etree._Element) -> Optional[IrEndnote]:
        """hp:ctrl 내 미주 요소 파싱"""
        en = ctrl.xpath(".//hp:endNote", namespaces=NS)
        if not en:
            return None

        endnote = en[0]
        number = first_int([endnote.get("number", "1")], 1)

        # 미주 내용 파싱
        content: List[IrParagraph] = []
        for p in endnote.xpath(".//hp:subList//hp:p", namespaces=NS):
            para = self.paragraph_reader.parse(p)
            content.append(para)

        return IrEndnote(
            number=number,
            content=content,
        )

    def is_footnote(self, ctrl: etree._Element) -> bool:
        """요소가 각주인지 확인"""
        return len(ctrl.xpath(".//hp:footNote", namespaces=NS)) > 0

    def is_endnote(self, ctrl: etree._Element) -> bool:
        """요소가 미주인지 확인"""
        return len(ctrl.xpath(".//hp:endNote", namespaces=NS)) > 0
