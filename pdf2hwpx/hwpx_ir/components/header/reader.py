"""Header Reader - header.xml 파싱"""

from __future__ import annotations

from typing import List, Optional
from lxml import etree

from pdf2hwpx.hwpx_ir.models import (
    IrHeaderXmlDef,
    IrFontFace, IrFontDef,
    IrBorderFillDef, IrHwpxBorder, IrDiagonal, IrFillBrush, IrWinBrush, IrGradation,
    IrCharPrDef, IrFontRef, IrLangValues, IrUnderline, IrStrikeout, IrShadow,
    IrParaPrDef, IrParaAlign, IrBreakSetting, IrParaBorder,
    IrStyleDef, IrTabPrDef, IrTabItem,
    IrNumberingDef, IrBulletDef,
)


# 네임스페이스
NS = {
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
}


class HeaderReader:
    """header.xml 파싱"""

    def parse(self, header_xml: bytes, preserve_raw: bool = True) -> IrHeaderXmlDef:
        """header.xml 바이트를 IrHeaderXmlDef로 파싱

        Args:
            header_xml: header.xml 바이트
            preserve_raw: True면 raw_xml 보존 (100% 라운드트립용)
        """
        root = etree.fromstring(header_xml)
        return self.parse_element(root, raw_xml=header_xml if preserve_raw else None)

    def parse_element(self, root: etree._Element, raw_xml: Optional[bytes] = None) -> IrHeaderXmlDef:
        """hh:head 요소를 IrHeaderXmlDef로 파싱

        Args:
            root: hh:head 요소
            raw_xml: 원본 XML 바이트 (100% 라운드트립용)
        """
        version = root.get("version", "1.5")
        sec_cnt = int(root.get("secCnt", "1"))

        # beginNum
        begin_num = root.find("hh:beginNum", NS)
        begin_page = 1
        begin_footnote = 1
        begin_endnote = 1
        begin_pic = 1
        begin_tbl = 1
        begin_equation = 1

        if begin_num is not None:
            begin_page = int(begin_num.get("page", "1"))
            begin_footnote = int(begin_num.get("footnote", "1"))
            begin_endnote = int(begin_num.get("endnote", "1"))
            begin_pic = int(begin_num.get("pic", "1"))
            begin_tbl = int(begin_num.get("tbl", "1"))
            begin_equation = int(begin_num.get("equation", "1"))

        # refList
        ref_list = root.find("hh:refList", NS)
        font_faces: List[IrFontFace] = []
        border_fills: List[IrBorderFillDef] = []
        char_properties: List[IrCharPrDef] = []
        tab_properties: List[IrTabPrDef] = []
        numberings: List[IrNumberingDef] = []
        bullets: List[IrBulletDef] = []
        para_properties: List[IrParaPrDef] = []
        styles: List[IrStyleDef] = []

        if ref_list is not None:
            # fontfaces
            fontfaces_el = ref_list.find("hh:fontfaces", NS)
            if fontfaces_el is not None:
                font_faces = self._parse_fontfaces(fontfaces_el)

            # borderFills
            border_fills_el = ref_list.find("hh:borderFills", NS)
            if border_fills_el is not None:
                border_fills = self._parse_border_fills(border_fills_el)

            # charProperties
            char_props_el = ref_list.find("hh:charProperties", NS)
            if char_props_el is not None:
                char_properties = self._parse_char_properties(char_props_el)

            # tabProperties
            tab_props_el = ref_list.find("hh:tabProperties", NS)
            if tab_props_el is not None:
                tab_properties = self._parse_tab_properties(tab_props_el)

            # numberings
            numberings_el = ref_list.find("hh:numberings", NS)
            if numberings_el is not None:
                numberings = self._parse_numberings(numberings_el)

            # bullets
            bullets_el = ref_list.find("hh:bullets", NS)
            if bullets_el is not None:
                bullets = self._parse_bullets(bullets_el)

            # paraProperties
            para_props_el = ref_list.find("hh:paraProperties", NS)
            if para_props_el is not None:
                para_properties = self._parse_para_properties(para_props_el)

            # styles
            styles_el = ref_list.find("hh:styles", NS)
            if styles_el is not None:
                styles = self._parse_styles(styles_el)

        return IrHeaderXmlDef(
            version=version,
            sec_cnt=sec_cnt,
            begin_page=begin_page,
            begin_footnote=begin_footnote,
            begin_endnote=begin_endnote,
            begin_pic=begin_pic,
            begin_tbl=begin_tbl,
            begin_equation=begin_equation,
            font_faces=font_faces,
            border_fills=border_fills,
            char_properties=char_properties,
            tab_properties=tab_properties,
            numberings=numberings,
            bullets=bullets,
            para_properties=para_properties,
            styles=styles,
            raw_xml=raw_xml,
        )

    def _parse_fontfaces(self, fontfaces_el: etree._Element) -> List[IrFontFace]:
        """폰트 목록 파싱"""
        font_faces = []
        for ff in fontfaces_el.findall("hh:fontface", NS):
            lang = ff.get("lang", "HANGUL")
            fonts = []

            for font in ff.findall("hh:font", NS):
                font_id = int(font.get("id", "0"))
                face = font.get("face", "")
                font_type = font.get("type", "TTF")
                is_embedded = font.get("isEmbedded", "0") == "1"

                subst_font = font.find("hh:substFont", NS)
                subst_font_face = None
                if subst_font is not None:
                    subst_font_face = subst_font.get("face")

                fonts.append(IrFontDef(
                    id=font_id,
                    face=face,
                    type=font_type,
                    is_embedded=is_embedded,
                    subst_font_face=subst_font_face,
                ))

            font_faces.append(IrFontFace(lang=lang, fonts=fonts))

        return font_faces

    def _parse_border_fills(self, border_fills_el: etree._Element) -> List[IrBorderFillDef]:
        """테두리/채우기 정의 파싱"""
        border_fills = []
        for bf in border_fills_el.findall("hh:borderFill", NS):
            bf_id = int(bf.get("id", "0"))
            three_d = bf.get("threeD", "0") == "1"
            shadow = bf.get("shadow", "0") == "1"
            center_line = bf.get("centerLine", "NONE")
            break_cell = bf.get("breakCellSeparateLine", "0") == "1"

            # slash
            slash_el = bf.find("hh:slash", NS)
            slash = None
            if slash_el is not None and slash_el.get("type", "NONE") != "NONE":
                slash = IrDiagonal(
                    type=slash_el.get("type", "NONE"),
                    crooked=slash_el.get("Crooked", "0") == "1",
                    is_counter=slash_el.get("isCounter", "0") == "1",
                )

            # backSlash
            back_slash_el = bf.find("hh:backSlash", NS)
            back_slash = None
            if back_slash_el is not None and back_slash_el.get("type", "NONE") != "NONE":
                back_slash = IrDiagonal(
                    type=back_slash_el.get("type", "NONE"),
                    crooked=back_slash_el.get("Crooked", "0") == "1",
                    is_counter=back_slash_el.get("isCounter", "0") == "1",
                )

            # 4방향 테두리
            left_border = self._parse_border(bf.find("hh:leftBorder", NS))
            right_border = self._parse_border(bf.find("hh:rightBorder", NS))
            top_border = self._parse_border(bf.find("hh:topBorder", NS))
            bottom_border = self._parse_border(bf.find("hh:bottomBorder", NS))
            diagonal = self._parse_border(bf.find("hh:diagonal", NS))

            # fillBrush
            fill_brush = None
            fill_brush_el = bf.find("hc:fillBrush", NS)
            if fill_brush_el is not None:
                fill_brush = self._parse_fill_brush(fill_brush_el)

            border_fills.append(IrBorderFillDef(
                id=bf_id,
                three_d=three_d,
                shadow=shadow,
                center_line=center_line,
                break_cell_separate_line=break_cell,
                slash=slash,
                back_slash=back_slash,
                left_border=left_border,
                right_border=right_border,
                top_border=top_border,
                bottom_border=bottom_border,
                diagonal=diagonal,
                fill_brush=fill_brush,
            ))

        return border_fills

    def _parse_border(self, border_el: Optional[etree._Element]) -> Optional[IrHwpxBorder]:
        """단일 테두리 파싱"""
        if border_el is None:
            return None

        border_type = border_el.get("type", "NONE")
        width = border_el.get("width", "0.1 mm")
        color = border_el.get("color", "#000000")

        return IrHwpxBorder(type=border_type, width=width, color=color)

    def _parse_fill_brush(self, fill_brush_el: etree._Element) -> IrFillBrush:
        """채우기 브러시 파싱"""
        win_brush = None
        gradation = None

        wb_el = fill_brush_el.find("hc:winBrush", NS)
        if wb_el is not None:
            win_brush = IrWinBrush(
                face_color=wb_el.get("faceColor", "none"),
                hatch_color=wb_el.get("hatchColor", "#000000"),
                alpha=int(wb_el.get("alpha", "0")),
            )

        grad_el = fill_brush_el.find("hc:gradation", NS)
        if grad_el is not None:
            colors = []
            for color_el in grad_el.findall("hc:color", NS):
                colors.append(color_el.get("value", "#FFFFFF"))

            gradation = IrGradation(
                type=grad_el.get("type", "LINEAR"),
                angle=int(grad_el.get("angle", "0")),
                center_x=int(grad_el.get("centerX", "0")),
                center_y=int(grad_el.get("centerY", "0")),
                step=int(grad_el.get("step", "50")),
                color_num=int(grad_el.get("colorNum", "2")),
                step_center=int(grad_el.get("stepCenter", "50")),
                colors=colors,
            )

        return IrFillBrush(win_brush=win_brush, gradation=gradation)

    def _parse_char_properties(self, char_props_el: etree._Element) -> List[IrCharPrDef]:
        """문자 속성 정의 파싱"""
        char_properties = []
        for cp in char_props_el.findall("hh:charPr", NS):
            cp_id = int(cp.get("id", "0"))
            height = int(cp.get("height", "1000"))
            text_color = cp.get("textColor", "#000000")
            shade_color = cp.get("shadeColor", "none")
            use_font_space = cp.get("useFontSpace", "0") == "1"
            use_kerning = cp.get("useKerning", "0") == "1"
            sym_mark = cp.get("symMark", "NONE")
            border_fill_id_ref = int(cp.get("borderFillIDRef", "1"))

            # fontRef
            font_ref = None
            fr_el = cp.find("hh:fontRef", NS)
            if fr_el is not None:
                font_ref = IrFontRef(
                    hangul=int(fr_el.get("hangul", "0")),
                    latin=int(fr_el.get("latin", "0")),
                    hanja=int(fr_el.get("hanja", "0")),
                    japanese=int(fr_el.get("japanese", "0")),
                    other=int(fr_el.get("other", "0")),
                    symbol=int(fr_el.get("symbol", "0")),
                    user=int(fr_el.get("user", "0")),
                )

            # ratio, spacing, relSz, offset
            ratio = self._parse_lang_values(cp.find("hh:ratio", NS), 100)
            spacing = self._parse_lang_values(cp.find("hh:spacing", NS), 0)
            rel_sz = self._parse_lang_values(cp.find("hh:relSz", NS), 100)
            offset = self._parse_lang_values(cp.find("hh:offset", NS), 0)

            # bold, italic
            bold = cp.find("hh:bold", NS) is not None
            italic = cp.find("hh:italic", NS) is not None

            # underline
            underline = None
            ul_el = cp.find("hh:underline", NS)
            if ul_el is not None:
                underline = IrUnderline(
                    type=ul_el.get("type", "NONE"),
                    shape=ul_el.get("shape", "SOLID"),
                    color=ul_el.get("color", "#000000"),
                )

            # strikeout
            strikeout = None
            so_el = cp.find("hh:strikeout", NS)
            if so_el is not None:
                strikeout = IrStrikeout(
                    shape=so_el.get("shape", "NONE"),
                    color=so_el.get("color", "#000000"),
                )

            # outline
            outline_type = "NONE"
            outline_el = cp.find("hh:outline", NS)
            if outline_el is not None:
                outline_type = outline_el.get("type", "NONE")

            # shadow
            shadow = None
            shadow_el = cp.find("hh:shadow", NS)
            if shadow_el is not None:
                shadow = IrShadow(
                    type=shadow_el.get("type", "NONE"),
                    color=shadow_el.get("color", "#B2B2B2"),
                    offset_x=int(shadow_el.get("offsetX", "10")),
                    offset_y=int(shadow_el.get("offsetY", "10")),
                )

            char_properties.append(IrCharPrDef(
                id=cp_id,
                height=height,
                text_color=text_color,
                shade_color=shade_color,
                use_font_space=use_font_space,
                use_kerning=use_kerning,
                sym_mark=sym_mark,
                border_fill_id_ref=border_fill_id_ref,
                font_ref=font_ref,
                ratio=ratio,
                spacing=spacing,
                rel_sz=rel_sz,
                offset=offset,
                bold=bold,
                italic=italic,
                underline=underline,
                strikeout=strikeout,
                outline_type=outline_type,
                shadow=shadow,
            ))

        return char_properties

    def _parse_lang_values(self, el: Optional[etree._Element], default: int) -> Optional[IrLangValues]:
        """언어별 값 파싱"""
        if el is None:
            return None

        return IrLangValues(
            hangul=int(el.get("hangul", str(default))),
            latin=int(el.get("latin", str(default))),
            hanja=int(el.get("hanja", str(default))),
            japanese=int(el.get("japanese", str(default))),
            other=int(el.get("other", str(default))),
            symbol=int(el.get("symbol", str(default))),
            user=int(el.get("user", str(default))),
        )

    def _parse_tab_properties(self, tab_props_el: etree._Element) -> List[IrTabPrDef]:
        """탭 속성 정의 파싱"""
        tab_properties = []
        for tp in tab_props_el.findall("hh:tabPr", NS):
            tp_id = int(tp.get("id", "0"))
            auto_tab_left = tp.get("autoTabLeft", "0") == "1"
            auto_tab_right = tp.get("autoTabRight", "0") == "1"

            tabs = []
            for tab in tp.findall("hh:tabItem", NS):
                tabs.append(IrTabItem(
                    pos=int(tab.get("pos", "0")),
                    type=tab.get("type", "LEFT"),
                    leader=tab.get("leader", "NONE"),
                ))

            tab_properties.append(IrTabPrDef(
                id=tp_id,
                auto_tab_left=auto_tab_left,
                auto_tab_right=auto_tab_right,
                tabs=tabs,
            ))

        return tab_properties

    def _parse_numberings(self, numberings_el: etree._Element) -> List[IrNumberingDef]:
        """번호매기기 정의 파싱"""
        numberings = []
        for num in numberings_el.findall("hh:numbering", NS):
            numberings.append(IrNumberingDef(
                id=int(num.get("id", "0")),
                start=int(num.get("start", "1")),
            ))
        return numberings

    def _parse_bullets(self, bullets_el: etree._Element) -> List[IrBulletDef]:
        """글머리 기호 정의 파싱"""
        bullets = []
        for b in bullets_el.findall("hh:bullet", NS):
            bullets.append(IrBulletDef(
                id=int(b.get("id", "0")),
                char=b.get("char", "●"),
                char_pr_id_ref=int(b.get("charPrIDRef", "0")),
            ))
        return bullets

    def _parse_para_properties(self, para_props_el: etree._Element) -> List[IrParaPrDef]:
        """단락 속성 정의 파싱"""
        para_properties = []
        for pp in para_props_el.findall("hh:paraPr", NS):
            pp_id = int(pp.get("id", "0"))
            tab_pr_id_ref = int(pp.get("tabPrIDRef", "0"))
            condense = int(pp.get("condense", "0"))
            font_line_height = pp.get("fontLineHeight", "0") == "1"
            snap_to_grid = pp.get("snapToGrid", "1") == "1"
            suppress_line_numbers = pp.get("suppressLineNumbers", "0") == "1"
            checked = pp.get("checked", "0") == "1"

            # align
            align = None
            align_el = pp.find("hh:align", NS)
            if align_el is not None:
                align = IrParaAlign(
                    horizontal=align_el.get("horizontal", "JUSTIFY"),
                    vertical=align_el.get("vertical", "BASELINE"),
                )

            # breakSetting
            break_setting = None
            bs_el = pp.find("hh:breakSetting", NS)
            if bs_el is not None:
                break_setting = IrBreakSetting(
                    break_latin_word=bs_el.get("breakLatinWord", "KEEP_WORD"),
                    break_non_latin_word=bs_el.get("breakNonLatinWord", "KEEP_WORD"),
                    widow_orphan=bs_el.get("widowOrphan", "0") == "1",
                    keep_with_next=bs_el.get("keepWithNext", "0") == "1",
                    keep_lines=bs_el.get("keepLines", "0") == "1",
                    page_break_before=bs_el.get("pageBreakBefore", "0") == "1",
                    line_wrap=bs_el.get("lineWrap", "BREAK"),
                )

            # border
            border = None
            border_el = pp.find("hh:border", NS)
            if border_el is not None:
                border = IrParaBorder(
                    border_fill_id_ref=int(border_el.get("borderFillIDRef", "2")),
                    offset_left=int(border_el.get("offsetLeft", "0")),
                    offset_right=int(border_el.get("offsetRight", "0")),
                    offset_top=int(border_el.get("offsetTop", "0")),
                    offset_bottom=int(border_el.get("offsetBottom", "0")),
                    connect=border_el.get("connect", "0") == "1",
                    ignore_margin=border_el.get("ignoreMargin", "0") == "1",
                )

            para_properties.append(IrParaPrDef(
                id=pp_id,
                tab_pr_id_ref=tab_pr_id_ref,
                condense=condense,
                font_line_height=font_line_height,
                snap_to_grid=snap_to_grid,
                suppress_line_numbers=suppress_line_numbers,
                checked=checked,
                align=align,
                break_setting=break_setting,
                border=border,
            ))

        return para_properties

    def _parse_styles(self, styles_el: etree._Element) -> List[IrStyleDef]:
        """스타일 정의 파싱"""
        styles = []
        for s in styles_el.findall("hh:style", NS):
            styles.append(IrStyleDef(
                id=int(s.get("id", "0")),
                type=s.get("type", "PARA"),
                name=s.get("name", ""),
                eng_name=s.get("engName", ""),
                para_pr_id_ref=int(s.get("paraPrIDRef", "0")),
                char_pr_id_ref=int(s.get("charPrIDRef", "0")),
                next_style_id_ref=int(s.get("nextStyleIDRef", "0")),
                lang_id=int(s.get("langId", "1042")),
            ))
        return styles
