"""pdf2hwpx MCP 서버 - HWPX 편집 전체 기능"""

import asyncio
import base64
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

from pdf2hwpx import Pdf2Hwpx


# MCP 서버 인스턴스
server = Server("pdf2hwpx")


# =============================================================================
# Tool Definitions
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """사용 가능한 도구 목록"""
    return [
        # =====================================================================
        # PDF 변환
        # =====================================================================
        Tool(
            name="convert_pdf_to_hwpx",
            description="PDF 파일을 HWPX (한글) 파일로 변환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "변환할 PDF 파일 경로",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 HWPX 파일 경로 (옵션, 기본: PDF 파일명.hwpx)",
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["pymupdf", "cloud", "openai", "vllm", "mineru", "gemini", "openrouter"],
                        "description": "PDF 파싱 백엔드 (기본: pymupdf)",
                        "default": "pymupdf",
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="convert_pdf_bytes_to_hwpx",
            description="Base64 인코딩된 PDF 바이트를 HWPX 바이트로 변환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_base64": {
                        "type": "string",
                        "description": "Base64 인코딩된 PDF 데이터",
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["pymupdf", "cloud", "openai", "vllm", "mineru", "gemini", "openrouter"],
                        "description": "PDF 파싱 백엔드 (기본: pymupdf)",
                        "default": "pymupdf",
                    },
                },
                "required": ["pdf_base64"],
            },
        ),
        # =====================================================================
        # HWPX 정보 조회
        # =====================================================================
        Tool(
            name="get_hwpx_info",
            description="HWPX 파일의 정보를 가져옵니다 (단락 수, 테이블 수, 이미지 수, 추정 페이지 수 등).",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "정보를 가져올 HWPX 파일 경로",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        Tool(
            name="get_hwpx_text",
            description="HWPX 파일의 전체 텍스트를 추출합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "텍스트를 추출할 HWPX 파일 경로",
                    },
                    "page": {
                        "type": "integer",
                        "description": "특정 페이지만 추출 (옵션, 없으면 전체)",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        Tool(
            name="get_hwpx_paragraph",
            description="HWPX 파일의 특정 단락(들)을 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "단락 인덱스 (0-based)",
                    },
                    "start": {
                        "type": "integer",
                        "description": "시작 인덱스 (범위 조회시)",
                    },
                    "end": {
                        "type": "integer",
                        "description": "끝 인덱스 (범위 조회시, exclusive)",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        Tool(
            name="get_hwpx_tables",
            description="HWPX 파일의 테이블 정보를 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "HWPX 파일 경로",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        Tool(
            name="get_hwpx_images",
            description="HWPX 파일의 이미지 정보를 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "HWPX 파일 경로",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        Tool(
            name="find_page_breaks",
            description="HWPX 파일의 페이지 브레이크 위치를 찾습니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "HWPX 파일 경로",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        # =====================================================================
        # 검색
        # =====================================================================
        Tool(
            name="search_hwpx",
            description="HWPX 파일에서 텍스트를 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "검색할 HWPX 파일 경로",
                    },
                    "query": {
                        "type": "string",
                        "description": "검색할 텍스트",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "대소문자 구분 여부 (기본: false)",
                        "default": False,
                    },
                },
                "required": ["hwpx_path", "query"],
            },
        ),
        Tool(
            name="search_hwpx_regex",
            description="HWPX 파일에서 정규식으로 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "검색할 HWPX 파일 경로",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "정규식 패턴",
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "대소문자 무시 여부 (기본: false)",
                        "default": False,
                    },
                },
                "required": ["hwpx_path", "pattern"],
            },
        ),
        # =====================================================================
        # 텍스트 편집
        # =====================================================================
        Tool(
            name="replace_text",
            description="HWPX 파일의 텍스트를 치환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "찾을 텍스트",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "바꿀 텍스트",
                    },
                    "count": {
                        "type": "integer",
                        "description": "최대 치환 횟수 (-1이면 전체, 기본: -1)",
                        "default": -1,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션, 기본: 원본 파일 덮어쓰기)",
                    },
                },
                "required": ["hwpx_path", "old_text", "new_text"],
            },
        ),
        Tool(
            name="set_paragraph_text",
            description="HWPX 파일의 특정 단락 텍스트를 교체합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "단락 인덱스 (0-based)",
                    },
                    "text": {
                        "type": "string",
                        "description": "새 텍스트",
                    },
                    "char_style_id": {
                        "type": "integer",
                        "description": "문자 스타일 ID (기본: 0)",
                        "default": 0,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "index", "text"],
            },
        ),
        # =====================================================================
        # 단락 삽입/삭제
        # =====================================================================
        Tool(
            name="insert_paragraph",
            description="HWPX 파일에 새 단락을 삽입합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "text": {
                        "type": "string",
                        "description": "삽입할 텍스트",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["before", "after", "end"],
                        "description": "삽입 위치 (before: 단락 앞, after: 단락 뒤, end: 문서 끝)",
                        "default": "end",
                    },
                    "index": {
                        "type": "integer",
                        "description": "기준 단락 인덱스 (position이 before/after일 때 필수)",
                    },
                    "para_style_id": {
                        "type": "integer",
                        "description": "단락 스타일 ID (기본: 0)",
                        "default": 0,
                    },
                    "char_style_id": {
                        "type": "integer",
                        "description": "문자 스타일 ID (기본: 0)",
                        "default": 0,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "text"],
            },
        ),
        Tool(
            name="delete_paragraph",
            description="HWPX 파일의 단락을 삭제합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "삭제할 단락 인덱스",
                    },
                    "start": {
                        "type": "integer",
                        "description": "삭제 시작 인덱스 (범위 삭제시)",
                    },
                    "end": {
                        "type": "integer",
                        "description": "삭제 끝 인덱스 (범위 삭제시, exclusive)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path"],
            },
        ),
        # =====================================================================
        # 단락 복사/이동
        # =====================================================================
        Tool(
            name="copy_paragraph",
            description="HWPX 파일의 단락을 복사합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "from_index": {
                        "type": "integer",
                        "description": "복사할 단락 인덱스",
                    },
                    "to_index": {
                        "type": "integer",
                        "description": "복사 대상 위치 인덱스",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "from_index", "to_index"],
            },
        ),
        Tool(
            name="move_paragraph",
            description="HWPX 파일의 단락을 이동합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "from_index": {
                        "type": "integer",
                        "description": "이동할 단락 인덱스",
                    },
                    "to_index": {
                        "type": "integer",
                        "description": "이동 대상 위치 인덱스",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "from_index", "to_index"],
            },
        ),
        # =====================================================================
        # 스타일 변경
        # =====================================================================
        Tool(
            name="set_paragraph_style",
            description="HWPX 파일의 단락 스타일을 변경합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "단락 인덱스",
                    },
                    "para_style_id": {
                        "type": "integer",
                        "description": "단락 스타일 ID",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "index", "para_style_id"],
            },
        ),
        Tool(
            name="set_char_style",
            description="HWPX 파일의 단락 내 문자 스타일을 변경합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "단락 인덱스",
                    },
                    "char_style_id": {
                        "type": "integer",
                        "description": "문자 스타일 ID",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "index", "char_style_id"],
            },
        ),
        # =====================================================================
        # 페이지/열 브레이크
        # =====================================================================
        Tool(
            name="set_page_break",
            description="HWPX 파일의 단락에 페이지 브레이크를 설정합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "단락 인덱스",
                    },
                    "enable": {
                        "type": "boolean",
                        "description": "페이지 브레이크 활성화 여부 (기본: true)",
                        "default": True,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "index"],
            },
        ),
        Tool(
            name="set_column_break",
            description="HWPX 파일의 단락에 열 브레이크를 설정합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "index": {
                        "type": "integer",
                        "description": "단락 인덱스",
                    },
                    "enable": {
                        "type": "boolean",
                        "description": "열 브레이크 활성화 여부 (기본: true)",
                        "default": True,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "index"],
            },
        ),
        # =====================================================================
        # 테이블 삽입
        # =====================================================================
        Tool(
            name="insert_table",
            description="HWPX 파일에 테이블을 삽입합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "after_index": {
                        "type": "integer",
                        "description": "삽입 위치 (이 단락 뒤에 삽입)",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "행 수",
                    },
                    "cols": {
                        "type": "integer",
                        "description": "열 수",
                    },
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "description": "테이블 데이터 (2D 문자열 배열, 옵션)",
                    },
                    "col_widths": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "열 너비 배열 (HWPUNIT, 옵션)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "after_index", "rows", "cols"],
            },
        ),
        # =====================================================================
        # 이미지 삽입
        # =====================================================================
        Tool(
            name="insert_image",
            description="HWPX 파일에 이미지를 삽입합니다. 이미지 바이너리는 별도로 BinData/에 추가해야 합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hwpx_path": {
                        "type": "string",
                        "description": "수정할 HWPX 파일 경로",
                    },
                    "after_index": {
                        "type": "integer",
                        "description": "삽입 위치 (이 단락 뒤에 삽입)",
                    },
                    "binary_item_id": {
                        "type": "string",
                        "description": "BinData 항목 ID (예: 'IMG1')",
                    },
                    "width": {
                        "type": "integer",
                        "description": "너비 (HWPUNIT)",
                    },
                    "height": {
                        "type": "integer",
                        "description": "높이 (HWPUNIT)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "출력 파일 경로 (옵션)",
                    },
                },
                "required": ["hwpx_path", "after_index", "binary_item_id", "width", "height"],
            },
        ),
    ]


# =============================================================================
# Tool Implementations
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """도구 실행"""
    try:
        # 도구 이름을 함수에 매핑
        tool_handlers = {
            "convert_pdf_to_hwpx": handle_convert_pdf_to_hwpx,
            "convert_pdf_bytes_to_hwpx": handle_convert_pdf_bytes_to_hwpx,
            "get_hwpx_info": handle_get_hwpx_info,
            "get_hwpx_text": handle_get_hwpx_text,
            "get_hwpx_paragraph": handle_get_hwpx_paragraph,
            "get_hwpx_tables": handle_get_hwpx_tables,
            "get_hwpx_images": handle_get_hwpx_images,
            "find_page_breaks": handle_find_page_breaks,
            "search_hwpx": handle_search_hwpx,
            "search_hwpx_regex": handle_search_hwpx_regex,
            "replace_text": handle_replace_text,
            "set_paragraph_text": handle_set_paragraph_text,
            "insert_paragraph": handle_insert_paragraph,
            "delete_paragraph": handle_delete_paragraph,
            "copy_paragraph": handle_copy_paragraph,
            "move_paragraph": handle_move_paragraph,
            "set_paragraph_style": handle_set_paragraph_style,
            "set_char_style": handle_set_char_style,
            "set_page_break": handle_set_page_break,
            "set_column_break": handle_set_column_break,
            "insert_table": handle_insert_table,
            "insert_image": handle_insert_image,
        }

        handler = tool_handlers.get(name)
        if handler:
            return await handler(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _load_section_xml(hwpx_path: Path) -> bytes:
    """HWPX 파일에서 section0.xml 로드"""
    with zipfile.ZipFile(hwpx_path, "r") as zf:
        return zf.read("Contents/section0.xml")


def _save_hwpx(hwpx_path: Path, output_path: Path, section_xml: bytes):
    """수정된 section XML로 HWPX 파일 저장"""
    with zipfile.ZipFile(hwpx_path, "r") as zf_in:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.namelist():
                if item == "Contents/section0.xml":
                    zf_out.writestr(item, section_xml)
                else:
                    zf_out.writestr(item, zf_in.read(item))


def _get_searcher(hwpx_path: Path):
    """HwpxSearcher 인스턴스 생성"""
    from pdf2hwpx.hwpx_ir.components.query import HwpxSearcher
    section_xml = _load_section_xml(hwpx_path)
    return HwpxSearcher(section_xml)


def _get_editor(hwpx_path: Path):
    """HwpxEditor 인스턴스 생성"""
    from pdf2hwpx.hwpx_ir.components.query import HwpxEditor
    section_xml = _load_section_xml(hwpx_path)
    return HwpxEditor(section_xml)


def _check_file_exists(path: Path) -> Optional[CallToolResult]:
    """파일 존재 여부 확인"""
    if not path.exists():
        return CallToolResult(
            content=[TextContent(type="text", text=f"파일을 찾을 수 없습니다: {path}")],
            isError=True,
        )
    return None


# =============================================================================
# PDF 변환 Handlers
# =============================================================================

async def handle_convert_pdf_to_hwpx(args: dict) -> CallToolResult:
    """PDF를 HWPX로 변환"""
    pdf_path = Path(args["pdf_path"])
    backend = args.get("backend", "pymupdf")
    output_path = args.get("output_path")

    if error := _check_file_exists(pdf_path):
        return error

    if output_path is None:
        output_path = pdf_path.with_suffix(".hwpx")
    else:
        output_path = Path(output_path)

    converter = Pdf2Hwpx(backend=backend)
    result = converter.convert(pdf_path, output_path)

    return CallToolResult(
        content=[TextContent(type="text", text=f"변환 완료: {result}")]
    )


async def handle_convert_pdf_bytes_to_hwpx(args: dict) -> CallToolResult:
    """PDF 바이트를 HWPX 바이트로 변환"""
    pdf_base64 = args["pdf_base64"]
    backend = args.get("backend", "pymupdf")

    pdf_bytes = base64.b64decode(pdf_base64)
    converter = Pdf2Hwpx(backend=backend)
    hwpx_bytes = converter.convert_bytes(pdf_bytes)
    hwpx_base64 = base64.b64encode(hwpx_bytes).decode("utf-8")

    return CallToolResult(
        content=[TextContent(type="text", text=hwpx_base64)]
    )


# =============================================================================
# 정보 조회 Handlers
# =============================================================================

async def handle_get_hwpx_info(args: dict) -> CallToolResult:
    """HWPX 파일 정보"""
    hwpx_path = Path(args["hwpx_path"])

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)

    with zipfile.ZipFile(hwpx_path, "r") as zf:
        file_list = zf.namelist()

    info = {
        "파일": str(hwpx_path),
        "단락 수": searcher.get_paragraph_count(),
        "테이블 수": len(searcher.get_tables_info()),
        "이미지 수": len(searcher.get_images_info()),
        "추정 페이지 수": searcher.get_page_count_estimate(),
        "포함된 파일": file_list,
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(info, ensure_ascii=False, indent=2))]
    )


async def handle_get_hwpx_text(args: dict) -> CallToolResult:
    """HWPX 전체/페이지별 텍스트 추출"""
    hwpx_path = Path(args["hwpx_path"])
    page = args.get("page")

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)

    if page is not None:
        text = searcher.get_text_by_page(page)
        header = f"=== 페이지 {page} ===\n"
    else:
        text = searcher.get_all_text()
        header = ""

    return CallToolResult(
        content=[TextContent(type="text", text=header + text)]
    )


async def handle_get_hwpx_paragraph(args: dict) -> CallToolResult:
    """HWPX 단락 조회"""
    hwpx_path = Path(args["hwpx_path"])
    index = args.get("index")
    start = args.get("start")
    end = args.get("end")

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)

    if index is not None:
        para = searcher.get_paragraph(index)
        if para is None:
            return CallToolResult(
                content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
                isError=True,
            )
        result = {
            "index": para.index,
            "paragraph_id": para.paragraph_id,
            "text": para.text,
            "para_style_id": para.para_pr_id,
            "char_style_ids": para.char_pr_ids,
            "has_table": para.has_table,
            "has_image": para.has_image,
            "page_estimate": para.page_estimate,
        }
    elif start is not None and end is not None:
        paras = searcher.get_paragraphs_range(start, end)
        result = [{
            "index": p.index,
            "text": p.text[:100] + "..." if len(p.text) > 100 else p.text,
            "has_table": p.has_table,
            "has_image": p.has_image,
        } for p in paras]
    else:
        return CallToolResult(
            content=[TextContent(type="text", text="index 또는 start/end를 지정해주세요.")],
            isError=True,
        )

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    )


async def handle_get_hwpx_tables(args: dict) -> CallToolResult:
    """HWPX 테이블 정보"""
    hwpx_path = Path(args["hwpx_path"])

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)
    tables = searcher.get_tables_info()

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(tables, ensure_ascii=False, indent=2))]
    )


async def handle_get_hwpx_images(args: dict) -> CallToolResult:
    """HWPX 이미지 정보"""
    hwpx_path = Path(args["hwpx_path"])

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)
    images = searcher.get_images_info()

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(images, ensure_ascii=False, indent=2))]
    )


async def handle_find_page_breaks(args: dict) -> CallToolResult:
    """페이지 브레이크 찾기"""
    hwpx_path = Path(args["hwpx_path"])

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)
    breaks = searcher.find_page_breaks()

    result = [{
        "paragraph_index": b.paragraph_index,
        "paragraph_id": b.paragraph_id,
        "break_type": b.break_type,
        "text_preview": b.text_preview,
    } for b in breaks]

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    )


# =============================================================================
# 검색 Handlers
# =============================================================================

async def handle_search_hwpx(args: dict) -> CallToolResult:
    """HWPX에서 텍스트 검색"""
    hwpx_path = Path(args["hwpx_path"])
    query = args["query"]
    case_sensitive = args.get("case_sensitive", False)

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)
    results = searcher.search(query, case_sensitive=case_sensitive)

    if not results:
        return CallToolResult(
            content=[TextContent(type="text", text="검색 결과가 없습니다.")]
        )

    output = f"검색 결과: {len(results)}개\n\n"
    for i, r in enumerate(results[:20]):
        output += f"{i+1}. 단락 {r.paragraph_index} (페이지 ~{r.page_estimate}): {r.context}\n"

    if len(results) > 20:
        output += f"\n... 외 {len(results) - 20}개"

    return CallToolResult(
        content=[TextContent(type="text", text=output)]
    )


async def handle_search_hwpx_regex(args: dict) -> CallToolResult:
    """HWPX에서 정규식 검색"""
    import re

    hwpx_path = Path(args["hwpx_path"])
    pattern = args["pattern"]
    ignore_case = args.get("ignore_case", False)

    if error := _check_file_exists(hwpx_path):
        return error

    searcher = _get_searcher(hwpx_path)
    flags = re.IGNORECASE if ignore_case else 0
    results = searcher.search_regex(pattern, flags=flags)

    if not results:
        return CallToolResult(
            content=[TextContent(type="text", text="검색 결과가 없습니다.")]
        )

    output = f"검색 결과: {len(results)}개\n\n"
    for i, r in enumerate(results[:20]):
        output += f"{i+1}. 단락 {r.paragraph_index}: {r.context}\n"

    if len(results) > 20:
        output += f"\n... 외 {len(results) - 20}개"

    return CallToolResult(
        content=[TextContent(type="text", text=output)]
    )


# =============================================================================
# 텍스트 편집 Handlers
# =============================================================================

async def handle_replace_text(args: dict) -> CallToolResult:
    """텍스트 치환"""
    hwpx_path = Path(args["hwpx_path"])
    old_text = args["old_text"]
    new_text = args["new_text"]
    count = args.get("count", -1)
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    replaced = editor.replace_text(old_text, new_text, count=count)

    if replaced == 0:
        return CallToolResult(
            content=[TextContent(type="text", text=f"'{old_text}'를 찾을 수 없습니다.")]
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"{replaced}개 치환됨. 저장됨: {output_path}")]
    )


async def handle_set_paragraph_text(args: dict) -> CallToolResult:
    """단락 텍스트 교체"""
    hwpx_path = Path(args["hwpx_path"])
    index = args["index"]
    text = args["text"]
    char_style_id = args.get("char_style_id", 0)
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.set_paragraph_text(index, text, char_pr_id=char_style_id)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {index} 텍스트 교체됨. 저장됨: {output_path}")]
    )


# =============================================================================
# 단락 삽입/삭제 Handlers
# =============================================================================

async def handle_insert_paragraph(args: dict) -> CallToolResult:
    """단락 삽입"""
    hwpx_path = Path(args["hwpx_path"])
    text = args["text"]
    position = args.get("position", "end")
    index = args.get("index")
    para_style_id = args.get("para_style_id", 0)
    char_style_id = args.get("char_style_id", 0)
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)

    if position == "end":
        success = editor.append_paragraph(text, para_pr_id=para_style_id, char_pr_id=char_style_id)
        pos_desc = "문서 끝"
    elif position == "after":
        if index is None:
            return CallToolResult(
                content=[TextContent(type="text", text="position='after'일 때 index가 필요합니다.")],
                isError=True,
            )
        success = editor.insert_paragraph_after(index, text, para_pr_id=para_style_id, char_pr_id=char_style_id)
        pos_desc = f"단락 {index} 뒤"
    elif position == "before":
        if index is None:
            return CallToolResult(
                content=[TextContent(type="text", text="position='before'일 때 index가 필요합니다.")],
                isError=True,
            )
        success = editor.insert_paragraph_before(index, text, para_pr_id=para_style_id, char_pr_id=char_style_id)
        pos_desc = f"단락 {index} 앞"
    else:
        return CallToolResult(
            content=[TextContent(type="text", text=f"알 수 없는 position: {position}")],
            isError=True,
        )

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text="단락 삽입 실패")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"{pos_desc}에 단락 삽입됨. 저장됨: {output_path}")]
    )


async def handle_delete_paragraph(args: dict) -> CallToolResult:
    """단락 삭제"""
    hwpx_path = Path(args["hwpx_path"])
    index = args.get("index")
    start = args.get("start")
    end = args.get("end")
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)

    if index is not None:
        success = editor.delete_paragraph(index)
        if not success:
            return CallToolResult(
                content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
                isError=True,
            )
        msg = f"단락 {index} 삭제됨"
    elif start is not None and end is not None:
        deleted = editor.delete_paragraphs_range(start, end)
        msg = f"{deleted}개 단락 삭제됨 ({start}~{end-1})"
    else:
        return CallToolResult(
            content=[TextContent(type="text", text="index 또는 start/end를 지정해주세요.")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"{msg}. 저장됨: {output_path}")]
    )


# =============================================================================
# 단락 복사/이동 Handlers
# =============================================================================

async def handle_copy_paragraph(args: dict) -> CallToolResult:
    """단락 복사"""
    hwpx_path = Path(args["hwpx_path"])
    from_index = args["from_index"]
    to_index = args["to_index"]
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.copy_paragraph(from_index, to_index)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text="단락 복사 실패")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {from_index} → {to_index} 복사됨. 저장됨: {output_path}")]
    )


async def handle_move_paragraph(args: dict) -> CallToolResult:
    """단락 이동"""
    hwpx_path = Path(args["hwpx_path"])
    from_index = args["from_index"]
    to_index = args["to_index"]
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.move_paragraph(from_index, to_index)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text="단락 이동 실패")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {from_index} → {to_index} 이동됨. 저장됨: {output_path}")]
    )


# =============================================================================
# 스타일 변경 Handlers
# =============================================================================

async def handle_set_paragraph_style(args: dict) -> CallToolResult:
    """단락 스타일 변경"""
    hwpx_path = Path(args["hwpx_path"])
    index = args["index"]
    para_style_id = args["para_style_id"]
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.set_paragraph_style(index, para_style_id)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {index} 스타일 → {para_style_id}. 저장됨: {output_path}")]
    )


async def handle_set_char_style(args: dict) -> CallToolResult:
    """문자 스타일 변경"""
    hwpx_path = Path(args["hwpx_path"])
    index = args["index"]
    char_style_id = args["char_style_id"]
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.set_char_style(index, char_style_id)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {index} 문자 스타일 → {char_style_id}. 저장됨: {output_path}")]
    )


# =============================================================================
# 페이지/열 브레이크 Handlers
# =============================================================================

async def handle_set_page_break(args: dict) -> CallToolResult:
    """페이지 브레이크 설정"""
    hwpx_path = Path(args["hwpx_path"])
    index = args["index"]
    enable = args.get("enable", True)
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.set_page_break(index, enable=enable)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    status = "활성화" if enable else "비활성화"
    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {index} 페이지 브레이크 {status}. 저장됨: {output_path}")]
    )


async def handle_set_column_break(args: dict) -> CallToolResult:
    """열 브레이크 설정"""
    hwpx_path = Path(args["hwpx_path"])
    index = args["index"]
    enable = args.get("enable", True)
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.set_column_break(index, enable=enable)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text=f"단락 {index}를 찾을 수 없습니다.")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    status = "활성화" if enable else "비활성화"
    return CallToolResult(
        content=[TextContent(type="text", text=f"단락 {index} 열 브레이크 {status}. 저장됨: {output_path}")]
    )


# =============================================================================
# 테이블/이미지 삽입 Handlers
# =============================================================================

async def handle_insert_table(args: dict) -> CallToolResult:
    """테이블 삽입"""
    hwpx_path = Path(args["hwpx_path"])
    after_index = args["after_index"]
    rows = args["rows"]
    cols = args["cols"]
    data = args.get("data")
    col_widths = args.get("col_widths")
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.insert_table_after(
        after_index, rows, cols, data=data, col_widths=col_widths
    )

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text="테이블 삽입 실패")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(type="text", text=f"{rows}x{cols} 테이블 삽입됨 (단락 {after_index} 뒤). 저장됨: {output_path}")]
    )


async def handle_insert_image(args: dict) -> CallToolResult:
    """이미지 삽입"""
    hwpx_path = Path(args["hwpx_path"])
    after_index = args["after_index"]
    binary_item_id = args["binary_item_id"]
    width = args["width"]
    height = args["height"]
    output_path = Path(args.get("output_path", str(hwpx_path)))

    if error := _check_file_exists(hwpx_path):
        return error

    editor = _get_editor(hwpx_path)
    success = editor.insert_image_after(after_index, binary_item_id, width, height)

    if not success:
        return CallToolResult(
            content=[TextContent(type="text", text="이미지 삽입 실패")],
            isError=True,
        )

    _save_hwpx(hwpx_path, output_path, editor.to_bytes())

    return CallToolResult(
        content=[TextContent(
            type="text",
            text=f"이미지 삽입됨 (단락 {after_index} 뒤, {binary_item_id}). 저장됨: {output_path}\n"
                 f"Note: 이미지 바이너리는 BinData/에 별도로 추가해야 합니다."
        )]
    )


# =============================================================================
# Main
# =============================================================================

async def main():
    """MCP 서버 실행"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
