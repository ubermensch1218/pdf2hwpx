"""OCR 백엔드 추상 클래스"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TextBlock:
    """텍스트 블록"""
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float = 1.0


@dataclass
class TableCell:
    """테이블 셀"""
    text: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1


@dataclass
class Table:
    """테이블"""
    cells: list[TableCell]
    rows: int
    cols: int
    x: float
    y: float
    width: float
    height: float


@dataclass
class PageResult:
    """페이지별 OCR 결과"""
    page_num: int
    width: float
    height: float
    text_blocks: list[TextBlock]
    tables: list[Table]
    images: list[bytes]  # 이미지 바이트 데이터


@dataclass
class OCRResult:
    """전체 OCR 결과"""
    pages: list[PageResult]
    metadata: dict


class OCRBackend(ABC):
    """OCR 백엔드 추상 클래스"""

    @abstractmethod
    def process(self, pdf_path: Path) -> OCRResult:
        """
        PDF 파일에서 OCR 수행

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            OCR 결과
        """
        pass

    @abstractmethod
    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """
        PDF 바이트에서 OCR 수행

        Args:
            pdf_bytes: PDF 파일 바이트

        Returns:
            OCR 결과
        """
        pass
