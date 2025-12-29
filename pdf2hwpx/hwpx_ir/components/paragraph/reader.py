"""단락 Reader"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, is_tag, first_int, first_str
from pdf2hwpx.hwpx_ir.models import (
    IrParagraph,
    IrInline,
    AlignmentType,
    LineSpacingType,
)

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.components.text.reader import TextReader


class ParagraphReader:
    """단락 파싱"""

    def __init__(
        self,
        text_reader: "TextReader",
        header_tree: Optional[etree._Element] = None,
    ):
        self.text_reader = text_reader
        self.header_tree = header_tree
        self.para_pr_cache = {}
        self._parse_para_properties()

    def _parse_para_properties(self):
        """header.xml에서 단락 속성 파싱"""
        if self.header_tree is None:
            return

        para_prs = self.header_tree.xpath("//hh:paraPr", namespaces=NS)
        for pp in para_prs:
            pp_id = pp.get("id", "0")

            # 정렬
            align_map = {
                "JUSTIFY": "justify",
                "LEFT": "left",
                "RIGHT": "right",
                "CENTER": "center",
                "DISTRIBUTE": "distribute",
            }
            align = pp.get("align", "LEFT")
            alignment = align_map.get(align, "left")

            # 줄간격
            line_spacing = pp.xpath("./hh:lineSpacing", namespaces=NS)
            ls_type = "percent"
            ls_value = 160
            if line_spacing:
                ls = line_spacing[0]
                type_map = {
                    "PERCENT": "percent",
                    "FIXED": "fixed",
                    "BETWEEN_LINES": "between_lines",
                    "AT_LEAST": "at_least",
                }
                ls_type = type_map.get(ls.get("type", "PERCENT"), "percent")
                ls_value = first_int([ls.get("value", "160")], 160)

            # 들여쓰기
            margin = pp.xpath("./hh:margin", namespaces=NS)
            indent_left = 0
            indent_right = 0
            indent_first = 0
            if margin:
                m = margin[0]
                indent_left = first_int([m.get("left", "0")], 0)
                indent_right = first_int([m.get("right", "0")], 0)
                indent_first = first_int([m.get("indent", "0")], 0)

            self.para_pr_cache[pp_id] = {
                "alignment": alignment,
                "line_spacing_type": ls_type,
                "line_spacing_value": ls_value,
                "indent_left": indent_left,
                "indent_right": indent_right,
                "indent_first_line": indent_first,
            }

    def parse(self, p: etree._Element) -> IrParagraph:
        """hp:p 요소에서 IrParagraph 파싱"""
        inlines: List[IrInline] = []

        # 단락 속성 가져오기
        para_pr_id = p.get("paraPrIDRef", "0")
        para_props = self.para_pr_cache.get(para_pr_id, {})

        # 각 run 파싱
        for run in p.xpath("./hp:run", namespaces=NS):
            run_inlines = self.text_reader.parse_run(run)
            inlines.extend(run_inlines)

        raw_xml = etree.tostring(p, encoding="UTF-8")

        return IrParagraph(
            inlines=inlines,
            raw_xml=raw_xml,
            alignment=para_props.get("alignment", "left"),
            line_spacing_type=para_props.get("line_spacing_type", "percent"),
            line_spacing_value=para_props.get("line_spacing_value", 160),
            indent_left=para_props.get("indent_left", 0),
            indent_right=para_props.get("indent_right", 0),
            indent_first_line=para_props.get("indent_first_line", 0),
        )
