"""HWPX IR (Intermediate Representation) 모듈

PDF에서 추출한 데이터를 HWPX로 변환하기 위한 중간 표현 모델들.

구조:
- models.py: IR 모델 정의
- base.py: 공통 유틸리티 (NS, 단위 변환 등)
- reader.py: HWPX → IR 변환
- writer.py: IR → HWPX 변환
- components/: 컴포넌트별 reader/writer
- presets/: 문서 양식 프리셋
"""

from .models import (
    # 공통 타입 정의
    TextWrapType,
    VertRelToType,
    HorzRelToType,
    VertAlignType,
    HorzAlignType,
    CellVertAlignType,
    BorderStyleType,
    AlignmentType,
    BlockType,
    BulletStyle,
    ChangeType,
    FieldType,
    IrInline,
    LineSpacingType,
    ListType,
    NumberingStyle,
    PageNumFormatType,
    PageNumPosType,
    # 공통 데이터 클래스
    IrMargin,
    IrPosition,
    IrBorder,
    IrBorderSet,
    # 텍스트/인라인 요소
    IrTextRun,
    IrLineBreak,
    IrHyperlink,
    IrBookmark,
    IrField,
    IrFootnote,
    IrEndnote,
    IrComment,
    IrTrackChange,
    # 단락
    IrParagraph,
    # 표
    IrTableCell,
    IrTable,
    # 이미지
    IrImage,
    # 수식
    IrEquation,
    # 목록
    IrListItem,
    IrList,
    # 캡션
    IrCaption,
    # 목차
    IrTOCEntry,
    IrTOC,
    # 섹션/페이지
    IrPageMargin,
    IrHeader,
    IrFooter,
    IrPageNumber,
    IrSection,
    # 블록/문서
    IrBlock,
    IrDocument,
)

from .reader import HwpxIrReader, HwpxPackage, HwpxBinaryItem
from .writer import HwpxIrWriter, HwpxIdContext, StyleManager

__all__ = [
    # 공통 타입 정의
    "TextWrapType",
    "VertRelToType",
    "HorzRelToType",
    "VertAlignType",
    "HorzAlignType",
    "CellVertAlignType",
    "BorderStyleType",
    "AlignmentType",
    "BlockType",
    "BulletStyle",
    "ChangeType",
    "FieldType",
    "IrInline",
    "LineSpacingType",
    "ListType",
    "NumberingStyle",
    "PageNumFormatType",
    "PageNumPosType",
    # 공통 데이터 클래스
    "IrMargin",
    "IrPosition",
    "IrBorder",
    "IrBorderSet",
    # 텍스트/인라인 요소
    "IrTextRun",
    "IrLineBreak",
    "IrHyperlink",
    "IrBookmark",
    "IrField",
    "IrFootnote",
    "IrEndnote",
    "IrComment",
    "IrTrackChange",
    # 단락
    "IrParagraph",
    # 표
    "IrTableCell",
    "IrTable",
    # 이미지
    "IrImage",
    # 수식
    "IrEquation",
    # 목록
    "IrListItem",
    "IrList",
    # 캡션
    "IrCaption",
    # 목차
    "IrTOCEntry",
    "IrTOC",
    # 섹션/페이지
    "IrPageMargin",
    "IrHeader",
    "IrFooter",
    "IrPageNumber",
    "IrSection",
    # 블록/문서
    "IrBlock",
    "IrDocument",
    # Reader/Writer
    "HwpxIrReader",
    "HwpxIrWriter",
    "HwpxPackage",
    "HwpxBinaryItem",
    "HwpxIdContext",
    "StyleManager",
]
