"""각주/미주 Writer"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrFootnote, IrEndnote

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import HwpxIdContext
    from pdf2hwpx.hwpx_ir.components.paragraph.writer import ParagraphWriter


class FootnoteWriter:
    """각주/미주 생성"""

    def __init__(self, paragraph_writer: "ParagraphWriter"):
        self.paragraph_writer = paragraph_writer

    def build_footnote(self, footnote: IrFootnote, context: "HwpxIdContext") -> etree._Element:
        """IrFootnote를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        fn = etree.SubElement(ctrl, qname("hp", "footNote"))
        fn.set("number", str(footnote.number))

        # 각주 내용
        sub_list = etree.SubElement(fn, qname("hp", "subList"))
        sub_list.set("textDirection", "HORIZONTAL")
        sub_list.set("lineWrap", "BREAK")
        sub_list.set("vertAlign", "TOP")

        for para in footnote.content:
            p = self.paragraph_writer.build(para, context.next_para_id())
            sub_list.append(p)

        # 빈 각주면 빈 단락 추가
        if not footnote.content:
            p = self.paragraph_writer.build_empty(context.next_para_id())
            sub_list.append(p)

        return ctrl

    def build_endnote(self, endnote: IrEndnote, context: "HwpxIdContext") -> etree._Element:
        """IrEndnote를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        en = etree.SubElement(ctrl, qname("hp", "endNote"))
        en.set("number", str(endnote.number))

        # 미주 내용
        sub_list = etree.SubElement(en, qname("hp", "subList"))
        sub_list.set("textDirection", "HORIZONTAL")
        sub_list.set("lineWrap", "BREAK")
        sub_list.set("vertAlign", "TOP")

        for para in endnote.content:
            p = self.paragraph_writer.build(para, context.next_para_id())
            sub_list.append(p)

        # 빈 미주면 빈 단락 추가
        if not endnote.content:
            p = self.paragraph_writer.build_empty(context.next_para_id())
            sub_list.append(p)

        return ctrl

    def build_footnote_ref(self, number: int) -> etree._Element:
        """각주 참조 (본문 내 각주 번호) 생성"""
        # 각주 참조는 자동 번호 필드로 표현
        t = etree.Element(qname("hp", "t"))
        t.text = f"[{number}]"
        return t
