"""MinerU 기반 PDF 파싱 백엔드"""

import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from pdf2hwpx.ocr.base import OCRBackend, OCRResult, PageResult, TextBlock, Table, TableCell


class MinerUBackend(OCRBackend):
    """MinerU (magic-pdf) 기반 PDF 구조 추출

    고급 레이아웃 분석, 테이블 탐지, 수식 인식 지원.
    magic-pdf 패키지 필요: pip install magic-pdf
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        device: str = "cpu",
    ):
        """
        Args:
            model_dir: 모델 디렉토리 경로 (기본: 자동 다운로드)
            device: 장치 ("cpu" 또는 "cuda")
        """
        self.model_dir = model_dir
        self.device = device
        self._check_dependencies()

    def _check_dependencies(self):
        """의존성 확인"""
        try:
            import magic_pdf
        except ImportError:
            raise ImportError(
                "MinerU를 사용하려면 magic-pdf 패키지가 필요합니다: "
                "pip install magic-pdf"
            )

    def process(self, pdf_path: Path) -> OCRResult:
        """PDF 파일에서 구조 추출"""
        with open(pdf_path, "rb") as f:
            return self.process_bytes(f.read())

    def process_bytes(self, pdf_bytes: bytes) -> OCRResult:
        """PDF 바이트에서 구조 추출"""
        from magic_pdf.data.data_reader_writer import FileBasedDataReader, FileBasedDataWriter
        from magic_pdf.data.dataset import PymuDocDataset
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze

        # 임시 디렉토리에 저장
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "input.pdf"
            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir()

            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            # MinerU 처리
            reader = FileBasedDataReader("")
            writer = FileBasedDataWriter(str(output_dir))

            # PDF 분석
            dataset = PymuDocDataset(pdf_bytes)

            # 모델 분석 수행
            infer_result = doc_analyze(
                dataset,
                ocr=True,
                show_log=False,
                lang="ko+en",
            )

            # 결과 추출
            pages = self._parse_infer_result(infer_result, dataset)

            return OCRResult(pages=pages, metadata={})

    def _parse_infer_result(self, infer_result, dataset) -> List[PageResult]:
        """MinerU 결과 파싱"""
        pages = []

        for page_idx, page_result in enumerate(infer_result):
            page_info = dataset.get_page(page_idx)
            width = page_info.get("width", 595)
            height = page_info.get("height", 841)

            text_blocks = []
            tables = []

            for block in page_result.get("layout_dets", []):
                category = block.get("category_id", 0)
                bbox = block.get("bbox", [0, 0, 0, 0])
                x0, y0, x1, y1 = bbox

                # 텍스트 블록 (category 1, 2, 3, 4, 5...)
                if category in [1, 2, 3, 4, 5]:  # title, text, etc.
                    text = block.get("text", "")
                    if text:
                        text_blocks.append(TextBlock(
                            text=text,
                            x=x0,
                            y=y0,
                            width=x1 - x0,
                            height=y1 - y0,
                        ))

                # 테이블 (category 6)
                elif category == 6:
                    table_data = block.get("table", {})
                    if table_data:
                        table = self._parse_table(table_data, bbox)
                        tables.append(table)

            pages.append(PageResult(
                page_num=page_idx + 1,
                width=width,
                height=height,
                text_blocks=text_blocks,
                tables=tables,
                images=[],
            ))

        return pages

    def _parse_table(self, table_data: dict, bbox: List[float]) -> Table:
        """테이블 데이터 파싱"""
        cells = []
        rows_data = table_data.get("cells", [])

        max_row = 0
        max_col = 0

        for cell in rows_data:
            row = cell.get("row", 0)
            col = cell.get("col", 0)
            text = cell.get("text", "")
            rowspan = cell.get("rowspan", 1)
            colspan = cell.get("colspan", 1)

            max_row = max(max_row, row + rowspan)
            max_col = max(max_col, col + colspan)

            cells.append(TableCell(
                text=text,
                row=row,
                col=col,
                rowspan=rowspan,
                colspan=colspan,
            ))

        x0, y0, x1, y1 = bbox
        return Table(
            cells=cells,
            rows=max_row,
            cols=max_col,
            x=x0,
            y=y0,
            width=x1 - x0,
            height=y1 - y0,
        )
