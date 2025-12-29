"""이미지 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_int
from pdf2hwpx.hwpx_ir.models import IrImage


class ImageReader:
    """이미지 파싱"""

    def parse(self, pic: etree._Element) -> Optional[IrImage]:
        """hp:pic 요소에서 IrImage 파싱"""
        img = pic.xpath(".//hc:img", namespaces=NS)
        if not img:
            return None

        binary_id = img[0].get("binaryItemIDRef")
        if not binary_id:
            return None

        # 현재 크기
        width = first_int(pic.xpath("./hp:curSz/@width", namespaces=NS))
        height = first_int(pic.xpath("./hp:curSz/@height", namespaces=NS))

        # curSz가 없으면 sz에서 찾기
        if width is None:
            width = first_int(pic.xpath("./hp:sz/@width", namespaces=NS))
        if height is None:
            height = first_int(pic.xpath("./hp:sz/@height", namespaces=NS))

        # 원본 크기
        org_width = first_int(pic.xpath("./hp:orgSz/@width", namespaces=NS))
        org_height = first_int(pic.xpath("./hp:orgSz/@height", namespaces=NS))

        # 배치 옵션
        treat_as_char = first_int(pic.xpath("./hp:pos/@treatAsChar", namespaces=NS)) == 1

        raw_xml = etree.tostring(pic, encoding="UTF-8")

        return IrImage(
            image_id=binary_id,
            width_hwpunit=width,
            height_hwpunit=height,
            org_width=org_width,
            org_height=org_height,
            treat_as_char=treat_as_char,
            raw_xml=raw_xml,
        )
