"""OCR 백엔드 모듈"""

from pdf2hwpx.ocr.base import OCRBackend, OCRResult
from pdf2hwpx.ocr.cloud import CloudOCR
from pdf2hwpx.ocr.openai import OpenAIOCR
from pdf2hwpx.ocr.vllm import VllmOCR

__all__ = ["OCRBackend", "OCRResult", "CloudOCR", "OpenAIOCR", "VllmOCR"]
