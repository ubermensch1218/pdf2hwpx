"""텍스트/인라인 요소 Reader"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, is_tag, first_int, first_str
from pdf2hwpx.hwpx_ir.models import (
    IrTextRun,
    IrLineBreak,
    IrInline,
)

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.components.hyperlink.reader import HyperlinkReader
    from pdf2hwpx.hwpx_ir.components.bookmark.reader import BookmarkReader
    from pdf2hwpx.hwpx_ir.components.field.reader import FieldReader
    from pdf2hwpx.hwpx_ir.components.footnote.reader import FootnoteReader


class TextReader:
    """텍스트 런 및 인라인 요소 파싱"""

    def __init__(self, header_tree: Optional[etree._Element] = None):
        self.header_tree = header_tree
        self.char_pr_cache = {}
        self._parse_char_properties()

    def _parse_char_properties(self):
        """header.xml에서 문자 속성 파싱"""
        if self.header_tree is None:
            return

        char_prs = self.header_tree.xpath("//hh:charPr", namespaces=NS)
        for cp in char_prs:
            cp_id = cp.get("id", "0")
            self.char_pr_cache[cp_id] = {
                "bold": cp.get("bold") == "1",
                "italic": cp.get("italic") == "1",
                "underline": cp.get("underline", "NONE") != "NONE",
                "strikethrough": cp.get("strikeout", "NONE") != "NONE",
                "font_size": first_int([cp.get("height", "")]),
                "color": cp.get("textColor"),
                "background_color": cp.get("shadeColor"),
            }

    def parse_run(self, run: etree._Element) -> List[IrInline]:
        """hp:run 요소에서 인라인 요소들 파싱"""
        inlines: List[IrInline] = []

        # 문자 속성 ID 가져오기
        char_pr_id = run.get("charPrIDRef", "0")
        char_props = self.char_pr_cache.get(char_pr_id, {})

        for node in run:
            if is_tag(node, "hp", "t"):
                # 텍스트
                if node.text:
                    parts = node.text.split("\n")
                    for idx, part in enumerate(parts):
                        if idx > 0:
                            inlines.append(IrLineBreak())
                        if part:
                            inlines.append(IrTextRun(
                                text=part,
                                bold=char_props.get("bold", False),
                                italic=char_props.get("italic", False),
                                underline=char_props.get("underline", False),
                                strikethrough=char_props.get("strikethrough", False),
                                font_size=char_props.get("font_size"),
                                color=char_props.get("color"),
                                background_color=char_props.get("background_color"),
                            ))

            elif is_tag(node, "hp", "lineBreak"):
                inlines.append(IrLineBreak())

            # 다른 인라인 요소들은 해당 컴포넌트 reader에서 처리

        return inlines

    def parse_text_only(self, run: etree._Element) -> str:
        """텍스트만 추출 (스타일 무시)"""
        text_parts = []
        for t in run.xpath(".//hp:t", namespaces=NS):
            if t.text:
                text_parts.append(t.text)
        return "".join(text_parts)
