"""수식 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int, first_str
from pdf2hwpx.hwpx_ir.models import IrEquation


class EquationReader:
    """수식 파싱"""

    def parse(self, eq: etree._Element) -> Optional[IrEquation]:
        """hp:equation 요소에서 IrEquation 파싱"""
        # 스크립트 추출
        script_elem = eq.xpath("./hp:script", namespaces=NS)
        if not script_elem:
            return None

        script = script_elem[0].text or ""

        # 크기
        width = first_int(eq.xpath("./hp:sz/@width", namespaces=NS), 4000)
        height = first_int(eq.xpath("./hp:sz/@height", namespaces=NS), 1000)

        # 속성
        text_color = eq.get("textColor", "#000000")
        base_line = first_int([eq.get("baseLine", "85")], 85)
        version = eq.get("version", "Equation Version 60")

        return IrEquation(
            script=script,
            width_hwpunit=width,
            height_hwpunit=height,
            text_color=text_color,
            base_line=base_line,
            version=version,
        )
