"""표 Reader"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, is_tag, first_int
from pdf2hwpx.hwpx_ir.models import IrTable, IrTableCell, IrBlock, IrParagraph

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.components.paragraph.reader import ParagraphReader


class TableReader:
    """표 파싱"""

    def __init__(self, paragraph_reader: "ParagraphReader"):
        self.paragraph_reader = paragraph_reader

    def parse(self, tbl: etree._Element) -> IrTable:
        """hp:tbl 요소에서 IrTable 파싱"""
        row_cnt = int(tbl.get("rowCnt", "0"))
        col_cnt = int(tbl.get("colCnt", "0"))
        border_fill_id = first_int([tbl.get("borderFillIDRef", "5")], 5)

        width = first_int(tbl.xpath("./hp:sz/@width", namespaces=NS))
        height = first_int(tbl.xpath("./hp:sz/@height", namespaces=NS))
        treat_as_char = first_int(tbl.xpath("./hp:pos/@treatAsChar", namespaces=NS)) != 0

        cells: List[IrTableCell] = []
        for tc in tbl.xpath(".//hp:tc", namespaces=NS):
            cell = self._parse_cell(tc)
            cells.append(cell)

        raw_xml = etree.tostring(tbl, encoding="UTF-8")

        return IrTable(
            row_cnt=row_cnt,
            col_cnt=col_cnt,
            cells=cells,
            width_hwpunit=width,
            height_hwpunit=height,
            treat_as_char=treat_as_char,
            raw_xml=raw_xml,
            border_fill_id=border_fill_id,
        )

    def _parse_cell(self, tc: etree._Element) -> IrTableCell:
        """hp:tc 요소에서 IrTableCell 파싱"""
        row = first_int(tc.xpath("./hp:cellAddr/@rowAddr", namespaces=NS), 0)
        col = first_int(tc.xpath("./hp:cellAddr/@colAddr", namespaces=NS), 0)
        row_span = first_int(tc.xpath("./hp:cellSpan/@rowSpan", namespaces=NS), 1)
        col_span = first_int(tc.xpath("./hp:cellSpan/@colSpan", namespaces=NS), 1)
        cell_width = first_int(tc.xpath("./hp:cellSz/@width", namespaces=NS))
        cell_height = first_int(tc.xpath("./hp:cellSz/@height", namespaces=NS))
        border_fill_id = first_int([tc.get("borderFillIDRef", "5")], 5)

        # 셀 내용 파싱
        blocks: List[IrBlock] = []
        for p in tc.xpath(".//hp:subList//hp:p", namespaces=NS):
            para = self.paragraph_reader.parse(p)
            blocks.append(IrBlock(type="paragraph", paragraph=para))

        return IrTableCell(
            row=row,
            col=col,
            row_span=row_span,
            col_span=col_span,
            blocks=blocks,
            width_hwpunit=cell_width,
            height_hwpunit=cell_height,
            border_fill_id=border_fill_id,
        )
