"""캡션 Writer"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrCaption, IrParagraph, IrTextRun

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import HwpxIdContext
    from pdf2hwpx.hwpx_ir.components.paragraph.writer import ParagraphWriter


class CaptionWriter:
    """캡션 생성"""

    def __init__(self, paragraph_writer: "ParagraphWriter"):
        self.paragraph_writer = paragraph_writer

    def build(self, caption: IrCaption, context: "HwpxIdContext") -> etree._Element:
        """IrCaption을 단락 요소로 변환"""
        # 캡션 텍스트 구성
        text_parts = []

        if caption.prefix:
            text_parts.append(caption.prefix)

        if caption.number is not None:
            text_parts.append(str(caption.number))

        if text_parts:
            text_parts.append(". ")

        text_parts.append(caption.text)

        full_text = "".join(text_parts)

        # 캡션 단락 생성
        para = IrParagraph(
            inlines=[IrTextRun(text=full_text, font_size=900)],  # 9pt
            alignment="center",
        )

        return self.paragraph_writer.build(para, context.next_para_id())

    def build_ctrl(self, caption: IrCaption) -> etree._Element:
        """IrCaption을 hp:ctrl/hp:caption 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        c = etree.SubElement(ctrl, qname("hp", "caption"))

        # 대상 타입
        type_map = {
            "image": "PICTURE",
            "table": "TABLE",
            "equation": "EQUATION",
        }
        c.set("type", type_map.get(caption.target_type, "PICTURE"))

        # 위치
        c.set("side", "BOTTOM" if caption.position == "below" else "TOP")

        if caption.number is not None:
            c.set("number", str(caption.number))

        if caption.prefix:
            c.set("prefix", caption.prefix)

        # 캡션 내용
        sub_list = etree.SubElement(c, qname("hp", "subList"))
        sub_list.set("textDirection", "HORIZONTAL")

        p = etree.SubElement(sub_list, qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        t = etree.SubElement(run, qname("hp", "t"))
        t.text = caption.text

        return ctrl

    def get_default_prefix(self, target_type: str) -> str:
        """대상 타입에 따른 기본 접두사 반환"""
        prefixes = {
            "image": "그림",
            "table": "표",
            "equation": "수식",
        }
        return prefixes.get(target_type, "")
