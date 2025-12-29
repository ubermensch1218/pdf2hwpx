"""캡션 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int
from pdf2hwpx.hwpx_ir.models import IrCaption


class CaptionReader:
    """캡션 파싱"""

    def parse(self, ctrl: etree._Element) -> Optional[IrCaption]:
        """hp:ctrl 내 캡션 요소 파싱"""
        caption = ctrl.xpath(".//hp:caption", namespaces=NS)
        if not caption:
            return None

        c = caption[0]

        # 캡션 텍스트 추출
        text_parts = []
        for t in c.xpath(".//hp:t", namespaces=NS):
            if t.text:
                text_parts.append(t.text)
        text = "".join(text_parts)

        # 대상 타입
        target_type_str = c.get("type", "image")
        target_type_map = {
            "PICTURE": "image",
            "TABLE": "table",
            "EQUATION": "equation",
        }
        target_type = target_type_map.get(target_type_str.upper(), "image")

        # 번호
        number = first_int([c.get("number")])

        # 위치
        position = "below" if c.get("side", "BOTTOM") == "BOTTOM" else "above"

        # 접두사
        prefix = c.get("prefix")

        return IrCaption(
            text=text,
            target_type=target_type,
            number=number,
            position=position,
            prefix=prefix,
        )

    def is_caption(self, ctrl: etree._Element) -> bool:
        """요소가 캡션인지 확인"""
        return len(ctrl.xpath(".//hp:caption", namespaces=NS)) > 0
