"""목록/번호매기기 Reader"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int, first_str
from pdf2hwpx.hwpx_ir.models import (
    IrList,
    IrListItem,
    IrParagraph,
    ListType,
    BulletStyle,
    NumberingStyle,
)

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.components.paragraph.reader import ParagraphReader


class ListReader:
    """목록 파싱"""

    def __init__(self, paragraph_reader: "ParagraphReader"):
        self.paragraph_reader = paragraph_reader

    def parse(self, numbering: etree._Element) -> Optional[IrList]:
        """hp:numbering 또는 관련 요소에서 IrList 파싱"""
        # HWPX에서 목록은 단락의 paraPrIDRef로 번호매기기 스타일을 참조
        # 실제 목록 구조는 header.xml의 numbering 정의 참조
        # 여기서는 기본 구조만 파싱

        items: List[IrListItem] = []
        list_type: ListType = "bullet"

        # numbering type 확인
        num_type = numbering.get("type", "BULLET")
        if num_type == "BULLET":
            list_type = "bullet"
        elif num_type in ("DECIMAL", "UPPER_ALPHA", "LOWER_ALPHA", "UPPER_ROMAN", "LOWER_ROMAN"):
            list_type = "numbered"

        return IrList(
            items=items,
            list_type=list_type,
            start_number=1,
        )

    def parse_list_paragraph(
        self,
        p: etree._Element,
        level: int = 0,
        list_type: ListType = "bullet",
    ) -> IrListItem:
        """목록 단락을 IrListItem으로 파싱"""
        para = self.paragraph_reader.parse(p)

        return IrListItem(
            content=para,
            level=level,
            list_type=list_type,
        )
