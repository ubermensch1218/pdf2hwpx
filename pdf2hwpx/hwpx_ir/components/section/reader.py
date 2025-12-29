"""섹션 Reader"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int, first_str
from pdf2hwpx.hwpx_ir.models import IrSection, IrHeader, IrFooter, IrBlock

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.components.paragraph.reader import ParagraphReader
    from pdf2hwpx.hwpx_ir.components.table.reader import TableReader
    from pdf2hwpx.hwpx_ir.components.image.reader import ImageReader


class SectionReader:
    """섹션 파싱"""

    def __init__(
        self,
        paragraph_reader: "ParagraphReader",
        table_reader: "TableReader",
        image_reader: "ImageReader",
    ):
        self.paragraph_reader = paragraph_reader
        self.table_reader = table_reader
        self.image_reader = image_reader

    def parse(self, section_xml: bytes, preserve_raw: bool = True) -> IrSection:
        """섹션 XML에서 IrSection 파싱

        Args:
            section_xml: 섹션 XML 바이트
            preserve_raw: True면 raw_xml 보존 (100% 라운드트립용)
        """
        root = etree.fromstring(section_xml)

        # 섹션 속성 파싱
        sec_pr = root.xpath(".//hp:secPr", namespaces=NS)
        col_count = 1
        col_gap = 0
        col_line_type = None
        page_width = 59528
        page_height = 84188

        if sec_pr:
            sp = sec_pr[0]
            # 페이지 크기
            page_pr = sp.xpath("./hp:pagePr", namespaces=NS)
            if page_pr:
                pp = page_pr[0]
                page_width = first_int([pp.get("width", "59528")], 59528)
                page_height = first_int([pp.get("height", "84188")], 84188)

        # 열 속성
        col_pr = root.xpath(".//hp:colPr", namespaces=NS)
        if col_pr:
            cp = col_pr[0]
            col_count = first_int([cp.get("colCount", "1")], 1)
            col_gap = first_int([cp.get("sameGap", "0")], 0)
            col_line = cp.xpath("./hp:colLine", namespaces=NS)
            if col_line:
                col_line_type = col_line[0].get("type")

        # 머리글/바닥글
        header = self._parse_header(root)
        footer = self._parse_footer(root)

        # 블록들 파싱
        blocks = self._parse_blocks(root)

        # raw_xml 보존 (100% 라운드트립용)
        raw_xml = section_xml if preserve_raw else None

        return IrSection(
            blocks=blocks,
            col_count=col_count,
            col_gap=col_gap,
            header=header,
            footer=footer,
            page_width=page_width,
            page_height=page_height,
            col_line_type=col_line_type,
            raw_xml=raw_xml,
        )

    def _parse_header(self, root: etree._Element) -> Optional[IrHeader]:
        """머리글 파싱"""
        headers = root.xpath(".//hp:header", namespaces=NS)
        if not headers:
            return None

        h = headers[0]
        height = first_int([h.get("height", "1500")], 1500)

        # 텍스트 추출
        text_parts = []
        for t in h.xpath(".//hp:t", namespaces=NS):
            if t.text:
                text_parts.append(t.text)
        text = "".join(text_parts)

        return IrHeader(text=text, height=height)

    def _parse_footer(self, root: etree._Element) -> Optional[IrFooter]:
        """바닥글 파싱"""
        footers = root.xpath(".//hp:footer", namespaces=NS)
        if not footers:
            return None

        f = footers[0]
        height = first_int([f.get("height", "1500")], 1500)

        # 텍스트 추출
        text_parts = []
        for t in f.xpath(".//hp:t", namespaces=NS):
            if t.text:
                text_parts.append(t.text)
        text = "".join(text_parts)

        # 페이지 번호 표시 여부
        show_page_number = len(f.xpath(".//hp:fieldBegin[@type='PAGE']", namespaces=NS)) > 0

        return IrFooter(text=text, height=height, show_page_number=show_page_number)

    def _parse_blocks(self, root: etree._Element) -> List[IrBlock]:
        """섹션 내 블록들 파싱"""
        from pdf2hwpx.hwpx_ir.base import is_tag

        blocks: List[IrBlock] = []

        for elem in root:
            if is_tag(elem, "hp", "p"):
                para = self.paragraph_reader.parse(elem)
                blocks.append(IrBlock(type="paragraph", paragraph=para))
            elif is_tag(elem, "hp", "tbl"):
                table = self.table_reader.parse(elem)
                blocks.append(IrBlock(type="table", table=table))
            elif is_tag(elem, "hp", "pic"):
                image = self.image_reader.parse(elem)
                if image:
                    blocks.append(IrBlock(type="image", image=image))

        return blocks
