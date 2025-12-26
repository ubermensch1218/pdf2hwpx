from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional


def _guess_media_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".bmp"):
        return "image/bmp"
    return "application/octet-stream"

from lxml import etree

from pdf2hwpx.hwpx_ir.models import IrBlock, IrDocument, IrEquation, IrImage, IrLineBreak, IrParagraph, IrTable, IrTableCell, IrTextRun


NS = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "opf": "http://www.idpf.org/2007/opf/",
}


@dataclass(frozen=True)
class HwpxBinaryItem:
    id: str
    filename: str
    data: bytes


class HwpxIdContext:
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
    def __init__(self, header_xml: bytes):
        self.tree = etree.fromstring(header_xml)
        self.root = self.tree
        
        # Find refList
        ref_list = self.root.find(etree.QName(NS["hh"], "refList"))
        if ref_list is None:
            # Fallback for weird structures
            ref_list = self.root

        # Parse FontFaces
        self.fontfaces_node = ref_list.find(etree.QName(NS["hh"], "fontfaces"))
        self.font_map = {} # name -> id
        self.next_font_id = 0
        if self.fontfaces_node is not None:
            for ff in self.fontfaces_node.findall(etree.QName(NS["hh"], "fontface")):
                fid = int(ff.get("id", "0"))
                name = ff.get("font", "")
                self.font_map[name] = fid
                if fid >= self.next_font_id:
                    self.next_font_id = fid + 1
        
        # Parse CharPrs
        self.char_prs_node = ref_list.find(etree.QName(NS["hh"], "charProperties"))
        self.char_pr_map = {} # sig -> id
        self.next_char_pr_id = 0
        if self.char_prs_node is not None:
             for cp in self.char_prs_node.findall(etree.QName(NS["hh"], "charPr")):
                 cid = int(cp.get("id", "0"))
                 if cid >= self.next_char_pr_id:
                     self.next_char_pr_id = cid + 1

    def get_font_id(self, font_name: str) -> int:
        if not font_name:
            return 0
        if font_name in self.font_map:
            return self.font_map[font_name]
        
        # Create new fontface
        fid = self.next_font_id
        self.next_font_id += 1
        
        ff = etree.SubElement(self.fontfaces_node, etree.QName(NS["hh"], "fontface"))
        ff.set("lang", "ko") # Default lang
        ff.set("font", font_name)
        ff.set("id", str(fid))
        
        # Add basic sub-elements for substitution?
        # Usually requires <hh:fontTypeInfo family="..."/> etc.
        # Minimal: just id and font.
        
        self.font_map[font_name] = fid
        return fid

    def get_char_pr_id(self, run: IrTextRun) -> int:
        # Signature: (bold, italic, size, font, color)
        # Check if default (all None/False)
        if not run.bold and not run.italic and run.font_size is None and run.font_family is None and run.color is None:
            return 0 # Default style
        
        sig = (run.bold, run.italic, run.font_size, run.font_family, run.color)
        if sig in self.char_pr_map:
            return self.char_pr_map[sig]
        
        cid = self.next_char_pr_id
        self.next_char_pr_id += 1
        
        # Create CharPr
        # Based on default? Or scratch?
        # I'll base it on implied default (generic).
        cp = etree.SubElement(self.char_prs_node, etree.QName(NS["hh"], "charPr"))
        cp.set("id", str(cid))
        
        # 1. Height
        if run.font_size is not None:
            cp.set("height", str(run.font_size))
        else:
            cp.set("height", "1000") # Default 10pt
            
        # 2. Color
        if run.color:
            cp.set("textColor", run.color)
        else:
            cp.set("textColor", "#000000")
            
        # 3. Fonts (fontRef)
        # 3. Fonts (fontRef)
        if run.font_family:
            fid = self.get_font_id(run.font_family)
            cp.set("fontRef", str(fid))
            cp.set("fontRefHangul", str(fid))
            cp.set("fontRefLatin", str(fid))
            cp.set("fontRefHanja", str(fid))
            cp.set("fontRefJapanese", str(fid))
            cp.set("fontRefOther", str(fid))
            cp.set("fontRefSymbol", str(fid))
            cp.set("fontRefUser", str(fid))

        # 4. Bold/Italic
        if run.bold:
            cp.set("bold", "1")
        if run.italic:
            cp.set("italic", "1")
            
        self.char_pr_map[sig] = cid
        return cid

    def get_updated_header_xml(self) -> bytes:
        # Update itemCnt for charProperties
        if self.char_prs_node is not None:
             # Count all charPr children
             count = len(self.char_prs_node.findall(etree.QName(NS["hh"], "charPr")))
             self.char_prs_node.set("itemCnt", str(count))
        
        # Update itemCnt for fontfaces
        if self.fontfaces_node is not None:
             count = len(self.fontfaces_node.findall(etree.QName(NS["hh"], "fontface")))
             self.fontfaces_node.set("itemCnt", str(count))

        return etree.tostring(self.root, encoding="UTF-8", xml_declaration=True, standalone=True)


class HwpxIrWriter:
    def __init__(self, template_hwpx_path: str):
        self.template_hwpx_path = template_hwpx_path
        self.style_manager: Optional[StyleManager] = None

    def _build_content_hpf(self, template_content_hpf: bytes, binary_items: Dict[str, HwpxBinaryItem]) -> bytes:
        root = etree.fromstring(template_content_hpf)
        manifest = root.find(etree.QName(NS["opf"], "manifest"))
        if manifest is None:
            raise ValueError("Template content.hpf is missing <opf:manifest>")

        existing_by_id: Dict[str, etree._Element] = {}
        for item in manifest.findall(etree.QName(NS["opf"], "item")):
            item_id = item.get("id")
            if item_id:
                existing_by_id[item_id] = item

        # Remove stale BinData references from the template manifest.
        # Some templates contain placeholder images; we must not keep them unless the
        # output package actually includes the referenced BinData.
        for item in list(manifest.findall(etree.QName(NS["opf"], "item"))):
            href = item.get("href") or ""
            if not href.startswith("BinData/"):
                continue

            item_id = item.get("id")
            if not item_id or item_id not in binary_items:
                manifest.remove(item)
                if item_id:
                    existing_by_id.pop(item_id, None)

        for binary_item_id, binary_item in binary_items.items():
            media_type = _guess_media_type(binary_item.filename)

            item = existing_by_id.get(binary_item_id)
            if item is None:
                item = etree.SubElement(manifest, etree.QName(NS["opf"], "item"))
                item.set("id", binary_item_id)
                existing_by_id[binary_item_id] = item

            item.set("href", f"BinData/{binary_item.filename}")
            item.set("media-type", media_type)
            item.set("isEmbeded", "1")

        return etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )

    def _build_control_paragraph(self, ctrl: etree._Element, paragraph_id: int) -> etree._Element:
        p = etree.Element(etree.QName(NS["hp"], "p"))
        p.set("id", str(paragraph_id))
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run = etree.SubElement(p, etree.QName(NS["hp"], "run"))
        run.set("charPrIDRef", "0")
        run.append(ctrl)

        linesegarray = etree.SubElement(p, etree.QName(NS["hp"], "linesegarray"))
        lineseg = etree.SubElement(linesegarray, etree.QName(NS["hp"], "lineseg"))
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

    def write(self, doc: IrDocument, binary_items: Dict[str, HwpxBinaryItem]) -> bytes:
        with zipfile.ZipFile(self.template_hwpx_path, "r") as src:
            # 1. Read header.xml first to init StyleManager
            try:
                header_xml = src.read("Contents/header.xml")
                self.style_manager = StyleManager(header_xml)
            except KeyError:
                print("Warning: Contents/header.xml not found in template.")
                self.style_manager = None

            template_content_hpf: Optional[bytes] = None

            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as out:
                # 2. Build Content (now using style_manager)
                section_xml = self._build_section0(doc)

                # 3. Write items from template
                for info in src.infolist():
                    if info.filename == "Contents/section0.xml":
                        continue
                    if info.filename == "Contents/content.hpf":
                        template_content_hpf = src.read(info.filename)
                        continue
                    if info.filename == "Contents/header.xml":
                        # Write updated header if manager exists
                        if self.style_manager:
                             out.writestr(info.filename, self.style_manager.get_updated_header_xml())
                        else:
                             out.writestr(info.filename, src.read(info.filename))
                        continue
                    if info.filename.startswith("BinData/"):
                        continue

                    # Copy other files
                    data = src.read(info.filename)
                    out.writestr(info, data)

                if template_content_hpf is None:
                     # Check if we missed it (maybe loop didn't run or file missing?)
                     # If missing, try to read specifically?
                     # src.infolist() covers all.
                     pass

                out.writestr("Contents/section0.xml", section_xml)

                if template_content_hpf:
                    content_hpf = self._build_content_hpf(template_content_hpf, binary_items=binary_items)
                    out.writestr("Contents/content.hpf", content_hpf)
                
                for item in binary_items.values():
                    out.writestr(f"BinData/{item.filename}", item.data)

            return mem.getvalue()

    def _process_block(self, b: IrBlock, context: HwpxIdContext) -> List[etree._Element]:
        elements = []
        if b.type == "paragraph" and b.paragraph is not None:
             p = self._build_paragraph(b.paragraph, paragraph_id=context.next_para_id())
             elements.append(p)
        elif b.type == "table" and b.table is not None:
             tbl = self._build_table(b.table, context)
             p = self._build_control_paragraph(tbl, paragraph_id=context.next_para_id())
             elements.append(p)
        elif b.type == "image" and b.image is not None:
             pic = self._build_picture(b.image, pic_id=context.next_pic_id())
             p = self._build_control_paragraph(pic, paragraph_id=context.next_para_id())
             elements.append(p)
        elif b.type == "equation" and b.equation is not None:
             eq = self._build_equation(b.equation, eq_id=context.next_pic_id())
             p = self._build_control_paragraph(eq, paragraph_id=context.next_para_id())
             elements.append(p)
        return elements

    def _build_section0(self, doc: IrDocument) -> bytes:
        root = etree.Element(
            etree.QName(NS["hs"], "sec"),
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
                # 1. Generate controls
                controls = self._build_section_definition(block.section)
                
                # 2. Determine anchor paragraph
                processing_blocks = block.section.blocks
                
                anchor_para = None
                
                if not processing_blocks:
                    # Empty section
                    anchor_para = self._build_paragraph(IrParagraph(), context.next_para_id())
                    root.append(anchor_para)
                else:
                    first = processing_blocks[0]
                    if first.type == "paragraph" and first.paragraph:
                        anchor_para = self._build_paragraph(first.paragraph, context.next_para_id())
                        root.append(anchor_para)
                        processing_blocks = processing_blocks[1:] # Consume first
                    else:
                        # Prepend empty anchor paragraph
                        anchor_para = self._build_paragraph(IrParagraph(), context.next_para_id())
                        root.append(anchor_para)

                # 3. Inject controls into anchor_para's first run
                if len(anchor_para) > 0:
                    run = anchor_para[0] 
                    # Insert controls at index 0 of run
                    for ctrl in reversed(controls):
                        run.insert(0, ctrl)
                
                # 4. Process remaining blocks
                for b in processing_blocks:
                    elements = self._process_block(b, context)
                    for el in elements:
                        root.append(el)

            else:
                 # Standard block
                 elements = self._process_block(block, context)
                 for el in elements:
                     root.append(el)

        xml_bytes = etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )
        return xml_bytes

    def _build_paragraph(self, para: IrParagraph, paragraph_id: int) -> etree._Element:
        if para.raw_xml:
            return etree.fromstring(para.raw_xml)

        p = etree.Element(etree.QName(NS["hp"], "p"))
        p.set("id", str(paragraph_id))
        p.set("paraPrIDRef", "0")
        p.set("styleIDRef", "0")
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        if not para.inlines:
            # Empty paragraph requires at least one run? 
            # Usually creates a run with empty text or just a run structure.
            # Using defaults.
            run = etree.SubElement(p, etree.QName(NS["hp"], "run"))
            run.set("charPrIDRef", "0")
            return p

        for inline in para.inlines:
            run = etree.SubElement(p, etree.QName(NS["hp"], "run"))
            
            # Determine Style
            char_pr_id = 0
            if isinstance(inline, IrTextRun) and self.style_manager:
                char_pr_id = self.style_manager.get_char_pr_id(inline)
            
            run.set("charPrIDRef", str(char_pr_id))

            if isinstance(inline, IrTextRun):
                parts = inline.text.split("\n")
                for idx, part in enumerate(parts):
                    if idx > 0:
                        etree.SubElement(run, etree.QName(NS["hp"], "lineBreak"))
                    if part:
                        t = etree.SubElement(run, etree.QName(NS["hp"], "t"))
                        t.text = part
            
            elif isinstance(inline, IrLineBreak):
                etree.SubElement(run, etree.QName(NS["hp"], "lineBreak"))

            else:
                raise ValueError(f"Unsupported inline: {type(inline)}")

        return p

    def _build_picture(self, image: IrImage, pic_id: int) -> etree._Element:
        if image.raw_xml:
            return etree.fromstring(image.raw_xml)

    def _build_picture(self, image: IrImage, pic_id: int) -> etree._Element:
        if image.raw_xml:
            return etree.fromstring(image.raw_xml)

        # distinct Current Size (display) vs Original Size (binary)
        cur_w = str(image.width_hwpunit) if image.width_hwpunit else "3000"
        cur_h = str(image.height_hwpunit) if image.height_hwpunit else "3000"
        
        org_w = str(image.org_width) if image.org_width else cur_w
        org_h = str(image.org_height) if image.org_height else cur_h
        
        # Calculate Scale Factors
        try:
            sca_x = float(cur_w) / float(org_w)
            sca_y = float(cur_h) / float(org_h)
        except ZeroDivisionError:
            sca_x = 1.0
            sca_y = 1.0
            
        sca_x_str = f"{sca_x:.6f}"
        sca_y_str = f"{sca_y:.6f}"

        pic = etree.Element(etree.QName(NS["hp"], "pic"))
        pic.set("id", str(pic_id))
        pic.set("zOrder", "0") # Standard Z-order
        pic.set("numberingType", "PICTURE")
        pic.set("textWrap", "TOP_AND_BOTTOM")
        pic.set("textFlow", "BOTH_SIDES")
        pic.set("lock", "0")
        pic.set("dropcapstyle", "None")
        pic.set("href", "")
        pic.set("groupLevel", "0")
        pic.set("instid", str(pic_id + 3000000))
        pic.set("reverse", "0")

        # 1. offset
        offset = etree.SubElement(pic, etree.QName(NS["hp"], "offset"))
        offset.set("x", "0")
        offset.set("y", "0")

        # 2. orgSz (Original Binary Size)
        org_sz = etree.SubElement(pic, etree.QName(NS["hp"], "orgSz"))
        org_sz.set("width", org_w)
        org_sz.set("height", org_h)

        # 3. curSz (Display Size)
        cur_sz = etree.SubElement(pic, etree.QName(NS["hp"], "curSz"))
        cur_sz.set("width", cur_w)
        cur_sz.set("height", cur_h)

        # 4. flip
        flip = etree.SubElement(pic, etree.QName(NS["hp"], "flip"))
        flip.set("horizontal", "0")
        flip.set("vertical", "0")

        # 5. rotationInfo
        rot_info = etree.SubElement(pic, etree.QName(NS["hp"], "rotationInfo"))
        rot_info.set("angle", "0")
        rot_info.set("centerX", str(int(int(cur_w)/2)))
        rot_info.set("centerY", str(int(int(cur_h)/2)))
        rot_info.set("rotateimage", "1")

        # 6. renderingInfo (Matrix Scaling)
        rend_info = etree.SubElement(pic, etree.QName(NS["hp"], "renderingInfo"))
        # Identity matrices
        hc_trans = etree.SubElement(rend_info, etree.QName(NS["hc"], "transMatrix"))
        hc_trans.set("e1", "1"); hc_trans.set("e2", "0"); hc_trans.set("e3", "0")
        hc_trans.set("e4", "0"); hc_trans.set("e5", "1"); hc_trans.set("e6", "0")
        
        hc_sca = etree.SubElement(rend_info, etree.QName(NS["hc"], "scaMatrix"))
        hc_sca.set("e1", sca_x_str)
        hc_sca.set("e2", "0")
        hc_sca.set("e3", "0")
        hc_sca.set("e4", "0")
        hc_sca.set("e5", sca_y_str)
        hc_sca.set("e6", "0")

        hc_rot = etree.SubElement(rend_info, etree.QName(NS["hc"], "rotMatrix"))
        hc_rot.set("e1", "1"); hc_rot.set("e2", "0"); hc_rot.set("e3", "0")
        hc_rot.set("e4", "0"); hc_rot.set("e5", "1"); hc_rot.set("e6", "0")

        # 7. img
        img = etree.SubElement(pic, etree.QName(NS["hc"], "img"))
        img.set("binaryItemIDRef", image.image_id)
        img.set("effect", "REAL_PIC")
        img.set("alpha", "0")
        img.set("bright", "0")
        img.set("contrast", "0")

        # 8. imgRect (Uses orgSz)
        img_rect = etree.SubElement(pic, etree.QName(NS["hp"], "imgRect"))
        pt0 = etree.SubElement(img_rect, etree.QName(NS["hc"], "pt0")); pt0.set("x", "0"); pt0.set("y", "0")
        pt1 = etree.SubElement(img_rect, etree.QName(NS["hc"], "pt1")); pt1.set("x", org_w); pt1.set("y", "0")
        pt2 = etree.SubElement(img_rect, etree.QName(NS["hc"], "pt2")); pt2.set("x", org_w); pt2.set("y", org_h)
        pt3 = etree.SubElement(img_rect, etree.QName(NS["hc"], "pt3")); pt3.set("x", "0"); pt3.set("y", org_h)

        # 9. imgClip (Uses orgSz)
        img_clip = etree.SubElement(pic, etree.QName(NS["hp"], "imgClip"))
        img_clip.set("left", "0"); img_clip.set("right", org_w)
        img_clip.set("top", "0"); img_clip.set("bottom", org_h)

        # 10. inMargin
        in_margin = etree.SubElement(pic, etree.QName(NS["hp"], "inMargin"))
        in_margin.set("left", "0"); in_margin.set("right", "0")
        in_margin.set("top", "0"); in_margin.set("bottom", "0")

        # 11. imgDim (Uses orgSz)
        img_dim = etree.SubElement(pic, etree.QName(NS["hp"], "imgDim"))
        img_dim.set("dimwidth", org_w)
        img_dim.set("dimheight", org_h)

        # 12. effects
        etree.SubElement(pic, etree.QName(NS["hp"], "effects"))

        # 13. sz (Uses curSz)
        sz = etree.SubElement(pic, etree.QName(NS["hp"], "sz"))
        sz.set("width", cur_w)
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", cur_h)
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # 14. pos
        pos = etree.SubElement(pic, etree.QName(NS["hp"], "pos"))
        pos.set("treatAsChar", "0") # Floating (match mid.hwpx)
        pos.set("affectLSpacing", "0")
        pos.set("flowWithText", "1")
        pos.set("allowOverlap", "0") # Match mid.hwpx
        pos.set("holdAnchorAndSO", "0")
        pos.set("vertRelTo", "PARA") # Match mid.hwpx
        pos.set("horzRelTo", "COLUMN") # Match mid.hwpx
        pos.set("vertAlign", "TOP")
        pos.set("horzAlign", "LEFT")
        pos.set("vertOffset", "0")
        pos.set("horzOffset", "0") # Or small offset if needed

        # 15. outMargin
        out_margin = etree.SubElement(pic, etree.QName(NS["hp"], "outMargin"))
        out_margin.set("left", "0"); out_margin.set("right", "0")
        out_margin.set("top", "0"); out_margin.set("bottom", "0")

        # 16. shapeComment
        shape_comment = etree.SubElement(pic, etree.QName(NS["hp"], "shapeComment"))
        shape_comment.text = f"Original Size: {org_w}, {org_h}"

        return pic

    def _build_table(self, table: IrTable, context: HwpxIdContext) -> etree._Element:
        if table.raw_xml:
            return etree.fromstring(table.raw_xml)
        
        table_id = context.next_tbl_id()

        tbl = etree.Element(etree.QName(NS["hp"], "tbl"))
        tbl.set("id", str(table_id))
        tbl.set("zOrder", "0")
        tbl.set("numberingType", "TABLE")
        tbl.set("textWrap", "TOP_AND_BOTTOM")
        tbl.set("rowCnt", str(table.row_cnt))
        tbl.set("colCnt", str(table.col_cnt))
        tbl.set("cellSpacing", "0")
        tbl.set("borderFillIDRef", str(table.border_fill_id))

        if table.width_hwpunit is not None or table.height_hwpunit is not None:
            sz = etree.SubElement(tbl, etree.QName(NS["hp"], "sz"))
            if table.width_hwpunit is not None:
                sz.set("width", str(table.width_hwpunit))
                sz.set("widthRelTo", "ABSOLUTE")
            if table.height_hwpunit is not None:
                sz.set("height", str(table.height_hwpunit))
                sz.set("heightRelTo", "ABSOLUTE")
            sz.set("protect", "0")


        row_map: Dict[int, List[IrTableCell]] = {}
        for cell in table.cells:
            row_map.setdefault(cell.row, []).append(cell)

        for row in sorted(row_map.keys()):
            tr = etree.SubElement(tbl, etree.QName(NS["hp"], "tr"))
            for cell in sorted(row_map[row], key=lambda c: c.col):
                tr.append(self._build_table_cell(cell, context))

        return tbl


    def _build_section_definition(self, section: IrSection) -> List[etree._Element]:
        """Builds section property controls (secPr, colPr, header, footer)."""
        controls = []

        # 1. Column Property (Wrapped in hp:ctrl)
        if section.col_count > 1:
            col_pr = etree.Element(etree.QName(NS["hp"], "colPr"))
            col_pr.set("id", "")
            col_pr.set("type", "NEWSPAPER")
            col_pr.set("layout", "LEFT")
            col_pr.set("colCount", str(section.col_count))
            col_pr.set("sameSz", "1")
            
            gap = str(section.col_gap) if section.col_gap > 0 else "1134" # 4mm default
            col_pr.set("sameGap", gap)

            if section.col_line_type:
                 col_line = etree.SubElement(col_pr, etree.QName(NS["hp"], "colLine"))
                 col_line.set("type", section.col_line_type) # e.g. "SOLID"
                 col_line.set("width", "100") # 0.1mm
                 col_line.set("color", "#000000")

            ctrl = etree.Element(etree.QName(NS["hp"], "ctrl"))
            ctrl.append(col_pr)
            controls.append(ctrl)

        # 2. Section Property (Direct Element)
        sec_pr = etree.Element(etree.QName(NS["hp"], "secPr"))
        sec_pr.set("id", "")
        sec_pr.set("textDirection", "HORIZONTAL")
        sec_pr.set("spaceColumns", "1134")
        sec_pr.set("tabStop", "8000")
        sec_pr.set("tabStopVal", "4000")
        sec_pr.set("tabStopUnit", "HWPUNIT")

        # grid
        grid = etree.Element(etree.QName(NS["hp"], "grid"))
        grid.set("lineGrid", "0")
        grid.set("charGrid", "0")
        grid.set("wonggojiFormat", "0")
        sec_pr.append(grid)

        # startNum
        start_num = etree.Element(etree.QName(NS["hp"], "startNum"))
        start_num.set("pageStartsOn", "BOTH")
        start_num.set("page", "0")
        start_num.set("pic", "0")
        start_num.set("tbl", "0")
        start_num.set("equation", "0")
        sec_pr.append(start_num)

        # visibility
        visibility = etree.Element(etree.QName(NS["hp"], "visibility"))
        visibility.set("hideFirstHeader", "0")
        visibility.set("hideFirstFooter", "0")
        visibility.set("hideFirstMasterPage", "0")
        visibility.set("border", "SHOW_ALL")
        visibility.set("fill", "SHOW_ALL")
        visibility.set("hideFirstPageNum", "0")
        visibility.set("hideFirstEmptyLine", "0")
        visibility.set("showLineNumber", "0")
        sec_pr.append(visibility)

        # lineNumberShape
        linenum = etree.Element(etree.QName(NS["hp"], "lineNumberShape"))
        linenum.set("restartType", "0")
        linenum.set("countBy", "0")
        linenum.set("distance", "0")
        linenum.set("startNumber", "0")
        sec_pr.append(linenum)
        
        # pagePr
        page_pr = etree.Element(etree.QName(NS["hp"], "pagePr"))
        page_pr.set("landscape", "WIDELY")
        page_pr.set("width", str(section.page_width))
        page_pr.set("height", str(section.page_height))
        page_pr.set("gutterType", "LEFT_ONLY")
        
        margin = etree.Element(etree.QName(NS["hp"], "margin"))
        margin.set("header", "4252") # 15mm
        margin.set("footer", "4252")
        margin.set("gutter", "0")
        margin.set("left", "8504") # 30mm
        margin.set("right", "8504")
        margin.set("top", "5669") # 20mm
        margin.set("bottom", "5669")
        page_pr.append(margin)
        
        sec_pr.append(page_pr)

        # footNotePr
        footnote = etree.Element(etree.QName(NS["hp"], "footNotePr"))
        footnote.set("place", "EACH_COLUMN") # Minimal
        sec_pr.append(footnote)

        # endNotePr
        endnote = etree.Element(etree.QName(NS["hp"], "endNotePr"))
        endnote.set("place", "END_OF_DOCUMENT") # Minimal
        sec_pr.append(endnote)

        controls.append(sec_pr)

        # 3. Header
        if section.header:
            header_ctrl = self._build_header_footer_ctrl(section.header, is_header=True)
            controls.append(header_ctrl)

        # 4. Footer
        if section.footer:
            footer_ctrl = self._build_header_footer_ctrl(section.footer, is_header=False)
            controls.append(footer_ctrl)

        return controls

    def _build_header_footer_ctrl(self, item: Union[IrHeader, IrFooter], is_header: bool) -> etree._Element:
        tag = "header" if is_header else "footer"
        ctrl = etree.Element(etree.QName(NS["hp"], "ctrl"))
        
        hf = etree.Element(etree.QName(NS["hp"], tag))
        hf.set("id", "1")
        hf.set("applyPageType", "BOTH")
        
        sublist = etree.Element(etree.QName(NS["hp"], "subList"))
        sublist.set("textDirection", "HORIZONTAL")
        sublist.set("lineWrap", "BREAK")
        sublist.set("vertAlign", "BOTTOM" if not is_header else "TOP")
        
        para = etree.Element(etree.QName(NS["hp"], "p"))
        para.set("id", "0")
        para.set("paraPrIDRef", "0")
        para.set("styleIDRef", "0")
        para.set("pageBreak", "0")
        para.set("columnBreak", "0")
        para.set("merged", "0")
        
        run = etree.Element(etree.QName(NS["hp"], "run"))
        run.set("charPrIDRef", "0")
        
        text = etree.Element(etree.QName(NS["hp"], "t"))
        text.text = item.text
        run.append(text)
        para.append(run)
        
        lineseg = etree.Element(etree.QName(NS["hp"], "linesegarray"))
        ls = etree.Element(etree.QName(NS["hp"], "lineseg"))
        ls.set("textpos", "0")
        ls.set("vertpos", "0")
        ls.set("vertsize", "1000")
        ls.set("textheight", "1000")
        ls.set("baseline", "850")
        ls.set("spacing", "600")
        ls.set("horzpos", "0")
        ls.set("horzsize", "10000")
        ls.set("flags", "393216")
        lineseg.append(ls)
        para.append(lineseg)

        sublist.append(para)
        hf.append(sublist)
        ctrl.append(hf)
        
        return ctrl

    def _build_equation(self, eq: IrEquation, eq_id: int) -> etree._Element:
        equation = etree.Element(etree.QName(NS["hp"], "equation"))
        equation.set("id", str(eq_id))
        equation.set("zOrder", "0")
        equation.set("numberingType", "EQUATION")
        equation.set("textWrap", "TOP_AND_BOTTOM")
        equation.set("textFlow", "BOTH_SIDES")
        equation.set("lock", "0")
        equation.set("dropcapstyle", "None")
        equation.set("version", eq.version)
        equation.set("baseLine", str(eq.base_line))
        equation.set("textColor", eq.text_color)
        equation.set("baseUnit", "1100") # 11pt?
        equation.set("lineMode", "CHAR")
        equation.set("font", "HYhwpEQ")

        # 1. sz
        sz = etree.SubElement(equation, etree.QName(NS["hp"], "sz"))
        sz.set("width", str(eq.width_hwpunit))
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", str(eq.height_hwpunit))
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # 2. pos (Default Inline for now)
        pos = etree.SubElement(equation, etree.QName(NS["hp"], "pos"))
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

        # 3. outMargin
        out_margin = etree.SubElement(equation, etree.QName(NS["hp"], "outMargin"))
        out_margin.set("left", "0"); out_margin.set("right", "0")
        out_margin.set("top", "0"); out_margin.set("bottom", "0")

        # 4. shapeComment
        comment = etree.SubElement(equation, etree.QName(NS["hp"], "shapeComment"))
        # No text content? Or Author name?
        
        # 5. script
        script = etree.SubElement(equation, etree.QName(NS["hp"], "script"))
        script.text = eq.script

        return equation

    def _build_table_cell(self, cell: IrTableCell, context: HwpxIdContext) -> etree._Element:
        tc = etree.Element(etree.QName(NS["hp"], "tc"))
        tc.set("header", "0")
        tc.set("hasMargin", "0")
        tc.set("protect", "0")
        tc.set("editable", "0")
        tc.set("dirty", "0")
        tc.set("borderFillIDRef", str(cell.border_fill_id))

        cell_addr = etree.SubElement(tc, etree.QName(NS["hp"], "cellAddr"))
        cell_addr.set("colAddr", str(cell.col))
        cell_addr.set("rowAddr", str(cell.row))

        cell_span = etree.SubElement(tc, etree.QName(NS["hp"], "cellSpan"))
        cell_span.set("colSpan", str(cell.col_span))
        cell_span.set("rowSpan", str(cell.row_span))

        cell_sz = etree.SubElement(tc, etree.QName(NS["hp"], "cellSz"))
        cell_sz.set("width", str(cell.width_hwpunit or 10000))
        cell_sz.set("height", str(cell.height_hwpunit or 1000))

        sub_list = etree.SubElement(tc, etree.QName(NS["hp"], "subList"))
        sub_list.set("id", str(context.next_tbl_id())) # Assign unique ID
        sub_list.set("textDirection", "HORIZONTAL")
        sub_list.set("lineWrap", "BREAK")
        sub_list.set("vertAlign", "CENTER")

        # Process Blocks
        has_content = False
        for block in cell.blocks:
             elements = self._process_block(block, context)
             for el in elements:
                 sub_list.append(el)
                 has_content = True
        
        # Ensure at least one paragraph exists in cell if empty
        if not has_content:
             p = self._build_paragraph(IrParagraph(), context.next_para_id())
             sub_list.append(p)

        return tc
