"""필드 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS
from pdf2hwpx.hwpx_ir.models import IrField, FieldType


class FieldReader:
    """필드 파싱"""

    def parse(self, ctrl: etree._Element) -> Optional[IrField]:
        """hp:ctrl 내 필드 요소 파싱"""
        field = ctrl.xpath(".//hp:fieldBegin | .//hp:field", namespaces=NS)
        if not field:
            return None

        f = field[0]
        field_type_str = f.get("type", "")

        # 필드 타입 매핑
        type_map = {
            "DATE": "date",
            "TIME": "time",
            "PAGE": "page_number",
            "NUMPAGES": "total_pages",
            "FILENAME": "file_name",
            "AUTHOR": "author",
            "TITLE": "title",
            "CREATEDATE": "created_date",
            "SAVEDATE": "modified_date",
        }

        field_type: FieldType = type_map.get(field_type_str.upper(), "custom")
        format_str = f.get("format")

        # custom 타입이면 값 추출
        custom_value = None
        if field_type == "custom":
            custom_value = f.get("value") or f.text

        return IrField(
            field_type=field_type,
            format=format_str,
            custom_value=custom_value,
        )

    def is_field(self, ctrl: etree._Element) -> bool:
        """요소가 필드인지 확인"""
        return len(ctrl.xpath(".//hp:fieldBegin | .//hp:field", namespaces=NS)) > 0
