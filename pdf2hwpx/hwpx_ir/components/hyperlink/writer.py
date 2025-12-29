"""하이퍼링크 Writer"""

from __future__ import annotations

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrHyperlink


class HyperlinkWriter:
    """하이퍼링크 생성"""

    def build(self, hyperlink: IrHyperlink) -> etree._Element:
        """IrHyperlink를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        # clickHere
        click_here = etree.SubElement(ctrl, qname("hp", "clickHere"))
        click_here.set("url", hyperlink.url)
        if hyperlink.tooltip:
            click_here.set("tooltip", hyperlink.tooltip)

        # 텍스트
        run = etree.SubElement(ctrl, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        t = etree.SubElement(run, qname("hp", "t"))
        t.text = hyperlink.text

        return ctrl

    def build_inline(self, hyperlink: IrHyperlink) -> etree._Element:
        """인라인 하이퍼링크 생성 (run 내부용)"""
        # HWPX에서 인라인 하이퍼링크는 run 내 fieldBegin/fieldEnd로 표현될 수 있음
        # 간단한 구현: 텍스트만 반환
        t = etree.Element(qname("hp", "t"))
        t.text = hyperlink.text
        return t
