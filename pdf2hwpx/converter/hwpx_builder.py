"""HWPX 빌더 - OCR 결과를 HWPX로 변환"""

import io
import zipfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from pdf2hwpx.ocr.base import OCRResult, PageResult, TextBlock, Table


class HwpxBuilder:
    """OCR 결과를 HWPX 파일로 변환"""

    # HWPX 네임스페이스
    NAMESPACES = {
        "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
        "hs": "http://www.hancom.co.kr/hwpml/2011/section",
        "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    }

    def __init__(self):
        pass

    def build(self, ocr_result: OCRResult, output_path: Path) -> None:
        """
        OCR 결과를 HWPX 파일로 저장

        Args:
            ocr_result: OCR 결과
            output_path: 출력 HWPX 파일 경로
        """
        hwpx_bytes = self.build_bytes(ocr_result)
        with open(output_path, "wb") as f:
            f.write(hwpx_bytes)

    def build_bytes(self, ocr_result: OCRResult) -> bytes:
        """
        OCR 결과를 HWPX 바이트로 변환

        Args:
            ocr_result: OCR 결과

        Returns:
            HWPX 파일 바이트
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. [Content_Types].xml
            zf.writestr("[Content_Types].xml", self._create_content_types())

            # 2. _rels/.rels
            zf.writestr("_rels/.rels", self._create_rels())

            # 3. META-INF/manifest.xml
            zf.writestr("META-INF/manifest.xml", self._create_manifest())

            # 4. header.xml (문서 헤더)
            zf.writestr("header.xml", self._create_header())

            # 5. Contents/section0.xml (본문)
            section_xml = self._create_section(ocr_result)
            zf.writestr("Contents/section0.xml", section_xml)

        buffer.seek(0)
        return buffer.read()

    def _create_content_types(self) -> str:
        """[Content_Types].xml 생성"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/header.xml" ContentType="application/hwp+xml"/>
    <Override PartName="/Contents/section0.xml" ContentType="application/hwp+xml"/>
</Types>'''

    def _create_rels(self) -> str:
        """_rels/.rels 생성"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://www.hancom.co.kr/hwpml/2011/header" Target="header.xml"/>
    <Relationship Id="rId2" Type="http://www.hancom.co.kr/hwpml/2011/section" Target="Contents/section0.xml"/>
</Relationships>'''

    def _create_manifest(self) -> str:
        """META-INF/manifest.xml 생성"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
    <manifest:file-entry manifest:full-path="/" manifest:media-type="application/hwp+zip"/>
    <manifest:file-entry manifest:full-path="header.xml" manifest:media-type="application/hwp+xml"/>
    <manifest:file-entry manifest:full-path="Contents/section0.xml" manifest:media-type="application/hwp+xml"/>
</manifest:manifest>'''

    def _create_header(self) -> str:
        """header.xml 생성"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head">
    <hh:beginNum page="1" footnote="1" endnote="1" picture="1" table="1" equation="1"/>
    <hh:refList>
        <hh:fontfaces>
            <hh:fontface lang="HANGUL" fontCnt="1">
                <hh:font id="0" face="맑은 고딕" type="TTF"/>
            </hh:fontface>
        </hh:fontfaces>
    </hh:refList>
</hh:head>'''

    def _create_section(self, ocr_result: OCRResult) -> str:
        """section0.xml 생성 (본문)"""
        paragraphs = []

        for page in ocr_result.pages:
            for block in page.text_blocks:
                para = self._create_paragraph(block.text)
                paragraphs.append(para)

            # 페이지 구분 (마지막 페이지 제외)
            if page.page_num < len(ocr_result.pages):
                paragraphs.append('<hp:p><hp:ctrl><hp:colPr type="PAGE_BREAK"/></hp:ctrl></hp:p>')

        content = "\n".join(paragraphs)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">
    {content}
</hs:sec>'''

    def _create_paragraph(self, text: str) -> str:
        """단락 XML 생성"""
        # XML 이스케이프
        escaped_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

        return f'''<hp:p>
    <hp:run>
        <hp:t>{escaped_text}</hp:t>
    </hp:run>
</hp:p>'''
