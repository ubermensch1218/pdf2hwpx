"""목차 Writer"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrTOC, IrTOCEntry, IrParagraph, IrTextRun

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import HwpxIdContext
    from pdf2hwpx.hwpx_ir.components.paragraph.writer import ParagraphWriter


class TOCWriter:
    """목차 생성"""

    def __init__(self, paragraph_writer: "ParagraphWriter"):
        self.paragraph_writer = paragraph_writer

    def build(self, toc: IrTOC, context: "HwpxIdContext") -> List[etree._Element]:
        """IrTOC를 단락 요소들로 변환"""
        elements = []

        # 목차 제목
        title_para = IrParagraph(
            inlines=[IrTextRun(text=toc.title, bold=True, font_size=1400)],
            alignment="center",
        )
        elements.append(self.paragraph_writer.build(title_para, context.next_para_id()))

        # 빈 줄
        elements.append(self.paragraph_writer.build_empty(context.next_para_id()))

        # 목차 항목들
        for entry in toc.entries:
            entry_elem = self._build_entry(entry, toc, context)
            elements.append(entry_elem)

        return elements

    def _build_entry(
        self,
        entry: IrTOCEntry,
        toc: IrTOC,
        context: "HwpxIdContext",
    ) -> etree._Element:
        """목차 항목을 단락으로 변환"""
        # 레벨에 따른 들여쓰기
        indent = (entry.level - 1) * 500  # 레벨당 500 HWPUNIT

        # 텍스트 구성
        text = entry.text
        if toc.show_page_numbers and entry.page_number:
            # 탭과 페이지 번호 추가
            text = f"{entry.text}\t{entry.page_number}"

        para = IrParagraph(
            inlines=[IrTextRun(text=text)],
            indent_left=indent,
        )

        return self.paragraph_writer.build(para, context.next_para_id())

    def build_toc_field(self) -> etree._Element:
        """목차 필드 (자동 생성용) 생성"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        toc = etree.SubElement(ctrl, qname("hp", "toc"))
        toc.set("title", "목차")
        toc.set("maxLevel", "3")
        toc.set("showPageNumbers", "1")
        toc.set("useHyperlinks", "1")

        return ctrl
