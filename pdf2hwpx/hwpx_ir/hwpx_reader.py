from __future__ import annotations

import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from lxml import etree

from hwpx_ir.models import (
    IrBlock,
    IrDocument,
    IrImage,
    IrLineBreak,
    IrParagraph,
    IrTable,
    IrTableCell,
    IrTextRun,
)


NS = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}


@dataclass(frozen=True)
class HwpxBinaryItem:
    id: str
    filename: str
    data: bytes


@dataclass(frozen=True)
class HwpxPackage:
    header_xml: bytes
    section_xml_list: List[Tuple[str, bytes]]
    binary_items: Dict[str, HwpxBinaryItem]


class HwpxIrReader:
    def read_package(self, hwpx_path: str) -> HwpxPackage:
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            mimetype = zf.read("mimetype").decode("utf-8").strip()
            if mimetype != "application/hwp+zip":
                raise ValueError(f"Invalid HWPX mimetype: {mimetype}")

            header_xml = zf.read("Contents/header.xml")

            section_xml_list: List[Tuple[str, bytes]] = []
            section_idx = 0
            while True:
                name = f"Contents/section{section_idx}.xml"
                try:
                    section_xml_list.append((name, zf.read(name)))
                    section_idx += 1
                except KeyError:
                    break

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
        pkg = self.read_package(hwpx_path)
        blocks: List[IrBlock] = []

        for _, section_xml in pkg.section_xml_list:
            blocks.extend(self._parse_section(section_xml))

        return IrDocument(blocks=blocks)

    def _parse_section(self, section_xml: bytes) -> List[IrBlock]:
        root = etree.fromstring(section_xml)

        blocks: List[IrBlock] = []
        for elem in root:
            if self._is_tag(elem, "hp", "p"):
                para = self._parse_paragraph(elem)
                blocks.append(IrBlock(type="paragraph", paragraph=para))
            elif self._is_tag(elem, "hp", "tbl"):
                table = self._parse_table(elem)
                blocks.append(IrBlock(type="table", table=table))
            elif self._is_tag(elem, "hp", "pic"):
                image = self._parse_picture(elem)
                if image is not None:
                    blocks.append(IrBlock(type="image", image=image))

        return blocks

    def _parse_paragraph(self, p: etree._Element) -> IrParagraph:
        inlines: List[object] = []

        for run in p.xpath("./hp:run", namespaces=NS):
            for node in run:
                if self._is_tag(node, "hp", "t"):
                    if node.text:
                        parts = node.text.split("\n")
                        for idx, part in enumerate(parts):
                            if idx > 0:
                                inlines.append(IrLineBreak())
                            if part:
                                inlines.append(IrTextRun(text=part))
                elif self._is_tag(node, "hp", "ctrl"):
                    # Some documents embed images/tables as controls inside a paragraph.
                    # Milestone 1 keeps them at block level only.
                    continue
                elif self._is_tag(node, "hp", "pic") or self._is_tag(node, "hp", "tbl"):
                    continue
                elif self._is_tag(node, "hp", "lineBreak"):
                    inlines.append(IrLineBreak())

        raw_xml = etree.tostring(p, encoding="UTF-8")
        return IrParagraph(inlines=inlines, raw_xml=raw_xml)

    # Intentionally do not "lift" nested tables/images out of paragraphs.
    # Real-world HWPX frequently nests hp:tbl / hp:pic under hp:p controls.
    # For Milestone 1 we preserve fidelity by keeping the paragraph raw XML intact.

    def _parse_picture(self, pic: etree._Element) -> Optional[IrImage]:
        img = pic.xpath(".//hc:img", namespaces=NS)
        if not img:
            return None
        binary_id = img[0].get("binaryItemIDRef")
        if not binary_id:
            return None

        width = self._first_int(pic.xpath("./hp:sz/@width", namespaces=NS))
        height = self._first_int(pic.xpath("./hp:sz/@height", namespaces=NS))
        treat_as_char = self._first_int(pic.xpath("./hp:pos/@treatAsChar", namespaces=NS)) == 1

        raw_xml = etree.tostring(pic, encoding="UTF-8")
        return IrImage(
            image_id=binary_id,
            width_hwpunit=width,
            height_hwpunit=height,
            treat_as_char=treat_as_char,
            raw_xml=raw_xml,
        )

    def _parse_table(self, tbl: etree._Element) -> IrTable:
        row_cnt = int(tbl.get("rowCnt", "0"))
        col_cnt = int(tbl.get("colCnt", "0"))
        width = self._first_int(tbl.xpath("./hp:sz/@width", namespaces=NS))
        height = self._first_int(tbl.xpath("./hp:sz/@height", namespaces=NS))
        treat_as_char = self._first_int(tbl.xpath("./hp:pos/@treatAsChar", namespaces=NS)) != 0

        cells: List[IrTableCell] = []
        for tc in tbl.xpath(".//hp:tc", namespaces=NS):
            row = self._first_int(tc.xpath("./hp:cellAddr/@rowAddr", namespaces=NS))
            col = self._first_int(tc.xpath("./hp:cellAddr/@colAddr", namespaces=NS))
            row_span = self._first_int(tc.xpath("./hp:cellSpan/@rowSpan", namespaces=NS), default=1)
            col_span = self._first_int(tc.xpath("./hp:cellSpan/@colSpan", namespaces=NS), default=1)

            cell_width = self._first_int(tc.xpath("./hp:cellSz/@width", namespaces=NS))
            cell_height = self._first_int(tc.xpath("./hp:cellSz/@height", namespaces=NS))

            paragraphs: List[IrParagraph] = []
            for p in tc.xpath(".//hp:subList//hp:p", namespaces=NS):
                paragraphs.append(self._parse_paragraph(p))

            cells.append(
                IrTableCell(
                    row=row,
                    col=col,
                    row_span=row_span,
                    col_span=col_span,
                    paragraphs=paragraphs,
                    width_hwpunit=cell_width,
                    height_hwpunit=cell_height,
                )
            )

        raw_xml = etree.tostring(tbl, encoding="UTF-8")
        return IrTable(
            row_cnt=row_cnt,
            col_cnt=col_cnt,
            cells=cells,
            width_hwpunit=width,
            height_hwpunit=height,
            treat_as_char=treat_as_char,
            raw_xml=raw_xml,
        )

    def _is_tag(self, elem: etree._Element, prefix: str, local: str) -> bool:
        return elem.tag == f"{{{NS[prefix]}}}{local}"

    def _first_int(self, values: List[str], default: Optional[int] = None) -> Optional[int]:
        if not values:
            return default
        try:
            return int(values[0])
        except Exception:
            return default
