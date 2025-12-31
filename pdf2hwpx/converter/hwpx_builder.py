"""HWPX 빌더 - OCR 결과를 HWPX로 변환"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from pdf2hwpx.ocr.base import OCRResult, PageResult, TextBlock, Table, TableCell
from pdf2hwpx.hwpx_ir.models import (
    IrBlock,
    IrDocument,
    IrImage,
    IrInline,
    IrLineBreak,
    IrParagraph,
    IrTab,
    IrTable,
    IrTableCell as IrTableCell,
    IrTextRun,
)
from pdf2hwpx.hwpx_ir.writer import HwpxIrWriter, HwpxBinaryItem


# 기본 폰트 설정
DEFAULT_FONT_FAMILY = "함초롬바탕"
DEFAULT_FONT_SIZE = 1000  # 10pt (1/100 pt 단위)
DEFAULT_LINE_SPACING = 160  # 160%


class HwpxBuilder:
    """OCR 결과를 HWPX 파일로 변환"""

    def __init__(
        self,
        template_path: Optional[str] = None,
        font_family: str = DEFAULT_FONT_FAMILY,
        font_size: int = DEFAULT_FONT_SIZE,
        line_spacing: int = DEFAULT_LINE_SPACING,
    ):
        """
        Args:
            template_path: HWPX 템플릿 파일 경로
            font_family: 기본 폰트 (기본: 함초롬바탕)
            font_size: 기본 폰트 크기 (1/100 pt, 기본: 1000 = 10pt)
            line_spacing: 줄간격 (%, 기본: 160)
        """
        if template_path is None:
            # 기본 템플릿 사용
            template_path = Path(__file__).parent.parent / "templates" / "template.hwpx"

        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"HWPX template not found: {template_path}")

        self.writer = HwpxIrWriter(str(self.template_path))
        self.font_family = font_family
        self.font_size = font_size
        self.line_spacing = line_spacing

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

        for page_idx, page in enumerate(ocr_result.pages):
            # 페이지별로 변환
            page_blocks = self._page_to_blocks(page, is_first_page=(page_idx == 0))
            blocks.extend(page_blocks)

        return IrDocument(blocks=blocks)

    def _page_to_blocks(self, page: PageResult, is_first_page: bool = True) -> List[IrBlock]:
        """페이지를 IR 블록들로 변환"""
        blocks: List[IrBlock] = []

        # 첫 페이지가 아니면 페이지 브레이크 추가
        if not is_first_page:
            page_break_para = IrParagraph(
                inlines=[IrTextRun(text="", font_family=self.font_family, font_size=self.font_size)],
            )
            blocks.append(IrBlock(type="paragraph", paragraph=page_break_para, page_break=True))

        # 텍스트 블록을 단락으로 변환
        for text_block in page.text_blocks:
            # 텍스트를 줄 단위로 분리하여 각각 단락으로 생성
            para_blocks = self._text_to_paragraphs(text_block.text)
            blocks.extend(para_blocks)

        # 테이블 변환
        for table in page.tables:
            ir_table = self._table_to_ir(table)
            blocks.append(IrBlock(type="table", table=ir_table))

        return blocks

    def _text_to_paragraphs(self, text: str) -> List[IrBlock]:
        """텍스트를 단락으로 변환 (블록 내 줄바꿈은 유지)"""
        blocks: List[IrBlock] = []

        if not text:
            return blocks

        # 텍스트 정리 - 블록 내 줄바꿈을 공백으로 변환
        # (PDF 표 셀 등에서 발생하는 불필요한 줄바꿈 제거)
        cleaned = ' '.join(line.strip() for line in text.split('\n') if line.strip())

        if not cleaned:
            return blocks

        # 불릿/리스트 패턴
        bullet_pattern = re.compile(r'^(\s*)(○|●|◎|□|■|※|·|-|\*|→|▶|▷|►|◆|◇)\s*')
        number_pattern = re.compile(r'^(\s*)(\d+)[.)\s]\s*')
        sub_bullet_pattern = re.compile(r'^(\s*)[*-]\s+')

        indent_left = 0

        # 불릿 패턴 감지
        if bullet_pattern.match(cleaned):
            indent_left = 400
        elif sub_bullet_pattern.match(cleaned):
            indent_left = 800

        inlines = [IrTextRun(
            text=cleaned,
            font_family=self.font_family,
            font_size=self.font_size,
        )]

        para = IrParagraph(
            inlines=inlines,
            line_spacing_type="percent",
            line_spacing_value=self.line_spacing,
            indent_left=indent_left,
        )
        blocks.append(IrBlock(type="paragraph", paragraph=para))

        return blocks

    def _parse_text_to_inlines(self, text: str) -> List[IrInline]:
        """텍스트를 인라인 요소로 파싱 (줄바꿈, 탭 처리)"""
        inlines: List[IrInline] = []

        if not text:
            return inlines

        # 줄바꿈과 탭으로 분리
        # 패턴: 줄바꿈(\n, \r\n) 또는 탭(\t)
        pattern = r'(\r?\n|\t)'
        parts = re.split(pattern, text)

        for part in parts:
            if not part:
                continue
            elif part == '\n' or part == '\r\n':
                inlines.append(IrLineBreak())
            elif part == '\t':
                inlines.append(IrTab())
            else:
                # 일반 텍스트
                inlines.append(IrTextRun(
                    text=part,
                    font_family=self.font_family,
                    font_size=self.font_size,
                ))

        return inlines

    def _table_to_ir(self, table: Table) -> IrTable:
        """테이블을 IR 테이블로 변환"""
        # 셀을 IR 셀로 변환
        ir_cells: List[IrTableCell] = []

        for cell in table.cells:
            # 셀 내용을 파싱하여 단락으로 변환
            inlines = self._parse_text_to_inlines(cell.text)
            cell_para = IrParagraph(
                inlines=inlines,
                line_spacing_type="percent",
                line_spacing_value=self.line_spacing,
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
