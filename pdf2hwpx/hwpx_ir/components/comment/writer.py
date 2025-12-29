"""주석/변경추적 Writer"""

from __future__ import annotations

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrComment, IrTrackChange


class CommentWriter:
    """주석/변경추적 생성"""

    def build_comment(self, comment: IrComment) -> etree._Element:
        """IrComment를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        memo = etree.SubElement(ctrl, qname("hp", "memo"))
        memo.set("author", comment.author)
        if comment.date:
            memo.set("date", comment.date)

        # 메모 내용
        sub_list = etree.SubElement(memo, qname("hp", "subList"))
        sub_list.set("textDirection", "HORIZONTAL")

        p = etree.SubElement(sub_list, qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        t = etree.SubElement(run, qname("hp", "t"))
        t.text = comment.content

        return ctrl

    def build_track_change(self, track: IrTrackChange) -> etree._Element:
        """IrTrackChange를 hp:ctrl 요소로 변환"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        tc = etree.SubElement(ctrl, qname("hp", "trackChange"))
        tc.set("type", track.change_type.upper())
        tc.set("author", track.author)
        if track.date:
            tc.set("date", track.date)

        # 원본 텍스트
        if track.original_text:
            old_text = etree.SubElement(tc, qname("hp", "oldText"))
            run = etree.SubElement(old_text, qname("hp", "run"))
            t = etree.SubElement(run, qname("hp", "t"))
            t.text = track.original_text

        # 새 텍스트
        if track.new_text:
            new_text = etree.SubElement(tc, qname("hp", "newText"))
            run = etree.SubElement(new_text, qname("hp", "run"))
            t = etree.SubElement(run, qname("hp", "t"))
            t.text = track.new_text

        return ctrl
