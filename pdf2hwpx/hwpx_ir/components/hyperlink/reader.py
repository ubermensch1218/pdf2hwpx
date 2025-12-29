"""하이퍼링크 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_str
from pdf2hwpx.hwpx_ir.models import IrHyperlink


class HyperlinkReader:
    """하이퍼링크 파싱"""

    def parse(self, ctrl: etree._Element) -> Optional[IrHyperlink]:
        """hp:ctrl 내 하이퍼링크 요소 파싱"""
        # HWPX에서 하이퍼링크는 hp:ctrl 내 hp:clickHere로 표현
        click_here = ctrl.xpath(".//hp:clickHere", namespaces=NS)
        if not click_here:
            return None

        ch = click_here[0]
        url = ch.get("url", "")
        tooltip = ch.get("tooltip", "")

        # 텍스트 추출
        text_parts = []
        for t in ctrl.xpath(".//hp:t", namespaces=NS):
            if t.text:
                text_parts.append(t.text)
        text = "".join(text_parts)

        if not url:
            return None

        return IrHyperlink(
            url=url,
            text=text or url,
            tooltip=tooltip if tooltip else None,
        )

    def is_hyperlink(self, ctrl: etree._Element) -> bool:
        """요소가 하이퍼링크인지 확인"""
        return len(ctrl.xpath(".//hp:clickHere", namespaces=NS)) > 0
