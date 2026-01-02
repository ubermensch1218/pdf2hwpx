"""단락 Writer"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname
from pdf2hwpx.hwpx_ir.models import IrParagraph, IrTextRun, IrLineBreak, IrTab, IrInlineEquation

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import StyleManager


class InlineEquationBuilder:
    """인라인 수식 빌더"""

    def __init__(self):
        self._eq_counter = 0

    def next_id(self) -> int:
        self._eq_counter += 1
        return self._eq_counter

    def build(self, eq: IrInlineEquation, eq_id: int) -> etree._Element:
        """인라인 수식을 hp:equation 요소로 변환"""
        equation = etree.Element(qname("hp", "equation"))
        equation.set("id", str(eq_id))
        equation.set("zOrder", "0")
        equation.set("numberingType", "EQUATION")
        equation.set("textWrap", "TOP_AND_BOTTOM")
        equation.set("textFlow", "BOTH_SIDES")
        equation.set("lock", "0")
        equation.set("dropcapstyle", "None")
        equation.set("version", "Equation Version 60")
        equation.set("baseLine", str(eq.base_line))
        equation.set("textColor", "#000000")
        equation.set("baseUnit", "1000")
        equation.set("lineMode", "CHAR")
        equation.set("font", "HancomEQN")  # 한컴 수식 폰트

        # 크기 추정 (스크립트 길이 기반)
        width = max(1200, min(len(eq.script) * 300, 40000))
        height = 1200

        # sz
        sz = etree.SubElement(equation, qname("hp", "sz"))
        sz.set("width", str(width))
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", str(height))
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # pos (인라인 - 글자처럼 취급)
        pos = etree.SubElement(equation, qname("hp", "pos"))
        pos.set("treatAsChar", "1")
        pos.set("affectLSpacing", "0")
        pos.set("flowWithText", "1")
        pos.set("allowOverlap", "0")
        pos.set("holdAnchorAndSO", "0")
        pos.set("vertRelTo", "PARA")
        pos.set("horzRelTo", "PARA")  # PARA로 변경
        pos.set("vertAlign", "TOP")   # TOP으로 변경
        pos.set("horzAlign", "LEFT")
        pos.set("vertOffset", "0")
        pos.set("horzOffset", "0")

        # outMargin
        out_margin = etree.SubElement(equation, qname("hp", "outMargin"))
        out_margin.set("left", "56")  # 샘플과 동일
        out_margin.set("right", "56")
        out_margin.set("top", "0")
        out_margin.set("bottom", "0")

        # shapeComment
        shape_comment = etree.SubElement(equation, qname("hp", "shapeComment"))
        shape_comment.text = "수식입니다."

        # script
        script = etree.SubElement(equation, qname("hp", "script"))
        script.text = eq.script

        return equation


class ParagraphWriter:
    """단락 생성"""

    def __init__(self, style_manager: Optional["StyleManager"] = None):
        self.style_manager = style_manager
        self._inline_eq_builder = InlineEquationBuilder()

    def build(self, para: IrParagraph, paragraph_id: int) -> etree._Element:
        """IrParagraph를 hp:p 요소로 변환"""
        if para.raw_xml:
            return etree.fromstring(para.raw_xml)

        p = etree.Element(qname("hp", "p"))
        p.set("id", str(paragraph_id))

        # 단락 속성 ID (TODO: StyleManager에서 관리)
        para_pr_id = self._get_para_pr_id(para)
        p.set("paraPrIDRef", str(para_pr_id))
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        if not para.inlines:
            # 빈 단락
            run = etree.SubElement(p, qname("hp", "run"))
            run.set("charPrIDRef", "0")
            # linesegarray 추가
            linesegarray = etree.SubElement(p, qname("hp", "linesegarray"))
            lineseg = etree.SubElement(linesegarray, qname("hp", "lineseg"))
            lineseg.set("textpos", "0")
            lineseg.set("vertpos", "0")
            lineseg.set("vertsize", "1000")
            lineseg.set("textheight", "1000")
            lineseg.set("baseline", "850")
            lineseg.set("spacing", "600")
            lineseg.set("horzpos", "0")
            lineseg.set("horzsize", "0")
            lineseg.set("flags", "393216")
            return p

        for inline in para.inlines:
            run = etree.SubElement(p, qname("hp", "run"))

            # 스타일 ID 결정
            char_pr_id = 0
            if isinstance(inline, IrTextRun) and self.style_manager:
                char_pr_id = self.style_manager.get_char_pr_id(inline)
            run.set("charPrIDRef", str(char_pr_id))

            if isinstance(inline, IrTextRun):
                parts = inline.text.split("\n")
                for idx, part in enumerate(parts):
                    if idx > 0:
                        etree.SubElement(run, qname("hp", "lineBreak"))
                    if part:
                        t = etree.SubElement(run, qname("hp", "t"))
                        t.text = part

            elif isinstance(inline, IrLineBreak):
                etree.SubElement(run, qname("hp", "lineBreak"))

            elif isinstance(inline, IrTab):
                etree.SubElement(run, qname("hp", "tab"))

            elif isinstance(inline, IrInlineEquation):
                # 인라인 수식 - run 내부에 삽입 (샘플 파일 구조 준수)
                eq_elem = self._inline_eq_builder.build(
                    inline, self._inline_eq_builder.next_id()
                )
                run.append(eq_elem)
                # 수식 뒤에 빈 t 태그 추가 (샘플과 동일)
                etree.SubElement(run, qname("hp", "t"))

        # linesegarray 추가 (렌더링에 필수)
        linesegarray = etree.SubElement(p, qname("hp", "linesegarray"))
        lineseg = etree.SubElement(linesegarray, qname("hp", "lineseg"))
        lineseg.set("textpos", "0")
        lineseg.set("vertpos", "0")
        lineseg.set("vertsize", "1000")
        lineseg.set("textheight", "1000")
        lineseg.set("baseline", "850")
        lineseg.set("spacing", "600")
        lineseg.set("horzpos", "0")
        lineseg.set("horzsize", "0")
        lineseg.set("flags", "393216")

        return p

    def _get_para_pr_id(self, para: IrParagraph) -> int:
        """단락 속성 ID 반환 (기본값 0)"""
        # TODO: StyleManager에서 단락 스타일 관리
        # 현재는 기본 스타일 사용
        if (
            para.alignment == "left"
            and para.line_spacing_type == "percent"
            and para.line_spacing_value == 160
            and para.indent_left == 0
            and para.indent_right == 0
            and para.indent_first_line == 0
            and para.background_color is None
        ):
            return 0
        # TODO: 새 단락 스타일 생성
        return 0

    def build_empty(self, paragraph_id: int) -> etree._Element:
        """빈 단락 생성"""
        return self.build(IrParagraph(), paragraph_id)
