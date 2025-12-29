"""표 Writer"""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname
from pdf2hwpx.hwpx_ir.models import IrTable, IrTableCell, IrParagraph, IrPosition, IrMargin

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import HwpxIdContext
    from pdf2hwpx.hwpx_ir.components.paragraph.writer import ParagraphWriter


# 텍스트 줄바꿈 타입 매핑
TEXT_WRAP_MAP = {
    "top_and_bottom": "TOP_AND_BOTTOM",
    "both_sides": "SQUARE",
    "left_only": "LEFT",
    "right_only": "RIGHT",
    "behind_text": "BEHIND_TEXT",
    "in_front_of_text": "IN_FRONT_OF_TEXT",
}

# 수직 기준 매핑
VERT_REL_TO_MAP = {
    "paper": "PAPER",
    "page": "PAGE",
    "para": "PARA",
}

# 수평 기준 매핑
HORZ_REL_TO_MAP = {
    "paper": "PAPER",
    "page": "PAGE",
    "column": "COLUMN",
    "para": "PARA",
}

# 수직 정렬 매핑
VERT_ALIGN_MAP = {
    "top": "TOP",
    "center": "CENTER",
    "bottom": "BOTTOM",
    "inside": "INSIDE",
    "outside": "OUTSIDE",
}

# 수평 정렬 매핑
HORZ_ALIGN_MAP = {
    "left": "LEFT",
    "center": "CENTER",
    "right": "RIGHT",
    "inside": "INSIDE",
    "outside": "OUTSIDE",
}

# 셀 수직 정렬 매핑
CELL_VERT_ALIGN_MAP = {
    "top": "TOP",
    "center": "CENTER",
    "bottom": "BOTTOM",
}


class TableWriter:
    """표 생성"""

    def __init__(self, paragraph_writer: "ParagraphWriter"):
        self.paragraph_writer = paragraph_writer

    def build(self, table: IrTable, context: "HwpxIdContext") -> etree._Element:
        """IrTable을 hp:tbl 요소로 변환"""
        if table.raw_xml:
            return etree.fromstring(table.raw_xml)

        table_id = context.next_tbl_id()

        # 텍스트 줄바꿈 타입
        text_wrap = TEXT_WRAP_MAP.get(table.text_wrap, "TOP_AND_BOTTOM")

        tbl = etree.Element(qname("hp", "tbl"))
        tbl.set("id", str(table_id))
        tbl.set("zOrder", "0")
        tbl.set("numberingType", "TABLE")
        tbl.set("textWrap", text_wrap)
        tbl.set("textFlow", "BOTH_SIDES")
        tbl.set("lock", "0")
        tbl.set("dropcapstyle", "None")
        tbl.set("pageBreak", "CELL")
        tbl.set("repeatHeader", "1" if table.repeat_header else "0")
        tbl.set("rowCnt", str(table.row_cnt))
        tbl.set("colCnt", str(table.col_cnt))
        tbl.set("cellSpacing", str(table.cell_spacing))
        tbl.set("borderFillIDRef", str(table.border_fill_id))
        tbl.set("noAdjust", "0")

        # 크기 (hp:sz)
        total_width = table.width_hwpunit
        total_height = table.height_hwpunit

        # col_widths가 있으면 합산하여 total_width 계산
        if table.col_widths and not total_width:
            total_width = sum(table.col_widths)

        # row_heights가 있으면 합산하여 total_height 계산
        if table.row_heights and not total_height:
            total_height = sum(table.row_heights)

        if total_width is not None or total_height is not None:
            sz = etree.SubElement(tbl, qname("hp", "sz"))
            if total_width is not None:
                sz.set("width", str(total_width))
                sz.set("widthRelTo", "ABSOLUTE")
            if total_height is not None:
                sz.set("height", str(total_height))
                sz.set("heightRelTo", "ABSOLUTE")
            sz.set("protect", "0")

        # 위치 (hp:pos)
        pos = etree.SubElement(tbl, qname("hp", "pos"))
        self._set_position_attrs(pos, table)

        # 외부 여백 (hp:outMargin)
        out_margin_el = etree.SubElement(tbl, qname("hp", "outMargin"))
        if table.out_margin:
            out_margin_el.set("left", str(table.out_margin.left))
            out_margin_el.set("right", str(table.out_margin.right))
            out_margin_el.set("top", str(table.out_margin.top))
            out_margin_el.set("bottom", str(table.out_margin.bottom))
        else:
            out_margin_el.set("left", "283")
            out_margin_el.set("right", "283")
            out_margin_el.set("top", "283")
            out_margin_el.set("bottom", "283")

        # 내부 여백 (hp:inMargin) - 셀 기본값
        in_margin_el = etree.SubElement(tbl, qname("hp", "inMargin"))
        if table.in_margin:
            in_margin_el.set("left", str(table.in_margin.left))
            in_margin_el.set("right", str(table.in_margin.right))
            in_margin_el.set("top", str(table.in_margin.top))
            in_margin_el.set("bottom", str(table.in_margin.bottom))
        else:
            in_margin_el.set("left", "141")
            in_margin_el.set("right", "141")
            in_margin_el.set("top", "141")
            in_margin_el.set("bottom", "141")

        # 행별로 셀 그룹화
        row_map: Dict[int, List[IrTableCell]] = {}
        for cell in table.cells:
            row_map.setdefault(cell.row, []).append(cell)

        # 행 생성
        for row_idx in sorted(row_map.keys()):
            tr = etree.SubElement(tbl, qname("hp", "tr"))
            for cell in sorted(row_map[row_idx], key=lambda c: c.col):
                # 셀 크기 결정 (col_widths, row_heights 우선)
                cell_width = cell.width_hwpunit
                cell_height = cell.height_hwpunit

                if table.col_widths and cell.col < len(table.col_widths):
                    # 병합 시 여러 열 너비 합산
                    cell_width = sum(
                        table.col_widths[cell.col:cell.col + cell.col_span]
                    )

                if table.row_heights and cell.row < len(table.row_heights):
                    # 병합 시 여러 행 높이 합산
                    cell_height = sum(
                        table.row_heights[cell.row:cell.row + cell.row_span]
                    )

                tc = self._build_cell(cell, context, cell_width, cell_height, table.in_margin)
                tr.append(tc)

        return tbl

    def _set_position_attrs(self, pos_el: etree._Element, table: IrTable) -> None:
        """위치 속성 설정"""
        pos = table.position

        if pos:
            pos_el.set("treatAsChar", "1" if pos.treat_as_char else "0")
            pos_el.set("affectLSpacing", "0")
            pos_el.set("flowWithText", "1" if pos.flow_with_text else "0")
            pos_el.set("allowOverlap", "1" if pos.allow_overlap else "0")
            pos_el.set("holdAnchorAndSO", "0")
            pos_el.set("vertRelTo", VERT_REL_TO_MAP.get(pos.vert_rel_to, "PARA"))
            pos_el.set("horzRelTo", HORZ_REL_TO_MAP.get(pos.horz_rel_to, "COLUMN"))
            pos_el.set("vertAlign", VERT_ALIGN_MAP.get(pos.vert_align, "TOP"))
            pos_el.set("horzAlign", HORZ_ALIGN_MAP.get(pos.horz_align, "LEFT"))
            pos_el.set("vertOffset", str(pos.vert_offset))
            pos_el.set("horzOffset", str(pos.horz_offset))
        else:
            # 기본값 또는 레거시 treat_as_char 사용
            pos_el.set("treatAsChar", "1" if table.treat_as_char else "0")
            pos_el.set("affectLSpacing", "0")
            pos_el.set("flowWithText", "1")
            pos_el.set("allowOverlap", "0")
            pos_el.set("holdAnchorAndSO", "0")
            pos_el.set("vertRelTo", "PARA")
            pos_el.set("horzRelTo", "COLUMN")
            pos_el.set("vertAlign", "TOP")
            pos_el.set("horzAlign", "LEFT")
            pos_el.set("vertOffset", "0")
            pos_el.set("horzOffset", "0")

    def _build_cell(
        self,
        cell: IrTableCell,
        context: "HwpxIdContext",
        computed_width: Optional[int],
        computed_height: Optional[int],
        default_margin: Optional[IrMargin],
    ) -> etree._Element:
        """IrTableCell을 hp:tc 요소로 변환"""
        tc = etree.Element(qname("hp", "tc"))
        tc.set("name", "")
        tc.set("header", "0")
        tc.set("hasMargin", "1" if cell.margin else "0")
        tc.set("protect", "1" if cell.protect else "0")
        tc.set("editable", "0")
        tc.set("dirty", "0")
        tc.set("borderFillIDRef", str(cell.border_fill_id))

        # 셀 내용 (hp:subList)
        sub_list = etree.SubElement(tc, qname("hp", "subList"))
        sub_list.set("id", "")
        sub_list.set("textDirection", "HORIZONTAL")
        sub_list.set("lineWrap", "BREAK")
        sub_list.set("vertAlign", CELL_VERT_ALIGN_MAP.get(cell.vert_align, "CENTER"))
        sub_list.set("linkListIDRef", "0")
        sub_list.set("linkListNextIDRef", "0")
        sub_list.set("textWidth", "0")
        sub_list.set("textHeight", "0")
        sub_list.set("hasTextRef", "0")
        sub_list.set("hasNumRef", "0")

        # 블록 처리
        has_content = False
        for block in cell.blocks:
            if block.type == "paragraph" and block.paragraph:
                p = self.paragraph_writer.build(block.paragraph, context.next_para_id())
                sub_list.append(p)
                has_content = True

        # 빈 셀에 빈 단락 추가
        if not has_content:
            p = self.paragraph_writer.build_empty(context.next_para_id())
            sub_list.append(p)

        # 셀 주소 (hp:cellAddr)
        cell_addr = etree.SubElement(tc, qname("hp", "cellAddr"))
        cell_addr.set("colAddr", str(cell.col))
        cell_addr.set("rowAddr", str(cell.row))

        # 셀 병합 (hp:cellSpan)
        cell_span = etree.SubElement(tc, qname("hp", "cellSpan"))
        cell_span.set("colSpan", str(cell.col_span))
        cell_span.set("rowSpan", str(cell.row_span))

        # 셀 크기 (hp:cellSz)
        cell_sz = etree.SubElement(tc, qname("hp", "cellSz"))
        width = computed_width or cell.width_hwpunit or 10000
        height = computed_height or cell.height_hwpunit or 1000
        cell_sz.set("width", str(width))
        cell_sz.set("height", str(height))

        # 셀 여백 (hp:cellMargin)
        cell_margin_el = etree.SubElement(tc, qname("hp", "cellMargin"))
        margin = cell.margin or default_margin
        if margin:
            cell_margin_el.set("left", str(margin.left))
            cell_margin_el.set("right", str(margin.right))
            cell_margin_el.set("top", str(margin.top))
            cell_margin_el.set("bottom", str(margin.bottom))
        else:
            cell_margin_el.set("left", "141")
            cell_margin_el.set("right", "141")
            cell_margin_el.set("top", "141")
            cell_margin_el.set("bottom", "141")

        return tc
