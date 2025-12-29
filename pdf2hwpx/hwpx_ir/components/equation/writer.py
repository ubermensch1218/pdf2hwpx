"""수식 Writer"""

from __future__ import annotations

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrEquation


class EquationWriter:
    """수식 생성"""

    def build(self, eq: IrEquation, eq_id: int) -> etree._Element:
        """IrEquation을 hp:equation 요소로 변환"""
        equation = etree.Element(qname("hp", "equation"))
        equation.set("id", str(eq_id))
        equation.set("zOrder", "0")
        equation.set("numberingType", "EQUATION")
        equation.set("textWrap", "TOP_AND_BOTTOM")
        equation.set("textFlow", "BOTH_SIDES")
        equation.set("lock", "0")
        equation.set("dropcapstyle", "None")
        equation.set("version", eq.version)
        equation.set("baseLine", str(eq.base_line))
        equation.set("textColor", eq.text_color)
        equation.set("baseUnit", "1100")
        equation.set("lineMode", "CHAR")
        equation.set("font", "HYhwpEQ")

        # sz
        sz = etree.SubElement(equation, qname("hp", "sz"))
        sz.set("width", str(eq.width_hwpunit))
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", str(eq.height_hwpunit))
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # pos (인라인)
        pos = etree.SubElement(equation, qname("hp", "pos"))
        pos.set("treatAsChar", "1")
        pos.set("affectLSpacing", "0")
        pos.set("flowWithText", "1")
        pos.set("allowOverlap", "0")
        pos.set("holdAnchorAndSO", "0")
        pos.set("vertRelTo", "PARA")
        pos.set("horzRelTo", "COLUMN")
        pos.set("vertAlign", "TOP")
        pos.set("horzAlign", "LEFT")
        pos.set("vertOffset", "0")
        pos.set("horzOffset", "0")

        # outMargin
        out_margin = etree.SubElement(equation, qname("hp", "outMargin"))
        out_margin.set("left", "0"); out_margin.set("right", "0")
        out_margin.set("top", "0"); out_margin.set("bottom", "0")

        # shapeComment
        etree.SubElement(equation, qname("hp", "shapeComment"))

        # script
        script = etree.SubElement(equation, qname("hp", "script"))
        script.text = eq.script

        return equation
