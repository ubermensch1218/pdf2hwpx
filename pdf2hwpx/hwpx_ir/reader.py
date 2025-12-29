"""HWPX IR Reader

HWPX 파일을 읽어서 IR 모델로 변환하는 메인 리더.
각 컴포넌트 리더들을 조합하여 사용합니다.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, is_tag
from pdf2hwpx.hwpx_ir.models import (
    IrBlock,
    IrDocument,
)
from pdf2hwpx.hwpx_ir.components import (
    TextReader,
    ParagraphReader,
    TableReader,
    ImageReader,
    EquationReader,
    SectionReader,
)


@dataclass(frozen=True)
class HwpxBinaryItem:
    """HWPX 바이너리 항목 (이미지 등)"""
    id: str
    filename: str
    data: bytes


@dataclass(frozen=True)
class HwpxPackage:
    """HWPX 패키지 구조"""
    header_xml: bytes
    section_xml_list: List[Tuple[str, bytes]]
    binary_items: Dict[str, HwpxBinaryItem]


class HwpxIrReader:
    """HWPX 파일을 IR로 변환하는 리더"""

    def __init__(self):
        self.header_tree: Optional[etree._Element] = None

        # 컴포넌트 리더들 (lazy init)
        self._text_reader: Optional[TextReader] = None
        self._paragraph_reader: Optional[ParagraphReader] = None
        self._table_reader: Optional[TableReader] = None
        self._image_reader: Optional[ImageReader] = None
        self._equation_reader: Optional[EquationReader] = None
        self._section_reader: Optional[SectionReader] = None

    def _init_readers(self):
        """컴포넌트 리더들 초기화"""
        self._text_reader = TextReader(self.header_tree)
        self._paragraph_reader = ParagraphReader(self._text_reader, self.header_tree)
        self._table_reader = TableReader(self._paragraph_reader)
        self._image_reader = ImageReader()
        self._equation_reader = EquationReader()
        self._section_reader = SectionReader(
            self._paragraph_reader,
            self._table_reader,
            self._image_reader,
        )

    def read_package(self, hwpx_path: str) -> HwpxPackage:
        """HWPX 파일에서 패키지 정보 읽기"""
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            # mimetype 확인
            mimetype = zf.read("mimetype").decode("utf-8").strip()
            if mimetype != "application/hwp+zip":
                raise ValueError(f"Invalid HWPX mimetype: {mimetype}")

            # header.xml
            header_xml = zf.read("Contents/header.xml")

            # section XML들
            section_xml_list: List[Tuple[str, bytes]] = []
            section_idx = 0
            while True:
                name = f"Contents/section{section_idx}.xml"
                try:
                    section_xml_list.append((name, zf.read(name)))
                    section_idx += 1
                except KeyError:
                    break

            # 바이너리 항목들
            binary_items: Dict[str, HwpxBinaryItem] = {}
            for name in zf.namelist():
                if not name.startswith("BinData/"):
                    continue
                filename = name.split("/", 1)[1]
                if not filename:
                    continue
                item_id = filename.rsplit(".", 1)[0]
                binary_items[item_id] = HwpxBinaryItem(
                    id=item_id,
                    filename=filename,
                    data=zf.read(name),
                )

            return HwpxPackage(
                header_xml=header_xml,
                section_xml_list=section_xml_list,
                binary_items=binary_items,
            )

    def read_ir(self, hwpx_path: str) -> IrDocument:
        """HWPX 파일을 IrDocument로 변환"""
        pkg = self.read_package(hwpx_path)

        # header 파싱
        self.header_tree = etree.fromstring(pkg.header_xml)
        self._init_readers()

        blocks: List[IrBlock] = []

        for _, section_xml in pkg.section_xml_list:
            section_blocks = self._parse_section(section_xml)
            blocks.extend(section_blocks)

        return IrDocument(blocks=blocks)

    def _parse_section(self, section_xml: bytes) -> List[IrBlock]:
        """섹션 XML 파싱"""
        root = etree.fromstring(section_xml)

        blocks: List[IrBlock] = []

        for elem in root:
            if is_tag(elem, "hp", "p"):
                para = self._paragraph_reader.parse(elem)
                blocks.append(IrBlock(type="paragraph", paragraph=para))

            elif is_tag(elem, "hp", "tbl"):
                table = self._table_reader.parse(elem)
                blocks.append(IrBlock(type="table", table=table))

            elif is_tag(elem, "hp", "pic"):
                image = self._image_reader.parse(elem)
                if image is not None:
                    blocks.append(IrBlock(type="image", image=image))

            elif is_tag(elem, "hp", "equation"):
                equation = self._equation_reader.parse(elem)
                if equation is not None:
                    blocks.append(IrBlock(type="equation", equation=equation))

        return blocks

    def read_binary_items(self, hwpx_path: str) -> Dict[str, HwpxBinaryItem]:
        """바이너리 항목들만 읽기"""
        pkg = self.read_package(hwpx_path)
        return pkg.binary_items
