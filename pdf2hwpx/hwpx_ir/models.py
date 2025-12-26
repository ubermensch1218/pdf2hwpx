from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Union


@dataclass(frozen=True)
class IrTextRun:
    text: str
    bold: bool = False
    italic: bool = False
    font_size: Optional[int] = None  # 1/100 pt (e.g., 1000 = 10pt)
    font_family: Optional[str] = None
    color: Optional[str] = None


@dataclass(frozen=True)
class IrLineBreak:
    pass


IrInline = Union[IrTextRun, IrLineBreak]


@dataclass(frozen=True)
class IrParagraph:
    inlines: List[IrInline] = field(default_factory=list)
    raw_xml: Optional[bytes] = None


@dataclass(frozen=True)
class IrImage:
    image_id: str
    width_hwpunit: Optional[int] = None
    height_hwpunit: Optional[int] = None
    org_width: Optional[int] = None
    org_height: Optional[int] = None
    treat_as_char: bool = False
    raw_xml: Optional[bytes] = None


@dataclass(frozen=True)
class IrTableCell:
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    blocks: List["IrBlock"] = field(default_factory=list)
    width_hwpunit: Optional[int] = None
    height_hwpunit: Optional[int] = None
    border_fill_id: int = 5


@dataclass(frozen=True)
class IrTable:
    row_cnt: int
    col_cnt: int
    cells: List[IrTableCell] = field(default_factory=list)
    width_hwpunit: Optional[int] = None
    height_hwpunit: Optional[int] = None
    treat_as_char: bool = True
    raw_xml: Optional[bytes] = None
    border_fill_id: int = 5


@dataclass(frozen=True)
class IrEquation:
    script: str
    width_hwpunit: int = 4000
    height_hwpunit: int = 1000
    text_color: str = "#000000"
    base_line: int = 85
    version: str = "Equation Version 60"


BlockType = Literal["paragraph", "table", "image", "section", "equation"]


@dataclass(frozen=True)
class IrHeader:
    text: str
    height: int = 1500

@dataclass(frozen=True)
class IrFooter:
    text: str
    height: int = 1500
    show_page_number: bool = False

@dataclass(frozen=True)
class IrSection:
    blocks: List[IrBlock] = field(default_factory=list)
    col_count: int = 1
    col_gap: int = 0
    header: Optional[IrHeader] = None
    footer: Optional[IrFooter] = None
    page_width: int = 59528  # A4 width
    page_height: int = 84188 # A4 height
    col_line_type: Optional[str] = None


@dataclass(frozen=True)
class IrBlock:
    type: BlockType
    paragraph: Optional[IrParagraph] = None
    table: Optional[IrTable] = None
    image: Optional[IrImage] = None
    section: Optional[IrSection] = None
    equation: Optional[IrEquation] = None


@dataclass(frozen=True)
class IrDocument:
    blocks: List[IrBlock] = field(default_factory=list)
