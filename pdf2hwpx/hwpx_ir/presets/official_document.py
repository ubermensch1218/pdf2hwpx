"""공문서 프리셋 (Preset #1)

2025 개정 공문서 작성법 기준 공문서 양식.
"""

from __future__ import annotations

from typing import Dict, List

from pdf2hwpx.hwpx_ir.models import (
    IrBlock,
    IrDocument,
    IrMargin,
    IrPageMargin,
    IrPageNumber,
    IrParagraph,
    IrPosition,
    IrSection,
    IrTable,
    IrTableCell,
    IrTextRun,
)

from .base import DocumentPreset, PresetField, PresetRegistry


@PresetRegistry.register
class OfficialDocumentPreset(DocumentPreset):
    """공문서 프리셋

    2025년 개정 공문서 작성법 기준:
    - 용지: A4 (210mm x 297mm)
    - 여백: 상 20mm, 하 10mm, 좌우 각 10mm
    - 머리말 여백: 10mm
    - 꼬리말 여백: 10mm
    - 기본 글꼴: 함초롬바탕, 15pt
    - 제목: 16pt, 진하게
    """

    preset_id = "official_document"
    preset_name = "공문서"
    description = "2025년 개정 공문서 작성법 기준 공문서 양식"

    # 페이지 설정 상수 (HWPUNIT)
    PAGE_WIDTH = 59528   # A4 width (210mm)
    PAGE_HEIGHT = 84188  # A4 height (297mm)
    MARGIN_LEFT = 5669   # 10mm
    MARGIN_RIGHT = 5669  # 10mm
    MARGIN_TOP = 5669    # 10mm (실제 20mm이지만 헤더 포함)
    MARGIN_BOTTOM = 2835 # 5mm
    HEADER_HEIGHT = 2835 # 5mm
    FOOTER_HEIGHT = 2835 # 5mm

    # 본문 폭 계산
    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT  # 약 48190

    # 글자 크기 (1/100 pt 단위)
    FONT_SIZE_TITLE = 1600   # 16pt
    FONT_SIZE_BODY = 1500    # 15pt
    FONT_SIZE_HEADER = 2000  # 20pt (행정기관명)

    @classmethod
    def get_fields(cls) -> List[PresetField]:
        """공문서 필드 목록"""
        return [
            PresetField(
                name="agency_name",
                label="행정기관명",
                required=True,
                max_length=50,
            ),
            PresetField(
                name="document_number",
                label="문서번호",
                required=True,
                max_length=30,
            ),
            PresetField(
                name="date",
                label="시행일자",
                required=True,
                default_value="",  # YYYY. MM. DD. 형식
            ),
            PresetField(
                name="recipient",
                label="수신",
                required=True,
                max_length=100,
            ),
            PresetField(
                name="via",
                label="경유",
                required=False,
                max_length=100,
            ),
            PresetField(
                name="title",
                label="제목",
                required=True,
                max_length=200,
            ),
            PresetField(
                name="body",
                label="본문",
                required=True,
            ),
            PresetField(
                name="drafter",
                label="기안자",
                required=True,
                max_length=20,
            ),
            PresetField(
                name="reviewer",
                label="검토자",
                required=False,
                max_length=20,
            ),
            PresetField(
                name="approver",
                label="결재권자",
                required=True,
                max_length=20,
            ),
            PresetField(
                name="contact_info",
                label="연락처",
                required=False,
                max_length=100,
            ),
        ]

    @classmethod
    def get_page_settings(cls) -> IrSection:
        """공문서 페이지 설정"""
        return IrSection(
            blocks=[],
            page_width=cls.PAGE_WIDTH,
            page_height=cls.PAGE_HEIGHT,
            landscape=False,
            margin=IrPageMargin(
                left=cls.MARGIN_LEFT,
                right=cls.MARGIN_RIGHT,
                top=cls.MARGIN_TOP,
                bottom=cls.MARGIN_BOTTOM,
                header=cls.HEADER_HEIGHT,
                footer=cls.FOOTER_HEIGHT,
                gutter=0,
            ),
            page_number=IrPageNumber(
                position="bottom_center",
                format_type="digit",
                start_number=1,
                hide_first_page=True,  # 첫 페이지 번호 숨김
            ),
        )

    @classmethod
    def build_document(cls, field_values: Dict[str, str]) -> IrDocument:
        """공문서 생성"""
        blocks: List[IrBlock] = []

        # 1. 시행일자 표 (오른쪽 정렬)
        date_table = cls._build_date_table(field_values.get("date", ""))
        blocks.append(IrBlock(type="table", table=date_table))

        # 2. 빈 줄 2개
        blocks.append(cls._empty_paragraph())
        blocks.append(cls._empty_paragraph())

        # 3. 행정기관명
        agency_para = IrParagraph(
            inlines=[
                IrTextRun(
                    text=field_values.get("agency_name", ""),
                    font_size=cls.FONT_SIZE_HEADER,
                    bold=True,
                )
            ],
            alignment="center",
        )
        blocks.append(IrBlock(type="paragraph", paragraph=agency_para))

        # 4. 빈 줄
        blocks.append(cls._empty_paragraph())

        # 5. 본문 표 (수신, 경유, 제목, 본문)
        content_table = cls._build_content_table(field_values)
        blocks.append(IrBlock(type="table", table=content_table))

        # 6. 빈 줄 2개
        blocks.append(cls._empty_paragraph())
        blocks.append(cls._empty_paragraph())

        # 7. 결재란
        approval_table = cls._build_approval_table(field_values)
        blocks.append(IrBlock(type="table", table=approval_table))

        # 8. 연락처
        if field_values.get("contact_info"):
            contact_para = IrParagraph(
                inlines=[
                    IrTextRun(
                        text=field_values.get("contact_info", ""),
                        font_size=1000,  # 10pt
                    )
                ],
                alignment="left",
            )
            blocks.append(IrBlock(type="paragraph", paragraph=contact_para))

        return IrDocument(blocks=blocks)

    @classmethod
    def _empty_paragraph(cls) -> IrBlock:
        """빈 단락 생성"""
        return IrBlock(
            type="paragraph",
            paragraph=IrParagraph(inlines=[IrTextRun(text="")])
        )

    @classmethod
    def _build_date_table(cls, date: str) -> IrTable:
        """시행일자 표 (우측 상단)"""
        cell = IrTableCell(
            row=0,
            col=0,
            blocks=[
                IrBlock(
                    type="paragraph",
                    paragraph=IrParagraph(
                        inlines=[IrTextRun(text=date, font_size=cls.FONT_SIZE_BODY)],
                        alignment="center",
                    )
                )
            ],
            width_hwpunit=12249,
            height_hwpunit=2567,
            vert_align="center",
        )

        return IrTable(
            row_cnt=1,
            col_cnt=1,
            cells=[cell],
            width_hwpunit=12249,
            height_hwpunit=2567,
            col_widths=[12249],
            row_heights=[2567],
            position=IrPosition(
                treat_as_char=True,
                horz_align="right",
            ),
            out_margin=IrMargin(left=283, right=283, top=283, bottom=283),
            in_margin=IrMargin(left=510, right=510, top=141, bottom=141),
        )

    @classmethod
    def _build_content_table(cls, field_values: Dict[str, str]) -> IrTable:
        """본문 내용 표 (수신, 경유, 제목, 본문)"""
        cells: List[IrTableCell] = []
        row = 0

        # 수신
        cells.append(cls._build_label_value_cell(
            row=row, label="수신", value=field_values.get("recipient", "")
        ))
        row += 1

        # 경유 (선택)
        if field_values.get("via"):
            cells.append(cls._build_label_value_cell(
                row=row, label="(경유)", value=field_values.get("via", "")
            ))
            row += 1

        # 제목
        cells.append(cls._build_label_value_cell(
            row=row, label="제목", value=field_values.get("title", ""),
            bold=True, font_size=cls.FONT_SIZE_TITLE
        ))
        row += 1

        # 본문 (빈 행 후 본문)
        body_text = field_values.get("body", "")
        body_cell = IrTableCell(
            row=row,
            col=0,
            blocks=[
                IrBlock(
                    type="paragraph",
                    paragraph=IrParagraph(
                        inlines=[IrTextRun(text=body_text, font_size=cls.FONT_SIZE_BODY)],
                        alignment="justify",
                        indent_first_line=1000,  # 첫줄 들여쓰기
                    )
                )
            ],
            width_hwpunit=cls.CONTENT_WIDTH,
            vert_align="top",
        )
        cells.append(body_cell)

        return IrTable(
            row_cnt=len(cells),
            col_cnt=1,
            cells=cells,
            width_hwpunit=cls.CONTENT_WIDTH,
            col_widths=[cls.CONTENT_WIDTH],
            position=IrPosition(treat_as_char=True),
            border_fill_id=3,  # 테두리 없음
        )

    @classmethod
    def _build_label_value_cell(
        cls,
        row: int,
        label: str,
        value: str,
        bold: bool = False,
        font_size: int = None,
    ) -> IrTableCell:
        """레이블: 값 형태의 셀 생성"""
        if font_size is None:
            font_size = cls.FONT_SIZE_BODY

        return IrTableCell(
            row=row,
            col=0,
            blocks=[
                IrBlock(
                    type="paragraph",
                    paragraph=IrParagraph(
                        inlines=[
                            IrTextRun(text=f"{label}  ", font_size=font_size),
                            IrTextRun(text=value, font_size=font_size, bold=bold),
                        ],
                        alignment="left",
                    )
                )
            ],
            width_hwpunit=cls.CONTENT_WIDTH,
            vert_align="center",
        )

    @classmethod
    def _build_approval_table(cls, field_values: Dict[str, str]) -> IrTable:
        """결재란 표"""
        drafter = field_values.get("drafter", "")
        reviewer = field_values.get("reviewer", "")
        approver = field_values.get("approver", "")

        # 결재란은 3열 (기안, 검토, 결재)
        col_count = 3 if reviewer else 2

        cells: List[IrTableCell] = []

        # 헤더 행
        headers = ["기안", "검토", "결재"] if reviewer else ["기안", "결재"]
        for col, header in enumerate(headers):
            cells.append(IrTableCell(
                row=0,
                col=col,
                blocks=[
                    IrBlock(
                        type="paragraph",
                        paragraph=IrParagraph(
                            inlines=[IrTextRun(text=header, font_size=1200, bold=True)],
                            alignment="center",
                        )
                    )
                ],
                vert_align="center",
            ))

        # 서명 행 (빈칸)
        for col in range(col_count):
            cells.append(IrTableCell(
                row=1,
                col=col,
                blocks=[IrBlock(type="paragraph", paragraph=IrParagraph(inlines=[]))],
                height_hwpunit=2000,
                vert_align="center",
            ))

        # 이름 행
        names = [drafter, reviewer, approver] if reviewer else [drafter, approver]
        for col, name in enumerate(names):
            cells.append(IrTableCell(
                row=2,
                col=col,
                blocks=[
                    IrBlock(
                        type="paragraph",
                        paragraph=IrParagraph(
                            inlines=[IrTextRun(text=name, font_size=1200)],
                            alignment="center",
                        )
                    )
                ],
                vert_align="center",
            ))

        col_width = 6000
        return IrTable(
            row_cnt=3,
            col_cnt=col_count,
            cells=cells,
            width_hwpunit=col_width * col_count,
            col_widths=[col_width] * col_count,
            row_heights=[1200, 2000, 1200],
            position=IrPosition(
                treat_as_char=True,
                horz_align="right",
            ),
            border_fill_id=5,  # 실선 테두리
        )
