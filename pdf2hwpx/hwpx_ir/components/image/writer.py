"""이미지 Writer"""

from __future__ import annotations

import math
from lxml import etree

from pdf2hwpx.hwpx_ir.base import NS, qname
from pdf2hwpx.hwpx_ir.models import IrImage, IrPosition, IrMargin


# 텍스트 줄바꿈 타입 매핑
TEXT_WRAP_MAP = {
    "top_and_bottom": "TOP_AND_BOTTOM",
    "both_sides": "SQUARE",
    "left_only": "LEFT",
    "right_only": "RIGHT",
    "behind_text": "BEHIND_TEXT",
    "in_front_of_text": "IN_FRONT_OF_TEXT",
}

# 수직 기준 매핑
VERT_REL_TO_MAP = {
    "paper": "PAPER",
    "page": "PAGE",
    "para": "PARA",
}

# 수평 기준 매핑
HORZ_REL_TO_MAP = {
    "paper": "PAPER",
    "page": "PAGE",
    "column": "COLUMN",
    "para": "PARA",
}

# 수직 정렬 매핑
VERT_ALIGN_MAP = {
    "top": "TOP",
    "center": "CENTER",
    "bottom": "BOTTOM",
    "inside": "INSIDE",
    "outside": "OUTSIDE",
}

# 수평 정렬 매핑
HORZ_ALIGN_MAP = {
    "left": "LEFT",
    "center": "CENTER",
    "right": "RIGHT",
    "inside": "INSIDE",
    "outside": "OUTSIDE",
}


class ImageWriter:
    """이미지 생성"""

    def build(self, image: IrImage, pic_id: int) -> etree._Element:
        """IrImage를 hp:pic 요소로 변환"""
        if image.raw_xml:
            return etree.fromstring(image.raw_xml)

        # 크기 설정
        cur_w = str(image.width_hwpunit) if image.width_hwpunit else "3000"
        cur_h = str(image.height_hwpunit) if image.height_hwpunit else "3000"
        org_w = str(image.org_width) if image.org_width else cur_w
        org_h = str(image.org_height) if image.org_height else cur_h

        # 스케일 계산
        try:
            sca_x = float(cur_w) / float(org_w)
            sca_y = float(cur_h) / float(org_h)
        except ZeroDivisionError:
            sca_x = 1.0
            sca_y = 1.0

        # 회전 매트릭스 계산
        angle_rad = math.radians(image.rotation_angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # 텍스트 줄바꿈 타입
        text_wrap = TEXT_WRAP_MAP.get(image.text_wrap, "TOP_AND_BOTTOM")

        pic = etree.Element(qname("hp", "pic"))
        pic.set("id", str(pic_id))
        pic.set("zOrder", "0")
        pic.set("numberingType", "PICTURE")
        pic.set("textWrap", text_wrap)
        pic.set("textFlow", "BOTH_SIDES")
        pic.set("lock", "0")
        pic.set("dropcapstyle", "None")
        pic.set("href", "")
        pic.set("groupLevel", "0")
        pic.set("instid", str(pic_id + 3000000))
        pic.set("reverse", "0")

        # offset
        offset = etree.SubElement(pic, qname("hp", "offset"))
        offset.set("x", "0")
        offset.set("y", "0")

        # orgSz
        org_sz = etree.SubElement(pic, qname("hp", "orgSz"))
        org_sz.set("width", org_w)
        org_sz.set("height", org_h)

        # curSz
        cur_sz = etree.SubElement(pic, qname("hp", "curSz"))
        cur_sz.set("width", cur_w)
        cur_sz.set("height", cur_h)

        # flip
        flip = etree.SubElement(pic, qname("hp", "flip"))
        flip.set("horizontal", "1" if image.flip_horizontal else "0")
        flip.set("vertical", "1" if image.flip_vertical else "0")

        # rotationInfo
        rot_info = etree.SubElement(pic, qname("hp", "rotationInfo"))
        rot_info.set("angle", str(image.rotation_angle))
        rot_info.set("centerX", str(int(int(cur_w) / 2)))
        rot_info.set("centerY", str(int(int(cur_h) / 2)))
        rot_info.set("rotateimage", "1")

        # renderingInfo
        rend_info = etree.SubElement(pic, qname("hp", "renderingInfo"))

        trans = etree.SubElement(rend_info, qname("hc", "transMatrix"))
        trans.set("e1", "1"); trans.set("e2", "0"); trans.set("e3", "0")
        trans.set("e4", "0"); trans.set("e5", "1"); trans.set("e6", "0")

        sca = etree.SubElement(rend_info, qname("hc", "scaMatrix"))
        sca.set("e1", f"{sca_x:.6f}"); sca.set("e2", "0"); sca.set("e3", "0")
        sca.set("e4", "0"); sca.set("e5", f"{sca_y:.6f}"); sca.set("e6", "0")

        rot = etree.SubElement(rend_info, qname("hc", "rotMatrix"))
        rot.set("e1", f"{cos_a:.6f}"); rot.set("e2", f"{-sin_a:.6f}"); rot.set("e3", "0")
        rot.set("e4", f"{sin_a:.6f}"); rot.set("e5", f"{cos_a:.6f}"); rot.set("e6", "0")

        # img (with brightness, contrast, alpha)
        img = etree.SubElement(pic, qname("hc", "img"))
        img.set("binaryItemIDRef", image.image_id)
        img.set("effect", "REAL_PIC")
        img.set("alpha", str(image.alpha))
        img.set("bright", str(image.brightness))
        img.set("contrast", str(image.contrast))

        # imgRect
        img_rect = etree.SubElement(pic, qname("hp", "imgRect"))
        pt0 = etree.SubElement(img_rect, qname("hc", "pt0")); pt0.set("x", "0"); pt0.set("y", "0")
        pt1 = etree.SubElement(img_rect, qname("hc", "pt1")); pt1.set("x", org_w); pt1.set("y", "0")
        pt2 = etree.SubElement(img_rect, qname("hc", "pt2")); pt2.set("x", org_w); pt2.set("y", org_h)
        pt3 = etree.SubElement(img_rect, qname("hc", "pt3")); pt3.set("x", "0"); pt3.set("y", org_h)

        # imgClip
        img_clip = etree.SubElement(pic, qname("hp", "imgClip"))
        img_clip.set("left", "0"); img_clip.set("right", org_w)
        img_clip.set("top", "0"); img_clip.set("bottom", org_h)

        # inMargin
        in_margin = etree.SubElement(pic, qname("hp", "inMargin"))
        in_margin.set("left", "0"); in_margin.set("right", "0")
        in_margin.set("top", "0"); in_margin.set("bottom", "0")

        # imgDim
        img_dim = etree.SubElement(pic, qname("hp", "imgDim"))
        img_dim.set("dimwidth", org_w)
        img_dim.set("dimheight", org_h)

        # effects
        etree.SubElement(pic, qname("hp", "effects"))

        # sz
        sz = etree.SubElement(pic, qname("hp", "sz"))
        sz.set("width", cur_w)
        sz.set("widthRelTo", "ABSOLUTE")
        sz.set("height", cur_h)
        sz.set("heightRelTo", "ABSOLUTE")
        sz.set("protect", "0")

        # pos - position 설정 반영
        pos = etree.SubElement(pic, qname("hp", "pos"))
        self._set_position_attrs(pos, image)

        # outMargin
        out_margin_el = etree.SubElement(pic, qname("hp", "outMargin"))
        if image.out_margin:
            out_margin_el.set("left", str(image.out_margin.left))
            out_margin_el.set("right", str(image.out_margin.right))
            out_margin_el.set("top", str(image.out_margin.top))
            out_margin_el.set("bottom", str(image.out_margin.bottom))
        else:
            out_margin_el.set("left", "0"); out_margin_el.set("right", "0")
            out_margin_el.set("top", "0"); out_margin_el.set("bottom", "0")

        # shapeComment
        etree.SubElement(pic, qname("hp", "shapeComment"))

        return pic

    def _set_position_attrs(self, pos_el: etree._Element, image: IrImage) -> None:
        """위치 속성 설정"""
        pos = image.position

        if pos:
            pos_el.set("treatAsChar", "1" if pos.treat_as_char else "0")
            pos_el.set("affectLSpacing", "0")
            pos_el.set("flowWithText", "1" if pos.flow_with_text else "0")
            pos_el.set("allowOverlap", "1" if pos.allow_overlap else "0")
            pos_el.set("holdAnchorAndSO", "0")
            pos_el.set("vertRelTo", VERT_REL_TO_MAP.get(pos.vert_rel_to, "PARA"))
            pos_el.set("horzRelTo", HORZ_REL_TO_MAP.get(pos.horz_rel_to, "COLUMN"))
            pos_el.set("vertAlign", VERT_ALIGN_MAP.get(pos.vert_align, "TOP"))
            pos_el.set("horzAlign", HORZ_ALIGN_MAP.get(pos.horz_align, "LEFT"))
            pos_el.set("vertOffset", str(pos.vert_offset))
            pos_el.set("horzOffset", str(pos.horz_offset))
        else:
            # 기본값 또는 레거시 treat_as_char 사용
            pos_el.set("treatAsChar", "1" if image.treat_as_char else "0")
            pos_el.set("affectLSpacing", "0")
            pos_el.set("flowWithText", "1")
            pos_el.set("allowOverlap", "0")
            pos_el.set("holdAnchorAndSO", "0")
            pos_el.set("vertRelTo", "PARA")
            pos_el.set("horzRelTo", "COLUMN")
            pos_el.set("vertAlign", "TOP")
            pos_el.set("horzAlign", "LEFT")
            pos_el.set("vertOffset", "0")
            pos_el.set("horzOffset", "0")
