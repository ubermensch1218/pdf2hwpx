"""OCR 백엔드 모듈"""

from pdf2hwpx.ocr.base import OCRBackend, OCRResult
from pdf2hwpx.ocr.cloud import CloudOCR
from pdf2hwpx.ocr.openai import OpenAIOCR
from pdf2hwpx.ocr.vllm import VllmOCR
from pdf2hwpx.ocr.pymupdf import PyMuPDFBackend
from pdf2hwpx.ocr.mineru import MinerUBackend
from pdf2hwpx.ocr.openrouter import OpenRouterOCR
from pdf2hwpx.ocr.gemini import GeminiOCR

__all__ = [
    "OCRBackend", "OCRResult",
    "CloudOCR", "OpenAIOCR", "VllmOCR",
    "PyMuPDFBackend", "MinerUBackend", "OpenRouterOCR", "GeminiOCR",
]
