"""PyMuPDF 기반 PDF 파싱 백엔드"""

import io
from pathlib import Path
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock, Table, TableCell


class PyMuPDFBackend(OCRBackend):
    """PyMuPDF 기반 PDF 직접 파싱 (OCR 없이 텍스트 추출)

    디지털 PDF (텍스트가 있는 PDF)에 적합.
    스캔된 이미지 PDF는 텍스트 추출 불가.
    """

    def __init__(self, extract_images: bool = True):
        """
        Args:
            extract_images: 이미지 추출 여부
        """
        self.extract_images = extract_images

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 텍스트/테이블/이미지 추출"""
        doc = fitz.open(pdf_path)
        return self._process_document(doc)

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 텍스트/테이블/이미지 추출"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return self._process_document(doc)

    def _process_document(self, doc: fitz.Document) -> OCRResult:
        """문서 처리"""
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_result = self._process_page(page, page_num + 1)
            pages.append(page_result)

        # 메타데이터 추출
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creationDate": doc.metadata.get("creationDate", ""),
            "modDate": doc.metadata.get("modDate", ""),
            "page_count": len(doc),
        }

        doc.close()
        return OCRResult(pages=pages, metadata=metadata)

    def _process_page(self, page: fitz.Page, page_num: int) -> PageResult:
        """페이지 처리"""
        rect = page.rect
        width = rect.width
        height = rect.height

        # 텍스트 블록 추출
        text_blocks = self._extract_text_blocks(page)

        # 테이블 추출
        tables = self._extract_tables(page)

        # 이미지 추출
        images = []
        if self.extract_images:
            images = self._extract_images(page)

        return PageResult(
            page_num=page_num,
            width=width,
            height=height,
            text_blocks=text_blocks,
            tables=tables,
            images=images,
        )

    def _extract_text_blocks(self, page: fitz.Page) -> List[TextBlock]:
        """텍스트 블록 추출"""
        blocks = []

        # 텍스트 사전 추출 (blocks 형태)
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = 텍스트 블록
                continue

            bbox = block.get("bbox", [0, 0, 0, 0])
            x0, y0, x1, y1 = bbox

            # 블록 내 모든 라인의 텍스트 결합
            lines_text = []
            for line in block.get("lines", []):
                spans_text = []
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if text.strip():
                        spans_text.append(text)
                if spans_text:
                    lines_text.append("".join(spans_text))

            text = "\n".join(lines_text)
            if text.strip():
                blocks.append(TextBlock(
                    text=text,
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    confidence=1.0,
                ))

        return blocks

    def _extract_tables(self, page: fitz.Page) -> List[Table]:
        """테이블 추출 (PyMuPDF 내장 테이블 탐지)"""
        tables = []

        try:
            # PyMuPDF 1.23.0+ 테이블 탐지
            tab_finder = page.find_tables()

            for tab in tab_finder.tables:
                cells = []
                data = tab.extract()

                for row_idx, row in enumerate(data):
                    for col_idx, cell_text in enumerate(row):
                        cells.append(TableCell(
                            text=str(cell_text) if cell_text else "",
                            row=row_idx,
                            col=col_idx,
                            rowspan=1,
                            colspan=1,
                        ))

                bbox = tab.bbox
                tables.append(Table(
                    cells=cells,
                    rows=len(data),
                    cols=len(data[0]) if data else 0,
                    x=bbox[0],
                    y=bbox[1],
                    width=bbox[2] - bbox[0],
                    height=bbox[3] - bbox[1],
                ))
        except AttributeError:
            # 구버전 PyMuPDF - 테이블 탐지 미지원
            pass

        return tables

    def _extract_images(self, page: fitz.Page) -> List[bytes]:
        """이미지 추출"""
        images = []

        image_list = page.get_images(full=True)

        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = page.parent.extract_image(xref)
                if base_image:
                    images.append(base_image["image"])
            except Exception:
                continue

        return images
