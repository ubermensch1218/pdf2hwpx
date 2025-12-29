"""HWPX 빌더 - OCR 결과를 HWPX로 변환"""

from pathlib import Path
from typing import Dict, List, Optional

from pdf2hwpx.ocr.base import OCRResult, PageResult, TextBlock, Table, TableCell
from pdf2hwpx.hwpx_ir.models import (
    IrBlock,
    IrDocument,
    IrImage,
    IrParagraph,
    IrTable,
    IrTableCell as IrTableCell,
    IrTextRun,
)
from pdf2hwpx.hwpx_ir.writer import HwpxIrWriter, HwpxBinaryItem


class HwpxBuilder:
    """OCR 결과를 HWPX 파일로 변환"""

    def __init__(self, template_path: Optional[str] = None):
        """
        Args:
            template_path: HWPX 템플릿 파일 경로
        """
        if template_path is None:
            # 기본 템플릿 사용
            template_path = Path(__file__).parent.parent / "templates" / "template.hwpx"

        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"HWPX template not found: {template_path}")

        self.writer = HwpxIrWriter(str(self.template_path))

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
        # OCR 결과 → IR 변환
        doc = self._ocr_result_to_ir(ocr_result)

        # TODO: 이미지 처리
        binary_items: Dict[str, HwpxBinaryItem] = {}

        # IR → HWPX 변환
        return self.writer.write(doc, binary_items=binary_items)

    def _ocr_result_to_ir(self, ocr_result: OCRResult) -> IrDocument:
        """OCR 결과를 IR 문서로 변환"""
        blocks: List[IrBlock] = []

        for page in ocr_result.pages:
            # 페이지별로 변환
            page_blocks = self._page_to_blocks(page)
            blocks.extend(page_blocks)

        return IrDocument(blocks=blocks)

    def _page_to_blocks(self, page: PageResult) -> List[IrBlock]:
        """페이지를 IR 블록들로 변환"""
        blocks: List[IrBlock] = []

        # 텍스트 블록을 단락으로 변환
        for text_block in page.text_blocks:
            para = IrParagraph(
                inlines=[
                    IrTextRun(
                        text=text_block.text,
                    )
                ]
            )
            blocks.append(IrBlock(type="paragraph", paragraph=para))

        # 테이블 변환
        for table in page.tables:
            ir_table = self._table_to_ir(table)
            blocks.append(IrBlock(type="table", table=ir_table))

        return blocks

    def _table_to_ir(self, table: Table) -> IrTable:
        """테이블을 IR 테이블로 변환"""
        # 셀을 IR 셀로 변환
        ir_cells: List[IrTableCell] = []

        for cell in table.cells:
            # 셀 내용을 단락으로 변환
            cell_para = IrParagraph(
                inlines=[
                    IrTextRun(text=cell.text)
                ]
            )
            cell_block = IrBlock(type="paragraph", paragraph=cell_para)

            ir_cell = IrTableCell(
                row=cell.row,
                col=cell.col,
                row_span=cell.rowspan,
                col_span=cell.colspan,
                blocks=[cell_block],
            )
            ir_cells.append(ir_cell)

        return IrTable(
            row_cnt=table.rows,
            col_cnt=table.cols,
            cells=ir_cells,
        )
