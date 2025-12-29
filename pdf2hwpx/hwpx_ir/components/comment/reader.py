"""주석/변경추적 Reader"""

from __future__ import annotations

from typing import Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, first_str
from pdf2hwpx.hwpx_ir.models import IrComment, IrTrackChange, ChangeType


class CommentReader:
    """주석/변경추적 파싱"""

    def parse_comment(self, ctrl: etree._Element) -> Optional[IrComment]:
        """hp:ctrl 내 주석(메모) 요소 파싱"""
        memo = ctrl.xpath(".//hp:memo", namespaces=NS)
        if not memo:
            return None

        m = memo[0]
        author = m.get("author", "")

        # 주석 내용 추출
        content_parts = []
        for t in m.xpath(".//hp:t", namespaces=NS):
            if t.text:
                content_parts.append(t.text)
        content = "".join(content_parts)

        date = m.get("date")

        return IrComment(
            author=author,
            content=content,
            date=date,
        )

    def parse_track_change(self, ctrl: etree._Element) -> Optional[IrTrackChange]:
        """hp:ctrl 내 변경추적 요소 파싱"""
        tc = ctrl.xpath(".//hp:trackChange", namespaces=NS)
        if not tc:
            return None

        track = tc[0]
        change_type_str = track.get("type", "insert")

        # 변경 타입 매핑
        type_map = {
            "INSERT": "insert",
            "DELETE": "delete",
            "FORMAT": "format",
        }
        change_type: ChangeType = type_map.get(change_type_str.upper(), "insert")

        author = track.get("author", "")
        date = track.get("date")

        # 원본/새 텍스트 추출
        original_text = None
        new_text = None

        old_elem = track.xpath(".//hp:oldText//hp:t", namespaces=NS)
        if old_elem and old_elem[0].text:
            original_text = old_elem[0].text

        new_elem = track.xpath(".//hp:newText//hp:t", namespaces=NS)
        if new_elem and new_elem[0].text:
            new_text = new_elem[0].text

        return IrTrackChange(
            change_type=change_type,
            author=author,
            date=date,
            original_text=original_text,
            new_text=new_text,
        )

    def is_comment(self, ctrl: etree._Element) -> bool:
        """요소가 주석인지 확인"""
        return len(ctrl.xpath(".//hp:memo", namespaces=NS)) > 0

    def is_track_change(self, ctrl: etree._Element) -> bool:
        """요소가 변경추적인지 확인"""
        return len(ctrl.xpath(".//hp:trackChange", namespaces=NS)) > 0
