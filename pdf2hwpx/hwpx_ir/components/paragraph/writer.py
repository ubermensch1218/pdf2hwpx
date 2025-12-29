"""단락 Writer"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname
from pdf2hwpx.hwpx_ir.models import IrParagraph, IrTextRun, IrLineBreak

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import StyleManager


class ParagraphWriter:
    """단락 생성"""

    def __init__(self, style_manager: Optional["StyleManager"] = None):
        self.style_manager = style_manager

    def build(self, para: IrParagraph, paragraph_id: int) -> etree._Element:
        """IrParagraph를 hp:p 요소로 변환"""
        if para.raw_xml:
            return etree.fromstring(para.raw_xml)

        p = etree.Element(qname("hp", "p"))
        p.set("id", str(paragraph_id))

        # 단락 속성 ID (TODO: StyleManager에서 관리)
        para_pr_id = self._get_para_pr_id(para)
        p.set("paraPrIDRef", str(para_pr_id))
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        if not para.inlines:
            # 빈 단락
            run = etree.SubElement(p, qname("hp", "run"))
            run.set("charPrIDRef", "0")
            return p

        for inline in para.inlines:
            run = etree.SubElement(p, qname("hp", "run"))

            # 스타일 ID 결정
            char_pr_id = 0
            if isinstance(inline, IrTextRun) and self.style_manager:
                char_pr_id = self.style_manager.get_char_pr_id(inline)
            run.set("charPrIDRef", str(char_pr_id))

            if isinstance(inline, IrTextRun):
                parts = inline.text.split("\n")
                for idx, part in enumerate(parts):
                    if idx > 0:
                        etree.SubElement(run, qname("hp", "lineBreak"))
                    if part:
                        t = etree.SubElement(run, qname("hp", "t"))
                        t.text = part

            elif isinstance(inline, IrLineBreak):
                etree.SubElement(run, qname("hp", "lineBreak"))

        return p

    def _get_para_pr_id(self, para: IrParagraph) -> int:
        """단락 속성 ID 반환 (기본값 0)"""
        # TODO: StyleManager에서 단락 스타일 관리
        # 현재는 기본 스타일 사용
        if (
            para.alignment == "left"
            and para.line_spacing_type == "percent"
            and para.line_spacing_value == 160
            and para.indent_left == 0
            and para.indent_right == 0
            and para.indent_first_line == 0
            and para.background_color is None
        ):
            return 0
        # TODO: 새 단락 스타일 생성
        return 0

    def build_empty(self, paragraph_id: int) -> etree._Element:
        """빈 단락 생성"""
        return self.build(IrParagraph(), paragraph_id)
