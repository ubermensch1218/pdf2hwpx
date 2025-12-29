"""텍스트/인라인 요소 Writer"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname
from pdf2hwpx.hwpx_ir.models import IrTextRun, IrLineBreak

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import StyleManager


class TextWriter:
    """텍스트 런 및 인라인 요소 생성"""

    def __init__(self, style_manager: Optional["StyleManager"] = None):
        self.style_manager = style_manager

    def build_run(self, text_run: IrTextRun) -> etree._Element:
        """IrTextRun을 hp:run 요소로 변환"""
        run = etree.Element(qname("hp", "run"))

        # 스타일 ID 결정
        char_pr_id = 0
        if self.style_manager:
            char_pr_id = self.style_manager.get_char_pr_id(text_run)
        run.set("charPrIDRef", str(char_pr_id))

        # 텍스트 내용
        parts = text_run.text.split("\n")
        for idx, part in enumerate(parts):
            if idx > 0:
                etree.SubElement(run, qname("hp", "lineBreak"))
            if part:
                t = etree.SubElement(run, qname("hp", "t"))
                t.text = part

        return run

    def build_line_break(self) -> etree._Element:
        """IrLineBreak를 hp:lineBreak 요소로 변환"""
        return etree.Element(qname("hp", "lineBreak"))

    def append_text_to_run(self, run: etree._Element, text: str):
        """기존 run에 텍스트 추가"""
        t = etree.SubElement(run, qname("hp", "t"))
        t.text = text

    def append_line_break_to_run(self, run: etree._Element):
        """기존 run에 줄바꿈 추가"""
        etree.SubElement(run, qname("hp", "lineBreak"))
