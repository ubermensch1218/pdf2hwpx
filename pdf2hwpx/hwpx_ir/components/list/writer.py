"""목록/번호매기기 Writer"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrList, IrListItem

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import HwpxIdContext
    from pdf2hwpx.hwpx_ir.components.paragraph.writer import ParagraphWriter


class ListWriter:
    """목록 생성"""

    def __init__(self, paragraph_writer: "ParagraphWriter"):
        self.paragraph_writer = paragraph_writer

    def build(self, ir_list: IrList, context: "HwpxIdContext") -> List[etree._Element]:
        """IrList를 단락 요소들로 변환

        HWPX에서 목록은 특별한 paraPrIDRef를 가진 단락들로 표현됨
        """
        elements = []

        for idx, item in enumerate(ir_list.items):
            p = self._build_list_item(item, context, idx + ir_list.start_number)
            elements.append(p)

        return elements

    def _build_list_item(
        self,
        item: IrListItem,
        context: "HwpxIdContext",
        number: int,
    ) -> etree._Element:
        """IrListItem을 단락 요소로 변환"""
        # 기본 단락 생성
        p = self.paragraph_writer.build(item.content, context.next_para_id())

        # TODO: 목록 스타일 적용
        # - paraPrIDRef를 목록 스타일로 설정
        # - 들여쓰기 레벨 적용
        # - 글머리 기호/번호 추가

        return p

    def build_bullet_char(self, style: str) -> str:
        """글머리 기호 문자 반환"""
        bullet_chars = {
            "disc": "●",
            "circle": "○",
            "square": "■",
            "dash": "—",
            "arrow": "→",
            "check": "✓",
        }
        return bullet_chars.get(style, "●")

    def build_number_text(self, number: int, style: str) -> str:
        """번호 텍스트 생성"""
        if style == "decimal":
            return f"{number}."
        elif style == "lower_alpha":
            return f"{chr(ord('a') + number - 1)}."
        elif style == "upper_alpha":
            return f"{chr(ord('A') + number - 1)}."
        elif style == "lower_roman":
            return f"{self._to_roman(number).lower()}."
        elif style == "upper_roman":
            return f"{self._to_roman(number)}."
        elif style == "korean":
            korean = "가나다라마바사아자차카타파하"
            if 1 <= number <= len(korean):
                return f"{korean[number - 1]}."
            return f"{number}."
        elif style == "circled":
            circled = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
            if 1 <= number <= len(circled):
                return circled[number - 1]
            return f"({number})"
        return f"{number}."

    def _to_roman(self, num: int) -> str:
        """숫자를 로마 숫자로 변환"""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman = ""
        for i, v in enumerate(val):
            while num >= v:
                roman += syms[i]
                num -= v
        return roman
