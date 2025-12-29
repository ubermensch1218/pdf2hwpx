"""HWPX 콘텐츠 편집기"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import List, Optional, Tuple
from lxml import etree


NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
}

NSMAP = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}


def qname(prefix: str, local: str) -> str:
    """QName 생성"""
    return f"{{{NSMAP[prefix]}}}{local}"


class HwpxEditor:
    """HWPX 콘텐츠 편집기"""

    def __init__(self, section_xml: bytes):
        """
        Args:
            section_xml: section0.xml 바이트
        """
        self.root = etree.fromstring(section_xml)
        self._modified = False

    def is_modified(self) -> bool:
        """수정 여부"""
        return self._modified

    def to_bytes(self) -> bytes:
        """수정된 XML을 바이트로 반환"""
        return etree.tostring(self.root, encoding="UTF-8", xml_declaration=True, standalone="yes")

    def _get_paragraphs(self) -> List[etree._Element]:
        """최상위 단락만 반환 (테이블 내 단락 제외)"""
        return list(self.root.xpath("./hp:p", namespaces=NS))

    def _get_all_paragraphs(self) -> List[etree._Element]:
        """모든 단락 반환 (중첩 포함)"""
        return list(self.root.xpath(".//hp:p", namespaces=NS))

    # ============================================================
    # 1. 단락 삽입
    # ============================================================

    def insert_paragraph_after(
        self,
        after_index: int,
        text: str,
        para_pr_id: int = 0,
        char_pr_id: int = 0,
    ) -> bool:
        """특정 단락 뒤에 새 단락 삽입

        Args:
            after_index: 이 단락 뒤에 삽입 (최상위 단락 기준)
            text: 삽입할 텍스트
            para_pr_id: 단락 스타일 ID
            char_pr_id: 문자 스타일 ID

        Returns:
            성공 여부
        """
        paragraphs = self._get_paragraphs()
        if after_index < 0 or after_index >= len(paragraphs):
            return False

        target = paragraphs[after_index]
        parent = target.getparent()
        index = list(parent).index(target)

        new_p = self._create_paragraph(text, para_pr_id, char_pr_id)
        parent.insert(index + 1, new_p)

        self._modified = True
        return True

    def insert_paragraph_before(
        self,
        before_index: int,
        text: str,
        para_pr_id: int = 0,
        char_pr_id: int = 0,
    ) -> bool:
        """특정 단락 앞에 새 단락 삽입"""
        paragraphs = self._get_paragraphs()
        if before_index < 0 or before_index >= len(paragraphs):
            return False

        target = paragraphs[before_index]
        parent = target.getparent()
        index = list(parent).index(target)

        new_p = self._create_paragraph(text, para_pr_id, char_pr_id)
        parent.insert(index, new_p)

        self._modified = True
        return True

    def append_paragraph(
        self,
        text: str,
        para_pr_id: int = 0,
        char_pr_id: int = 0,
    ) -> bool:
        """문서 끝에 단락 추가"""
        new_p = self._create_paragraph(text, para_pr_id, char_pr_id)
        self.root.append(new_p)
        self._modified = True
        return True

    def _create_paragraph(
        self,
        text: str,
        para_pr_id: int = 0,
        char_pr_id: int = 0,
    ) -> etree._Element:
        """단락 요소 생성"""
        p = etree.Element(qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", str(para_pr_id))
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", str(char_pr_id))

        # 줄바꿈 처리
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                etree.SubElement(run, qname("hp", "lineBreak"))
            if line:
                t = etree.SubElement(run, qname("hp", "t"))
                t.text = line

        # linesegarray (기본)
        lsa = etree.SubElement(p, qname("hp", "linesegarray"))
        ls = etree.SubElement(lsa, qname("hp", "lineseg"))
        ls.set("textpos", "0")
        ls.set("vertpos", "0")
        ls.set("vertsize", "1000")
        ls.set("textheight", "1000")
        ls.set("baseline", "850")
        ls.set("spacing", "600")
        ls.set("horzpos", "0")
        ls.set("horzsize", "0")
        ls.set("flags", "393216")

        return p

    # ============================================================
    # 2. 단락 삭제
    # ============================================================

    def delete_paragraph(self, index: int) -> bool:
        """특정 단락 삭제 (최상위 단락 기준)"""
        paragraphs = self._get_paragraphs()
        if index < 0 or index >= len(paragraphs):
            return False

        target = paragraphs[index]
        parent = target.getparent()
        parent.remove(target)

        self._modified = True
        return True

    def delete_paragraphs_range(self, start: int, end: int) -> int:
        """범위 내 단락 삭제, 삭제된 개수 반환"""
        paragraphs = self._get_paragraphs()
        deleted = 0

        # 역순으로 삭제 (인덱스 변경 방지)
        for i in range(min(end, len(paragraphs)) - 1, max(0, start) - 1, -1):
            target = paragraphs[i]
            parent = target.getparent()
            parent.remove(target)
            deleted += 1

        if deleted > 0:
            self._modified = True
        return deleted

    # ============================================================
    # 3. 텍스트 수정
    # ============================================================

    def replace_text(self, old_text: str, new_text: str, count: int = -1) -> int:
        """텍스트 치환, 치환된 횟수 반환

        Args:
            old_text: 찾을 텍스트
            new_text: 바꿀 텍스트
            count: 최대 치환 횟수 (-1이면 전체)
        """
        replaced = 0
        for t_elem in self.root.xpath(".//hp:t", namespaces=NS):
            if t_elem.text and old_text in t_elem.text:
                if count == -1:
                    t_elem.text = t_elem.text.replace(old_text, new_text)
                    replaced += t_elem.text.count(new_text)
                else:
                    remaining = count - replaced
                    if remaining > 0:
                        t_elem.text = t_elem.text.replace(old_text, new_text, remaining)
                        replaced += min(remaining, t_elem.text.count(new_text))

                if count != -1 and replaced >= count:
                    break

        if replaced > 0:
            self._modified = True
        return replaced

    def set_paragraph_text(self, index: int, text: str, char_pr_id: int = 0) -> bool:
        """특정 단락의 텍스트 교체"""
        paragraphs = self._get_paragraphs()
        if index < 0 or index >= len(paragraphs):
            return False

        p = paragraphs[index]

        # 기존 run 제거
        for run in p.xpath("./hp:run", namespaces=NS):
            p.remove(run)

        # 새 run 추가
        run = etree.Element(qname("hp", "run"))
        run.set("charPrIDRef", str(char_pr_id))

        lines = text.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                etree.SubElement(run, qname("hp", "lineBreak"))
            if line:
                t = etree.SubElement(run, qname("hp", "t"))
                t.text = line

        # linesegarray 앞에 삽입
        lsa = p.find("hp:linesegarray", NS)
        if lsa is not None:
            lsa_index = list(p).index(lsa)
            p.insert(lsa_index, run)
        else:
            p.append(run)

        self._modified = True
        return True

    # ============================================================
    # 4. 단락 복사/이동
    # ============================================================

    def copy_paragraph(self, from_index: int, to_index: int) -> bool:
        """단락 복사"""
        paragraphs = self._get_paragraphs()
        if from_index < 0 or from_index >= len(paragraphs):
            return False
        if to_index < 0 or to_index > len(paragraphs):
            return False

        source = paragraphs[from_index]
        new_p = copy.deepcopy(source)

        if to_index >= len(paragraphs):
            self.root.append(new_p)
        else:
            target = paragraphs[to_index]
            parent = target.getparent()
            index = list(parent).index(target)
            parent.insert(index, new_p)

        self._modified = True
        return True

    def move_paragraph(self, from_index: int, to_index: int) -> bool:
        """단락 이동"""
        paragraphs = self._get_paragraphs()
        if from_index < 0 or from_index >= len(paragraphs):
            return False
        if to_index < 0 or to_index > len(paragraphs):
            return False
        if from_index == to_index:
            return True

        source = paragraphs[from_index]
        parent = source.getparent()
        parent.remove(source)

        # 인덱스 재계산
        paragraphs = self._get_paragraphs()
        if to_index >= len(paragraphs):
            self.root.append(source)
        else:
            target = paragraphs[to_index]
            parent = target.getparent()
            index = list(parent).index(target)
            parent.insert(index, source)

        self._modified = True
        return True

    # ============================================================
    # 5. 페이지 브레이크 제어
    # ============================================================

    def set_page_break(self, index: int, enable: bool = True) -> bool:
        """단락에 페이지 브레이크 설정"""
        paragraphs = self._get_paragraphs()
        if index < 0 or index >= len(paragraphs):
            return False

        paragraphs[index].set("pageBreak", "1" if enable else "0")
        self._modified = True
        return True

    def set_column_break(self, index: int, enable: bool = True) -> bool:
        """단락에 열 브레이크 설정"""
        paragraphs = self._get_paragraphs()
        if index < 0 or index >= len(paragraphs):
            return False

        paragraphs[index].set("columnBreak", "1" if enable else "0")
        self._modified = True
        return True

    # ============================================================
    # 6. 스타일 변경
    # ============================================================

    def set_paragraph_style(self, index: int, para_pr_id: int) -> bool:
        """단락 스타일 변경"""
        paragraphs = self._get_paragraphs()
        if index < 0 or index >= len(paragraphs):
            return False

        paragraphs[index].set("paraPrIDRef", str(para_pr_id))
        self._modified = True
        return True

    def set_char_style(self, para_index: int, char_pr_id: int) -> bool:
        """단락 내 모든 run의 문자 스타일 변경"""
        paragraphs = self._get_paragraphs()
        if para_index < 0 or para_index >= len(paragraphs):
            return False

        for run in paragraphs[para_index].xpath("./hp:run", namespaces=NS):
            run.set("charPrIDRef", str(char_pr_id))

        self._modified = True
        return True

    # ============================================================
    # 7. 유틸리티
    # ============================================================

    def get_paragraph_count(self) -> int:
        """최상위 단락 수"""
        return len(self._get_paragraphs())

    def get_paragraph_text(self, index: int) -> Optional[str]:
        """특정 단락 텍스트"""
        paragraphs = self._get_paragraphs()
        if index < 0 or index >= len(paragraphs):
            return None

        texts = []
        for t in paragraphs[index].xpath(".//hp:t", namespaces=NS):
            if t.text:
                texts.append(t.text)
        return "".join(texts)

    # ============================================================
    # 8. 테이블 삽입
    # ============================================================

    def insert_table_after(
        self,
        after_index: int,
        rows: int,
        cols: int,
        data: Optional[List[List[str]]] = None,
        col_widths: Optional[List[int]] = None,
        border_fill_id: int = 1,
    ) -> bool:
        """특정 단락 뒤에 테이블 삽입

        Args:
            after_index: 이 단락 뒤에 삽입
            rows: 행 수
            cols: 열 수
            data: 2D 문자열 리스트 (옵션)
            col_widths: 열 너비 리스트 (HWPUNIT, 옵션)
            border_fill_id: 테두리 스타일 ID

        Returns:
            성공 여부
        """
        paragraphs = self._get_paragraphs()
        if after_index < 0 or after_index >= len(paragraphs):
            return False

        target = paragraphs[after_index]
        parent = target.getparent()
        index = list(parent).index(target)

        # 테이블을 담을 단락 생성
        table_p = self._create_table_paragraph(rows, cols, data, col_widths, border_fill_id)
        parent.insert(index + 1, table_p)

        self._modified = True
        return True

    def _create_table_paragraph(
        self,
        rows: int,
        cols: int,
        data: Optional[List[List[str]]],
        col_widths: Optional[List[int]],
        border_fill_id: int,
    ) -> etree._Element:
        """테이블이 포함된 단락 생성"""
        # 기본 열 너비 (없으면 균등 분할, 총 너비 약 42520 HWPUNIT = 약 15cm)
        if not col_widths:
            default_width = 42520 // cols
            col_widths = [default_width] * cols

        total_width = sum(col_widths)
        row_height = 1000  # 기본 행 높이

        p = etree.Element(qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        # 테이블 생성
        tbl = etree.SubElement(run, qname("hp", "tbl"))
        tbl.set("id", "0")
        tbl.set("zOrder", "0")
        tbl.set("numberingType", "TABLE")
        tbl.set("textWrap", "TOP_AND_BOTTOM")
        tbl.set("textFlow", "BOTH_SIDES")
        tbl.set("lock", "0")
        tbl.set("dropcapstyle", "None")
        tbl.set("pageBreak", "CELL")
        tbl.set("repeatHeader", "0")
        tbl.set("rowCnt", str(rows))
        tbl.set("colCnt", str(cols))
        tbl.set("cellSpacing", "0")
        tbl.set("borderFillIDRef", str(border_fill_id))
        tbl.set("noAdjust", "0")

        # 테이블 크기
        sz = etree.SubElement(tbl, qname("hp", "sz"))
        sz.set("width", str(total_width))
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", str(row_height * rows))
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # 위치
        pos = etree.SubElement(tbl, qname("hp", "pos"))
        pos.set("treatAsChar", "1")
        pos.set("affectLSpacing", "0")
        pos.set("flowWithText", "1")
        pos.set("allowOverlap", "0")
        pos.set("holdAnchorAndSO", "0")
        pos.set("vertRelTo", "PARA")
        pos.set("horzRelTo", "COLUMN")
        pos.set("vertAlign", "TOP")
        pos.set("horzAlign", "LEFT")
        pos.set("vertOffset", "0")
        pos.set("horzOffset", "0")

        # 여백
        out_margin = etree.SubElement(tbl, qname("hp", "outMargin"))
        out_margin.set("left", "0")
        out_margin.set("right", "0")
        out_margin.set("top", "0")
        out_margin.set("bottom", "0")

        in_margin = etree.SubElement(tbl, qname("hp", "inMargin"))
        in_margin.set("left", "141")
        in_margin.set("right", "141")
        in_margin.set("top", "141")
        in_margin.set("bottom", "141")

        # 행/셀 생성
        for row_idx in range(rows):
            tr = etree.SubElement(tbl, qname("hp", "tr"))
            for col_idx in range(cols):
                tc = self._create_table_cell(
                    row_idx, col_idx,
                    col_widths[col_idx], row_height,
                    data[row_idx][col_idx] if data and row_idx < len(data) and col_idx < len(data[row_idx]) else "",
                    border_fill_id,
                )
                tr.append(tc)

        # linesegarray
        lsa = etree.SubElement(p, qname("hp", "linesegarray"))
        ls = etree.SubElement(lsa, qname("hp", "lineseg"))
        ls.set("textpos", "0")
        ls.set("vertpos", "0")
        ls.set("vertsize", str(row_height * rows))
        ls.set("textheight", str(row_height * rows))
        ls.set("baseline", "850")
        ls.set("spacing", "600")
        ls.set("horzpos", "0")
        ls.set("horzsize", str(total_width))
        ls.set("flags", "393216")

        return p

    def _create_table_cell(
        self,
        row: int,
        col: int,
        width: int,
        height: int,
        text: str,
        border_fill_id: int,
    ) -> etree._Element:
        """테이블 셀 생성"""
        tc = etree.Element(qname("hp", "tc"))
        tc.set("name", "")
        tc.set("header", "0")
        tc.set("hasMargin", "0")
        tc.set("protect", "0")
        tc.set("editable", "0")
        tc.set("dirty", "0")
        tc.set("borderFillIDRef", str(border_fill_id))

        # 셀 내용
        sub_list = etree.SubElement(tc, qname("hp", "subList"))
        sub_list.set("id", "")
        sub_list.set("textDirection", "HORIZONTAL")
        sub_list.set("lineWrap", "BREAK")
        sub_list.set("vertAlign", "CENTER")
        sub_list.set("linkListIDRef", "0")
        sub_list.set("linkListNextIDRef", "0")
        sub_list.set("textWidth", "0")
        sub_list.set("textHeight", "0")
        sub_list.set("hasTextRef", "0")
        sub_list.set("hasNumRef", "0")

        # 셀 내 단락
        cell_p = etree.SubElement(sub_list, qname("hp", "p"))
        cell_p.set("id", "0")
        cell_p.set("paraPrIDRef", "0")
        cell_p.set("styleIDRef", "0")
        cell_p.set("pageBreak", "0")
        cell_p.set("columnBreak", "0")
        cell_p.set("merged", "0")

        cell_run = etree.SubElement(cell_p, qname("hp", "run"))
        cell_run.set("charPrIDRef", "0")

        if text:
            t = etree.SubElement(cell_run, qname("hp", "t"))
            t.text = text

        cell_lsa = etree.SubElement(cell_p, qname("hp", "linesegarray"))
        cell_ls = etree.SubElement(cell_lsa, qname("hp", "lineseg"))
        cell_ls.set("textpos", "0")
        cell_ls.set("vertpos", "0")
        cell_ls.set("vertsize", "1000")
        cell_ls.set("textheight", "1000")
        cell_ls.set("baseline", "850")
        cell_ls.set("spacing", "600")
        cell_ls.set("horzpos", "0")
        cell_ls.set("horzsize", "0")
        cell_ls.set("flags", "393216")

        # 셀 주소
        cell_addr = etree.SubElement(tc, qname("hp", "cellAddr"))
        cell_addr.set("colAddr", str(col))
        cell_addr.set("rowAddr", str(row))

        # 셀 병합
        cell_span = etree.SubElement(tc, qname("hp", "cellSpan"))
        cell_span.set("colSpan", "1")
        cell_span.set("rowSpan", "1")

        # 셀 크기
        cell_sz = etree.SubElement(tc, qname("hp", "cellSz"))
        cell_sz.set("width", str(width))
        cell_sz.set("height", str(height))

        # 셀 여백
        cell_margin = etree.SubElement(tc, qname("hp", "cellMargin"))
        cell_margin.set("left", "141")
        cell_margin.set("right", "141")
        cell_margin.set("top", "141")
        cell_margin.set("bottom", "141")

        return tc

    # ============================================================
    # 9. 이미지 삽입
    # ============================================================

    def insert_image_after(
        self,
        after_index: int,
        binary_item_id: str,
        width: int,
        height: int,
    ) -> bool:
        """특정 단락 뒤에 이미지 삽입

        Args:
            after_index: 이 단락 뒤에 삽입
            binary_item_id: BinData 항목 ID (예: "IMG1")
            width: 너비 (HWPUNIT)
            height: 높이 (HWPUNIT)

        Returns:
            성공 여부

        Note:
            이미지 바이너리는 별도로 BinData/에 추가해야 함
        """
        paragraphs = self._get_paragraphs()
        if after_index < 0 or after_index >= len(paragraphs):
            return False

        target = paragraphs[after_index]
        parent = target.getparent()
        index = list(parent).index(target)

        image_p = self._create_image_paragraph(binary_item_id, width, height)
        parent.insert(index + 1, image_p)

        self._modified = True
        return True

    def _create_image_paragraph(
        self,
        binary_item_id: str,
        width: int,
        height: int,
    ) -> etree._Element:
        """이미지가 포함된 단락 생성"""
        p = etree.Element(qname("hp", "p"))
        p.set("id", "0")
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")

        # 이미지 생성
        pic = etree.SubElement(run, qname("hp", "pic"))
        pic.set("id", "0")
        pic.set("zOrder", "0")
        pic.set("numberingType", "PICTURE")
        pic.set("textWrap", "TOP_AND_BOTTOM")
        pic.set("textFlow", "BOTH_SIDES")
        pic.set("lock", "0")
        pic.set("dropcapstyle", "None")
        pic.set("href", "")
        pic.set("groupLevel", "0")
        pic.set("instid", "0")
        pic.set("reverse", "0")

        # offset
        offset = etree.SubElement(pic, qname("hp", "offset"))
        offset.set("x", "0")
        offset.set("y", "0")

        # orgSz
        org_sz = etree.SubElement(pic, qname("hp", "orgSz"))
        org_sz.set("width", str(width))
        org_sz.set("height", str(height))

        # curSz
        cur_sz = etree.SubElement(pic, qname("hp", "curSz"))
        cur_sz.set("width", str(width))
        cur_sz.set("height", str(height))

        # flip
        flip = etree.SubElement(pic, qname("hp", "flip"))
        flip.set("horizontal", "0")
        flip.set("vertical", "0")

        # rotationInfo
        rot_info = etree.SubElement(pic, qname("hp", "rotationInfo"))
        rot_info.set("angle", "0")
        rot_info.set("centerX", str(width // 2))
        rot_info.set("centerY", str(height // 2))
        rot_info.set("rotateimage", "1")

        # renderingInfo
        rend_info = etree.SubElement(pic, qname("hp", "renderingInfo"))

        trans = etree.SubElement(rend_info, qname("hc", "transMatrix"))
        trans.set("e1", "1"); trans.set("e2", "0"); trans.set("e3", "0")
        trans.set("e4", "0"); trans.set("e5", "1"); trans.set("e6", "0")

        sca = etree.SubElement(rend_info, qname("hc", "scaMatrix"))
        sca.set("e1", "1.000000"); sca.set("e2", "0"); sca.set("e3", "0")
        sca.set("e4", "0"); sca.set("e5", "1.000000"); sca.set("e6", "0")

        rot = etree.SubElement(rend_info, qname("hc", "rotMatrix"))
        rot.set("e1", "1.000000"); rot.set("e2", "0"); rot.set("e3", "0")
        rot.set("e4", "0"); rot.set("e5", "1.000000"); rot.set("e6", "0")

        # img
        img = etree.SubElement(pic, qname("hc", "img"))
        img.set("binaryItemIDRef", binary_item_id)
        img.set("effect", "REAL_PIC")
        img.set("alpha", "0")
        img.set("bright", "0")
        img.set("contrast", "0")

        # imgRect
        img_rect = etree.SubElement(pic, qname("hp", "imgRect"))
        pt0 = etree.SubElement(img_rect, qname("hc", "pt0")); pt0.set("x", "0"); pt0.set("y", "0")
        pt1 = etree.SubElement(img_rect, qname("hc", "pt1")); pt1.set("x", str(width)); pt1.set("y", "0")
        pt2 = etree.SubElement(img_rect, qname("hc", "pt2")); pt2.set("x", str(width)); pt2.set("y", str(height))
        pt3 = etree.SubElement(img_rect, qname("hc", "pt3")); pt3.set("x", "0"); pt3.set("y", str(height))

        # imgClip
        img_clip = etree.SubElement(pic, qname("hp", "imgClip"))
        img_clip.set("left", "0"); img_clip.set("right", str(width))
        img_clip.set("top", "0"); img_clip.set("bottom", str(height))

        # inMargin
        in_margin = etree.SubElement(pic, qname("hp", "inMargin"))
        in_margin.set("left", "0"); in_margin.set("right", "0")
        in_margin.set("top", "0"); in_margin.set("bottom", "0")

        # imgDim
        img_dim = etree.SubElement(pic, qname("hp", "imgDim"))
        img_dim.set("dimwidth", str(width))
        img_dim.set("dimheight", str(height))

        # effects
        etree.SubElement(pic, qname("hp", "effects"))

        # sz
        sz = etree.SubElement(pic, qname("hp", "sz"))
        sz.set("width", str(width))
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", str(height))
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # pos
        pos = etree.SubElement(pic, qname("hp", "pos"))
        pos.set("treatAsChar", "1")
        pos.set("affectLSpacing", "0")
        pos.set("flowWithText", "1")
        pos.set("allowOverlap", "0")
        pos.set("holdAnchorAndSO", "0")
        pos.set("vertRelTo", "PARA")
        pos.set("horzRelTo", "COLUMN")
        pos.set("vertAlign", "TOP")
        pos.set("horzAlign", "LEFT")
        pos.set("vertOffset", "0")
        pos.set("horzOffset", "0")

        # outMargin
        out_margin = etree.SubElement(pic, qname("hp", "outMargin"))
        out_margin.set("left", "0"); out_margin.set("right", "0")
        out_margin.set("top", "0"); out_margin.set("bottom", "0")

        # shapeComment
        etree.SubElement(pic, qname("hp", "shapeComment"))

        # linesegarray
        lsa = etree.SubElement(p, qname("hp", "linesegarray"))
        ls = etree.SubElement(lsa, qname("hp", "lineseg"))
        ls.set("textpos", "0")
        ls.set("vertpos", "0")
        ls.set("vertsize", str(height))
        ls.set("textheight", str(height))
        ls.set("baseline", "850")
        ls.set("spacing", "600")
        ls.set("horzpos", "0")
        ls.set("horzsize", str(width))
        ls.set("flags", "393216")

        return p
