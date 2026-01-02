from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple, Union


# ============================================================
# 공통 타입 정의
# ============================================================

# 텍스트 줄바꿈 타입
TextWrapType = Literal[
    "top_and_bottom",  # 위아래로
    "both_sides",      # 양쪽
    "left_only",       # 왼쪽만
    "right_only",      # 오른쪽만
    "behind_text",     # 글 뒤로
    "in_front_of_text" # 글 앞으로
]

# 수직 기준
VertRelToType = Literal["paper", "page", "para"]

# 수평 기준
HorzRelToType = Literal["paper", "page", "column", "para"]

# 수직 정렬
VertAlignType = Literal["top", "center", "bottom", "inside", "outside"]

# 수평 정렬
HorzAlignType = Literal["left", "center", "right", "inside", "outside"]

# 셀 수직 정렬
CellVertAlignType = Literal["top", "center", "bottom"]

# 테두리 스타일 (HWPX 형식)
BorderStyleType = Literal[
    "none", "solid", "dashed", "dotted",
    "double", "dash_dot", "dash_dot_dot"
]

# HWPX 네이티브 테두리 타입
HwpxBorderType = Literal[
    "NONE", "SOLID", "DASH", "DOT", "DASH_DOT", "DASH_DOT_DOT",
    "DOUBLE_SLIM", "THICK_SLIM", "SLIM_THICK", "THICK_SLIM_THICK",
    "SLIM_THICK_SLIM", "WAVE", "DOUBLE_WAVE", "LONG_DASH", "INSET", "OUTSET"
]

# 대각선 타입
DiagonalType = Literal["NONE", "SLASH", "BACKSLASH", "CENTER"]


@dataclass(frozen=True)
class IrHwpxBorder:
    """HWPX 네이티브 테두리 정의"""
    type: HwpxBorderType = "NONE"
    width: str = "0.1 mm"  # "0.12 mm" 형식
    color: str = "#000000"  # HEX 또는 "none"


@dataclass(frozen=True)
class IrDiagonal:
    """대각선 정의"""
    type: DiagonalType = "NONE"
    crooked: bool = False
    is_counter: bool = False


@dataclass(frozen=True)
class IrWinBrush:
    """Windows 브러시 채우기"""
    face_color: str = "none"  # HEX 또는 "none"
    hatch_color: str = "#000000"  # HEX
    alpha: int = 0  # 0-255


@dataclass(frozen=True)
class IrGradation:
    """그라데이션 채우기"""
    type: str = "LINEAR"  # LINEAR, RADIAL, CONICAL, SQUARE
    angle: int = 0
    center_x: int = 0
    center_y: int = 0
    step: int = 50
    color_num: int = 2
    step_center: int = 50
    colors: List[str] = field(default_factory=list)  # HEX 색상 목록


@dataclass(frozen=True)
class IrFillBrush:
    """채우기 브러시 (winBrush 또는 gradation)"""
    win_brush: Optional[IrWinBrush] = None
    gradation: Optional[IrGradation] = None


@dataclass(frozen=True)
class IrBorderFillDef:
    """HWPX BorderFill 정의 (header.xml용)"""
    id: int
    three_d: bool = False
    shadow: bool = False
    center_line: str = "NONE"
    break_cell_separate_line: bool = False
    # 대각선
    slash: Optional[IrDiagonal] = None
    back_slash: Optional[IrDiagonal] = None
    # 4방향 테두리
    left_border: Optional[IrHwpxBorder] = None
    right_border: Optional[IrHwpxBorder] = None
    top_border: Optional[IrHwpxBorder] = None
    bottom_border: Optional[IrHwpxBorder] = None
    # 대각선 (셀 내 대각선)
    diagonal: Optional[IrHwpxBorder] = None
    # 채우기
    fill_brush: Optional[IrFillBrush] = None


# ============================================================
# 폰트 정의 (header.xml용)
# ============================================================

@dataclass(frozen=True)
class IrFontDef:
    """폰트 정의"""
    id: int
    face: str  # 폰트 이름
    type: str = "TTF"  # TTF, HFT 등
    is_embedded: bool = False
    subst_font_face: Optional[str] = None  # 대체 폰트


@dataclass(frozen=True)
class IrFontFace:
    """언어별 폰트 목록"""
    lang: str  # HANGUL, LATIN, HANJA, JAPANESE, OTHER, SYMBOL, USER
    fonts: List[IrFontDef] = field(default_factory=list)


@dataclass(frozen=True)
class IrFontRef:
    """폰트 참조 (언어별 폰트 ID)"""
    hangul: int = 0
    latin: int = 0
    hanja: int = 0
    japanese: int = 0
    other: int = 0
    symbol: int = 0
    user: int = 0


@dataclass(frozen=True)
class IrLangValues:
    """언어별 값 (ratio, spacing, relSz, offset)"""
    hangul: int = 100
    latin: int = 100
    hanja: int = 100
    japanese: int = 100
    other: int = 100
    symbol: int = 100
    user: int = 100


@dataclass(frozen=True)
class IrUnderline:
    """밑줄 설정"""
    type: str = "NONE"  # NONE, BOTTOM, CENTER, TOP
    shape: str = "SOLID"  # SOLID, DASH, DOT 등
    color: str = "#000000"


@dataclass(frozen=True)
class IrStrikeout:
    """취소선 설정"""
    shape: str = "NONE"  # NONE, CONTINUOUS
    color: str = "#000000"


@dataclass(frozen=True)
class IrShadow:
    """그림자 설정"""
    type: str = "NONE"  # NONE, DROP, CONTINUOUS
    color: str = "#B2B2B2"
    offset_x: int = 10
    offset_y: int = 10


@dataclass(frozen=True)
class IrCharPrDef:
    """문자 속성 정의 (header.xml용)"""
    id: int
    height: int = 1000  # 글자 크기 (1/100 pt)
    text_color: str = "#000000"
    shade_color: str = "none"
    use_font_space: bool = False
    use_kerning: bool = False
    sym_mark: str = "NONE"
    border_fill_id_ref: int = 1
    # 폰트 참조
    font_ref: Optional[IrFontRef] = None
    ratio: Optional[IrLangValues] = None
    spacing: Optional[IrLangValues] = None
    rel_sz: Optional[IrLangValues] = None
    offset: Optional[IrLangValues] = None
    # 스타일
    bold: bool = False
    italic: bool = False
    # 장식
    underline: Optional[IrUnderline] = None
    strikeout: Optional[IrStrikeout] = None
    outline_type: str = "NONE"
    shadow: Optional[IrShadow] = None


@dataclass(frozen=True)
class IrParaAlign:
    """단락 정렬"""
    horizontal: str = "JUSTIFY"  # LEFT, CENTER, RIGHT, JUSTIFY, DISTRIBUTE
    vertical: str = "BASELINE"  # TOP, CENTER, BOTTOM, BASELINE


@dataclass(frozen=True)
class IrBreakSetting:
    """단락 분리 설정"""
    break_latin_word: str = "KEEP_WORD"
    break_non_latin_word: str = "KEEP_WORD"
    widow_orphan: bool = False
    keep_with_next: bool = False
    keep_lines: bool = False
    page_break_before: bool = False
    line_wrap: str = "BREAK"


@dataclass(frozen=True)
class IrParaBorder:
    """단락 테두리"""
    border_fill_id_ref: int = 2
    offset_left: int = 0
    offset_right: int = 0
    offset_top: int = 0
    offset_bottom: int = 0
    connect: bool = False
    ignore_margin: bool = False


@dataclass(frozen=True)
class IrParaPrDef:
    """단락 속성 정의 (header.xml용)"""
    id: int
    tab_pr_id_ref: int = 0
    condense: int = 0
    font_line_height: bool = False
    snap_to_grid: bool = True
    suppress_line_numbers: bool = False
    checked: bool = False
    # 정렬
    align: Optional[IrParaAlign] = None
    # 줄바꿈 설정
    break_setting: Optional[IrBreakSetting] = None
    # 테두리
    border: Optional[IrParaBorder] = None
    # 들여쓰기/내어쓰기
    margin_left: int = 0
    margin_right: int = 0
    indent: int = 0
    # 줄간격
    line_spacing_type: str = "PERCENT"
    line_spacing_value: int = 160


@dataclass(frozen=True)
class IrMargin:
    """여백 (HWPUNIT)"""
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0


@dataclass(frozen=True)
class IrPosition:
    """위치 설정"""
    treat_as_char: bool = True  # 글자처럼 취급
    vert_rel_to: VertRelToType = "para"  # 수직 기준
    horz_rel_to: HorzRelToType = "column"  # 수평 기준
    vert_align: VertAlignType = "top"  # 수직 정렬
    horz_align: HorzAlignType = "left"  # 수평 정렬
    vert_offset: int = 0  # 수직 오프셋 (HWPUNIT)
    horz_offset: int = 0  # 수평 오프셋 (HWPUNIT)
    flow_with_text: bool = True  # 텍스트와 함께 이동
    allow_overlap: bool = False  # 겹침 허용


@dataclass(frozen=True)
class IrBorder:
    """테두리"""
    style: BorderStyleType = "solid"
    width: int = 1  # 선 두께 (0.1mm 단위)
    color: str = "#000000"


@dataclass(frozen=True)
class IrBorderSet:
    """4방향 테두리"""
    left: Optional[IrBorder] = None
    right: Optional[IrBorder] = None
    top: Optional[IrBorder] = None
    bottom: Optional[IrBorder] = None


@dataclass(frozen=True)
class IrTextRun:
    """텍스트 실행 단위"""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False  # 밑줄
    strikethrough: bool = False  # 취소선
    font_size: Optional[int] = None  # 1/100 pt (e.g., 1000 = 10pt)
    font_family: Optional[str] = None
    color: Optional[str] = None  # 텍스트 색상 (HEX)
    background_color: Optional[str] = None  # 텍스트 배경색 (HEX)


@dataclass(frozen=True)
class IrLineBreak:
    """줄바꿈"""
    pass


@dataclass(frozen=True)
class IrTab:
    """탭 문자"""
    pass


# 단락 정렬 타입
AlignmentType = Literal["left", "right", "center", "justify", "distribute"]

# 줄간격 타입
LineSpacingType = Literal["percent", "fixed", "between_lines", "at_least"]


@dataclass(frozen=True)
class IrHyperlink:
    """하이퍼링크"""
    url: str  # 링크 URL
    text: str  # 표시 텍스트
    tooltip: Optional[str] = None  # 툴팁


@dataclass(frozen=True)
class IrBookmark:
    """북마크"""
    name: str  # 북마크 이름
    text: Optional[str] = None  # 북마크된 텍스트


@dataclass(frozen=True)
class IrFootnote:
    """각주"""
    number: int  # 각주 번호
    content: List["IrParagraph"] = field(default_factory=list)  # 각주 내용


@dataclass(frozen=True)
class IrEndnote:
    """미주"""
    number: int  # 미주 번호
    content: List["IrParagraph"] = field(default_factory=list)  # 미주 내용


# 필드 타입
FieldType = Literal[
    "date",           # 현재 날짜
    "time",           # 현재 시간
    "page_number",    # 페이지 번호
    "total_pages",    # 총 페이지 수
    "file_name",      # 파일명
    "author",         # 작성자
    "title",          # 제목
    "created_date",   # 작성일
    "modified_date",  # 수정일
    "custom"          # 사용자 정의
]


@dataclass(frozen=True)
class IrField:
    """필드 (자동 삽입 요소)"""
    field_type: FieldType
    format: Optional[str] = None  # 날짜/시간 포맷 (예: "yyyy-MM-dd")
    custom_value: Optional[str] = None  # custom 타입일 때 값


@dataclass(frozen=True)
class IrComment:
    """주석/메모"""
    author: str  # 작성자
    content: str  # 주석 내용
    date: Optional[str] = None  # 작성 날짜 (ISO 형식)


# 변경 추적 타입
ChangeType = Literal["insert", "delete", "format"]


@dataclass(frozen=True)
class IrTrackChange:
    """변경 추적"""
    change_type: ChangeType
    author: str
    date: Optional[str] = None  # ISO 형식
    original_text: Optional[str] = None  # 삭제된 텍스트
    new_text: Optional[str] = None  # 삽입된 텍스트


@dataclass(frozen=True)
class IrInlineEquation:
    """인라인 수식"""
    script: str  # HWP 수식 스크립트
    base_line: int = 85  # 베이스라인 (0-100)


IrInline = Union[IrTextRun, IrLineBreak, IrTab, IrHyperlink, IrBookmark, IrField, IrFootnote, IrEndnote, IrComment, IrTrackChange, IrInlineEquation]


@dataclass(frozen=True)
class IrParagraph:
    """단락"""
    inlines: List[IrInline] = field(default_factory=list)
    raw_xml: Optional[bytes] = None
    # 단락 정렬
    alignment: AlignmentType = "left"
    # 줄간격
    line_spacing_type: LineSpacingType = "percent"
    line_spacing_value: int = 160  # percent일 경우 160 = 160%
    # 들여쓰기 (HWPUNIT)
    indent_left: int = 0  # 왼쪽 들여쓰기
    indent_right: int = 0  # 오른쪽 들여쓰기
    indent_first_line: int = 0  # 첫줄 들여쓰기
    # 단락 전후 간격 (HWPUNIT)
    space_before: int = 0  # 단락 앞 간격
    space_after: int = 0  # 단락 뒤 간격
    # 배경색
    background_color: Optional[str] = None  # HEX
    # 스타일 참조
    style_id: Optional[str] = None  # 스타일 ID (예: "제목1", "본문")


@dataclass(frozen=True)
class IrImage:
    """이미지"""
    image_id: str
    # 크기 (HWPUNIT)
    width_hwpunit: Optional[int] = None
    height_hwpunit: Optional[int] = None
    org_width: Optional[int] = None
    org_height: Optional[int] = None
    # 배치 설정
    treat_as_char: bool = False  # 글자처럼 취급 (deprecated, use position.treat_as_char)
    position: Optional[IrPosition] = None  # 위치 설정
    text_wrap: TextWrapType = "top_and_bottom"  # 텍스트 배치
    # 여백
    out_margin: Optional[IrMargin] = None  # 외부 여백
    # 변형
    flip_horizontal: bool = False
    flip_vertical: bool = False
    rotation_angle: int = 0  # 회전 각도 (도)
    # 효과
    brightness: int = 0  # 밝기 (-100 ~ 100)
    contrast: int = 0  # 대비 (-100 ~ 100)
    alpha: int = 0  # 투명도 (0 ~ 100)
    # 원본 XML (직접 파싱용)
    raw_xml: Optional[bytes] = None


@dataclass(frozen=True)
class IrTableCell:
    """표 셀"""
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    blocks: List["IrBlock"] = field(default_factory=list)
    # 크기 (HWPUNIT)
    width_hwpunit: Optional[int] = None
    height_hwpunit: Optional[int] = None
    # 셀 여백
    margin: Optional[IrMargin] = None
    # 수직 정렬
    vert_align: CellVertAlignType = "center"
    # 테두리/배경
    border_fill_id: int = 5
    borders: Optional[IrBorderSet] = None  # 개별 테두리 설정
    background_color: Optional[str] = None  # 배경색 (HEX)
    # 보호/편집
    protect: bool = False


@dataclass(frozen=True)
class IrTable:
    """표"""
    row_cnt: int
    col_cnt: int
    cells: List[IrTableCell] = field(default_factory=list)
    # 크기 (HWPUNIT)
    width_hwpunit: Optional[int] = None
    height_hwpunit: Optional[int] = None
    # 열/행 크기 목록 (HWPUNIT)
    col_widths: Optional[List[int]] = None  # 각 열의 너비
    row_heights: Optional[List[int]] = None  # 각 행의 높이
    # 배치
    treat_as_char: bool = True  # 글자처럼 취급 (deprecated)
    position: Optional[IrPosition] = None  # 위치 설정
    text_wrap: TextWrapType = "top_and_bottom"  # 텍스트 배치
    # 여백
    out_margin: Optional[IrMargin] = None  # 외부 여백 (표 바깥)
    in_margin: Optional[IrMargin] = None  # 내부 여백 (셀 기본값)
    # 셀 간격
    cell_spacing: int = 0
    # 테두리/배경
    border_fill_id: int = 5
    # 헤더 행 반복
    repeat_header: bool = False
    # 원본 XML
    raw_xml: Optional[bytes] = None


@dataclass(frozen=True)
class IrEquation:
    """수식"""
    script: str
    width_hwpunit: int = 4000
    height_hwpunit: int = 1000
    text_color: str = "#000000"
    base_line: int = 85
    version: str = "Equation Version 60"


# 목록/번호매기기 타입
ListType = Literal[
    "bullet",       # 글머리 기호
    "numbered",     # 번호 매기기
    "checklist",    # 체크리스트
    "multi_level"   # 다단계 목록
]

# 글머리 기호 스타일
BulletStyle = Literal["disc", "circle", "square", "dash", "arrow", "check"]

# 번호 매기기 스타일
NumberingStyle = Literal[
    "decimal",      # 1, 2, 3
    "lower_alpha",  # a, b, c
    "upper_alpha",  # A, B, C
    "lower_roman",  # i, ii, iii
    "upper_roman",  # I, II, III
    "korean",       # 가, 나, 다
    "circled"       # ①, ②, ③
]


@dataclass(frozen=True)
class IrListItem:
    """목록 항목"""
    content: IrParagraph  # 목록 항목 내용
    level: int = 0  # 목록 레벨 (0부터 시작)
    list_type: ListType = "bullet"
    bullet_style: BulletStyle = "disc"  # 글머리 기호 스타일
    numbering_style: NumberingStyle = "decimal"  # 번호 스타일
    number: Optional[int] = None  # 현재 번호 (번호 매기기용)
    checked: Optional[bool] = None  # 체크 여부 (체크리스트용)


@dataclass(frozen=True)
class IrList:
    """목록/번호매기기"""
    items: List[IrListItem] = field(default_factory=list)
    list_type: ListType = "bullet"
    start_number: int = 1  # 시작 번호


@dataclass(frozen=True)
class IrCaption:
    """캡션 (표/그림 설명)"""
    text: str  # 캡션 텍스트
    target_type: Literal["table", "image", "equation"] = "image"  # 대상 타입
    number: Optional[int] = None  # 자동 번호
    position: Literal["above", "below"] = "below"  # 위치
    prefix: Optional[str] = None  # 접두사 (예: "그림", "표")


@dataclass(frozen=True)
class IrTOCEntry:
    """목차 항목"""
    text: str  # 제목 텍스트
    level: int  # 제목 레벨 (1=제목1, 2=제목2, ...)
    page_number: Optional[int] = None  # 페이지 번호
    bookmark_name: Optional[str] = None  # 연결된 북마크


@dataclass(frozen=True)
class IrTOC:
    """목차 (Table of Contents)"""
    entries: List[IrTOCEntry] = field(default_factory=list)
    title: str = "목차"  # 목차 제목
    max_level: int = 3  # 표시할 최대 레벨
    show_page_numbers: bool = True  # 페이지 번호 표시
    use_hyperlinks: bool = True  # 하이퍼링크 사용


BlockType = Literal["paragraph", "table", "image", "section", "equation", "list", "toc"]


@dataclass(frozen=True)
class IrPageMargin:
    """페이지 여백 (HWPUNIT) - 공문서 기본값 적용"""
    left: int = 5669      # 약 10mm
    right: int = 5669     # 약 10mm
    top: int = 5669       # 약 10mm
    bottom: int = 2835    # 약 5mm
    header: int = 2835    # 머리말 여백
    footer: int = 2835    # 꼬리말 여백
    gutter: int = 0       # 제본 여백


@dataclass(frozen=True)
class IrHeader:
    """머리말"""
    text: str
    height: int = 1500


@dataclass(frozen=True)
class IrFooter:
    """꼬리말"""
    text: str
    height: int = 1500
    show_page_number: bool = False


# 페이지 번호 표시 형식
PageNumFormatType = Literal["digit", "upper_roman", "lower_roman", "upper_alpha", "lower_alpha"]

# 페이지 번호 위치
PageNumPosType = Literal[
    "top_left", "top_center", "top_right",
    "bottom_left", "bottom_center", "bottom_right"
]


@dataclass(frozen=True)
class IrPageNumber:
    """페이지 번호 설정"""
    position: PageNumPosType = "bottom_center"
    format_type: PageNumFormatType = "digit"
    start_number: int = 1
    hide_first_page: bool = False
    side_char: str = "-"  # 페이지 번호 양 옆 문자


@dataclass(frozen=True)
class IrPageHiding:
    """페이지 요소 숨기기 설정"""
    hide_header: bool = False
    hide_footer: bool = False
    hide_master_page: bool = False
    hide_border: bool = False
    hide_fill: bool = False
    hide_page_num: bool = False


@dataclass(frozen=True)
class IrSection:
    """섹션 (페이지 설정 단위)"""
    blocks: List[IrBlock] = field(default_factory=list)
    # 다단 설정
    col_count: int = 1
    col_gap: int = 0
    col_line_type: Optional[str] = None
    # 머리말/꼬리말
    header: Optional[IrHeader] = None
    footer: Optional[IrFooter] = None
    # 페이지 크기 (HWPUNIT)
    page_width: int = 59528   # A4 width
    page_height: int = 84188  # A4 height
    landscape: bool = False   # 가로 방향
    # 페이지 여백
    margin: Optional[IrPageMargin] = None
    # 페이지 번호
    page_number: Optional[IrPageNumber] = None
    # 페이지 요소 숨기기
    page_hiding: Optional[IrPageHiding] = None
    # 원본 XML (100% 라운드트립용)
    raw_xml: Optional[bytes] = None


@dataclass(frozen=True)
class IrBlock:
    """블록 요소"""
    type: BlockType
    paragraph: Optional[IrParagraph] = None
    table: Optional[IrTable] = None
    image: Optional[IrImage] = None
    section: Optional[IrSection] = None
    equation: Optional[IrEquation] = None
    list: Optional[IrList] = None  # 목록/번호매기기
    toc: Optional[IrTOC] = None  # 목차
    caption: Optional[IrCaption] = None  # 캡션 (이미지/표에 연결)
    page_break: bool = False  # 이 블록 앞에 페이지 브레이크


@dataclass(frozen=True)
class IrDocument:
    blocks: List[IrBlock] = field(default_factory=list)


# ============================================================
# header.xml 전체 정의
# ============================================================

@dataclass(frozen=True)
class IrBinaryItem:
    """바이너리 아이템 (이미지 등)"""
    id: str  # image1, image2, ...
    href: str  # BinData/image1.png
    media_type: str  # image/png, image/jpeg
    is_embedded: bool = True


@dataclass(frozen=True)
class IrStyleDef:
    """스타일 정의"""
    id: int
    type: str = "PARA"  # PARA, CHAR
    name: str = ""
    eng_name: str = ""
    para_pr_id_ref: int = 0
    char_pr_id_ref: int = 0
    next_style_id_ref: int = 0
    lang_id: int = 1042  # 한국어


@dataclass(frozen=True)
class IrTabItem:
    """탭 정의"""
    pos: int = 0
    type: str = "LEFT"  # LEFT, CENTER, RIGHT, DECIMAL
    leader: str = "NONE"


@dataclass(frozen=True)
class IrTabPrDef:
    """탭 속성 정의"""
    id: int
    auto_tab_left: bool = False
    auto_tab_right: bool = False
    tabs: List[IrTabItem] = field(default_factory=list)


@dataclass(frozen=True)
class IrNumberingDef:
    """번호매기기 정의"""
    id: int
    start: int = 1
    levels: List[str] = field(default_factory=list)  # level별 형식


@dataclass(frozen=True)
class IrBulletDef:
    """글머리 기호 정의"""
    id: int
    char: str = "●"
    char_pr_id_ref: int = 0


@dataclass(frozen=True)
class IrHeaderXmlDef:
    """header.xml 전체 정의 (HWPX 문서 스타일)"""
    version: str = "1.5"
    sec_cnt: int = 1
    # 시작 번호
    begin_page: int = 1
    begin_footnote: int = 1
    begin_endnote: int = 1
    begin_pic: int = 1
    begin_tbl: int = 1
    begin_equation: int = 1
    # 폰트
    font_faces: List[IrFontFace] = field(default_factory=list)
    # 테두리/채우기
    border_fills: List[IrBorderFillDef] = field(default_factory=list)
    # 문자 속성
    char_properties: List[IrCharPrDef] = field(default_factory=list)
    # 탭 속성
    tab_properties: List[IrTabPrDef] = field(default_factory=list)
    # 번호매기기
    numberings: List[IrNumberingDef] = field(default_factory=list)
    # 글머리 기호
    bullets: List[IrBulletDef] = field(default_factory=list)
    # 단락 속성
    para_properties: List[IrParaPrDef] = field(default_factory=list)
    # 스타일
    styles: List[IrStyleDef] = field(default_factory=list)
    # 바이너리 아이템
    binary_items: List[IrBinaryItem] = field(default_factory=list)
    # 원본 XML (100% 라운드트립용)
    raw_xml: Optional[bytes] = None


# ============================================================
# content.hpf (패키지 매니페스트) 정의
# ============================================================

@dataclass(frozen=True)
class IrDocumentMeta:
    """문서 메타데이터"""
    title: str = ""
    language: str = "ko"
    creator: str = ""
    subject: str = ""
    description: str = ""
    last_saved_by: str = ""
    created_date: str = ""
    modified_date: str = ""
    date: str = ""
    keyword: str = ""


@dataclass(frozen=True)
class IrManifestItem:
    """매니페스트 아이템"""
    id: str
    href: str
    media_type: str
    is_embedded: bool = True


@dataclass(frozen=True)
class IrSpineItem:
    """스파인 아이템 (읽기 순서)"""
    idref: str
    linear: bool = True


@dataclass(frozen=True)
class IrContentHpf:
    """content.hpf 전체 정의 (HWPX 패키지 매니페스트)"""
    metadata: IrDocumentMeta = field(default_factory=IrDocumentMeta)
    manifest_items: List[IrManifestItem] = field(default_factory=list)
    spine_items: List[IrSpineItem] = field(default_factory=list)
    # 원본 XML (100% 라운드트립용)
    raw_xml: Optional[bytes] = None


# ============================================================
# settings.xml 정의
# ============================================================

@dataclass(frozen=True)
class IrCaretPosition:
    """캐럿 위치"""
    list_id_ref: int = 0
    para_id_ref: int = 0
    pos: int = 0


@dataclass(frozen=True)
class IrSettings:
    """settings.xml 전체 정의"""
    caret_position: Optional[IrCaretPosition] = None
    # 기타 설정들
    raw_xml: Optional[bytes] = None


# ============================================================
# version.xml 정의
# ============================================================

@dataclass(frozen=True)
class IrVersion:
    """version.xml 전체 정의"""
    target_application: str = "WORDPROCESSOR"
    major: int = 5
    minor: int = 1
    micro: int = 1
    build_number: int = 0
    os: int = 10
    xml_version: str = "1.5"
    application: str = "Hancom Office Hangul"
    app_version: str = ""
    raw_xml: Optional[bytes] = None


# ============================================================
# memoExtended.xml 정의
# ============================================================

@dataclass(frozen=True)
class IrMemoItem:
    """메모 아이템"""
    id: int
    parent_id: int


@dataclass(frozen=True)
class IrMemoExtended:
    """memoExtended.xml 전체 정의"""
    memos: List[IrMemoItem] = field(default_factory=list)
    raw_xml: Optional[bytes] = None


# ============================================================
# META-INF 정의
# ============================================================

@dataclass(frozen=True)
class IrRootFile:
    """루트 파일 참조"""
    full_path: str
    media_type: str


@dataclass(frozen=True)
class IrContainerXml:
    """META-INF/container.xml 정의"""
    root_files: List[IrRootFile] = field(default_factory=list)
    raw_xml: Optional[bytes] = None


@dataclass(frozen=True)
class IrContainerRdf:
    """META-INF/container.rdf 정의"""
    raw_xml: Optional[bytes] = None  # RDF는 복잡하므로 raw_xml만 사용


@dataclass(frozen=True)
class IrManifestXml:
    """META-INF/manifest.xml 정의"""
    raw_xml: Optional[bytes] = None  # 보통 비어있음
