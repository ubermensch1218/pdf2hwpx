"""Header Writer - header.xml 생성"""

from __future__ import annotations

from typing import List, Optional
from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname
from pdf2hwpx.hwpx_ir.models import (
    IrHeaderXmlDef,
    IrFontFace, IrFontDef,
    IrBorderFillDef, IrHwpxBorder, IrDiagonal, IrFillBrush, IrWinBrush, IrGradation,
    IrCharPrDef, IrFontRef, IrLangValues, IrUnderline, IrStrikeout, IrShadow,
    IrParaPrDef, IrParaAlign, IrBreakSetting, IrParaBorder,
    IrStyleDef, IrTabPrDef, IrTabItem,
    IrNumberingDef, IrBulletDef,
)


class HeaderWriter:
    """header.xml 생성"""

    def build_xml(self, header_def: IrHeaderXmlDef) -> bytes:
        """header.xml 바이트 생성 (100% 라운드트립용)

        raw_xml이 있으면 그대로 반환, 없으면 새로 생성
        """
        if header_def.raw_xml:
            return header_def.raw_xml

        head = self.build(header_def)
        return etree.tostring(head, encoding="UTF-8", xml_declaration=True, standalone="yes")

    def build(self, header_def: IrHeaderXmlDef) -> etree._Element:
        """IrHeaderXmlDef를 hh:head 요소로 변환"""
        head = etree.Element(qname("hh", "head"), nsmap=NS)
        head.set("version", header_def.version)
        head.set("secCnt", str(header_def.sec_cnt))

        # beginNum
        begin_num = etree.SubElement(head, qname("hh", "beginNum"))
        begin_num.set("page", str(header_def.begin_page))
        begin_num.set("footnote", str(header_def.begin_footnote))
        begin_num.set("endnote", str(header_def.begin_endnote))
        begin_num.set("pic", str(header_def.begin_pic))
        begin_num.set("tbl", str(header_def.begin_tbl))
        begin_num.set("equation", str(header_def.begin_equation))

        # refList
        ref_list = etree.SubElement(head, qname("hh", "refList"))

        # fontfaces
        self._build_fontfaces(ref_list, header_def.font_faces)

        # borderFills
        self._build_border_fills(ref_list, header_def.border_fills)

        # charProperties
        self._build_char_properties(ref_list, header_def.char_properties)

        # tabProperties
        self._build_tab_properties(ref_list, header_def.tab_properties)

        # numberings
        self._build_numberings(ref_list, header_def.numberings)

        # bullets
        self._build_bullets(ref_list, header_def.bullets)

        # paraProperties
        self._build_para_properties(ref_list, header_def.para_properties)

        # styles
        self._build_styles(ref_list, header_def.styles)

        return head

    def _build_fontfaces(self, parent: etree._Element, font_faces: List[IrFontFace]) -> None:
        """폰트 목록 생성"""
        if not font_faces:
            return

        fontfaces = etree.SubElement(parent, qname("hh", "fontfaces"))
        fontfaces.set("itemCnt", str(len(font_faces)))

        for ff in font_faces:
            fontface = etree.SubElement(fontfaces, qname("hh", "fontface"))
            fontface.set("lang", ff.lang)
            fontface.set("fontCnt", str(len(ff.fonts)))

            for font_def in ff.fonts:
                font = etree.SubElement(fontface, qname("hh", "font"))
                font.set("id", str(font_def.id))
                font.set("face", font_def.face)
                font.set("type", font_def.type)
                font.set("isEmbedded", "1" if font_def.is_embedded else "0")

                if font_def.subst_font_face:
                    subst = etree.SubElement(font, qname("hh", "substFont"))
                    subst.set("face", font_def.subst_font_face)
                    subst.set("type", "TTF")
                    subst.set("isEmbedded", "0")
                    subst.set("binaryItemIDRef", "")

    def _build_border_fills(self, parent: etree._Element, border_fills: List[IrBorderFillDef]) -> None:
        """테두리/채우기 정의 생성"""
        if not border_fills:
            return

        bf_container = etree.SubElement(parent, qname("hh", "borderFills"))
        bf_container.set("itemCnt", str(len(border_fills)))

        for bf in border_fills:
            bf_el = etree.SubElement(bf_container, qname("hh", "borderFill"))
            bf_el.set("id", str(bf.id))
            bf_el.set("threeD", "1" if bf.three_d else "0")
            bf_el.set("shadow", "1" if bf.shadow else "0")
            bf_el.set("centerLine", bf.center_line)
            bf_el.set("breakCellSeparateLine", "1" if bf.break_cell_separate_line else "0")

            # slash
            if bf.slash:
                slash = etree.SubElement(bf_el, qname("hh", "slash"))
                slash.set("type", bf.slash.type)
                slash.set("Crooked", "1" if bf.slash.crooked else "0")
                slash.set("isCounter", "1" if bf.slash.is_counter else "0")
            else:
                slash = etree.SubElement(bf_el, qname("hh", "slash"))
                slash.set("type", "NONE")
                slash.set("Crooked", "0")
                slash.set("isCounter", "0")

            # backSlash
            if bf.back_slash:
                back_slash = etree.SubElement(bf_el, qname("hh", "backSlash"))
                back_slash.set("type", bf.back_slash.type)
                back_slash.set("Crooked", "1" if bf.back_slash.crooked else "0")
                back_slash.set("isCounter", "1" if bf.back_slash.is_counter else "0")
            else:
                back_slash = etree.SubElement(bf_el, qname("hh", "backSlash"))
                back_slash.set("type", "NONE")
                back_slash.set("Crooked", "0")
                back_slash.set("isCounter", "0")

            # 4방향 테두리
            self._build_border(bf_el, "leftBorder", bf.left_border)
            self._build_border(bf_el, "rightBorder", bf.right_border)
            self._build_border(bf_el, "topBorder", bf.top_border)
            self._build_border(bf_el, "bottomBorder", bf.bottom_border)

            # diagonal
            if bf.diagonal:
                diag = etree.SubElement(bf_el, qname("hh", "diagonal"))
                diag.set("type", bf.diagonal.type)
                diag.set("width", bf.diagonal.width)
                diag.set("color", bf.diagonal.color)

            # fillBrush
            if bf.fill_brush:
                self._build_fill_brush(bf_el, bf.fill_brush)

    def _build_border(self, parent: etree._Element, name: str, border: Optional[IrHwpxBorder]) -> None:
        """단일 테두리 생성"""
        el = etree.SubElement(parent, qname("hh", name))
        if border:
            el.set("type", border.type)
            el.set("width", border.width)
            el.set("color", border.color)
        else:
            el.set("type", "NONE")
            el.set("width", "0.1 mm")
            el.set("color", "#000000")

    def _build_fill_brush(self, parent: etree._Element, fill_brush: IrFillBrush) -> None:
        """채우기 브러시 생성"""
        fb = etree.SubElement(parent, qname("hc", "fillBrush"))

        if fill_brush.win_brush:
            wb = etree.SubElement(fb, qname("hc", "winBrush"))
            wb.set("faceColor", fill_brush.win_brush.face_color)
            wb.set("hatchColor", fill_brush.win_brush.hatch_color)
            wb.set("alpha", str(fill_brush.win_brush.alpha))

        if fill_brush.gradation:
            grad = etree.SubElement(fb, qname("hc", "gradation"))
            grad.set("type", fill_brush.gradation.type)
            grad.set("angle", str(fill_brush.gradation.angle))
            grad.set("centerX", str(fill_brush.gradation.center_x))
            grad.set("centerY", str(fill_brush.gradation.center_y))
            grad.set("step", str(fill_brush.gradation.step))
            grad.set("colorNum", str(fill_brush.gradation.color_num))
            grad.set("stepCenter", str(fill_brush.gradation.step_center))

            for color in fill_brush.gradation.colors:
                color_el = etree.SubElement(grad, qname("hc", "color"))
                color_el.set("value", color)

    def _build_char_properties(self, parent: etree._Element, char_props: List[IrCharPrDef]) -> None:
        """문자 속성 정의 생성"""
        if not char_props:
            return

        cp_container = etree.SubElement(parent, qname("hh", "charProperties"))
        cp_container.set("itemCnt", str(len(char_props)))

        for cp in char_props:
            cp_el = etree.SubElement(cp_container, qname("hh", "charPr"))
            cp_el.set("id", str(cp.id))
            cp_el.set("height", str(cp.height))
            cp_el.set("textColor", cp.text_color)
            cp_el.set("shadeColor", cp.shade_color)
            cp_el.set("useFontSpace", "1" if cp.use_font_space else "0")
            cp_el.set("useKerning", "1" if cp.use_kerning else "0")
            cp_el.set("symMark", cp.sym_mark)
            cp_el.set("borderFillIDRef", str(cp.border_fill_id_ref))

            # fontRef
            if cp.font_ref:
                fr = etree.SubElement(cp_el, qname("hh", "fontRef"))
                fr.set("hangul", str(cp.font_ref.hangul))
                fr.set("latin", str(cp.font_ref.latin))
                fr.set("hanja", str(cp.font_ref.hanja))
                fr.set("japanese", str(cp.font_ref.japanese))
                fr.set("other", str(cp.font_ref.other))
                fr.set("symbol", str(cp.font_ref.symbol))
                fr.set("user", str(cp.font_ref.user))
            else:
                fr = etree.SubElement(cp_el, qname("hh", "fontRef"))
                fr.set("hangul", "0")
                fr.set("latin", "0")
                fr.set("hanja", "0")
                fr.set("japanese", "0")
                fr.set("other", "0")
                fr.set("symbol", "0")
                fr.set("user", "0")

            # ratio, spacing, relSz, offset
            self._build_lang_values(cp_el, "ratio", cp.ratio, 100)
            self._build_lang_values(cp_el, "spacing", cp.spacing, 0)
            self._build_lang_values(cp_el, "relSz", cp.rel_sz, 100)
            self._build_lang_values(cp_el, "offset", cp.offset, 0)

            # bold
            if cp.bold:
                etree.SubElement(cp_el, qname("hh", "bold"))

            # italic
            if cp.italic:
                etree.SubElement(cp_el, qname("hh", "italic"))

            # underline
            ul = etree.SubElement(cp_el, qname("hh", "underline"))
            if cp.underline:
                ul.set("type", cp.underline.type)
                ul.set("shape", cp.underline.shape)
                ul.set("color", cp.underline.color)
            else:
                ul.set("type", "NONE")
                ul.set("shape", "SOLID")
                ul.set("color", "#000000")

            # strikeout
            so = etree.SubElement(cp_el, qname("hh", "strikeout"))
            if cp.strikeout:
                so.set("shape", cp.strikeout.shape)
                so.set("color", cp.strikeout.color)
            else:
                so.set("shape", "NONE")
                so.set("color", "#000000")

            # outline
            outline = etree.SubElement(cp_el, qname("hh", "outline"))
            outline.set("type", cp.outline_type)

            # shadow
            shadow = etree.SubElement(cp_el, qname("hh", "shadow"))
            if cp.shadow:
                shadow.set("type", cp.shadow.type)
                shadow.set("color", cp.shadow.color)
                shadow.set("offsetX", str(cp.shadow.offset_x))
                shadow.set("offsetY", str(cp.shadow.offset_y))
            else:
                shadow.set("type", "NONE")
                shadow.set("color", "#B2B2B2")
                shadow.set("offsetX", "10")
                shadow.set("offsetY", "10")

    def _build_lang_values(
        self,
        parent: etree._Element,
        name: str,
        values: Optional[IrLangValues],
        default: int
    ) -> None:
        """언어별 값 생성"""
        el = etree.SubElement(parent, qname("hh", name))
        if values:
            el.set("hangul", str(values.hangul))
            el.set("latin", str(values.latin))
            el.set("hanja", str(values.hanja))
            el.set("japanese", str(values.japanese))
            el.set("other", str(values.other))
            el.set("symbol", str(values.symbol))
            el.set("user", str(values.user))
        else:
            el.set("hangul", str(default))
            el.set("latin", str(default))
            el.set("hanja", str(default))
            el.set("japanese", str(default))
            el.set("other", str(default))
            el.set("symbol", str(default))
            el.set("user", str(default))

    def _build_tab_properties(self, parent: etree._Element, tab_props: List[IrTabPrDef]) -> None:
        """탭 속성 정의 생성"""
        if not tab_props:
            return

        tp_container = etree.SubElement(parent, qname("hh", "tabProperties"))
        tp_container.set("itemCnt", str(len(tab_props)))

        for tp in tab_props:
            tp_el = etree.SubElement(tp_container, qname("hh", "tabPr"))
            tp_el.set("id", str(tp.id))
            tp_el.set("autoTabLeft", "1" if tp.auto_tab_left else "0")
            tp_el.set("autoTabRight", "1" if tp.auto_tab_right else "0")

            for tab in tp.tabs:
                tab_el = etree.SubElement(tp_el, qname("hh", "tabItem"))
                tab_el.set("pos", str(tab.pos))
                tab_el.set("type", tab.type)
                tab_el.set("leader", tab.leader)

    def _build_numberings(self, parent: etree._Element, numberings: List[IrNumberingDef]) -> None:
        """번호매기기 정의 생성"""
        if not numberings:
            return

        n_container = etree.SubElement(parent, qname("hh", "numberings"))
        n_container.set("itemCnt", str(len(numberings)))

        for num in numberings:
            num_el = etree.SubElement(n_container, qname("hh", "numbering"))
            num_el.set("id", str(num.id))
            num_el.set("start", str(num.start))

    def _build_bullets(self, parent: etree._Element, bullets: List[IrBulletDef]) -> None:
        """글머리 기호 정의 생성"""
        if not bullets:
            return

        b_container = etree.SubElement(parent, qname("hh", "bullets"))
        b_container.set("itemCnt", str(len(bullets)))

        for bullet in bullets:
            b_el = etree.SubElement(b_container, qname("hh", "bullet"))
            b_el.set("id", str(bullet.id))
            b_el.set("char", bullet.char)
            b_el.set("charPrIDRef", str(bullet.char_pr_id_ref))

    def _build_para_properties(self, parent: etree._Element, para_props: List[IrParaPrDef]) -> None:
        """단락 속성 정의 생성"""
        if not para_props:
            return

        pp_container = etree.SubElement(parent, qname("hh", "paraProperties"))
        pp_container.set("itemCnt", str(len(para_props)))

        for pp in para_props:
            pp_el = etree.SubElement(pp_container, qname("hh", "paraPr"))
            pp_el.set("id", str(pp.id))
            pp_el.set("tabPrIDRef", str(pp.tab_pr_id_ref))
            pp_el.set("condense", str(pp.condense))
            pp_el.set("fontLineHeight", "1" if pp.font_line_height else "0")
            pp_el.set("snapToGrid", "1" if pp.snap_to_grid else "0")
            pp_el.set("suppressLineNumbers", "1" if pp.suppress_line_numbers else "0")
            pp_el.set("checked", "1" if pp.checked else "0")

            # align
            align = etree.SubElement(pp_el, qname("hh", "align"))
            if pp.align:
                align.set("horizontal", pp.align.horizontal)
                align.set("vertical", pp.align.vertical)
            else:
                align.set("horizontal", "JUSTIFY")
                align.set("vertical", "BASELINE")

            # heading
            heading = etree.SubElement(pp_el, qname("hh", "heading"))
            heading.set("type", "NONE")
            heading.set("idRef", "0")
            heading.set("level", "0")

            # breakSetting
            bs = etree.SubElement(pp_el, qname("hh", "breakSetting"))
            if pp.break_setting:
                bs.set("breakLatinWord", pp.break_setting.break_latin_word)
                bs.set("breakNonLatinWord", pp.break_setting.break_non_latin_word)
                bs.set("widowOrphan", "1" if pp.break_setting.widow_orphan else "0")
                bs.set("keepWithNext", "1" if pp.break_setting.keep_with_next else "0")
                bs.set("keepLines", "1" if pp.break_setting.keep_lines else "0")
                bs.set("pageBreakBefore", "1" if pp.break_setting.page_break_before else "0")
                bs.set("lineWrap", pp.break_setting.line_wrap)
            else:
                bs.set("breakLatinWord", "KEEP_WORD")
                bs.set("breakNonLatinWord", "KEEP_WORD")
                bs.set("widowOrphan", "0")
                bs.set("keepWithNext", "0")
                bs.set("keepLines", "0")
                bs.set("pageBreakBefore", "0")
                bs.set("lineWrap", "BREAK")

            # autoSpacing
            auto_sp = etree.SubElement(pp_el, qname("hh", "autoSpacing"))
            auto_sp.set("eAsianEng", "0")
            auto_sp.set("eAsianNum", "0")

            # switch
            etree.SubElement(pp_el, qname("hh", "switch"))

            # border
            border = etree.SubElement(pp_el, qname("hh", "border"))
            if pp.border:
                border.set("borderFillIDRef", str(pp.border.border_fill_id_ref))
                border.set("offsetLeft", str(pp.border.offset_left))
                border.set("offsetRight", str(pp.border.offset_right))
                border.set("offsetTop", str(pp.border.offset_top))
                border.set("offsetBottom", str(pp.border.offset_bottom))
                border.set("connect", "1" if pp.border.connect else "0")
                border.set("ignoreMargin", "1" if pp.border.ignore_margin else "0")
            else:
                border.set("borderFillIDRef", "2")
                border.set("offsetLeft", "0")
                border.set("offsetRight", "0")
                border.set("offsetTop", "0")
                border.set("offsetBottom", "0")
                border.set("connect", "0")
                border.set("ignoreMargin", "0")

    def _build_styles(self, parent: etree._Element, styles: List[IrStyleDef]) -> None:
        """스타일 정의 생성"""
        if not styles:
            return

        s_container = etree.SubElement(parent, qname("hh", "styles"))
        s_container.set("itemCnt", str(len(styles)))

        for style in styles:
            s_el = etree.SubElement(s_container, qname("hh", "style"))
            s_el.set("id", str(style.id))
            s_el.set("type", style.type)
            s_el.set("name", style.name)
            s_el.set("engName", style.eng_name)
            s_el.set("paraPrIDRef", str(style.para_pr_id_ref))
            s_el.set("charPrIDRef", str(style.char_pr_id_ref))
            s_el.set("nextStyleIDRef", str(style.next_style_id_ref))
            s_el.set("langId", str(style.lang_id))
