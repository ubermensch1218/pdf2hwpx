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
    IrSection,
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
            # 페이지별로 섹션 생성 (컬럼 설정 포함)
            section_blocks = self._page_to_blocks(page, is_first_page=(page_idx == 0))

            # 섹션 생성 - col_count 적용
            col_count = getattr(page, 'column_count', 1)
            section = IrSection(
                blocks=section_blocks,
                col_count=col_count,
                col_gap=850 if col_count > 1 else 0,  # 2컬럼일 때 간격 설정 (~15mm)
            )
            blocks.append(IrBlock(type="section", section=section))

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
            if getattr(text_block, 'is_box', False):
                # 박스는 1x1 테두리 테이블로 변환
                box_table = self._create_box_table(text_block.text)
                blocks.append(IrBlock(type="table", table=box_table))
            else:
                # 일반 텍스트는 단락으로 변환 (heading_level 전달)
                heading_level = getattr(text_block, 'heading_level', 0)
                para_blocks = self._text_to_paragraphs(text_block.text, heading_level)
                blocks.extend(para_blocks)

        # 테이블 변환
        for table in page.tables:
            ir_table = self._table_to_ir(table)
            blocks.append(IrBlock(type="table", table=ir_table))

        return blocks

    def _text_to_paragraphs(self, text: str, heading_level: int = 0) -> List[IrBlock]:
        """텍스트를 단락으로 변환

        Args:
            text: 텍스트
            heading_level: 제목 레벨 (0=일반, 1=대제목, 2=중제목, 3=소제목)
        """
        blocks: List[IrBlock] = []

        if not text:
            return blocks

        # heading_level에 따른 폰트 크기
        font_size_map = {
            0: self.font_size,  # 일반: 10pt
            1: 1600,  # 대제목: 16pt
            2: 1300,  # 중제목: 13pt
            3: 1100,  # 소제목: 11pt
        }
        base_font_size = font_size_map.get(heading_level, self.font_size)
        is_heading = heading_level > 0

        # 줄 단위로 처리
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 인라인 요소 파싱 (굵은글씨 처리)
            inlines = self._parse_markdown_inlines(line, base_font_size, is_heading)

            # 들여쓰기 감지
            indent_left = 0
            bullet_pattern = re.compile(r'^(○|●|◎|□|■|※|·|→|▶|▷|►|◆|◇)\s*')
            if bullet_pattern.match(line):
                indent_left = 400

            para = IrParagraph(
                inlines=inlines,
                line_spacing_type="percent",
                line_spacing_value=self.line_spacing,
                indent_left=indent_left,
            )
            blocks.append(IrBlock(type="paragraph", paragraph=para))

        return blocks

    def _parse_markdown_inlines(self, text: str, base_font_size: int, base_bold: bool) -> List[IrInline]:
        """마크다운 인라인 요소 파싱 (**굵은글씨**)"""
        inlines: List[IrInline] = []

        # **굵은글씨** 패턴
        bold_pattern = re.compile(r'\*\*(.+?)\*\*')
        last_end = 0

        for match in bold_pattern.finditer(text):
            # 굵은글씨 앞의 일반 텍스트
            if match.start() > last_end:
                normal_text = text[last_end:match.start()]
                if normal_text:
                    inlines.append(IrTextRun(
                        text=normal_text,
                        font_family=self.font_family,
                        font_size=base_font_size,
                        bold=base_bold,
                    ))

            # 굵은글씨 텍스트
            bold_text = match.group(1)
            inlines.append(IrTextRun(
                text=bold_text,
                font_family=self.font_family,
                font_size=base_font_size,
                bold=True,
            ))
            last_end = match.end()

        # 나머지 텍스트
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                inlines.append(IrTextRun(
                    text=remaining,
                    font_family=self.font_family,
                    font_size=base_font_size,
                    bold=base_bold,
                ))

        # 빈 경우 기본 텍스트
        if not inlines:
            inlines.append(IrTextRun(
                text=text,
                font_family=self.font_family,
                font_size=base_font_size,
                bold=base_bold,
            ))

        return inlines

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

    def _create_box_table(self, text: str) -> IrTable:
        """박스(테두리 있는 영역)를 1x1 테이블로 생성"""
        # 텍스트 정리 - 원본 줄바꿈 보존
        cleaned = text.strip()

        # 셀 내용 생성
        inlines = [IrTextRun(
            text=cleaned,
            font_family=self.font_family,
            font_size=self.font_size,
        )]

        cell_para = IrParagraph(
            inlines=inlines,
            line_spacing_type="percent",
            line_spacing_value=self.line_spacing,
        )
        cell_block = IrBlock(type="paragraph", paragraph=cell_para)

        # 1x1 셀 생성 - 여백 설정
        from pdf2hwpx.hwpx_ir.models import IrMargin
        ir_cell = IrTableCell(
            row=0,
            col=0,
            row_span=1,
            col_span=1,
            blocks=[cell_block],
            border_fill_id=5,
            margin=IrMargin(left=283, right=283, top=142, bottom=142),  # 셀 여백
        )

        # 테이블 너비: 전체 컬럼 너비 (A4 기준 약 48000 HWPUNIT)
        table_width = 48000

        return IrTable(
            row_cnt=1,
            col_cnt=1,
            cells=[ir_cell],
            border_fill_id=5,
            width_hwpunit=table_width,
            col_widths=[table_width],
        )
