"""HWPX IR Writer

IR 모델을 HWPX 파일로 변환하는 메인 라이터.
각 컴포넌트 라이터들을 조합하여 사용합니다.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname, guess_media_type
from pdf2hwpx.hwpx_ir.models import (
    IrBlock,
    IrDocument,
    IrParagraph,
    IrTextRun,
)
from pdf2hwpx.hwpx_ir.components import (
    ParagraphWriter,
    TableWriter,
    ImageWriter,
    EquationWriter,
    SectionWriter,
    ListWriter,
    TOCWriter,
)


@dataclass(frozen=True)
class HwpxBinaryItem:
    """HWPX 바이너리 항목"""
    id: str
    filename: str
    data: bytes


class HwpxIdContext:
    """HWPX 요소 ID 관리"""

    def __init__(self):
        self.para_id = 0
        self.tbl_id = 0
        self.pic_id = 2000000000

    def next_para_id(self) -> int:
        pid = self.para_id
        self.para_id += 1
        return pid

    def next_tbl_id(self) -> int:
        tid = self.tbl_id
        self.tbl_id += 1
        return tid

    def next_pic_id(self) -> int:
        pid = self.pic_id
        self.pic_id += 1
        return pid


class StyleManager:
    """HWPX 스타일 관리자"""

    # 기본 폰트 설정 (함초롬돋움 = id 1)
    DEFAULT_FONT_ID = 1
    DEFAULT_FONT_SIZE = 1000  # 10pt

    def __init__(self, header_xml: bytes):
        self.tree = etree.fromstring(header_xml)
        self.root = self.tree

        # refList 찾기
        ref_list = self.root.find(etree.QName(NS["hh"], "refList"))
        if ref_list is None:
            ref_list = self.root

        # 폰트 파싱 - fontface > font 구조
        self.fontfaces_node = ref_list.find(etree.QName(NS["hh"], "fontfaces"))
        self.font_map: Dict[str, int] = {}
        if self.fontfaces_node is not None:
            for fontface in self.fontfaces_node.findall(etree.QName(NS["hh"], "fontface")):
                for font in fontface.findall(etree.QName(NS["hh"], "font")):
                    fid = int(font.get("id", "0"))
                    name = font.get("face", "")
                    if name and name not in self.font_map:
                        self.font_map[name] = fid

        # 문자 속성 노드
        self.char_prs_node = ref_list.find(etree.QName(NS["hh"], "charProperties"))

        # charPr id=0의 폰트를 함초롬돋움(id=1)으로 변경
        self._update_default_font()

    def _update_default_font(self):
        """기본 charPr(id=0)의 폰트를 함초롬돋움으로 변경"""
        if self.char_prs_node is None:
            return

        for cp in self.char_prs_node.findall(etree.QName(NS["hh"], "charPr")):
            if cp.get("id") == "0":
                # fontRef 자식 요소 찾기
                font_ref = cp.find(etree.QName(NS["hh"], "fontRef"))
                if font_ref is not None:
                    # 모든 언어의 폰트를 함초롬돋움(id=1)으로 변경
                    for attr in ["hangul", "latin", "hanja", "japanese", "other", "symbol", "user"]:
                        font_ref.set(attr, str(self.DEFAULT_FONT_ID))
                break

    def get_font_id(self, font_name: str) -> int:
        """폰트 ID 반환 (없으면 기본 1)"""
        if not font_name:
            return self.DEFAULT_FONT_ID
        return self.font_map.get(font_name, self.DEFAULT_FONT_ID)

    def get_char_pr_id(self, run: IrTextRun) -> int:
        """문자 속성 ID 반환 - 템플릿 기본 스타일(0) 사용"""
        return 0

    def get_updated_header_xml(self) -> bytes:
        """업데이트된 header.xml 반환"""
        if self.char_prs_node is not None:
            count = len(self.char_prs_node.findall(etree.QName(NS["hh"], "charPr")))
            self.char_prs_node.set("itemCnt", str(count))

        if self.fontfaces_node is not None:
            count = len(self.fontfaces_node.findall(etree.QName(NS["hh"], "fontface")))
            self.fontfaces_node.set("itemCnt", str(count))

        return etree.tostring(self.root, encoding="UTF-8", xml_declaration=True, standalone=True)


class HwpxIrWriter:
    """IR을 HWPX 파일로 변환하는 라이터"""

    def __init__(self, template_hwpx_path: str):
        self.template_hwpx_path = template_hwpx_path
        self.style_manager: Optional[StyleManager] = None

        # 컴포넌트 라이터들 (lazy init)
        self._paragraph_writer: Optional[ParagraphWriter] = None
        self._table_writer: Optional[TableWriter] = None
        self._image_writer: Optional[ImageWriter] = None
        self._equation_writer: Optional[EquationWriter] = None
        self._section_writer: Optional[SectionWriter] = None
        self._list_writer: Optional[ListWriter] = None
        self._toc_writer: Optional[TOCWriter] = None

    def _init_writers(self):
        """컴포넌트 라이터들 초기화"""
        self._paragraph_writer = ParagraphWriter(self.style_manager)
        self._table_writer = TableWriter(self._paragraph_writer)
        self._image_writer = ImageWriter()
        self._equation_writer = EquationWriter()
        self._section_writer = SectionWriter()
        self._list_writer = ListWriter(self._paragraph_writer)
        self._toc_writer = TOCWriter(self._paragraph_writer)

    def write(self, doc: IrDocument, binary_items: Dict[str, HwpxBinaryItem]) -> bytes:
        """IrDocument를 HWPX 바이트로 변환"""
        with zipfile.ZipFile(self.template_hwpx_path, "r") as src:
            # header.xml 읽어서 StyleManager 초기화
            try:
                header_xml = src.read("Contents/header.xml")
                self.style_manager = StyleManager(header_xml)
            except KeyError:
                self.style_manager = None

            self._init_writers()

            template_content_hpf: Optional[bytes] = None

            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as out:
                # 섹션 빌드
                section_xml = self._build_section0(doc)

                # 템플릿 파일들 복사
                for info in src.infolist():
                    if info.filename == "Contents/section0.xml":
                        continue
                    if info.filename == "Contents/content.hpf":
                        template_content_hpf = src.read(info.filename)
                        continue
                    if info.filename == "Contents/header.xml":
                        if self.style_manager:
                            out.writestr(info.filename, self.style_manager.get_updated_header_xml())
                        else:
                            out.writestr(info.filename, src.read(info.filename))
                        continue
                    if info.filename.startswith("BinData/"):
                        continue

                    out.writestr(info, src.read(info.filename))

                # 섹션 쓰기
                out.writestr("Contents/section0.xml", section_xml)

                # content.hpf 업데이트
                if template_content_hpf:
                    content_hpf = self._build_content_hpf(template_content_hpf, binary_items)
                    out.writestr("Contents/content.hpf", content_hpf)

                # 바이너리 항목들 쓰기
                for item in binary_items.values():
                    out.writestr(f"BinData/{item.filename}", item.data)

            return mem.getvalue()

    def _build_section0(self, doc: IrDocument) -> bytes:
        """섹션 XML 생성"""
        root = etree.Element(
            qname("hs", "sec"),
            nsmap={
                "ha": NS["ha"],
                "hp": NS["hp"],
                "hp10": NS["hp10"],
                "hs": NS["hs"],
                "hc": NS["hc"],
                "hh": NS["hh"],
                "hpf": NS["hpf"],
            },
        )

        context = HwpxIdContext()

        for block in doc.blocks:
            if block.type == "section" and block.section:
                # 섹션 정의 생성
                controls = self._section_writer.build_definition(block.section)

                # 앵커 단락
                processing_blocks = block.section.blocks
                anchor_para = None

                if not processing_blocks:
                    anchor_para = self._paragraph_writer.build_empty(context.next_para_id())
                    root.append(anchor_para)
                else:
                    first = processing_blocks[0]
                    if first.type == "paragraph" and first.paragraph:
                        anchor_para = self._paragraph_writer.build(first.paragraph, context.next_para_id())
                        root.append(anchor_para)
                        processing_blocks = processing_blocks[1:]
                    else:
                        anchor_para = self._paragraph_writer.build_empty(context.next_para_id())
                        root.append(anchor_para)

                # 컨트롤 삽입
                if len(anchor_para) > 0:
                    run = anchor_para[0]
                    for ctrl in reversed(controls):
                        run.insert(0, ctrl)

                # 나머지 블록 처리
                for b in processing_blocks:
                    elements = self._process_block(b, context)
                    for el in elements:
                        root.append(el)

            else:
                elements = self._process_block(block, context)
                for el in elements:
                    root.append(el)

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    def _process_block(self, block: IrBlock, context: HwpxIdContext) -> List[etree._Element]:
        """블록을 XML 요소로 변환"""
        elements = []

        if block.type == "paragraph" and block.paragraph:
            p = self._paragraph_writer.build(block.paragraph, context.next_para_id())
            # 페이지 브레이크 설정
            if block.page_break:
                p.set("pageBreak", "1")
            elements.append(p)

        elif block.type == "table" and block.table:
            tbl = self._table_writer.build(block.table, context)
            p = self._build_control_paragraph(tbl, context.next_para_id())
            elements.append(p)

        elif block.type == "image" and block.image:
            pic = self._image_writer.build(block.image, context.next_pic_id())
            p = self._build_control_paragraph(pic, context.next_para_id())
            elements.append(p)

        elif block.type == "equation" and block.equation:
            eq = self._equation_writer.build(block.equation, context.next_pic_id())
            p = self._build_control_paragraph(eq, context.next_para_id())
            elements.append(p)

        elif block.type == "list" and block.list:
            list_elements = self._list_writer.build(block.list, context)
            elements.extend(list_elements)

        elif block.type == "toc" and block.toc:
            toc_elements = self._toc_writer.build(block.toc, context)
            elements.extend(toc_elements)

        return elements

    def _build_control_paragraph(self, ctrl: etree._Element, paragraph_id: int) -> etree._Element:
        """컨트롤을 포함하는 단락 생성"""
        p = etree.Element(qname("hp", "p"))
        p.set("id", str(paragraph_id))
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, qname("hp", "run"))
        run.set("charPrIDRef", "0")
        run.append(ctrl)

        linesegarray = etree.SubElement(p, qname("hp", "linesegarray"))
        lineseg = etree.SubElement(linesegarray, qname("hp", "lineseg"))
        lineseg.set("textpos", "0")
        lineseg.set("vertpos", "0")
        lineseg.set("vertsize", "1000")
        lineseg.set("textheight", "1000")
        lineseg.set("baseline", "850")
        lineseg.set("spacing", "600")
        lineseg.set("horzpos", "0")
        lineseg.set("horzsize", "0")
        lineseg.set("flags", "393216")

        return p

    def _build_content_hpf(
        self,
        template_content_hpf: bytes,
        binary_items: Dict[str, HwpxBinaryItem],
    ) -> bytes:
        """content.hpf 업데이트"""
        root = etree.fromstring(template_content_hpf)
        manifest = root.find(etree.QName(NS["opf"], "manifest"))
        if manifest is None:
            raise ValueError("Template content.hpf is missing <opf:manifest>")

        existing_by_id: Dict[str, etree._Element] = {}
        for item in manifest.findall(etree.QName(NS["opf"], "item")):
            item_id = item.get("id")
            if item_id:
                existing_by_id[item_id] = item

        # 기존 BinData 참조 정리
        for item in list(manifest.findall(etree.QName(NS["opf"], "item"))):
            href = item.get("href") or ""
            if not href.startswith("BinData/"):
                continue
            item_id = item.get("id")
            if not item_id or item_id not in binary_items:
                manifest.remove(item)
                if item_id:
                    existing_by_id.pop(item_id, None)

        # 새 바이너리 항목 추가
        for binary_item_id, binary_item in binary_items.items():
            media_type = guess_media_type(binary_item.filename)

            item = existing_by_id.get(binary_item_id)
            if item is None:
                item = etree.SubElement(manifest, etree.QName(NS["opf"], "item"))
                item.set("id", binary_item_id)
                existing_by_id[binary_item_id] = item

            item.set("href", f"BinData/{binary_item.filename}")
            item.set("media-type", media_type)
            item.set("isEmbeded", "1")

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
