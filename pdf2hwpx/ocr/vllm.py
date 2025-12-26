"""vLLM 서버 OCR 백엔드"""

import base64
import os
from pathlib import Path
from typing import Optional

import httpx

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock


class VllmOCR(OCRBackend):
    """vLLM 서버 백엔드 (OpenAI-compatible API)"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.api_key = api_key or os.getenv("VLLM_API_KEY", "dummy")
        self.model = model or os.getenv("VLLM_MODEL", "gemini-2.5-flash-lite")

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 OCR 수행"""
        with open(pdf_path, "rb") as f:
            return self.process_bytes(f.read())

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 OCR 수행"""
        # PDF를 이미지로 변환 후 vLLM Vision 호출
        # TODO: pdf2image로 페이지별 이미지 추출 후 Vision 모델 호출
        raise NotImplementedError("vLLM backend coming soon")
