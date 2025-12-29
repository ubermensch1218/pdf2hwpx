"""섹션 Writer"""

from __future__ import annotations

from typing import List, Union, TYPE_CHECKING

from lxml import etree

from pdf2hwpx.hwpx_ir.base import qname
from pdf2hwpx.hwpx_ir.models import IrSection, IrHeader, IrFooter, IrPageMargin, IrPageNumber, IrPageHiding

if TYPE_CHECKING:
    from pdf2hwpx.hwpx_ir.writer import HwpxIdContext


# 페이지 번호 형식 매핑
PAGE_NUM_FORMAT_MAP = {
    "digit": "DIGIT",
    "upper_roman": "ROMAN_CAPITAL",
    "lower_roman": "ROMAN_SMALL",
    "upper_alpha": "LATIN_CAPITAL",
    "lower_alpha": "LATIN_SMALL",
}

# 페이지 번호 위치 매핑
PAGE_NUM_POS_MAP = {
    "top_left": "TOP_LEFT",
    "top_center": "TOP_CENTER",
    "top_right": "TOP_RIGHT",
    "bottom_left": "BOTTOM_LEFT",
    "bottom_center": "BOTTOM_CENTER",
    "bottom_right": "BOTTOM_RIGHT",
}


class SectionWriter:
    """섹션 생성"""

    def build_section_xml(self, section: IrSection) -> bytes:
        """섹션 전체 XML 생성 (100% 라운드트립용)

        raw_xml이 있으면 그대로 반환, 없으면 새로 생성
        """
        if section.raw_xml:
            return section.raw_xml

        # raw_xml이 없으면 새로 생성 (기본 구조)
        from pdf2hwpx.hwpx_ir.base import NS
        root = etree.Element(
            qname("hs", "sec"),
            nsmap={
                "ha": NS["ha"],
                "hp": NS["hp"],
                "hp10": NS.get("hp10", "http://www.hancom.co.kr/hwpml/2016/paragraph"),
                "hs": NS["hs"],
                "hc": NS["hc"],
                "hh": NS["hh"],
                "hhs": NS.get("hhs", "http://www.hancom.co.kr/hwpml/2011/history"),
                "hm": NS.get("hm", "http://www.hancom.co.kr/hwpml/2011/master-page"),
                "hpf": NS.get("hpf", "http://www.hancom.co.kr/schema/2011/hpf"),
                "dc": NS.get("dc", "http://purl.org/dc/elements/1.1/"),
                "opf": NS.get("opf", "http://www.idpf.org/2007/opf/"),
                "ooxmlchart": NS.get("ooxmlchart", "http://www.hancom.co.kr/hwpml/2016/ooxmlchart"),
                "hwpunitchar": NS.get("hwpunitchar", "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar"),
                "epub": NS.get("epub", "http://www.idpf.org/2007/ops"),
                "config": NS.get("config", "urn:oasis:names:tc:opendocument:xmlns:config:1.0"),
            }
        )

        # 첫 번째 단락에 secPr 포함
        p = etree.SubElement(root, qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        # secPr 추가
        sec_pr = self._build_sec_pr(section)
        run.append(sec_pr)

        return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    def build_definition(self, section: IrSection) -> List[etree._Element]:
        """섹션 속성 제어 요소들 생성 (secPr, colPr, header, footer)"""
        controls = []

        # 1. 열 속성 (다중 열일 때)
        if section.col_count > 1:
            col_pr = etree.Element(qname("hp", "colPr"))
            col_pr.set("id", "")
            col_pr.set("type", "NEWSPAPER")
            col_pr.set("layout", "LEFT")
            col_pr.set("colCount", str(section.col_count))
            col_pr.set("sameSz", "1")
            col_pr.set("sameGap", str(section.col_gap) if section.col_gap > 0 else "1134")

            if section.col_line_type:
                col_line = etree.SubElement(col_pr, qname("hp", "colLine"))
                col_line.set("type", section.col_line_type)
                col_line.set("width", "100")
                col_line.set("color", "#000000")

            ctrl = etree.Element(qname("hp", "ctrl"))
            ctrl.append(col_pr)
            controls.append(ctrl)

        # 2. 섹션 속성
        sec_pr = self._build_sec_pr(section)
        controls.append(sec_pr)

        # 3. 머리글
        if section.header:
            header_ctrl = self._build_header_footer(section.header, is_header=True)
            controls.append(header_ctrl)

        # 4. 바닥글
        if section.footer:
            footer_ctrl = self._build_header_footer(section.footer, is_header=False)
            controls.append(footer_ctrl)

        return controls

    def _build_sec_pr(self, section: IrSection) -> etree._Element:
        """섹션 속성 요소 생성"""
        sec_pr = etree.Element(qname("hp", "secPr"))
        sec_pr.set("id", "")
        sec_pr.set("textDirection", "HORIZONTAL")
        sec_pr.set("spaceColumns", "1134")
        sec_pr.set("tabStop", "8000")
        sec_pr.set("tabStopVal", "4000")
        sec_pr.set("tabStopUnit", "HWPUNIT")
        sec_pr.set("outlineShapeIDRef", "0")
        sec_pr.set("memoShapeIDRef", "0")
        sec_pr.set("textVerticalWidthHead", "0")
        sec_pr.set("masterPageCnt", "0")

        # grid
        grid = etree.SubElement(sec_pr, qname("hp", "grid"))
        grid.set("lineGrid", "0")
        grid.set("charGrid", "0")
        grid.set("wonggojiFormat", "0")

        # startNum
        start_num = etree.SubElement(sec_pr, qname("hp", "startNum"))
        start_num.set("pageStartsOn", "BOTH")
        if section.page_number:
            start_num.set("page", str(section.page_number.start_number - 1))  # 0-based
        else:
            start_num.set("page", "0")
        start_num.set("pic", "0")
        start_num.set("tbl", "0")
        start_num.set("equation", "0")

        # visibility
        visibility = etree.SubElement(sec_pr, qname("hp", "visibility"))
        visibility.set("hideFirstHeader", "0")
        visibility.set("hideFirstFooter", "0")
        visibility.set("hideFirstMasterPage", "0")
        visibility.set("border", "SHOW_ALL")
        visibility.set("fill", "SHOW_ALL")
        if section.page_number and section.page_number.hide_first_page:
            visibility.set("hideFirstPageNum", "1")
        else:
            visibility.set("hideFirstPageNum", "0")
        visibility.set("hideFirstEmptyLine", "0")
        visibility.set("showLineNumber", "0")

        # lineNumberShape
        linenum = etree.SubElement(sec_pr, qname("hp", "lineNumberShape"))
        linenum.set("restartType", "0")
        linenum.set("countBy", "0")
        linenum.set("distance", "0")
        linenum.set("startNumber", "0")

        # pagePr
        page_pr = etree.SubElement(sec_pr, qname("hp", "pagePr"))
        page_pr.set("landscape", "NARROWLY" if section.landscape else "WIDELY")
        page_pr.set("width", str(section.page_width))
        page_pr.set("height", str(section.page_height))
        page_pr.set("gutterType", "LEFT_ONLY")

        # 여백 (hp:margin)
        margin_el = etree.SubElement(page_pr, qname("hp", "margin"))
        if section.margin:
            margin_el.set("header", str(section.margin.header))
            margin_el.set("footer", str(section.margin.footer))
            margin_el.set("gutter", str(section.margin.gutter))
            margin_el.set("left", str(section.margin.left))
            margin_el.set("right", str(section.margin.right))
            margin_el.set("top", str(section.margin.top))
            margin_el.set("bottom", str(section.margin.bottom))
        else:
            # 공문서 기본값
            margin_el.set("header", "2835")
            margin_el.set("footer", "2835")
            margin_el.set("gutter", "0")
            margin_el.set("left", "5669")
            margin_el.set("right", "5669")
            margin_el.set("top", "5669")
            margin_el.set("bottom", "2835")

        # footNotePr
        footnote_pr = etree.SubElement(sec_pr, qname("hp", "footNotePr"))
        auto_num = etree.SubElement(footnote_pr, qname("hp", "autoNumFormat"))
        auto_num.set("type", "DIGIT")
        auto_num.set("userChar", "")
        auto_num.set("prefixChar", "")
        auto_num.set("suffixChar", ")")
        auto_num.set("supscript", "0")

        note_line = etree.SubElement(footnote_pr, qname("hp", "noteLine"))
        note_line.set("length", "-1")
        note_line.set("type", "SOLID")
        note_line.set("width", "0.12 mm")
        note_line.set("color", "#000000")

        note_spacing = etree.SubElement(footnote_pr, qname("hp", "noteSpacing"))
        note_spacing.set("betweenNotes", "283")
        note_spacing.set("belowLine", "567")
        note_spacing.set("aboveLine", "850")

        numbering = etree.SubElement(footnote_pr, qname("hp", "numbering"))
        numbering.set("type", "CONTINUOUS")
        numbering.set("newNum", "1")

        placement = etree.SubElement(footnote_pr, qname("hp", "placement"))
        placement.set("place", "EACH_COLUMN")
        placement.set("beneathText", "0")

        # endNotePr
        endnote_pr = etree.SubElement(sec_pr, qname("hp", "endNotePr"))
        auto_num2 = etree.SubElement(endnote_pr, qname("hp", "autoNumFormat"))
        auto_num2.set("type", "DIGIT")
        auto_num2.set("userChar", "")
        auto_num2.set("prefixChar", "")
        auto_num2.set("suffixChar", ")")
        auto_num2.set("supscript", "0")

        note_line2 = etree.SubElement(endnote_pr, qname("hp", "noteLine"))
        note_line2.set("length", "257")
        note_line2.set("type", "SOLID")
        note_line2.set("width", "0.12 mm")
        note_line2.set("color", "#000000")

        note_spacing2 = etree.SubElement(endnote_pr, qname("hp", "noteSpacing"))
        note_spacing2.set("betweenNotes", "0")
        note_spacing2.set("belowLine", "567")
        note_spacing2.set("aboveLine", "850")

        numbering2 = etree.SubElement(endnote_pr, qname("hp", "numbering"))
        numbering2.set("type", "CONTINUOUS")
        numbering2.set("newNum", "1")

        placement2 = etree.SubElement(endnote_pr, qname("hp", "placement"))
        placement2.set("place", "END_OF_DOCUMENT")
        placement2.set("beneathText", "0")

        # pageBorderFill (3번 - BOTH, EVEN, ODD)
        for border_type in ["BOTH", "EVEN", "ODD"]:
            pbf = etree.SubElement(sec_pr, qname("hp", "pageBorderFill"))
            pbf.set("type", border_type)
            pbf.set("borderFillIDRef", "1")
            pbf.set("textBorder", "PAPER")
            pbf.set("headerInside", "0")
            pbf.set("footerInside", "0")
            pbf.set("fillArea", "PAPER")

            offset = etree.SubElement(pbf, qname("hp", "offset"))
            offset.set("left", "1417")
            offset.set("right", "1417")
            offset.set("top", "1417")
            offset.set("bottom", "1417")

        return sec_pr

    def _build_header_footer(
        self,
        item: Union[IrHeader, IrFooter],
        is_header: bool,
    ) -> etree._Element:
        """머리글/바닥글 제어 요소 생성"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        tag = "header" if is_header else "footer"
        hf = etree.SubElement(ctrl, qname("hp", tag))
        hf.set("id", "1")
        hf.set("applyPageType", "BOTH")

        sub_list = etree.SubElement(hf, qname("hp", "subList"))
        sub_list.set("textDirection", "HORIZONTAL")
        sub_list.set("lineWrap", "BREAK")
        sub_list.set("vertAlign", "TOP" if is_header else "BOTTOM")

        p = etree.SubElement(sub_list, qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        t = etree.SubElement(run, qname("hp", "t"))
        t.text = item.text

        # linesegarray
        lineseg_array = etree.SubElement(p, qname("hp", "linesegarray"))
        lineseg = etree.SubElement(lineseg_array, qname("hp", "lineseg"))
        lineseg.set("textpos", "0")
        lineseg.set("vertpos", "0")
        lineseg.set("vertsize", "1000")
        lineseg.set("textheight", "1000")
        lineseg.set("baseline", "850")
        lineseg.set("spacing", "600")
        lineseg.set("horzpos", "0")
        lineseg.set("horzsize", "10000")
        lineseg.set("flags", "393216")

        return ctrl

    def build_page_number_ctrl(self, page_number: IrPageNumber) -> etree._Element:
        """페이지 번호 제어 요소 생성"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        page_num = etree.SubElement(ctrl, qname("hp", "pageNum"))
        page_num.set("pos", PAGE_NUM_POS_MAP.get(page_number.position, "BOTTOM_CENTER"))
        page_num.set("formatType", PAGE_NUM_FORMAT_MAP.get(page_number.format_type, "DIGIT"))
        page_num.set("sideChar", page_number.side_char)

        return ctrl

    def build_page_hiding_ctrl(self, page_hiding: IrPageHiding) -> etree._Element:
        """페이지 숨기기 제어 요소 생성"""
        ctrl = etree.Element(qname("hp", "ctrl"))

        hiding = etree.SubElement(ctrl, qname("hp", "pageHiding"))
        hiding.set("hideHeader", "1" if page_hiding.hide_header else "0")
        hiding.set("hideFooter", "1" if page_hiding.hide_footer else "0")
        hiding.set("hideMasterPage", "1" if page_hiding.hide_master_page else "0")
        hiding.set("hideBorder", "1" if page_hiding.hide_border else "0")
        hiding.set("hideFill", "1" if page_hiding.hide_fill else "0")
        hiding.set("hidePageNum", "1" if page_hiding.hide_page_num else "0")

        return ctrl
