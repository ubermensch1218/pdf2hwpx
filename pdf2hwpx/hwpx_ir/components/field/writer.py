"""필드 Writer"""

from __future__ import annotations

from datetime import datetime

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrField


class FieldWriter:
    """필드 생성"""

    def build(self, field: IrField) -> etree._Element:
        """IrField를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        # 필드 타입 매핑
        type_map = {
            "date": "DATE",
            "time": "TIME",
            "page_number": "PAGE",
            "total_pages": "NUMPAGES",
            "file_name": "FILENAME",
            "author": "AUTHOR",
            "title": "TITLE",
            "created_date": "CREATEDATE",
            "modified_date": "SAVEDATE",
            "custom": "CUSTOM",
        }

        field_begin = etree.SubElement(ctrl, qname("hp", "fieldBegin"))
        field_begin.set("type", type_map.get(field.field_type, "CUSTOM"))

        if field.format:
            field_begin.set("format", field.format)

        # 현재 값 (미리보기용)
        value = self._get_field_value(field)

        run = etree.SubElement(ctrl, qname("hp", "run"))
        run.set("charPrIDRef", "0")
        t = etree.SubElement(run, qname("hp", "t"))
        t.text = value

        # 필드 끝
        etree.SubElement(ctrl, qname("hp", "fieldEnd"))

        return ctrl

    def _get_field_value(self, field: IrField) -> str:
        """필드의 현재 값 반환"""
        now = datetime.now()

        if field.field_type == "date":
            fmt = field.format or "%Y-%m-%d"
            return now.strftime(fmt.replace("yyyy", "%Y").replace("MM", "%m").replace("dd", "%d"))

        elif field.field_type == "time":
            fmt = field.format or "%H:%M:%S"
            return now.strftime(fmt.replace("HH", "%H").replace("mm", "%M").replace("ss", "%S"))

        elif field.field_type == "page_number":
            return "1"  # 실제 값은 뷰어에서 계산

        elif field.field_type == "total_pages":
            return "1"  # 실제 값은 뷰어에서 계산

        elif field.field_type == "custom":
            return field.custom_value or ""

        return ""

    def build_page_number(self) -> etree._Element:
        """페이지 번호 필드 생성"""
        return self.build(IrField(field_type="page_number"))

    def build_date(self, format: str = "yyyy-MM-dd") -> etree._Element:
        """날짜 필드 생성"""
        return self.build(IrField(field_type="date", format=format))

    def build_time(self, format: str = "HH:mm:ss") -> etree._Element:
        """시간 필드 생성"""
        return self.build(IrField(field_type="time", format=format))
