"""
Pdf2Hwpx 메인 클래스
"""

from typing import Optional, Literal
from pathlib import Path

from pdf2hwpx.ocr.base import OCRBackend
from pdf2hwpx.ocr.cloud import CloudOCR
from pdf2hwpx.ocr.openai import OpenAIOCR
from pdf2hwpx.ocr.vllm import VllmOCR
from pdf2hwpx.ocr.pymupdf import PyMuPDFBackend
from pdf2hwpx.ocr.mineru import MinerUBackend
from pdf2hwpx.ocr.openrouter import OpenRouterOCR
from pdf2hwpx.ocr.gemini import GeminiOCR
from pdf2hwpx.converter.hwpx_builder import HwpxBuilder


class Pdf2Hwpx:
    """PDF를 HWPX로 변환하는 메인 클래스"""

    def __init__(
        self,
        backend: Literal["cloud", "openai", "vllm", "pymupdf", "mineru", "openrouter", "gemini"] = "cloud",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            backend: OCR 백엔드 ("cloud", "openai", "vllm", "pymupdf", "mineru", "openrouter", "gemini")
            api_key: API 키
            base_url: vLLM/OpenRouter 서버 URL
            model: OpenRouter 모델 (openrouter 백엔드 사용 시)
        """
        self.backend = backend
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._ocr: OCRBackend = self._create_ocr_backend()
        self._builder = HwpxBuilder()

    def _create_ocr_backend(self) -> OCRBackend:
        """OCR 백엔드 인스턴스 생성"""
        if self.backend == "cloud":
            return CloudOCR(api_key=self.api_key)
        elif self.backend == "openai":
            return OpenAIOCR(api_key=self.api_key)
        elif self.backend == "vllm":
            return VllmOCR(base_url=self.base_url, api_key=self.api_key)
        elif self.backend == "pymupdf":
            return PyMuPDFBackend()
        elif self.backend == "mineru":
            return MinerUBackend()
        elif self.backend == "openrouter":
            return OpenRouterOCR(api_key=self.api_key, model=self.model)
        elif self.backend == "gemini":
            return GeminiOCR(api_key=self.api_key, model=self.model)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def convert(
        self,
        input_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """
        PDF를 HWPX로 변환

        Args:
            input_path: 입력 PDF 파일 경로
            output_path: 출력 HWPX 파일 경로

        Returns:
            생성된 HWPX 파일 경로
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        # 1. PDF에서 OCR 수행
        ocr_result = self._ocr.process(input_path)

        # 2. OCR 결과를 HWPX로 변환
        self._builder.build(ocr_result, output_path)

        return output_path

    def convert_bytes(
        self,
        pdf_bytes: bytes,
    ) -> bytes:
        """
        PDF 바이트를 HWPX 바이트로 변환

        Args:
            pdf_bytes: PDF 파일 바이트

        Returns:
            HWPX 파일 바이트
        """
        # 1. PDF에서 OCR 수행
        ocr_result = self._ocr.process_bytes(pdf_bytes)

        # 2. OCR 결과를 HWPX로 변환
        return self._builder.build_bytes(ocr_result)
