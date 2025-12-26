"""Cloud API OCR 백엔드 (기본)"""

import os
from pathlib import Path
from typing import Optional

import httpx

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock, Table


class CloudOCR(OCRBackend):
    """pdf2hwpx Cloud API 백엔드"""

    DEFAULT_BASE_URL = "https://api.pdf2hwpx.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("PDF2HWPX_API_KEY")
        self.base_url = base_url or os.getenv("PDF2HWPX_BASE_URL", self.DEFAULT_BASE_URL)

        if not self.api_key:
            raise ValueError(
                "API key required. Set via api_key parameter or PDF2HWPX_API_KEY env var. "
                "Get your key at https://pdf2hwpx.com"
            )

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 OCR 수행"""
        with open(pdf_path, "rb") as f:
            return self.process_bytes(f.read())

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 OCR 수행"""
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{self.base_url}/v1/ocr",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("document.pdf", pdf_bytes, "application/pdf")},
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> OCRResult:
        """API 응답을 OCRResult로 변환"""
        pages = []
        for page_data in data.get("pages", []):
            text_blocks = [
                TextBlock(
                    text=block["text"],
                    x=block["x"],
                    y=block["y"],
                    width=block["width"],
                    height=block["height"],
                    confidence=block.get("confidence", 1.0),
                )
                for block in page_data.get("text_blocks", [])
            ]

            tables = []  # TODO: 테이블 파싱

            pages.append(
                PageResult(
                    page_num=page_data["page_num"],
                    width=page_data["width"],
                    height=page_data["height"],
                    text_blocks=text_blocks,
                    tables=tables,
                    images=[],
                )
            )

        return OCRResult(pages=pages, metadata=data.get("metadata", {}))
