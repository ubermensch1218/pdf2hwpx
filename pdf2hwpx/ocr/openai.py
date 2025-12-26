"""OpenAI Vision OCR 백엔드"""

import base64
import os
from pathlib import Path
from typing import Optional

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock


class OpenAIOCR(OCRBackend):
    """OpenAI Vision API 백엔드"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set via api_key parameter or OPENAI_API_KEY env var."
            )

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 OCR 수행"""
        with open(pdf_path, "rb") as f:
            return self.process_bytes(f.read())

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 OCR 수행"""
        # PDF를 이미지로 변환 후 Vision API 호출
        # TODO: pdf2image 또는 pymupdf로 페이지별 이미지 추출
        raise NotImplementedError("OpenAI backend coming soon")
